"""Stage later Neon publication signals without changing the AWS work queue."""
import argparse
import json
import os
from pathlib import Path

import psycopg


class RollBackVerification(Exception):
    pass


def rows(db):
    return {(season, league): changed_at for season, league, changed_at in
            db.execute("SELECT season,league_id,changed_at FROM statarena.dirty_partitions").fetchall()}


def stage(source, target, mode="plan", limit=None):
    if mode not in ("plan", "verify", "apply") or (limit is not None and limit < 1):
        raise ValueError("Invalid synchronization mode or limit")
    source.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
    source_rows = rows(source)
    report = {"mode": mode, "source_rows": len(source_rows), "committed": False}
    try:
        with target.transaction():
            target_rows = rows(target)
            candidates = sorted(key for key, changed in source_rows.items()
                                if key not in target_rows or changed > target_rows[key])
            report.update(target_rows=len(target_rows), source_only=sum(key not in target_rows for key in candidates),
                          newer_on_neon=sum(key in target_rows for key in candidates), available_to_stage=len(candidates))
            if mode == "plan" or not candidates:
                return report
            if limit is not None:
                candidates = candidates[:limit]
            migration = Path(__file__).resolve().parents[1] / "backend/migrations/023_neon_delta_dirty_partitions.sql"
            target.execute(migration.read_text())
            target.execute("""CREATE TEMP TABLE dirty_delta_input (
                season text NOT NULL,league_id text NOT NULL,changed_at timestamptz NOT NULL,
                target_changed_at_at_capture timestamptz,PRIMARY KEY(season,league_id)
            ) ON COMMIT DROP""")
            with target.cursor() as write:
                with write.copy("""COPY dirty_delta_input(season,league_id,changed_at,
                    target_changed_at_at_capture) FROM STDIN""") as copy:
                    for key in candidates:
                        copy.write_row((*key, source_rows[key], target_rows.get(key)))
            target.execute("""INSERT INTO statarena.neon_dirty_partition_delta AS staged
                (season,league_id,changed_at,target_changed_at_at_capture)
                SELECT season,league_id,changed_at,target_changed_at_at_capture FROM dirty_delta_input
                ON CONFLICT(season,league_id) DO UPDATE SET changed_at=excluded.changed_at,
                    target_changed_at_at_capture=excluded.target_changed_at_at_capture,captured_at=now()
                WHERE excluded.changed_at>staged.changed_at""")
            invalid = target.execute("""SELECT count(*) FROM dirty_delta_input incoming
                LEFT JOIN statarena.neon_dirty_partition_delta saved USING(season,league_id)
                WHERE saved.season IS NULL OR saved.changed_at<incoming.changed_at""").fetchone()[0]
            if invalid:
                raise RuntimeError("Staged publication signals are older than the source snapshot")
            report.update(rows_copied=len(candidates), verification_mismatches=invalid)
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
