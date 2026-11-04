"""Read-only domain-reference audit; aggregates only, no business row export."""
import datetime
import json
from pathlib import Path
import subprocess

import psycopg

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
HOST = "statarena-postgres.clcy2iqyajbl.us-east-2.rds.amazonaws.com"
QUERIES = {
    "matchReferences": """SELECT count(*) matches,
        count(*) FILTER (WHERE m.home_id IS NOT NULL AND h.id IS NULL) missing_home_team,
        count(*) FILTER (WHERE m.away_id IS NOT NULL AND a.id IS NULL) missing_away_team,
        count(*) FILTER (WHERE c.id IS NULL) missing_competition,
        count(*) FILTER (WHERE cs.competition_id IS NULL) missing_competition_season
        FROM statarena_app.matches m
        LEFT JOIN statarena_app.teams h ON h.id=m.home_id
        LEFT JOIN statarena_app.teams a ON a.id=m.away_id
        LEFT JOIN statarena_app.competitions c ON c.id=m.league_id
        LEFT JOIN statarena_app.competition_seasons cs
          ON cs.competition_id=m.league_id AND cs.season=m.season""",
    "appearanceReferences": """SELECT count(*) appearances,
        count(*) FILTER (WHERE a.team_id IS NOT NULL AND t.id IS NULL) missing_team,
        count(*) FILTER (WHERE a.match_id IS NULL) null_match,
        count(*) FILTER (WHERE a.match_id IS NOT NULL AND m.id IS NULL) missing_match,
        count(*) FILTER (WHERE p.id IS NULL) missing_player
        FROM statarena_app.appearances a
        LEFT JOIN statarena_app.teams t ON t.id=a.team_id
        LEFT JOIN statarena_app.matches m ON m.id=a.match_id
        LEFT JOIN statarena_app.players p ON p.id=a.player_ref""",
    "fixtureReferences": """SELECT count(*) fixtures,
        count(*) FILTER (WHERE f.home_team_id IS NOT NULL AND h.id IS NULL) missing_home_team,
        count(*) FILTER (WHERE f.away_team_id IS NOT NULL AND a.id IS NULL) missing_away_team,
        count(*) FILTER (WHERE f.league_id IS NOT NULL AND c.id IS NULL) missing_competition
        FROM statarena_app.fixtures f
        LEFT JOIN statarena_app.teams h ON h.id=f.home_team_id
        LEFT JOIN statarena_app.teams a ON a.id=f.away_team_id
        LEFT JOIN statarena_app.competitions c ON c.id=f.league_id""",
    "rawVsServingFixtureStatus": """SELECT s.status source_status,a.status serving_status,count(*)
        FROM statarena.fixtures s JOIN statarena_app.fixtures a ON a.id=s.id
        WHERE s.status IS DISTINCT FROM a.status
        GROUP BY 1,2 ORDER BY 1,2""",
    "matchStatuses": "SELECT status,count(*) FROM statarena_app.matches GROUP BY status ORDER BY status",
    "foreignTables": """SELECT n.nspname,c.relname FROM pg_class c
        JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE c.relkind='f' AND n.nspname NOT LIKE 'pg_%' ORDER BY 1,2""",
}
report = {
    "atUtc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "command": "PYTHONPATH=/tmp/statarena-publication-test-python python3 docs/verification/aws-architecture-audit-20261104/domain_integrity.py",
    "setup": "Existing RDS ingestion SSM parameter, credentials held only in memory; TLS verify-full; repeatable READ ONLY transaction;20s statement timeout; no source/provider reads, SQL writes, schema changes or business row export.",
    "expected": "An authoritative domain model would resolve populated entity IDs to canonical rows and keep published fixture statuses aligned. The current partial projection can fail those checks: report counts without deleting or repairing anything. Missing/null IDs are distinguished. No full source-equality claim.",
    "queries": QUERIES, "results": {},
}
secret = json.loads(json.loads(subprocess.check_output([
    "aws", "--profile", "statarena", "--region", "us-east-2", "ssm", "get-parameter",
    "--name", "/statarena/app/rds-ingest", "--with-decryption", "--output", "json"],
    text=True))["Parameter"]["Value"])
assert secret["host"] == HOST and secret["database"] == "statarena_prod"
with psycopg.connect(host=HOST, dbname=secret["database"], user=secret["username"],
                      password=secret["password"], sslmode="verify-full",
                      sslrootcert=str(ROOT / "dashboard/backend/certs/rds-us-east-2.pem"),
                      connect_timeout=7, autocommit=True,
                      options="-c default_transaction_read_only=on -c statement_timeout=20000 -c lock_timeout=1000 -c max_parallel_workers_per_gather=0",
                      application_name="statarena-architecture-audit") as db:
    db.execute("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY")
    report["identity"] = db.execute("SELECT current_database(),current_user,current_setting('transaction_read_only'),(SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid())").fetchone()
    assert report["identity"][0] == "statarena_prod" and report["identity"][2:] == ("on", True)
    for name, query in QUERIES.items():
        try:
            with db.transaction():
                cursor = db.execute(query)
                report["results"][name] = {"columns": [c.name for c in cursor.description], "rows": cursor.fetchall()}
        except psycopg.Error as error:
            report["results"][name] = {"error": type(error).__name__, "code": error.sqlstate}
    db.execute("ROLLBACK")
del secret
report["finishedUtc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
(OUT / "domain-integrity.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
print(json.dumps({"finishedUtc": report["finishedUtc"], "results": report["results"]}))
