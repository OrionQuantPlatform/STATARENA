"""Real SQL + real boto3/HTTP publication workflows, never production inputs."""
import argparse, hashlib, json, os, sys, threading, traceback
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, unquote
import psycopg, boto3, platform

ROOT = Path(__file__).resolve().parents[4]
baseline = os.environ.get("STATARENA_PUBLICATION_BASELINE") == "1"
frozen_source = os.environ.get("STATARENA_PUBLICATION_SOURCE")
source = Path(frozen_source) if frozen_source else Path(__file__).parent / "baseline-source" if baseline else ROOT / "dashboard/scripts"
sys.path.insert(0, str(source))
from neon_store import Store

args = argparse.ArgumentParser()
args.add_argument("--report", required=True)
args.add_argument("--phase", required=True)
a = args.parse_args()
url = os.environ["TEST_DATABASE_URL"]
assert urlparse(url).hostname == "127.0.0.1" and urlparse(url).path == "/publication_e2e"
objects, requests = {}, []
control = {"bad_etag": False, "deny_put": False}

def sha(body): return hashlib.sha256(body).hexdigest()
def md5(body): return hashlib.md5(body).hexdigest()

class S3(BaseHTTPRequestHandler):
    def log_message(self, *args): pass
    def do_PUT(self):
        key = unquote(self.path).removeprefix("/fixture/")
        body = self.rfile.read(int(self.headers["Content-Length"]))
        prior = objects.get(key)
        requests.append({"method": "PUT", "key": key, "bytes": len(body), "sha256": sha(body), "different_byte_overwrite": prior is not None and prior != body, "denied": control["deny_put"]})
        if control["deny_put"]:
            self.send_response(403); self.end_headers(); self.wfile.write(b"<Error><Code>AccessDenied</Code></Error>"); return
        objects[key] = body
        self.send_response(200)
        self.send_header("ETag", '"' + ("0" * 32 if control["bad_etag"] else md5(body)) + '"')
        self.send_header("Content-Length", "0"); self.end_headers()
    def do_GET(self):
        key = unquote(self.path).removeprefix("/fixture/")
        body = objects.get(key)
        requests.append({"method": "GET", "key": key, "bytes": len(body) if body is not None else 0})
        self.send_response(200 if body is not None else 404)
        self.send_header("Content-Length", str(len(body) if body is not None else 0))
        self.end_headers()
        if body is not None: self.wfile.write(body)

server = ThreadingHTTPServer(("127.0.0.1", 0), S3)
threading.Thread(target=server.serve_forever, daemon=True).start()
os.environ.update(NEON_DATABASE_URL=url, NEON_STORAGE_ENDPOINT=f"http://127.0.0.1:{server.server_port}", NEON_STORAGE_BUCKET="fixture", NEON_STORAGE_REGION="us-east-2", NEON_STORAGE_ACCESS_KEY_ID="fixture", NEON_STORAGE_SECRET_ACCESS_KEY="fixture")
report = {"setup": "Real PostgreSQL 18 + real psycopg and boto3 using local HTTP S3; fixed UTF-8 JSON bytes; no credentials inherited", "command": f"node docs/verification/backend-p1-20261103/publication/run.mjs {a.phase}", "expected": "PROTOCOL.md", "phase": a.phase, "cases": [], "inputs": {"v1": '{"version":1}', "v2": '{"version":2}'}, "status": "failed"}
db = psycopg.connect(url, autocommit=True)
db.execute((source / "001_neon.sql" if baseline or frozen_source else ROOT / "dashboard/backend/migrations/001_neon.sql").read_text())
migration = source / "002_immutable_storage.sql" if baseline or frozen_source else ROOT / "dashboard/backend/migrations/002_immutable_storage.sql"
report["versions"] = {"python": platform.python_version(), "boto3": boto3.__version__, "psycopg": psycopg.__version__, "postgres": db.execute("select version()").fetchone()[0]}

def check(name, expected, fn):
    start = len(requests)
    case = {"name": name, "expected": expected, "status": "failed"}
    report["cases"].append(case)
    try:
        case["actual"] = fn()
        case["status"] = "passed"
    except Exception:
        case["error"] = traceback.format_exc()
    finally:
        rows = requests[start:]
        case["operations"] = rows
        case["counts"] = {"PUT": sum(r["method"] == "PUT" for r in rows), "GET": sum(r["method"] == "GET" for r in rows), "different_byte_overwrites": sum(r.get("different_byte_overwrite", False) for r in rows)}
        control.update(bad_etag=False, deny_put=False)

