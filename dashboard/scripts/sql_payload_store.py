"""Store exact file bytes in PostgreSQL and verify every stored chunk."""
import hashlib
import io
import re

from psycopg.types.json import Jsonb

INLINE_LIMIT = 2 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024


def lock_payload(db, namespace, path):
    """Serialize initial writes as well as replacements of an existing payload."""
    db.execute("select pg_advisory_xact_lock(hashtextextended(%s,0))", (namespace + "\x1f" + path,))


def _read_exact(stream, size):
    result = bytearray()
    while len(result) < size:
        part = stream.read(size - len(result))
        if not part:
            break
        result.extend(part)
    if len(result) != size or stream.read(1):
        raise ValueError("Source size does not match its catalog")
    return bytes(result)


def _validate_source(size, actual_size, expected_sha, actual_sha, etag, md5):
    if actual_size != size or (expected_sha is not None and actual_sha != bytes(expected_sha)):
        raise ValueError("Source bytes do not match the expected size and SHA-256")
    plain_etag = (etag or "").strip('"').lower()
    if re.fullmatch(r"[0-9a-f]{32}", plain_etag) and md5 != plain_etag:
        raise ValueError("Source bytes do not match the object ETag")


def write_payload(db, namespace, path, stream, size, expected_sha=None,
                  content_type="application/octet-stream", source_etag=None, metadata=None):
    """Write one complete source stream transactionally; verify source and database bytes.

    The caller can wrap this in the same transaction as its catalog update. Larger
    files are streamed into 1 MiB chunks instead of allocating one huge value.
    """
    if not namespace or not path or size < 0:
        raise ValueError("Invalid payload identity or size")
    if expected_sha is not None and len(expected_sha) != 32:
        raise ValueError("Invalid expected SHA-256")
    metadata = Jsonb(metadata or {})
    with db.transaction():
        lock_payload(db, namespace, path)
        previous = db.execute("select chunk_count from statarena.file_payloads where namespace=%s and path=%s for update",
                              (namespace, path)).fetchone()
        if previous and previous[0]:
            db.execute("delete from statarena.file_payload_chunks where namespace=%s and path=%s", (namespace, path))
        if size <= INLINE_LIMIT:
            body = _read_exact(stream, size)
            digest, md5 = hashlib.sha256(body).digest(), hashlib.md5(body).hexdigest()
            _validate_source(size, len(body), expected_sha, digest, source_etag, md5)
            stored_size, stored_sha = db.execute("""insert into statarena.file_payloads
                (namespace,path,size,sha256,body,content_type,source_etag,metadata,chunk_count)
                values(%s,%s,%s,%s,%s,%s,%s,%s,0)
                on conflict(namespace,path) do update set size=excluded.size,sha256=excluded.sha256,
                    body=excluded.body,content_type=excluded.content_type,source_etag=excluded.source_etag,
                    metadata=excluded.metadata,chunk_count=0,verified_at=now()
                returning octet_length(body),sha256(body)""",
                (namespace, path, size, digest, body, content_type, source_etag, metadata)).fetchone()
            if stored_size != size or bytes(stored_sha) != digest:
                raise ValueError("PostgreSQL inline payload verification failed")
            return digest, 0

        # This provisional manifest and all chunks become visible only at commit.
        placeholder = bytes(expected_sha) if expected_sha is not None else bytes(32)
        db.execute("""insert into statarena.file_payloads
            (namespace,path,size,sha256,body,content_type,source_etag,metadata,chunk_count)
            values(%s,%s,%s,%s,null,%s,%s,%s,1)
            on conflict(namespace,path) do update set size=excluded.size,sha256=excluded.sha256,
                body=null,content_type=excluded.content_type,source_etag=excluded.source_etag,
                metadata=excluded.metadata,chunk_count=1,verified_at=now()""",
            (namespace, path, size, placeholder, content_type, source_etag, metadata))
        source_hash, source_md5 = hashlib.sha256(), hashlib.md5()
        expected_chunks = []
        actual_size = 0
        with db.cursor() as cursor:
            with cursor.copy("""copy statarena.file_payload_chunks
                (namespace,path,chunk_index,body,sha256) from stdin""") as copy:
                while True:
                    chunk = stream.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    actual_size += len(chunk)
                    if actual_size > size:
                        raise ValueError("Source stream exceeds its expected size")
                    source_hash.update(chunk)
                    source_md5.update(chunk)
                    digest = hashlib.sha256(chunk).digest()
                    expected_chunks.append((len(chunk), digest))
                    copy.write_row((namespace, path, len(expected_chunks) - 1, chunk, digest))
        source_sha = source_hash.digest()
        _validate_source(size, actual_size, expected_sha, source_sha, source_etag, source_md5.hexdigest())
        actual_chunks = db.execute("""select chunk_index,octet_length(body),sha256(body),sha256
            from statarena.file_payload_chunks where namespace=%s and path=%s order by chunk_index""",
            (namespace, path)).fetchall()
        if len(actual_chunks) != len(expected_chunks) or any(
            number != index or length != expected_chunks[index][0]
            or bytes(actual) != expected_chunks[index][1] or bytes(recorded) != expected_chunks[index][1]
            for index, (number, length, actual, recorded) in enumerate(actual_chunks)
        ):
            raise ValueError("PostgreSQL chunk verification failed")
        db.execute("""update statarena.file_payloads set sha256=%s,chunk_count=%s,verified_at=now()
            where namespace=%s and path=%s""", (source_sha, len(expected_chunks), namespace, path))
        return source_sha, len(expected_chunks)


def write_bytes(db, namespace, path, body, content_type="application/octet-stream"):
    return write_payload(db, namespace, path, io.BytesIO(body), len(body), hashlib.sha256(body).digest(), content_type)


def read_payload(db, namespace, path, expected_sha=None):
    row = db.execute("""select size,sha256,body,chunk_count from statarena.file_payloads
        where namespace=%s and path=%s""", (namespace, path)).fetchone()
    if not row:
        raise FileNotFoundError(path)
    size, digest, body, chunk_count = row
    if expected_sha is not None and bytes(digest) != bytes(expected_sha):
        raise ValueError("SQL payload version does not match its catalog")
    if body is None:
        chunks = db.execute("""select chunk_index,body,sha256 from statarena.file_payload_chunks
            where namespace=%s and path=%s order by chunk_index""", (namespace, path)).fetchall()
        if len(chunks) != chunk_count or any(index != number or hashlib.sha256(bytes(value)).digest() != bytes(sha)
                for index, (number, value, sha) in enumerate(chunks)):
            raise ValueError("SQL payload chunks are incomplete or corrupt")
        body = b"".join(bytes(chunk[1]) for chunk in chunks)
    else:
        body = bytes(body)
    if len(body) != size or hashlib.sha256(body).digest() != bytes(digest):
        raise ValueError("SQL payload failed size or SHA-256 validation")
    return body
