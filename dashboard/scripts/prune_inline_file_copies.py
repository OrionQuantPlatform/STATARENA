#!/usr/bin/env python3
"""Verify file copies before removing the redundant PostgreSQL bodies.

Dry-run by default. Run with the ingestion credentials and --apply after the
file-backed reader has been deployed. The collection advisory lock is held for
the whole check and update, so an active collector causes an immediate exit.
"""

import argparse
import hashlib
import json

from neon_store import Store


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    store = Store()
    lock = store.db.execute("select pg_try_advisory_lock(97813003)").fetchone()[0]
    if not lock:
        raise RuntimeError("A collection is running; retry after it completes")
    try:
        rows = store.db.execute(
            "select path,size,sha256,body from statarena.objects where body is not null order by path"
        ).fetchall()
        checked = []
        size = 0
        for path, length, digest, inline in rows:
            expected = bytes(digest)
            if len(inline) != length or hashlib.sha256(inline).digest() != expected:
                raise ValueError("Inline copy does not match catalog: " + path)
            # Require the current object itself to match; an archived fallback is
            # not enough to remove a copy from the database.
            remote = store.s3.get_object(
                Bucket=store.bucket, Key="data/" + path
            )["Body"]
            actual = hashlib.sha256()
            received = 0
            while True:
                part = remote.read(1024 * 1024)
                if not part:
                    break
                actual.update(part)
                received += len(part)
            remote.close()
            if received != length or actual.digest() != expected:
                raise ValueError("Stored file does not match catalog: " + path)
            checked.append((path, length, expected))
            size += length
        changed = 0
        if args.apply:
            with store.db.transaction():
                for path, length, digest in checked:
                    result = store.db.execute(
                        "update statarena.objects set body=null where path=%s and size=%s and sha256=%s and body is not null",
                        (path, length, digest),
                    )
                    if result.rowcount != 1:
                        raise RuntimeError("Catalog changed during verification: " + path)
                    changed += 1
        print(json.dumps({"verified": len(checked), "bytes": size, "updated": changed, "applied": args.apply}))
    finally:
        store.db.execute("select pg_advisory_unlock(97813003)")
        store.db.close()


if __name__ == "__main__":
    main()
