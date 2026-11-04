"""Reconcile Neon fixture rows into AWS without overwriting newer AWS rows.

Both endpoints are supplied through environment variables. Run in ``verify`` mode
to exercise the full write path inside a rolled-back transaction before applying.
This is an incremental snapshot, not a substitute for the final cutover sync.
"""
import argparse
import json
import os

import psycopg


class RollBackVerification(Exception):
    pass


def fixture_fingerprints(db):
    rows = {}
    with db.cursor(name="fixture_fingerprints") as cursor:
        cursor.execute("select id,updated_at,md5(to_jsonb(f)::text) from statarena.fixtures f")
        while batch := cursor.fetchmany(4000):
            rows.update((identifier, (updated_at, digest)) for identifier, updated_at, digest in batch)
    return rows


def compare_fixtures(source_rows, target_rows):
    both = source_rows.keys() & target_rows.keys()
    differing = [key for key in both if source_rows[key][1] != target_rows[key][1]]
    newer_source = [key for key in differing if source_rows[key][0] > target_rows[key][0]]
    newer_target = [key for key in differing if source_rows[key][0] < target_rows[key][0]]
    missing = source_rows.keys() - target_rows.keys()
    candidates = sorted(missing | set(newer_source))
    return ({"missing_on_aws": len(missing), "newer_on_neon": len(newer_source),
             "newer_on_aws": len(newer_target),
             "conflicting_equal_timestamps": len(differing)-len(newer_source)-len(newer_target),
             "available_to_sync": len(candidates)}, candidates)


def reconcile(source, target, mode="plan", limit=None):
    if mode not in ("plan", "verify", "apply") or (limit is not None and limit < 1):
        raise ValueError("Invalid synchronization mode or limit")
    source.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
    source.execute("SET LOCAL TIME ZONE 'UTC'")
    source_rows = fixture_fingerprints(source)
    report = {"mode": mode, "source_rows": len(source_rows), "committed": False}
    try:
        with target.transaction():
            target.execute("SET LOCAL TIME ZONE 'UTC'")
            target_rows = fixture_fingerprints(target)
            comparison, candidates = compare_fixtures(source_rows, target_rows)
            report.update(target_rows=len(target_rows), **comparison)
            if mode == "plan" or not candidates:
                return report
            if limit is not None:
                candidates = candidates[:limit]
            target.execute("""CREATE TEMP TABLE sync_fixture_input (
                id text PRIMARY KEY, league_id text NOT NULL, season text NOT NULL, day date,
                status text, body jsonb NOT NULL, updated_at timestamptz NOT NULL
            ) ON COMMIT DROP""")
            copied = 0
            with source.cursor(name="fixture_delta_rows") as read, target.cursor() as write:
                read.execute("""SELECT id,league_id,season,day,status,body::text,updated_at
                    FROM statarena.fixtures WHERE id=ANY(%s) ORDER BY id""", (candidates,))
                with write.copy("COPY sync_fixture_input (id,league_id,season,day,status,body,updated_at) FROM STDIN") as copy:
                    while batch := read.fetchmany(1000):
                        for row in batch:
                            copy.write_row(row)
                            copied += 1
            if copied != len(candidates):
                raise RuntimeError("Source fixture snapshot changed while being copied")
            target.execute("""CREATE TEMP TABLE sync_fixture_old_scopes ON COMMIT DROP AS
                SELECT DISTINCT old.season,old.league_id FROM statarena.fixtures old
                JOIN sync_fixture_input incoming USING(id) WHERE incoming.updated_at>old.updated_at""")
            target.execute("""CREATE TEMP TABLE sync_fixture_changes (
                id text PRIMARY KEY,season text NOT NULL,league_id text NOT NULL
            ) ON COMMIT DROP""")
            target.execute("""WITH changes AS (
                INSERT INTO statarena.fixtures AS current(id,league_id,season,day,status,body,updated_at)
                SELECT id,league_id,season,day,status,body,updated_at FROM sync_fixture_input
                ON CONFLICT(id) DO UPDATE SET league_id=excluded.league_id,season=excluded.season,
                    day=excluded.day,status=excluded.status,body=excluded.body,updated_at=excluded.updated_at
                WHERE excluded.updated_at>current.updated_at
                RETURNING id,season,league_id
            ) INSERT INTO sync_fixture_changes SELECT id,season,league_id FROM changes""")
            changed = target.execute("SELECT count(*) FROM sync_fixture_changes").fetchone()[0]
            mismatch = target.execute("""SELECT count(*) FROM sync_fixture_changes changed
                JOIN sync_fixture_input incoming USING(id) JOIN statarena.fixtures actual USING(id)
                WHERE to_jsonb(actual) IS DISTINCT FROM to_jsonb(incoming)""").fetchone()[0]
            if mismatch:
                raise RuntimeError("Synchronized fixture rows differ from the source snapshot")
            target.execute("""INSERT INTO statarena.dirty_partitions(season,league_id,changed_at)
                SELECT season,league_id,transaction_timestamp() FROM (
                    SELECT season,league_id FROM sync_fixture_old_scopes
                    UNION SELECT season,league_id FROM sync_fixture_changes
                ) scopes
                ON CONFLICT(season,league_id) DO UPDATE SET changed_at=
                    greatest(statarena.dirty_partitions.changed_at,excluded.changed_at)""")
            report.update(rows_copied=copied, rows_changed=changed,
                          concurrently_preserved=copied-changed, verification_mismatches=mismatch)
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
        print(json.dumps(reconcile(source, target, args.mode, args.limit)), flush=True)
    finally:
        source.close()
        target.close()


if __name__ == "__main__":
    main()
