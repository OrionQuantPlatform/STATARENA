"""Stage newer Neon image mappings only after their bytes are verified in AWS SQL."""
import argparse
import json
import os
from pathlib import Path

import psycopg
from sql_payload_store import read_payload


class RollBackVerification(Exception):
    pass


def stage(source, target, mode="plan", limit=None):
    if mode not in ("plan", "verify", "apply") or (limit is not None and limit < 1):
        raise ValueError("Invalid synchronization mode or limit")
    source.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
    source_rows = source.execute("""SELECT a.url,a.path,a.content_type,o.size,o.sha256
        FROM statarena.assets a JOIN statarena.objects o ON o.path=a.path""").fetchall()
    report = {"mode": mode, "source_rows": len(source_rows), "committed": False}
    try:
        with target.transaction():
            target_rows = {url: (path, content_type) for url, path, content_type in
                           target.execute("SELECT url,path,content_type FROM statarena.assets").fetchall()}
            missing = conflicting = 0
            candidates = []
            for url, path, content_type, size, digest in source_rows:
                old = target_rows.get(url)
                if old == (path, content_type):
                    continue
                missing += old is None
                conflicting += old is not None
                candidates.append((url, path, content_type, size, bytes(digest),
                                   old[0] if old else None, old[1] if old else None))
            candidates.sort(key=lambda row: row[0])
            report.update(target_rows=len(target_rows), missing_on_aws=missing,
                          conflicting_mappings=conflicting, available_to_stage=len(candidates))
            if mode == "plan" or not candidates:
                return report
            if limit is not None:
                candidates = candidates[:limit]
            migration = Path(__file__).resolve().parents[1] / "backend/migrations/016_neon_delta_assets.sql"
            target.execute(migration.read_text())
            checked = {}
            for _, path, _, size, digest, _, _ in candidates:
                if path not in checked:
                    body = read_payload(target, "data", path, digest)
                    if len(body) != size:
                        raise ValueError("SQL image payload size mismatch")
                    checked[path] = (size, digest)
                elif checked[path] != (size, digest):
                    raise ValueError("Conflicting source metadata for an image")
            target.execute("""CREATE TEMP TABLE asset_delta_input (
                url text PRIMARY KEY,path text NOT NULL,content_type text NOT NULL,size bigint NOT NULL,
                source_sha256 bytea NOT NULL,target_path_at_capture text,target_content_type_at_capture text
            ) ON COMMIT DROP""")
            with target.cursor() as write:
                with write.copy("""COPY asset_delta_input(url,path,content_type,size,source_sha256,
                    target_path_at_capture,target_content_type_at_capture) FROM STDIN""") as copy:
                    for row in candidates:
                        copy.write_row(row)
            target.execute("""INSERT INTO statarena.neon_asset_delta
                (url,path,content_type,size,source_sha256,target_path_at_capture,target_content_type_at_capture)
                SELECT url,path,content_type,size,source_sha256,target_path_at_capture,target_content_type_at_capture
                FROM asset_delta_input ON CONFLICT(url) DO NOTHING""")
            invalid = target.execute("""SELECT count(*) FROM asset_delta_input incoming
                LEFT JOIN statarena.neon_asset_delta saved USING(url)
                WHERE saved.url IS NULL OR
                    ROW(saved.path,saved.content_type,saved.size,saved.source_sha256)
                    IS DISTINCT FROM ROW(incoming.path,incoming.content_type,incoming.size,incoming.source_sha256)""").fetchone()[0]
            if invalid:
                raise RuntimeError("An asset mapping has changed since an earlier capture")
            report.update(rows_staged=len(candidates), payloads_verified=len(checked), verification_mismatches=invalid)
            if mode == "verify":
                raise RollBackVerification()
        report["committed"] = True
    except RollBackVerification:
        report["rolled_back"] = True
    finally:
        source.rollback()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("plan", "verify", "apply"))
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    source = psycopg.connect(os.environ["STATARENA_SOURCE_DATABASE_URL"],
                             sslrootcert=os.environ.get("STATARENA_SOURCE_CA", "system"), connect_timeout=20)
    target = psycopg.connect(os.environ["STATARENA_TARGET_DATABASE_URL"], autocommit=True, connect_timeout=20)
    try:
        print(json.dumps(stage(source, target, args.mode, args.limit)), flush=True)
    finally:
        source.close()
        target.close()


if __name__ == "__main__":
    main()
