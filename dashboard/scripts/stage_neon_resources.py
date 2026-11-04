"""Stage newer Neon resource rows without changing the live AWS references."""
import argparse
import json
import os
from pathlib import Path

import psycopg
from sync_neon_fixtures import compare_fixtures


class RollBackVerification(Exception):
    pass


def fingerprints(db):
    result = {}
    with db.cursor(name="resource_fingerprints") as cursor:
        cursor.execute("select endpoint,params,updated_at,md5(to_jsonb(r)::text) from statarena.resources r")
        while batch := cursor.fetchmany(5000):
            result.update(((endpoint, params), (updated_at, digest))
                          for endpoint, params, updated_at, digest in batch)
    return result


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
            migration = Path(__file__).resolve().parents[1] / "backend/migrations/014_neon_delta_resources.sql"
            target.execute(migration.read_text())
            target.execute("""CREATE TEMP TABLE resource_delta_input (
                endpoint text NOT NULL,params text NOT NULL,status smallint NOT NULL,
                ref jsonb,error jsonb,updated_at timestamptz NOT NULL,PRIMARY KEY(endpoint,params)
            ) ON COMMIT DROP""")
            endpoints, params = zip(*candidates)
            copied = 0
            with source.cursor(name="resource_delta_rows") as read, target.cursor() as write:
                read.execute("""SELECT r.endpoint,r.params,r.status,r.ref::text,r.error::text,r.updated_at
                    FROM statarena.resources r JOIN unnest(%s::text[],%s::text[]) requested(endpoint,params)
                    USING(endpoint,params) ORDER BY r.endpoint,r.params""", (list(endpoints), list(params)))
                with write.copy("COPY resource_delta_input(endpoint,params,status,ref,error,updated_at) FROM STDIN") as copy:
                    while batch := read.fetchmany(1000):
                        for row in batch:
                            copy.write_row(row)
                            copied += 1
            if copied != len(candidates):
                raise RuntimeError("Source resource snapshot changed while being copied")
            target.execute("""INSERT INTO statarena.neon_resource_delta AS staged
                (endpoint,params,status,ref,error,updated_at)
                SELECT endpoint,params,status,ref,error,updated_at FROM resource_delta_input
                ON CONFLICT(endpoint,params) DO UPDATE SET status=excluded.status,ref=excluded.ref,
                    error=excluded.error,updated_at=excluded.updated_at,captured_at=now()
                WHERE excluded.updated_at>staged.updated_at""")
            invalid = target.execute("""SELECT count(*) FROM resource_delta_input incoming
                LEFT JOIN statarena.neon_resource_delta saved USING(endpoint,params)
                WHERE saved.endpoint IS NULL OR saved.updated_at<incoming.updated_at OR
                    (saved.updated_at=incoming.updated_at AND
                     ROW(saved.status,saved.ref,saved.error) IS DISTINCT FROM
                     ROW(incoming.status,incoming.ref,incoming.error))""").fetchone()[0]
            if invalid:
                raise RuntimeError("Staged resource rows differ from the source snapshot")
            newer_staged = target.execute("""SELECT count(*) FROM resource_delta_input incoming
                JOIN statarena.neon_resource_delta saved USING(endpoint,params)
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