def migrate():
    assert migration.exists(), "additive migration 002 required"
    # Start the additive migration against an actual legacy-shaped table with data.
    preserved = b'{"migration":"preserved"}'
    db.execute("insert into statarena.objects(path,size,sha256,etag,body) values('raw/migration-preserved.json',%s,%s,%s,%s)", (len(preserved), bytes.fromhex(sha(preserved)), md5(preserved), preserved))
    db.execute("alter table statarena.objects drop column storage_key")
    db.execute("create role fixture_ingest login password 'fixture-role-only'")
    db.execute("grant usage on schema statarena to fixture_ingest")
    db.execute("grant select,insert,update on statarena.objects to fixture_ingest")
    db.execute(migration.read_text()); db.execute(migration.read_text())
    assert db.execute("select column_name from information_schema.columns where table_schema='statarena' and table_name='objects' and column_name='storage_key'").fetchone()
    assert db.execute("select body,storage_key from statarena.objects where path='raw/migration-preserved.json'").fetchone() == (preserved, None)
    return {"applied_twice": True, "legacy_inline_bytes_preserved": True}
check("idempotent migration", "002 applies twice and exposes storage_key/ledger", migrate)
has_key = bool(db.execute("select 1 from information_schema.columns where table_schema='statarena' and table_name='objects' and column_name='storage_key'").fetchone())
store = Store()
v1, v2 = b'{"version":1}', b'{"version":2}'

def pointer(path):
    row = db.execute("select encode(sha256,'hex'),size," + ("storage_key" if has_key else "null::text") + " from statarena.objects where path=%s", (path,)).fetchone()
    return {"sha256": row[0], "size": row[1], "key": row[2] or "data/" + path}

def seed(path, body=v1, inline=False):
    objects["data/" + path] = body
    db.execute("insert into statarena.objects(path,size,sha256,etag,body) values(%s,%s,%s,%s,%s)", (path,len(body),bytes.fromhex(sha(body)),md5(body),body if inline else None))

def legacy_reads():
    for inline in [False, True]:
        path = f"raw/legacy-read-{inline}.json"
        seed(path, inline=inline)
        assert store.bytes(path) == v1
    return {"cold_and_inline": "exact bytes"}
check("legacy reads", "unchanged cold/inline legacy bytes", legacy_reads)

def visibility():
    path = "raw/publication-visible.json"
    store.put(path, v1)
    old = pointer(path)
    with store.db.transaction():
        store.put(path, v2)
        before_commit = pointer(path)
        old_readable = store.s3.get_object(Bucket=store.bucket, Key=old["key"])["Body"].read() == v1
        assert before_commit == old, "uncommitted SQL alias leaked"
    current = pointer(path)
    assert old_readable, "old physical bytes overwritten before commit"
    assert current["key"] != old["key"]
    assert store.bytes(path) == v2
    return {"old": old, "new": current, "old_version_readable": old_readable}
check("publication visibility", "old SQL/bytes during transaction; new pointer after commit", visibility)

def rollback():
    path = "raw/publication-rollback.json"
    rolled_back = b'{"rollback":true}'
    store.put(path, v1)
    old = pointer(path)
    try:
        with store.db.transaction():
            store.put(path, rolled_back)
            raise RuntimeError("fixture callback fails")
    except RuntimeError: pass
    unchanged = pointer(path) == old
    readable = store.s3.get_object(Bucket=store.bucket, Key=old["key"])["Body"].read() == v1
    assert unchanged and readable, "rollback left committed alias pointing at replaced bytes"
    assert store.bytes(path) == v1
    ledger = db.execute("select state,size from statarena.object_storage where storage_key=%s", ("data/versions/" + sha(rolled_back),)).fetchone()
    assert ledger == ("verified", len(rolled_back)), "rollback upload absent from physical storage ledger"
    return {"sql_unchanged": unchanged, "old_version_readable": readable, "uploaded_version_still_accounted": True}
check("callback rollback", "old version remains readable; uploaded orphan still accounted", rollback)

def first_conversion():
    path = "raw/legacy-conversion.json"
    seed(path)
    store.put(path, v2)
    assert objects["data/" + path] == v1, "legacy object overwritten"
    assert objects["data/versions/" + sha(v1)] == v1
    recovery = "raw/neon/versions/" + sha(v1) + ".json"
    assert store.bytes(recovery) == v1
    assert store.bytes(path) == v2
    assert db.execute("select state from statarena.object_storage where storage_key=%s", ("data/" + path,)).fetchone() == ("verified",)
    return {"recovery_path": recovery, "legacy_and_immutable_old_versions_readable": True}
