"""Stage Neon-only collector jobs without adding work to the AWS queue."""
import argparse
import json
import os
from pathlib import Path

import psycopg


class RollBackVerification(Exception):
    pass


def read_keys(db, table):
    if table not in ("jobs", "neon_job_delta"):
        raise ValueError("Unexpected job table")
    keys = set()
    with db.cursor(name="job_keys_" + table) as cursor:
        cursor.execute("SELECT endpoint,params FROM statarena." + table)
        while batch := cursor.fetchmany(5000):
            keys.update(batch)
    return keys


def stage(source, target, mode="plan", limit=None):
    if mode not in ("plan", "verify", "apply") or (limit is not None and limit < 1):
        raise ValueError("Invalid synchronization mode or limit")
    source.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
    source.execute("SET LOCAL TIME ZONE 'UTC'")
    report = {"mode": mode, "committed": False, "source_scanned": 0, "new_rows": 0}
    try:
        with target.transaction():
            target.execute("SET LOCAL TIME ZONE 'UTC'")
            existing = read_keys(target, "jobs")
            report["aws_jobs"] = len(existing)
            exists = bool(target.execute("SELECT to_regclass('statarena.neon_job_delta')").fetchone()[0])
            staged = read_keys(target, "neon_job_delta") if exists else set()
            report["already_staged"] = len(staged)
            existing.update(staged)
            if mode != "plan":
                migration = Path(__file__).resolve().parents[1] / "backend/migrations/015_neon_delta_jobs.sql"
                target.execute(migration.read_text())
                target.execute("CREATE TEMP TABLE job_delta_input (LIKE statarena.jobs INCLUDING DEFAULTS) ON COMMIT DROP")
            with source.cursor(name="neon_job_snapshot") as read, target.cursor() as write:
                columns = ("endpoint,params" if mode == "plan" else
                           "endpoint,params,priority,state,attempts,available_at,lease_until,last_status,last_error")
                read.execute("SELECT " + columns + " FROM statarena.jobs")

                def incoming(copy=None):
                    while batch := read.fetchmany(2000):
                        for row in batch:
                            report["source_scanned"] += 1
                            if (row[0], row[1]) in existing:
                                continue
                            if copy is not None:
                                copy.write_row(row)
                            report["new_rows"] += 1
                            if limit is not None and report["new_rows"] >= limit:
                                return

                if mode == "plan":
                    incoming()
                else:
                    with write.copy("""COPY job_delta_input(endpoint,params,priority,state,attempts,available_at,
                        lease_until,last_status,last_error) FROM STDIN""") as copy:
                        incoming(copy)
            if mode == "plan":
                return report
            inserted = target.execute("""INSERT INTO statarena.neon_job_delta
                (endpoint,params,priority,state,attempts,available_at,lease_until,last_status,last_error)
                SELECT endpoint,params,priority,state,attempts,available_at,lease_until,last_status,last_error
                FROM job_delta_input ON CONFLICT(endpoint,params) DO NOTHING""").rowcount
            invalid = target.execute("""SELECT count(*) FROM job_delta_input incoming
                LEFT JOIN statarena.neon_job_delta saved USING(endpoint,params)
                WHERE saved.endpoint IS NULL OR
                  ROW(saved.priority,saved.state,saved.attempts,saved.available_at,saved.lease_until,saved.last_status,saved.last_error)
                  IS DISTINCT FROM ROW(incoming.priority,incoming.state,incoming.attempts,incoming.available_at,
                                       incoming.lease_until,incoming.last_status,incoming.last_error)""").fetchone()[0]
            if invalid:
                raise RuntimeError("Staged collector jobs differ from their source snapshot")
            report.update(rows_inserted=inserted, verification_mismatches=invalid)
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
