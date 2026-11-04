"""Full PostgreSQL workflow for the approved Orion schema; written before migrations."""
import datetime
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import traceback

import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get("STATARENA_ORION_EVIDENCE", ROOT / "docs/verification/orion-schema-pilot-20261104/local"))
SPEC = json.loads((ROOT / "docs/architecture/orion-plan-20261104/target-schema.proposed.json").read_text())
TABLES = {t["qualified_name"]: t for s in SPEC["schemas"] for t in s["tables"] if t["phase"] != "models"}
BIN = Path(os.environ.get("STATARENA_PG_BIN", "/tmp/statarena-cache-test-tools/node_modules/@embedded-postgres/darwin-arm64/native/bin"))
REPORT = {"startedUtc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
          "command": "PYTHONPATH=/tmp/statarena-publication-test-python python3 tests/orion_schema_postgres.py",
          "setup": "PROTOCOL.md; fresh owned loopback PostgreSQL18.6; synthetic two-season graph declared in this script, no provider call or remote DB.",
          "expected": "Approved schema, transactional histories, integrity failures, snapshot immutability, idempotent migrations and restricted runtime role.",
          "checks": [], "passed": False}

def check(name, condition, details=None):
    REPORT["checks"].append({"name": name, "passed": bool(condition), "details": details})
    if not condition:
        raise AssertionError(name)

def insert(db, relation, **values):
    assert relation in TABLES
    override = sql.SQL("OVERRIDING SYSTEM VALUE") if any(n in values and c.get("identity") for n, c in TABLES[relation]["columns"].items()) else sql.SQL("")
    result = db.execute(sql.SQL("INSERT INTO {} ({}) {} VALUES ({}) RETURNING *").format(
        sql.Identifier(*relation.split(".")), sql.SQL(",").join(map(sql.Identifier, values)),
        override, sql.SQL(",").join(sql.Placeholder() for _ in values)), list(values.values()))
    columns = [c.name for c in result.description]
    return dict(zip(columns, result.fetchone()))

def refused(db, name, action, allowed=("23514", "23503", "23505", "55000", "42501")):
    try:
        with db.transaction():
            action()
            db.execute("SET CONSTRAINTS ALL IMMEDIATE")
    except psycopg.Error as error:
        check(name, error.sqlstate in allowed, {"sqlstate": error.sqlstate})
    else:
        check(name, False, "Invalid transaction was accepted")

def seed(db):
    source = insert(db, "ingest.sources", code="e2e", name="Synthetic contract source")
    dataset = insert(db, "ingest.source_datasets", source_id=source["id"], dataset_key="two-seasons", contract_version="e2e-v1")
    document = insert(db, "ingest.source_documents", dataset_id=dataset["id"], source_id=source["id"],
                      content_sha256="a" * 64, retrieved_at=datetime.datetime.now(datetime.timezone.utc),
                      source_url="https://example.invalid/pitch/e2e")
    record = insert(db, "ingest.source_records", source_id=source["id"], document_id=document["id"],
                    locator_kind="whole_document", locator="/", record_kind="match")
    evidence = dict(source_id=source["id"], source_record_id=record["id"], canonical_policy_version="e2e-v1")
    competition = insert(db, "football.competitions", name="E2E league", slug="e2e-league", competition_type="league", gender="men")
    seasons = [insert(db, "football.competition_seasons", competition_id=competition["id"], season_key=s, label=s) for s in ["2025/2026", "2026/2027"]]
    teams = [insert(db, "football.teams", name=n, slug=n.lower(), team_type="club", gender="men") for n in ["Home", "Away", "Other"]]
    player = insert(db, "football.players", id=9007199254740993, display_name="Known player")
    matches = []
    for season in seasons:
        match = insert(db, "football.matches", competition_season_id=season["id"], kickoff_precision="unknown", status="finished", **evidence)
        for side, team in zip(["home", "away"], teams[:2]):
            insert(db, "football.match_teams", match_id=match["id"], side=side, team_id=team["id"], **evidence)
        db.execute("UPDATE football.matches SET publication_state='published' WHERE id=%s", (match["id"],))
        insert(db, "football.match_players", match_id=match["id"], player_id=player["id"], team_id=teams[0]["id"], **evidence)
        insert(db, "football.player_match_stats", match_id=match["id"], player_id=player["id"], team_id=teams[0]["id"],
               period_code="full_match", goals=0, assists=None, minutes_played=None, goals_prevented=Decimal("-0.25"), **evidence)
        matches.append(match)
    return locals()