check("first legacy conversion", "legacy bytes preserved, old SHA recovery catalogued, replacement readable", first_conversion)

def failure(kind):
    path = f"raw/upload-{kind}.json"
    seed(path, inline=True)
    # Preserve the old key before forcing the new publication to fail.
    control[kind] = True
    failed = False
    try: store.put(path, b'{"failure":"' + kind.encode() + b'"}')
    except Exception: failed = True
    assert failed, "upload failure accepted"
    assert pointer(path)["sha256"] == sha(v1)
    assert store.bytes(path) == v1
    return {"publication_rejected": failed, "old_version_readable": True}
for kind in ["deny_put", "bad_etag"]:
    check(kind, "failed/unverified upload never publishes alias", lambda kind=kind: failure(kind))

def immutable_collision():
    path = "raw/blob-" + sha(v1) + ".json"
    store.put(path, v1)
    start = len(requests)
    rejected = False
    try: store.put(path, v2)
    except ValueError: rejected = True
    assert rejected, "content-versioned public URL was overwritten"
    assert not any(r["method"] == "PUT" for r in requests[start:])
    assert store.bytes(path) == v1
    return {"replacement_rejected_before_upload": True}
check("immutable public URL", "different bytes rejected before PUT", immutable_collision)

def idempotent():
    path = "raw/idempotent.json"
    store.put(path, b'{"dedup":true}')
    start = len(requests)
    assert store.put(path, b'{"dedup":true}') is False
    assert not any(r["method"] == "PUT" for r in requests[start:])
    store.put("raw/shared-bytes.json", b'{"dedup":true}')
    assert not any(r["method"] == "PUT" for r in requests[start:]), "same bytes uploaded for a second alias"
    return {"repeat_and_second_alias_PUTs": 0}
check("idempotence and deduplication", "zero repeat PUTs including shared-byte alias", idempotent)

def old_writer():
    assert has_key
    path = "raw/old-writer.json"
    store.put(path, v1)
    objects["data/" + path] = v2
    db.execute("update statarena.objects set sha256=%s,size=%s,etag=%s,body=null where path=%s", (bytes.fromhex(sha(v2)),len(v2),md5(v2),path))
    assert db.execute("select storage_key from statarena.objects where path=%s", (path,)).fetchone() == (None,)
    assert store.bytes(path) == v2
    # Exercise the same retained legacy key after another old-writer publication.
    repaired = "raw/old-writer-repaired.json"
    seed(repaired)
    store.put(repaired, v2)
    third = b'{"version":3}'
    objects["data/" + repaired] = third
    db.execute("update statarena.objects set sha256=%s,size=%s,etag=%s,body=null where path=%s", (bytes.fromhex(sha(third)),len(third),md5(third),repaired))
    store.put(repaired, b'{"version":4}')
    assert objects["data/" + repaired] == third
    assert store.bytes(repaired) == b'{"version":4}'
    return {"legacy_update_cleared_pointer": True, "subsequent_publication_preserved_legacy_bytes": True}
check("legacy writer compatibility", "old-style SHA update clears stale pointer", old_writer)

def integrity():
    path = "raw/read-integrity.json"
    store.put(path, b'{"integrity":true}')
    key = pointer(path)["key"]
    previous = objects[key]
    objects[key] = b"corrupt"
    rejected = False
    try: store.bytes(path)
    except ValueError: rejected = True
    finally: objects[key] = previous
    assert rejected
    return {"corrupt_bytes_rejected": True}
check("read integrity", "size/hash verification retained", integrity)

def ingestion_permissions():
    assert has_key
    original = os.environ["NEON_DATABASE_URL"]
    parsed = urlparse(original)
    os.environ["NEON_DATABASE_URL"] = f"postgresql://fixture_ingest:fixture-role-only@127.0.0.1:{parsed.port}/publication_e2e"
    other = None
    try:
        other = Store()
        other.put("raw/role-permissions.json", b'{"permission":true}')
        assert other.bytes("raw/role-permissions.json") == b'{"permission":true}'
        assert other.storage_bytes() > 0
    finally:
        os.environ["NEON_DATABASE_URL"] = original
        if other:
            other.db.close()
            if getattr(other, "_storage_db", None): other._storage_db.close()
    public = db.execute("select exists(select 1 from pg_class c, lateral aclexplode(c.relacl) a where c.oid='statarena.object_storage'::regclass and a.grantee=0)").fetchone()[0]
    assert not public, "PUBLIC received ledger privileges"
    return {"restricted_ingestion_role_published": True, "PUBLIC_privileges": False}
