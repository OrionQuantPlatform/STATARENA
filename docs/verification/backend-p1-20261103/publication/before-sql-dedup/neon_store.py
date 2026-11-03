"""Shared ingestion store. No repository data directory or Git publication."""

import os, json, gzip, hashlib, base64, re
import boto3, psycopg
from botocore.config import Config
from psycopg.types.json import Jsonb


def canonical(params=None):
    return json.dumps(
        params or {}, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


class Store:
    def __init__(self):
        self.db = psycopg.connect(
            os.environ["NEON_DATABASE_URL"],
            autocommit=True,
            application_name="statarena-ingestion",
            options="-c statement_timeout=120000",
        )
        try:
            self.db.execute("select storage_key from statarena.objects limit 0")
            self.db.execute("select storage_key from statarena.object_storage limit 0")
        except (psycopg.errors.UndefinedColumn, psycopg.errors.UndefinedTable) as exc:
            self.db.close()
            raise RuntimeError("Apply 002_immutable_storage.sql before starting this writer") from exc
        self._storage_db = None
        # A forced refresh is performed at most once in each worker run.
        self.refresh_since = self.db.execute("select clock_timestamp()").fetchone()[0]
        self.s3 = boto3.client(
            "s3",
            endpoint_url=os.environ["NEON_STORAGE_ENDPOINT"],
            region_name=os.environ.get("NEON_STORAGE_REGION", "us-east-2"),
            aws_access_key_id=os.environ["NEON_STORAGE_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["NEON_STORAGE_SECRET_ACCESS_KEY"],
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
                request_checksum_calculation="when_required",
                response_checksum_validation="when_required",
                retries={"max_attempts": 4},
            ),
        )
        self.bucket = os.environ.get("NEON_STORAGE_BUCKET", "statarena-data")
        self.queue = {}

    def bytes(self, path):
        row = self.db.execute(
            "select body,sha256,size,storage_key from statarena.objects where path=%s", (path,)
        ).fetchone()
        if not row:
            raise FileNotFoundError(path)
        body = (
            bytes(row[0])
            if row[0] is not None
            else self.s3.get_object(Bucket=self.bucket, Key=row[3] or "data/" + path)[
                "Body"
            ].read()
        )
        if hashlib.sha256(body).digest() != bytes(row[1]) or len(body) != row[2]:
            raise ValueError("Neon object checksum mismatch: " + path)
        return body

    def json(self, path):
        b = self.bytes(path)
        return json.loads(gzip.decompress(b) if path.endswith(".gz") else b)

    def _storage_ledger(self):
        # S3 writes survive a surrounding SQL rollback. Their reservations must too.
        if self._storage_db is None:
            self._storage_db = psycopg.connect(
                os.environ["NEON_DATABASE_URL"],
                autocommit=True,
                application_name="statarena-storage-ledger",
                options="-c statement_timeout=120000",
            )
        return self._storage_db

    def _reserve_storage(self, key, digest, size, etag, verified=False):
        ledger = self._storage_ledger()
        with ledger.transaction():
            # The main publication connection may hold 97813003. A distinct lock
            # serializes admission without deadlocking that outer transaction.
            ledger.execute("select pg_advisory_xact_lock(97813004)")
            if not key.startswith("data/versions/"):
                # These bytes already exist: registering a legacy key is accounting,
                # not a request to upload an additional physical copy.
                ledger.execute(
                    "insert into statarena.object_storage(storage_key,sha256,size,etag,state) values(%s,%s,%s,%s,%s) on conflict(storage_key) do update set sha256=excluded.sha256,size=greatest(statarena.object_storage.size,excluded.size),etag=excluded.etag,state=excluded.state,updated_at=now()",
                    (key, digest, size, etag, "verified" if verified else "reserved"),
                )
                return verified
            row = ledger.execute(
                "select sha256,size,etag,state from statarena.object_storage where storage_key=%s",
                (key,),
            ).fetchone()
            if row:
                if bytes(row[0]) != digest or row[1] != size or row[2] != etag:
                    raise ValueError("Immutable storage key collision")
                # Verified deduplication and retries of an already budgeted upload
                # consume no additional reservation, even at the capacity limit.
                return row[3] == "verified"
            used = self._storage_bytes(ledger)
            sql_bytes = ledger.execute(
                "select pg_database_size(current_database())"
            ).fetchone()[0]
            if used + size > 4_750_000_000 or sql_bytes > 900_000_000:
                raise RuntimeError(
                    f"Neon capacity limit: object bytes {used}+{size}; SQL bytes {sql_bytes}"
                )
            ledger.execute(
                "insert into statarena.object_storage(storage_key,sha256,size,etag,state) values(%s,%s,%s,%s,%s)",
                (key, digest, size, etag, "verified" if verified else "reserved"),
            )
            return verified

    @staticmethod
    def _storage_bytes(connection):
        return int(connection.execute(
            "select coalesce((select sum(size) from statarena.object_storage),0) + coalesce((select sum(greatest(o.size-coalesce(s.size,0),0)) from statarena.objects o left join statarena.object_storage s on s.storage_key='data/'||o.path where o.storage_key is null),0)"
        ).fetchone()[0])

    def storage_bytes(self):
        """Conservative physical usage, including rollback/failed-upload reservations."""
        return self._storage_bytes(self.db)

    def _upload_immutable(self, body, content_type):
        digest = hashlib.sha256(body).digest()
        etag = hashlib.md5(body).hexdigest()
        key = "data/versions/" + digest.hex()
        if self._reserve_storage(key, digest, len(body), etag):
            return key
        result = self.s3.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=body,
            ContentMD5=base64.b64encode(bytes.fromhex(etag)).decode(),
            ContentType=content_type,
        )
        if result["ETag"].strip('"') != etag:
            raise ValueError("Neon server MD5 mismatch")
        self._storage_ledger().execute(
            "update statarena.object_storage set state='verified',updated_at=now() where storage_key=%s",
            (key,),
        )
        return key

    def put(self, path, body, content_type="application/json", hot=False):
        digest = hashlib.sha256(body).digest()
        etag = hashlib.md5(body).hexdigest()
        old = self.db.execute(
            "select sha256,size,etag,content_type,storage_key,body is not null from statarena.objects where path=%s", (path,)
        ).fetchone()
        if old and bytes(old[0]) == digest:
            return False
        if old and re.search(r"(?:-|/)[a-f0-9]{24,64}\.(?:json(?:\.gz)?|webp|png|jpe?g)$", path):
            raise ValueError("Cannot replace a content-versioned public URL")
        if old:
            previous_key = old[4]
            if previous_key is None:
                previous = self.bytes(path)
                # The old legacy physical key remains in the bucket; account for it
                # separately. Inline reads do not prove its remote bytes exist.
                self._reserve_storage("data/" + path, bytes(old[0]), old[1], old[2], verified=not old[5])
                previous_key = self._upload_immutable(previous, old[3])
            archive = (
                "raw/neon/versions/"
                + bytes(old[0]).hex()
                + (".json.gz" if path.endswith(".json.gz") else os.path.splitext(path)[1])
            )
            self.db.execute(
                "insert into statarena.objects(path,size,sha256,etag,content_type,storage_key) values(%s,%s,%s,%s,%s,%s) on conflict(path) do nothing",
                (archive, old[1], old[0], old[2], old[3], previous_key),
            )
        key = self._upload_immutable(body, content_type)
        self.db.execute(
            "insert into statarena.objects(path,size,sha256,etag,body,content_type,storage_key) values(%s,%s,%s,%s,%s,%s,%s) on conflict(path) do update set size=excluded.size,sha256=excluded.sha256,etag=excluded.etag,body=excluded.body,content_type=excluded.content_type,storage_key=excluded.storage_key,updated_at=now()",
            (path, len(body), digest, etag, body if hot else None, content_type, key),
        )
        return True

    def put_json(self, path, value, hot=False):
        body = canonical(value).encode()
        body = gzip.compress(body, mtime=0) if path.endswith(".gz") else body
        self.put(
            path,
            body,
            "application/gzip" if path.endswith(".gz") else "application/json",
            hot,
        )
        return {"path": path, "sha256": hashlib.sha256(body).hexdigest()}

    def enqueue(self, endpoint, params=None, priority=3, refresh=False, force=False):
        p = canonical(params)
        key = (endpoint, p)
        old = self.queue.get(key)
        self.queue[key] = {
            "endpoint": endpoint,
            "params": p,
            "priority": min(priority, old["priority"]) if old else priority,
            "refresh": refresh or force or bool(old and old["refresh"]),
            "force": force or bool(old and old["force"]),
        }

    def flush(self):
        for refresh, force in [(False, False), (True, False), (True, True)]:
            rows = [
                {k: v for k, v in row.items() if k not in {"refresh", "force"}}
                for row in self.queue.values()
                if row["refresh"] == refresh and row["force"] == force
            ]
            if not rows:
                continue
            condition = (
                "WHERE NOT EXISTS(SELECT 1 FROM statarena.resources r WHERE r.endpoint=i.endpoint AND r.params=i.params AND r.status IN(200,400,403,404,410,422)"
                + (" AND r.updated_at >= %s" if force else " AND r.updated_at>now()-interval '6 hours'" if refresh else "")
                + ")"
            )
            self.db.execute(
                "INSERT INTO statarena.jobs(endpoint,params,priority) SELECT i.endpoint,i.params,i.priority FROM jsonb_to_recordset(%s) AS i(endpoint text,params text,priority smallint) "
                + condition
                + " ON CONFLICT(endpoint,params) DO UPDATE SET priority=least(statarena.jobs.priority,excluded.priority),state=case when %s and statarena.jobs.state!='running' then 'pending' else statarena.jobs.state end,available_at=case when %s then now() else statarena.jobs.available_at end",
                (Jsonb(rows), *([self.refresh_since] if force else []), refresh, refresh),
            )
        self.queue.clear()

    def state(self, name, value):
        self.db.execute(
            "insert into statarena.state(name,value) values(%s,%s) on conflict(name) do update set value=excluded.value,updated_at=now()",
            (name, Jsonb(value)),
        )

    def revision(self):
        self.db.execute(
            "update statarena.state set value=to_jsonb((value::text::bigint)+1),updated_at=now() where name='revision'"
        )
