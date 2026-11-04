"""Read-only RDS capacity/publication receipt. Never persists SSM credentials."""
import datetime as dt
import json
from pathlib import Path
import subprocess
import sys

import psycopg

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def aws(*args):
    p = subprocess.run(
        ["aws", "--profile", "statarena", "--region", "us-east-2", "--no-cli-pager", "--output", "json", *args],
        capture_output=True, text=True,
    )
    if p.returncode:
        raise RuntimeError("AWS read failed: " + args[0] + " " + args[1])
    return json.loads(p.stdout)


def run(phase):
    if not phase.replace("-", "").isalnum():
        raise ValueError("Use a simple receipt label")
    c = json.loads(aws("ssm", "get-parameter", "--name", "/statarena/app/rds-runtime", "--with-decryption")["Parameter"]["Value"])
    if c["host"] != "statarena-postgres.clcy2iqyajbl.us-east-2.rds.amazonaws.com" or c["database"] != "statarena_prod":
        raise ValueError("Unexpected database target")
    with psycopg.connect(
        host=c["host"], dbname=c["database"], user=c["username"], password=c["password"],
        sslmode="verify-full", sslrootcert=str(ROOT / "dashboard/backend/certs/rds-us-east-2.pem"),
        connect_timeout=5, options="-c default_transaction_read_only=on -c statement_timeout=10000 -c lock_timeout=1000",
        autocommit=True, application_name="statarena-capacity-audit",
    ) as db:
        identity = db.execute("SELECT current_database(),current_user,current_setting('transaction_read_only'),ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()").fetchone()
        size = db.execute("SELECT pg_database_size(current_database())").fetchone()[0]
        # Statistics estimates are explicitly labelled; do not scan every large relation.
        tables = db.execute("""SELECT schemaname,relname,n_live_tup,pg_total_relation_size(relid)
            FROM pg_stat_user_tables ORDER BY pg_total_relation_size(relid) DESC""").fetchall()
        sessions = db.execute("""SELECT application_name,usename,state,count(*) FROM pg_stat_activity
            WHERE datname=current_database() GROUP BY application_name,usename,state""").fetchall()
        queued = db.execute("SELECT count(*) FROM statarena_app.publication_jobs").fetchone()[0]
        state = db.execute("SELECT generation::text FROM statarena_app.publications WHERE singleton").fetchone()
        partitions = db.execute("SELECT count(*) FROM statarena_app.partitions").fetchone()[0]
        workflow = db.execute("SELECT status,remaining,started_at,updated_at,completed_at FROM statarena_app.workflow_state WHERE workflow='relational-materialize'").fetchone()
    instance = aws("rds", "describe-db-instances", "--db-instance-identifier", "statarena-postgres")["DBInstances"][0]
    end = dt.datetime.now(dt.timezone.utc)
    start = end - dt.timedelta(minutes=10)
    metrics = {}
    for name in ("FreeStorageSpace", "DatabaseConnections", "CPUUtilization", "FreeableMemory", "DiskQueueDepth", "CPUCreditBalance"):
        data = aws("cloudwatch", "get-metric-statistics", "--namespace", "AWS/RDS", "--metric-name", name,
                   "--dimensions", "Name=DBInstanceIdentifier,Value=statarena-postgres", "--start-time", start.isoformat(),
                   "--end-time", end.isoformat(), "--period", "60", "--statistics", "Average", "Minimum", "Maximum")
        metrics[name] = sorted(data["Datapoints"], key=lambda x: x["Timestamp"])
    out = {
        "atUtc": end.isoformat(), "phase": phase,
        "command": f"PYTHONPATH=/tmp/statarena-archive-remat-pg/python python3 docs/verification/aws-release-20261104/inventory.py {phase}",
        "setup": "Existing Ohio RDS; SSM runtime identity; verified public regional CA; SELECT-only startup; bounded queries; AWS metric reads",
        "expected": {"readOnly": "on", "tls": True, "database": "statarena_prod", "sqlBudgetBytes": 16000000000, "reserveBytes": 256000000},
        "actual": {"database": identity[0], "user": identity[1], "readOnly": identity[2], "tls": identity[3],
                   "databaseBytes": size, "generation": state[0] if state else None, "partitionsExact": partitions,
                   "partitionJobsExact": queued, "workflowState": workflow,
                   "tables": [{"schema": t[0], "table": t[1], "liveRowsEstimate": t[2], "physicalBytesIncludingIndexes": t[3]} for t in tables],
                   "sessions": [{"application": s[0], "user": s[1], "state": s[2], "count": s[3]} for s in sessions],
                   "instanceClass": instance["DBInstanceClass"], "allocatedGiB": instance["AllocatedStorage"],
                   "instanceStatus": instance["DBInstanceStatus"], "metricsLastTenMinutes": metrics},
        "limits": "Relation row counts are PostgreSQL estimates. Workflow state is an end-of-invocation receipt and may lag the active publisher. CloudWatch samples are observational and not a before/after causal benchmark.",
    }
    (HERE / f"inventory-{phase}.json").write_text(json.dumps(out, indent=2, default=str) + "\n")
    print(json.dumps({"phase": phase, "databaseBytes": size, "partitions": partitions, "queued": queued, "readOnly": identity[2]}))
    if identity[0] != "statarena_prod" or identity[2] != "on" or identity[3] is not True:
        raise RuntimeError("Read-only TLS acceptance failed")


if __name__ == "__main__":
    try:
        run(sys.argv[1])
    except Exception as error:
        print("Capacity receipt failed: " + type(error).__name__, file=sys.stderr)
        raise SystemExit(1)