check("ingestion role ACL", "existing restricted ingestion permissions work without PUBLIC grants", ingestion_permissions)

def legacy_growth():
    path = "raw/ledger-legacy-growth.json"
    seed(path)
    store.put(path, v2)
    grown = b'{"grown":"' + b'x' * 1000 + b'"}'
    objects["data/" + path] = grown
    db.execute("update statarena.objects set sha256=%s,size=%s,etag=%s,body=null where path=%s", (bytes.fromhex(sha(grown)),len(grown),md5(grown),path))
    counted = store.storage_bytes()
    actual = sum(map(len, objects.values()))
    assert counted >= actual, f"old-writer growth undercounted: capacity={counted}, actual={actual}"
    assert store.bytes(path) == grown
    return {"legacy_growth_bytes": len(grown)-len(v1), "physical_fixture_bytes": actual, "conservative_capacity_bytes": counted}
check("legacy writer size growth", "overlapping ledger record cannot hide a larger current legacy object", legacy_growth)

def capacity():
    counted = store.storage_bytes()
    actual = sum(map(len, objects.values()))
    assert counted >= actual, "known physical bytes omitted from capacity accounting"
    assert db.execute("select count(*) from statarena.object_storage where state='reserved'").fetchone()[0] >= 1
    report["ledger"] = [{"key": r[0], "bytes": r[1], "state": r[2]} for r in db.execute("select storage_key,size,state from statarena.object_storage order by storage_key")]
    return {"physical_fixture_bytes": actual, "conservative_capacity_bytes": counted, "overcount_bytes": counted-actual}
check("retained version capacity", "ledger includes retained versions, rollback uploads and failed reservations", capacity)

def fill_capacity(free_bytes=0):
    size = 4_750_000_000 - store.storage_bytes() - free_bytes
    assert size > 0
    db.execute("insert into statarena.object_storage(storage_key,sha256,size,etag,state) values('fixture/capacity-fill',%s,%s,'fixture-size-only','reserved')", (bytes.fromhex(sha(b'capacity-fill')),size))

def quota_admission():
    path = "raw/quota-admission.json"
    store.put(path, v1)
    old = pointer(path)
    replacement = b'{"capacity":"retry-after-space"}'
    key = "data/versions/" + sha(replacement)
    fill_capacity()
    rejected = False
    start = len(requests)
    try:
        # Main publication lock is deliberately held by another connection.
        # Reusing it for reservation would self-deadlock instead of refusing promptly.
        store.db.execute("select pg_advisory_lock(97813003)")
        store._storage_ledger().execute("set statement_timeout=2000")
        try:
            store.put(path, replacement)
        except RuntimeError as exc:
            rejected = "capacity" in str(exc).lower()
        finally:
            store.db.execute("select pg_advisory_unlock(97813003)")
            store._storage_ledger().execute("set statement_timeout=120000")
        puts = sum(r["method"] == "PUT" for r in requests[start:])
        assert rejected and puts == 0, f"full ledger accepted new upload: rejected={rejected}, PUTs={puts}"
        assert pointer(path) == old
        assert not db.execute("select 1 from statarena.object_storage where storage_key=%s", (key,)).fetchone(), "capacity-refused reservation poisoned accounting"
        assert store.bytes(path) == v1
        # A second alias of already verified bytes consumes no new physical budget.
        dedup_start = len(requests)
        store.put("raw/quota-existing-bytes.json", v1)
        assert not any(r["method"] == "PUT" for r in requests[dedup_start:])
    finally:
        db.execute("delete from statarena.object_storage where storage_key='fixture/capacity-fill'")
    retry_start = len(requests)
    assert store.put(path, replacement)
    assert store.bytes(path) == replacement
    retry_puts = sum(r["method"] == "PUT" for r in requests[retry_start:])
    assert retry_puts == 1
    return {"capacity_limit":4_750_000_000,"refused_before_PUT":True,"refused_reservation_absent":True,"verified_alias_at_limit_PUTs":0,"retry_after_space_PUTs":retry_puts,"distinct_lock_while_main_locked":True}
check("quota admission before upload", "full known ledger refuses unique bytes before PUT; aliases/dedup/retry remain safe", quota_admission)

