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


def read_live_fingerprints(db):
    rows = {}
    with db.cursor(name="job_fingerprints") as cursor:
        cursor.execute("SELECT endpoint,params,md5(to_jsonb(j)::text) FROM statarena.jobs j")
        while batch := cursor.fetchmany(5000):
            rows.update(((endpoint, params), digest) for endpoint, params, digest in batch)
    return rows


def classify(key, source_digest, live, staged, include_conflicts):
    if key in staged:
        return None
    if key not in live:
        return "source_only"
    if include_conflicts and live[key] != source_digest:
        return "shared_conflict"
    return None


def stage(source, target, mode="plan", limit=None, include_conflicts=False):
    if mode not in ("plan", "verify", "apply") or (limit is not None and limit < 1):
        raise ValueError("Invalid synchronization mode or limit")
    source.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
    source.execute("SET LOCAL TIME ZONE 'UTC'")
    report = {"mode": mode, "committed": False, "source_scanned": 0, "new_rows": 0}
    try:
        with target.transaction():
            target.execute("SET LOCAL TIME ZONE 'UTC'")
            live = read_live_fingerprints(target) if include_conflicts else read_keys(target, "jobs")
            report["aws_jobs"] = len(live)
            exists = bool(target.execute("SELECT to_regclass('statarena.neon_job_delta')").fetchone()[0])
            staged = read_keys(target, "neon_job_delta") if exists else set()
            report["already_staged"] = len(staged)
            report.update(source_only=0, shared_conflicts=0)
            if mode != "plan":
                migration = Path(__file__).resolve().parents[1] / "backend/migrations/015_neon_delta_jobs.sql"
                target.execute(migration.read_text())
                conflict_migration = migration.with_name("022_neon_job_conflicts.sql")
                target.execute(conflict_migration.read_text())
                target.execute("""CREATE TEMP TABLE job_delta_input (LIKE statarena.jobs INCLUDING DEFAULTS,
                    target_present_at_capture boolean NOT NULL,target_digest_at_capture text) ON COMMIT DROP""")
            with source.cursor(name="neon_job_snapshot") as read, target.cursor() as write:
                columns = ("endpoint,params" if mode == "plan" else
                           "endpoint,params,priority,state,attempts,available_at,lease_until,last_status,last_error")
                if include_conflicts:
                    columns += ",md5(to_jsonb(j)::text)"
                read.execute("SELECT " + columns + " FROM statarena.jobs j")

                def incoming(copy=None):
                    while batch := read.fetchmany(2000):
                        for row in batch:
                            report["source_scanned"] += 1
                            key = (row[0], row[1])
                            digest = row[-1] if include_conflicts else None
                            category = classify(key, digest, live, staged, include_conflicts)
                            if category is None:
                                continue
                            if copy is not None:
                                values = row[:-1] if include_conflicts else row
                                copy.write_row((*values, category == "shared_conflict",
                                                live[key] if category == "shared_conflict" else None))
                            report["new_rows"] += 1
                            report["source_only" if category == "source_only" else "shared_conflicts"] += 1
                            if limit is not None and report["new_rows"] >= limit:
                                return

                if mode == "plan":
                    incoming()
                else:
                    with write.copy("""COPY job_delta_input(endpoint,params,priority,state,attempts,available_at,
                        lease_until,last_status,last_error,target_present_at_capture,target_digest_at_capture) FROM STDIN""") as copy:
                        incoming(copy)
            if mode == "plan":
                return report
            inserted = target.execute("""INSERT INTO statarena.neon_job_delta
                (endpoint,params,priority,state,attempts,available_at,lease_until,last_status,last_error,
                 target_present_at_capture,target_digest_at_capture)
                SELECT endpoint,params,priority,state,attempts,available_at,lease_until,last_status,last_error,
                       target_present_at_capture,target_digest_at_capture
                FROM job_delta_input ON CONFLICT(endpoint,params) DO NOTHING""").rowcount
            invalid = target.execute("""SELECT count(*) FROM job_delta_input incoming
                LEFT JOIN statarena.neon_job_delta saved USING(endpoint,params)
                WHERE saved.endpoint IS NULL OR
                  ROW(saved.priority,saved.state,saved.attempts,saved.available_at,saved.lease_until,saved.last_status,saved.last_error,
                      saved.target_present_at_capture,saved.target_digest_at_capture)
                  IS DISTINCT FROM ROW(incoming.priority,incoming.state,incoming.attempts,incoming.available_at,
                                       incoming.lease_until,incoming.last_status,incoming.last_error,
                                       incoming.target_present_at_capture,incoming.target_digest_at_capture)""").fetchone()[0]
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
    parser.add_argument("--include-conflicts", action="store_true",
                        help="also stage shared jobs whose source and AWS contents differ")
    args = parser.parse_args()
    source = psycopg.connect(os.environ["STATARENA_SOURCE_DATABASE_URL"],
                             sslrootcert=os.environ.get("STATARENA_SOURCE_CA", "system"), connect_timeout=20)
    target = psycopg.connect(os.environ["STATARENA_TARGET_DATABASE_URL"], autocommit=True, connect_timeout=20)
    try:
        print(json.dumps(stage(source, target, args.mode, args.limit, args.include_conflicts)), flush=True)
    finally:
        source.close()
        target.close()


if __name__ == "__main__":
    main()
