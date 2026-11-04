"""Read-only RDS capacity, concurrency and pilot-scope baseline; no source bodies."""
import datetime
import json
from pathlib import Path
import subprocess
import psycopg

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
now = datetime.datetime.now(datetime.timezone.utc)
report = {"atUtc": now.isoformat(), "command": "PYTHONPATH=/tmp/statarena-publication-test-python python3 docs/verification/orion-schema-pilot-20261104/preflight.py",
          "setup": "Existing pgpass ingestion login, verified TLS, read-only transaction and20s deadline. AWS metadata only; no schema/data/infrastructure write.", "queries": {}, "errors": []}
queries = {
    "identity": "SELECT current_database(),current_user,current_setting('server_version'),current_setting('transaction_read_only'),(SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid())",
    "schemas": "SELECT nspname,pg_get_userbyid(nspowner) FROM pg_namespace WHERE nspname NOT LIKE 'pg_%' AND nspname<>'information_schema' ORDER BY 1",
    "databases": "SELECT datname,pg_database_size(oid) FROM pg_database WHERE datname IN ('postgres','statarena','statarena_prod') ORDER BY 1",
    "access": "SELECT has_database_privilege(current_database(),'CREATE'),has_schema_privilege('statarena','USAGE'),has_schema_privilege('statarena_app','USAGE')",
    "activity": "SELECT datname,usename,application_name,state,wait_event_type,count(*),max(extract(epoch FROM now()-xact_start)) FROM pg_stat_activity WHERE datname IN ('statarena','statarena_prod') GROUP BY 1,2,3,4,5 ORDER BY 1,2,3,4",
    "scopes": "SELECT league_id,season,count(*) matches,count(*) FILTER(WHERE status='finished') finished,count(*) FILTER(WHERE status='not_started') upcoming FROM statarena.fixtures GROUP BY 1,2 ORDER BY 1,2",
    "fixtureKeys": "SELECT DISTINCT jsonb_object_keys(body) FROM (SELECT body FROM statarena.fixtures ORDER BY id LIMIT 10) f ORDER BY 1",
    "documentPaths": "SELECT source_path,status,document_count,error_count FROM statarena.file_document_sources WHERE status='ready' ORDER BY source_path LIMIT 16",
    "publisherLease": "SELECT count(*) FROM pg_locks WHERE locktype='advisory' AND objid=97813003 AND granted",
}
with psycopg.connect(host="statarena-postgres.clcy2iqyajbl.us-east-2.rds.amazonaws.com", dbname="statarena_prod", user="statarena_ingest",
                     sslmode="verify-full", sslrootcert=str(ROOT/"dashboard/backend/certs/rds-us-east-2.pem"), connect_timeout=7,
                     autocommit=True, options="-c default_transaction_read_only=on -c statement_timeout=20000 -c lock_timeout=1000",
                     application_name="statarena-orion-pilot-preflight") as db:
    db.execute("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY")
    for name, query in queries.items():
        try:
            with db.transaction():
                cursor=db.execute(query)
                report["queries"][name]={"sql":query,"columns":[c.name for c in cursor.description],"rows":cursor.fetchall()}
        except psycopg.Error as error:
            report["errors"].append({"query":name,"sqlstate":error.sqlstate,"error":type(error).__name__})
    db.execute("ROLLBACK")
for name, args in {
    "rds": ["rds","describe-db-instances","--db-instance-identifier","statarena-postgres","--query","DBInstances[0].{Version:EngineVersion,Class:DBInstanceClass,StorageGiB:AllocatedStorage,Status:DBInstanceStatus,Pending:PendingModifiedValues}"],
    "freeStorage": ["cloudwatch","get-metric-statistics","--namespace","AWS/RDS","--metric-name","FreeStorageSpace","--dimensions","Name=DBInstanceIdentifier,Value=statarena-postgres","--start-time",(now-datetime.timedelta(minutes=30)).isoformat(),"--end-time",now.isoformat(),"--period","300","--statistics","Minimum"],
}.items():
    result=subprocess.run(["aws","--profile","statarena","--region","us-east-2",*args,"--output","json"],capture_output=True,text=True)
    if result.returncode: report["errors"].append({"metadata":name,"exitCode":result.returncode})
    else: report[name]=json.loads(result.stdout)
(OUT/"preflight.json").write_text(json.dumps(report,indent=2,default=str)+"\n")
print(json.dumps({"identity":report["queries"].get("identity"),"schemas":report["queries"].get("schemas"),"rds":report.get("rds"),"freeStorage":report.get("freeStorage"),"scopePairs":len(report["queries"].get("scopes",{}).get("rows",[])),"errors":report["errors"]},default=str))