def concurrent_admission():
    bodies = [b'{"reservation":"A"}', b'{"reservation":"B"}']
    assert len(bodies[0]) == len(bodies[1])
    fill_capacity(len(bodies[0]))
    barrier = threading.Barrier(2)
    start = len(requests)
    def publish(index):
        other = Store()
        try:
            barrier.wait(timeout=5)
            other.put(f"raw/concurrent-admission-{index}.json", bodies[index])
            return "published"
        except RuntimeError as exc:
            if "capacity" in str(exc).lower(): return "capacity_refused"
            raise
        finally:
            other.db.close()
            if getattr(other,"_storage_db",None): other._storage_db.close()
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(publish,range(2)))
        puts = sum(r["method"] == "PUT" for r in requests[start:])
        assert sorted(results) == ["capacity_refused","published"], results
        assert puts == 1, f"shared remaining budget admitted {puts} uploads"
        assert store.storage_bytes() == 4_750_000_000
        return {"remaining_bytes":len(bodies[0]),"results":sorted(results),"PUTs":puts,"capacity_after_reservation":store.storage_bytes()}
    finally:
        db.execute("delete from statarena.object_storage where storage_key='fixture/capacity-fill'")
check("concurrent reservation admission", "space for one unique object admits one of two simultaneous writers", concurrent_admission)

def sql_capacity_dedup():
    existing = "raw/sql-quota-existing.json"
    existing_body = b'{"sqlquota":"old"}'
    store.put(existing, existing_body)
    before = pointer(existing)
    count = db.execute("select count(*) from statarena.objects").fetchone()[0]
    known = store.storage_bytes()
    actual_database_size = db.execute("select pg_catalog.pg_database_size(current_database())").fetchone()[0]
    assert actual_database_size < 900_000_000
    db.execute("create function public.pg_database_size(name) returns bigint language sql as 'select 900000001::bigint'")
    ledger = store._storage_ledger()
    ledger.execute("set search_path=public,pg_catalog")
    start = len(requests)
    refused = []
    try:
        assert ledger.execute("select pg_database_size(current_database())").fetchone()[0] == 900_000_001
        assert store.put(existing, existing_body) is False, "identical existing bytes should write nothing"
        for path, body in [("raw/sql-quota-new-alias.json",v1),(existing,v1),("raw/sql-quota-unique.json",b'{"sqlquota":"unique"}')]:
            try:
                store.put(path, body)
            except RuntimeError as exc:
                assert "capacity" in str(exc).lower()
                refused.append(path)
            else:
                raise AssertionError("SQL-full publication accepted: " + path)
        assert db.execute("select count(*) from statarena.objects").fetchone()[0] == count, "SQL-full publication inserted catalog/recovery rows"
        assert pointer(existing) == before
        assert store.storage_bytes() == known
        assert not any(r["method"] == "PUT" for r in requests[start:])
        return {"real_database_bytes":actual_database_size,"fixture_reported_database_bytes":900_000_001,"refused_publications":len(refused),"new_PUTs":0,"new_catalog_rows":0,"new_reserved_bytes":0,"identical_existing_path_allowed":True}
    finally:
        ledger.execute("reset search_path")
        db.execute("drop function public.pg_database_size(name)")
check("SQL quota applies to verified aliases", "SQL-full dedup/new aliases refuse before writes; identical existing path remains allowed", sql_capacity_dedup)

def migration_required():
    db.execute("drop table if exists statarena.object_storage")
    start = len(requests)
    other = None
    rejected = False
    try:
        other = Store()
    except RuntimeError:
        rejected = True
    finally:
        if other: other.db.close()
        if migration.exists(): db.execute(migration.read_text())
    assert rejected, "writer accepted missing required storage migration"
    assert len(requests) == start
    return {"writer_rejected_before_network": True}
check("required migration guard", "new writer refuses unmigrated storage schema before any S3 request", migration_required)

report["requests"] = requests
report["totals"] = {"PUT": sum(r["method"] == "PUT" for r in requests), "GET": sum(r["method"] == "GET" for r in requests), "different_byte_overwrites": sum(r.get("different_byte_overwrite", False) for r in requests)}
report["status"] = "passed" if all(c["status"] == "passed" for c in report["cases"]) else "failed"
Path(a.report).write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({"status": report["status"], "passed": sum(c["status"] == "passed" for c in report["cases"]), "cases": len(report["cases"]), "totals": report["totals"], "failures": [c["name"] for c in report["cases"] if c["status"] != "passed"]}))
store.db.close()
if getattr(store, "_storage_db", None): store._storage_db.close()
db.close(); server.shutdown(); server.server_close()
sys.exit(0 if report["status"] == "passed" else 1)
