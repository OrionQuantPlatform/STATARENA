"""Stage later Neon ingestion diagnostics without changing active AWS rows."""
import argparse
import json
import os
from pathlib import Path

import psycopg
from sync_neon_fixtures import compare_fixtures


class RollBackVerification(Exception):
    pass


def fingerprints(db):
    return {(endpoint, params): (updated_at, digest) for endpoint, params, updated_at, digest in
            db.execute("SELECT endpoint,params,updated_at,md5(to_jsonb(f)::text) FROM statarena.ingest_failures f").fetchall()}


def stage(source, target, mode="plan", limit=None):
    if mode not in ("plan", "verify", "apply") or (limit is not None and limit < 1):
        raise ValueError("Invalid synchronization mode or limit")
    source.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
    source.execute("SET LOCAL TIME ZONE 'UTC'")
    source_rows = fingerprints(source)
    report = {"mode": mode, "source_rows": len(source_rows), "committed": False}
    try:
        with target.transaction():
            target.execute("SET LOCAL TIME ZONE 'UTC'")
            target_rows = fingerprints(target)
            comparison, candidates = compare_fixtures(source_rows, target_rows)
            report.update(target_rows=len(target_rows), **comparison)
            if mode == "plan" or not candidates:
                return report
            if limit is not None:
                candidates = candidates[:limit]
            migration = Path(__file__).resolve().parents[1] / "backend/migrations/021_neon_delta_ingest_failures.sql"
            target.execute(migration.read_text())
            target.execute("""CREATE TEMP TABLE failure_delta_input (
                endpoint text NOT NULL,params text NOT NULL,status smallint NOT NULL,error jsonb,
                updated_at timestamptz NOT NULL,target_updated_at_at_capture timestamptz,
                target_digest_at_capture text,PRIMARY KEY(endpoint,params)
            ) ON COMMIT DROP""")
            endpoints, params = zip(*candidates)
            rows = source.execute("""SELECT f.endpoint,f.params,f.status,f.error::text,f.updated_at
                FROM statarena.ingest_failures f JOIN unnest(%s::text[],%s::text[]) requested(endpoint,params)
                USING(endpoint,params)""", (list(endpoints), list(params))).fetchall()
            if len(rows) != len(candidates):
                raise RuntimeError("Source diagnostics snapshot changed while being copied")
            with target.cursor() as write:
                with write.copy("""COPY failure_delta_input(endpoint,params,status,error,updated_at,
                    target_updated_at_at_capture,target_digest_at_capture) FROM STDIN""") as copy:
                    for endpoint, params, status, error, updated_at in rows:
                        prior = target_rows.get((endpoint, params))
                        copy.write_row((endpoint, params, status, error, updated_at,
                                        prior[0] if prior else None, prior[1] if prior else None))
            target.execute("""INSERT INTO statarena.neon_ingest_failure_delta AS staged
                (endpoint,params,status,error,updated_at,target_updated_at_at_capture,target_digest_at_capture)
                SELECT endpoint,params,status,error,updated_at,target_updated_at_at_capture,target_digest_at_capture
                FROM failure_delta_input ON CONFLICT(endpoint,params) DO UPDATE SET status=excluded.status,
                    error=excluded.error,updated_at=excluded.updated_at,
                    target_updated_at_at_capture=excluded.target_updated_at_at_capture,
                    target_digest_at_capture=excluded.target_digest_at_capture,captured_at=now()
                WHERE excluded.updated_at>staged.updated_at""")
            invalid = target.execute("""SELECT count(*) FROM failure_delta_input incoming
                LEFT JOIN statarena.neon_ingest_failure_delta saved USING(endpoint,params)
                WHERE saved.endpoint IS NULL OR saved.updated_at<incoming.updated_at OR
                    (saved.updated_at=incoming.updated_at AND ROW(saved.status,saved.error)
                     IS DISTINCT FROM ROW(incoming.status,incoming.error))""").fetchone()[0]
            if invalid:
                raise RuntimeError("Staged ingestion diagnostics differ from the source snapshot")
            newer_staged = target.execute("""SELECT count(*) FROM failure_delta_input incoming
                JOIN statarena.neon_ingest_failure_delta saved USING(endpoint,params)
                WHERE saved.updated_at>incoming.updated_at""").fetchone()[0]
            report.update(rows_copied=len(rows), newer_staged_preserved=newer_staged, verification_mismatches=invalid)
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
