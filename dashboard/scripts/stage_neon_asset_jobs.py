"""Stage Neon-only image collection jobs without adding work to AWS."""
import argparse
import json
import os
from pathlib import Path

import psycopg


class RollBackVerification(Exception):
    pass


def stage(source, target, mode="plan", limit=None):
    if mode not in ("plan", "verify", "apply") or (limit is not None and limit < 1):
        raise ValueError("Invalid synchronization mode or limit")
    source.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
    source_rows = source.execute("SELECT url,attempts,next_attempt,error FROM statarena.asset_jobs").fetchall()
    report = {"mode": mode, "source_rows": len(source_rows), "committed": False}
    try:
        with target.transaction():
            live = {row[0] for row in target.execute("SELECT url FROM statarena.asset_jobs").fetchall()}
            exists = bool(target.execute("SELECT to_regclass('statarena.neon_asset_job_delta')").fetchone()[0])
            saved = ({row[0] for row in target.execute("SELECT url FROM statarena.neon_asset_job_delta").fetchall()}
                     if exists else set())
            candidates = sorted((row for row in source_rows if row[0] not in live and row[0] not in saved),
                                key=lambda row: row[0])
            report.update(target_rows=len(live), already_staged=len(saved), available_to_stage=len(candidates))
            if mode == "plan" or not candidates:
                return report
            if limit is not None:
                candidates = candidates[:limit]
            migration = Path(__file__).resolve().parents[1] / "backend/migrations/019_neon_delta_asset_jobs.sql"
            target.execute(migration.read_text())
            target.execute("""CREATE TEMP TABLE asset_job_delta_input (
                url text PRIMARY KEY,attempts integer NOT NULL,next_attempt timestamptz NOT NULL,error text
            ) ON COMMIT DROP""")
            with target.cursor() as write:
                with write.copy("COPY asset_job_delta_input(url,attempts,next_attempt,error) FROM STDIN") as copy:
                    for row in candidates:
                        copy.write_row(row)
            inserted = target.execute("""INSERT INTO statarena.neon_asset_job_delta(url,attempts,next_attempt,error)
                SELECT url,attempts,next_attempt,error FROM asset_job_delta_input ON CONFLICT(url) DO NOTHING""").rowcount
            invalid = target.execute("""SELECT count(*) FROM asset_job_delta_input incoming
                LEFT JOIN statarena.neon_asset_job_delta saved USING(url)
                WHERE saved.url IS NULL OR ROW(saved.attempts,saved.next_attempt,saved.error)
                    IS DISTINCT FROM ROW(incoming.attempts,incoming.next_attempt,incoming.error)""").fetchone()[0]
            if invalid:
                raise RuntimeError("Staged image jobs differ from their source snapshot")
            report.update(rows_staged=inserted, verification_mismatches=invalid)
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
