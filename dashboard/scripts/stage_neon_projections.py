"""Stage newer Neon projections without replacing active AWS projections."""
import argparse
import json
import os
from pathlib import Path

import psycopg
from sync_neon_fixtures import compare_fixtures


class RollBackVerification(Exception):
    pass


def fingerprints(db):
    return {(name, params): (updated_at, digest) for name, params, updated_at, digest in
            db.execute("SELECT name,params,updated_at,md5(to_jsonb(p)::text) FROM statarena.projections p").fetchall()}


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
            migration = Path(__file__).resolve().parents[1] / "backend/migrations/018_neon_delta_projections.sql"
            target.execute(migration.read_text())
            target.execute("""CREATE TEMP TABLE projection_delta_input (
                name text NOT NULL,params text NOT NULL,body jsonb NOT NULL,updated_at timestamptz NOT NULL,
                target_updated_at_at_capture timestamptz,target_digest_at_capture text,PRIMARY KEY(name,params)
            ) ON COMMIT DROP""")
            names, params = zip(*candidates)
            copied = 0
            with source.cursor(name="projection_delta_rows") as read, target.cursor() as write:
                read.execute("""SELECT p.name,p.params,p.body::text,p.updated_at
                    FROM statarena.projections p JOIN unnest(%s::text[],%s::text[]) requested(name,params)
                    USING(name,params) ORDER BY p.name,p.params""", (list(names), list(params)))
                with write.copy("""COPY projection_delta_input(name,params,body,updated_at,
                    target_updated_at_at_capture,target_digest_at_capture) FROM STDIN""") as copy:
                    while batch := read.fetchmany(500):
                        for name, params, body, updated_at in batch:
                            prior = target_rows.get((name, params))
                            copy.write_row((name, params, body, updated_at,
                                            prior[0] if prior else None, prior[1] if prior else None))
                            copied += 1
            if copied != len(candidates):
                raise RuntimeError("Source projection snapshot changed while being copied")
            target.execute("""INSERT INTO statarena.neon_projection_delta AS staged
                (name,params,body,updated_at,target_updated_at_at_capture,target_digest_at_capture)
                SELECT name,params,body,updated_at,target_updated_at_at_capture,target_digest_at_capture
                FROM projection_delta_input ON CONFLICT(name,params) DO UPDATE SET body=excluded.body,
                    updated_at=excluded.updated_at,target_updated_at_at_capture=excluded.target_updated_at_at_capture,
                    target_digest_at_capture=excluded.target_digest_at_capture,captured_at=now()
                WHERE excluded.updated_at>staged.updated_at""")
            invalid = target.execute("""SELECT count(*) FROM projection_delta_input incoming
                LEFT JOIN statarena.neon_projection_delta saved USING(name,params)
                WHERE saved.name IS NULL OR saved.updated_at<incoming.updated_at OR
                    (saved.updated_at=incoming.updated_at AND saved.body IS DISTINCT FROM incoming.body)""").fetchone()[0]
            if invalid:
                raise RuntimeError("Staged projections differ from the source snapshot")
            newer_staged = target.execute("""SELECT count(*) FROM projection_delta_input incoming
                JOIN statarena.neon_projection_delta saved USING(name,params)
                WHERE saved.updated_at>incoming.updated_at""").fetchone()[0]
            report.update(rows_copied=copied, newer_staged_preserved=newer_staged, verification_mismatches=invalid)
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
