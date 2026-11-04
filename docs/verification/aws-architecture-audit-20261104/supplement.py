"""Bounded read-only audit: metadata, aggregate coverage, runtime and pause readbacks."""
import datetime
import json
from pathlib import Path
import subprocess
import urllib.error
import urllib.parse
import urllib.request

import psycopg

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
HOST = "statarena-postgres.clcy2iqyajbl.us-east-2.rds.amazonaws.com"


def aws(*args):
    return json.loads(subprocess.check_output(
        ["aws", "--profile", "statarena", "--region", "us-east-2", *args,
         "--output", "json"], text=True))


def gh(*args):
    return json.loads(subprocess.check_output(["gh", *args], cwd=ROOT, text=True))


def http(url, method="GET"):
    request = urllib.request.Request(url, method=method)
    try:
        response = urllib.request.urlopen(request, timeout=20)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        body = response.read(2048) if method == "GET" else b""
        result = {"url": url, "method": method, "status": response.status,
                  "headers": {k: v for k, v in response.headers.items()
                              if k.lower() in ("content-type", "content-length", "x-cache", "cache-control")},
                  "downloadedBodyBytes": len(body)}
        if method == "GET":
            result["body"] = json.loads(body)
        return result


queries = {
    "payloadArchiveMetadata": """SELECT namespace,path,size,content_type,chunk_count
        FROM statarena.file_payloads WHERE namespace IN ('migration','release')
        ORDER BY namespace,path""",
    "currentDocumentsView": "SELECT pg_get_viewdef('statarena.current_file_documents'::regclass,true)",
    "familiesWithoutCoreByFixtureStatus": """WITH ids AS (
        SELECT DISTINCT f.match_id FROM statarena_app.match_families f
        LEFT JOIN statarena_app.matches m ON m.id=f.match_id WHERE m.id IS NULL)
        SELECT coalesce(s.status,'source-fixture-absent') source_status,
               coalesce(a.status,'serving-fixture-absent') serving_status,count(*)
        FROM ids LEFT JOIN statarena.fixtures s ON s.id=ids.match_id
        LEFT JOIN statarena_app.fixtures a ON a.id=ids.match_id
        GROUP BY 1,2 ORDER BY 1,2""",
    "jobStates": "SELECT state,count(*) FROM statarena.jobs GROUP BY state ORDER BY state",
    "activityByDb": """SELECT datname,application_name,usename,state,count(*)
        FROM pg_stat_activity WHERE datname IN ('statarena','statarena_prod')
        GROUP BY 1,2,3,4 ORDER BY 1,2,3,4""",
    "publisherLease": "SELECT count(*) FROM pg_locks WHERE locktype='advisory' AND objid=97813003 AND granted",
    "workflowState": "SELECT workflow,status,remaining,started_at,completed_at,updated_at FROM statarena_app.workflow_state ORDER BY workflow",
    "exampleImage": "SELECT path FROM statarena_app.assets WHERE path LIKE '%.webp' ORDER BY path LIMIT 1",
}
report = {
    "atUtc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "command": "PYTHONPATH=/tmp/statarena-publication-test-python python3 docs/verification/aws-architecture-audit-20261104/supplement.py",
    "setup": "Existing AWS profile and preconfigured SSM parameter, secret held only in process memory; TLS verify-full; READ ONLY repeatable snapshot;20s statement limit. Aggregates/catalogs/archive names only. No source bodies, provider calls or remote writes.",
    "queries": queries, "results": {},
}
assert aws("sts", "get-caller-identity", "--query", "Account") == "361769570630"
secret = json.loads(aws("ssm", "get-parameter", "--name", "/statarena/app/rds-ingest", "--with-decryption")["Parameter"]["Value"])
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
    for name, query in queries.items():
        try:
            with db.transaction():
                report["results"][name] = {"rows": db.execute(query).fetchall()}
        except psycopg.Error as error:
            report["results"][name] = {"error": type(error).__name__, "code": error.sqlstate}
    db.execute("ROLLBACK")
del secret
report["rds"] = aws("rds", "describe-db-instances", "--db-instance-identifier", "statarena-postgres", "--query", "DBInstances[0].{Identifier:DBInstanceIdentifier,Engine:Engine,Version:EngineVersion,Class:DBInstanceClass,AllocatedGiB:AllocatedStorage,Status:DBInstanceStatus,Pending:PendingModifiedValues}")
report["workflows"] = gh("workflow", "list", "--all", "--json", "id,name,path,state")
report["cancelledRun"] = gh("run", "view", "41813449529", "--json", "databaseId,status,conclusion,updatedAt,jobs")
report["canonicalHealth"] = http("https://statarena-analytics.vercel.app/api/health")
report["awsHealth"] = http("https://d317dq37z1tacb.cloudfront.net/api/health")
image = report["results"]["exampleImage"].get("rows", [])
if image:
    path = urllib.parse.quote(image[0][0].lstrip("/"), safe="/")
    report["imageHead"] = http("https://d2clu0phovomb8.cloudfront.net/" + path, "HEAD")
report["finishedUtc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
(OUT / "supplement.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
print(json.dumps({"finishedUtc": report["finishedUtc"], "queryErrors": [k for k,v in report["results"].items() if "error" in v], "cancelledRun": {k: report["cancelledRun"][k] for k in ("status","conclusion")}, "healthSources": [report[k]["body"].get("source") for k in ("canonicalHealth","awsHealth")], "imageHead": report.get("imageHead",{}).get("status")}))