def workflow(db):
    relations = db.execute("SELECT table_schema,table_name FROM information_schema.tables WHERE table_schema IN ('ingest','football','analytics') AND table_type='BASE TABLE'").fetchall()
    check("all active approved tables exist", {".".join(r) for r in relations} == set(TABLES), len(relations))
    actual = db.execute("SELECT table_schema,table_name,column_name,is_nullable FROM information_schema.columns WHERE table_schema IN ('ingest','football','analytics') ORDER BY table_schema,table_name,ordinal_position").fetchall()
    wanted = {(n, c, "YES" if d["nullable"] else "NO") for n, t in TABLES.items() for c, d in t["columns"].items()}
    check("all 1897 column names and nullability match", {(s+"."+t, c, nullable) for s,t,c,nullable in actual} == wanted, len(actual))
    check("350 real foreign keys", db.execute("SELECT count(*) FROM pg_constraint c JOIN pg_namespace n ON n.oid=c.connamespace WHERE c.contype='f' AND n.nspname IN ('ingest','football','analytics')").fetchone()[0] == 350)
    db.execute("SELECT set_config('statarena.transform_version','e2e-v1',false)")
    with db.transaction():
        state = seed(db)
    player = state["player"]; first = state["matches"][0]["id"]
    row = db.execute("SELECT goals,assists,minutes_played,goals_prevented FROM football.player_match_stats WHERE match_id=%s", (first,)).fetchone()
    check("zero null unknown minutes and signed values retained", row == (0, None, None, Decimal("-0.25")), [str(x) for x in row])
    check("public-size identity is exact BIGINT", db.execute("SELECT id FROM football.players WHERE id=%s", (player["id"],)).fetchone()[0] == 9007199254740993)
    before = db.execute("SELECT row_version_id FROM football.players WHERE id=%s", (player["id"],)).fetchone()[0]
    with db.transaction():
        db.execute("UPDATE football.players SET display_name='Known player' WHERE id=%s", (player["id"],))
    check("identical update does not create a version", db.execute("SELECT row_version_id FROM football.players WHERE id=%s", (player["id"],)).fetchone()[0] == before)
    with db.transaction():
        db.execute("UPDATE football.players SET display_name='Corrected name' WHERE id=%s", (player["id"],))
    after = db.execute("SELECT row_version_id FROM football.players WHERE id=%s", (player["id"],)).fetchone()[0]
    check("correction retains both typed versions", after != before and db.execute("SELECT display_name FROM football.players_history WHERE row_version_id=%s", (before,)).fetchone()[0] == "Known player")
    refused(db, "history cannot be altered", lambda: db.execute("UPDATE football.players_history SET display_name='lost' WHERE row_version_id=%s", (before,)))
    refused(db, "registry cannot contain an orphan", lambda: db.execute("INSERT INTO ingest.row_versions(relation_code,logical_key,revision_no,provenance_kind,transform_version,content_sha256) VALUES ('football.players','[999999]',1,'manual','e2e-v1',%s)", ("b"*64,)))
    refused(db, "published match cannot lose a side", lambda: db.execute("DELETE FROM football.match_teams WHERE match_id=%s AND side='away'", (first,)))
    refused(db, "known opponents must differ", lambda: db.execute("UPDATE football.match_teams SET team_id=%s WHERE match_id=%s AND side='away'", (state["teams"][0]["id"], first)))
    refused(db, "played match cannot have an unresolved opponent", lambda: db.execute("UPDATE football.match_teams SET team_id=NULL,participant_label='TBD' WHERE match_id=%s AND side='away'", (first,)))
    refused(db, "stat cannot move to the wrong participant team", lambda: db.execute("UPDATE football.player_match_stats SET team_id=%s WHERE match_id=%s", (state["teams"][1]["id"], first)))
    refused(db, "non-finite sport value rejected", lambda: db.execute("UPDATE football.player_match_stats SET xg='NaN'::double precision WHERE match_id=%s", (first,)))
    refused(db, "business document cannot hide in quality flags", lambda: db.execute("UPDATE football.matches SET quality_flags=%s::jsonb WHERE id=%s", ('{"player":{"name":"hidden"}}', first)))
    with db.transaction():
        snapshot = insert(db, "ingest.dataset_snapshots", snapshot_key="e2e-two-seasons", transform_version="e2e-v1", source_priority_version="e2e-v1")
        db.execute("INSERT INTO ingest.dataset_snapshot_rows(snapshot_id,relation_code,logical_key,row_version_id) SELECT %s,relation_code,logical_key,id FROM ingest.row_versions v WHERE NOT is_tombstone AND revision_no=(SELECT max(w.revision_no) FROM ingest.row_versions w WHERE (w.relation_code,w.logical_key)=(v.relation_code,v.logical_key))", (snapshot["id"],))
        db.execute("UPDATE ingest.dataset_snapshots SET status='sealed' WHERE id=%s", (snapshot["id"],))
    refused(db, "sealed snapshot membership immutable", lambda: db.execute("DELETE FROM ingest.dataset_snapshot_rows WHERE snapshot_id=%s", (snapshot["id"],)))
    refused(db, "sealed snapshot cannot reopen", lambda: db.execute("UPDATE ingest.dataset_snapshots SET status='draft' WHERE id=%s", (snapshot["id"],)))
    with db.transaction():
        db.execute("UPDATE football.players SET display_name='Later correction' WHERE id=%s", (player["id"],))
    check("old snapshot survives current correction", db.execute("SELECT h.display_name FROM ingest.dataset_snapshot_rows s JOIN football.players_history h ON h.row_version_id=s.row_version_id WHERE s.snapshot_id=%s AND s.relation_code='football.players' AND h.id=%s", (snapshot["id"], player["id"])).fetchone()[0] == "Corrected name")
    refused(db, "runtime cannot update business data", lambda: (db.execute("SET LOCAL ROLE statarena_runtime"), db.execute("UPDATE football.players SET display_name='bad'")))
    check("new SQL facts have no legacy file dependency", db.execute("SELECT count(*) FROM pg_namespace WHERE nspname='statarena'").fetchone()[0] == 0)
    check("two seasons share the same entity", db.execute("SELECT count(DISTINCT m.competition_season_id),count(DISTINCT p.player_id) FROM football.matches m JOIN football.match_players p ON p.match_id=m.id").fetchone() == (2, 1))

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix="statarena-orion-pg-"))
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0)); port = listener.getsockname()[1]
    started = False
    try:
        REPORT["engine"] = subprocess.check_output([str(BIN / "postgres"), "--version"], text=True).strip()
        if not REPORT["engine"].endswith("18.6"):
            raise RuntimeError("Pilot requires PostgreSQL18.6")
        subprocess.run([str(BIN/"initdb"), "-D", str(directory), "-U", "orion_owner", "--auth=trust", "--encoding=UTF8", "--no-locale"], check=True, capture_output=True, text=True)
        subprocess.run([str(BIN/"pg_ctl"), "-D", str(directory), "-l", str(OUT/"postgres.log"), "-o", f"-h 127.0.0.1 -p {port} -k {directory}", "-w", "start"], check=True, capture_output=True, text=True)
        started = True
        url = f"postgresql://orion_owner@127.0.0.1:{port}/postgres"
        with psycopg.connect(url, autocommit=True) as db:
            db.execute("CREATE ROLE statarena_ingest NOLOGIN")
            db.execute("CREATE ROLE statarena_runtime NOLOGIN")
        env = {**os.environ, "TEST_DATABASE_URL": url}
        argv = [sys.executable, "dashboard/scripts/orion_migrate.py", "--local", "--report", str(OUT/"migration.json")]
        result = subprocess.run(argv, cwd=ROOT, env=env, capture_output=True, text=True)
        (OUT/"migration.log").write_text(result.stdout + result.stderr)
        check("migration command succeeds", result.returncode == 0, {"exitCode": result.returncode})
        with psycopg.connect(url, autocommit=True) as db:
            workflow(db)
            before = db.execute("SELECT version,content_sha256,applied_at FROM ingest.schema_migrations ORDER BY version").fetchall()
        replay = subprocess.run(argv, cwd=ROOT, env=env, capture_output=True, text=True)
        check("migration replay succeeds", replay.returncode == 0)
        with psycopg.connect(url, autocommit=True) as db:
            check("migration journal unchanged on replay", db.execute("SELECT version,content_sha256,applied_at FROM ingest.schema_migrations ORDER BY version").fetchall() == before)
        REPORT["passed"] = True
    except Exception as error:
        REPORT["error"] = {"type": type(error).__name__, "message": str(error)[:1500]}
        (OUT/"failure.log").write_text(traceback.format_exc())
    finally:
        if started:
            stopped = subprocess.run([str(BIN/"pg_ctl"), "-D", str(directory), "-m", "fast", "-w", "stop"], capture_output=True, text=True)
            REPORT["ownedPostgresStopped"] = stopped.returncode == 0
        REPORT["finishedUtc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        (OUT/"result.json").write_text(json.dumps(REPORT, indent=2, default=str) + "\n")
        print(json.dumps(REPORT, default=str))
    return 0 if REPORT["passed"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
