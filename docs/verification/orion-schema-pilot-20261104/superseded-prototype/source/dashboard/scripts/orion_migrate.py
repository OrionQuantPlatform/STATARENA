"""Apply only the approved Orion migrations with locking and immutable checksums."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
from urllib.parse import urlsplit
import psycopg

ROOT = Path(__file__).resolve().parents[2]
FILES = [ROOT/"dashboard/backend/migrations"/name for name in ["012_orion_domain.sql", "013_orion_integrity.sql"]]

def aws(*args):
    process = subprocess.run(["aws", "--profile", "statarena", "--region", "us-east-2", *args, "--output", "json"], capture_output=True, text=True, check=True)
    return json.loads(process.stdout)

def connect(args):
    if args.local:
        url = os.environ["TEST_DATABASE_URL"]
        if urlsplit(url).hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("--local requires an explicit loopback test database")
        return psycopg.connect(url, autocommit=True)
    if not args.apply:
        raise ValueError("RDS application requires the explicit --apply action")
    state = aws("rds", "describe-db-instances", "--db-instance-identifier", "statarena-postgres")["DBInstances"][0]
    if state["Engine"] != "postgres" or state["EngineVersion"] != "18.6" or state["DBInstanceStatus"] != "available" or state["PendingModifiedValues"]:
        raise ValueError("RDS version or available-state precondition failed")
    now = datetime.datetime.now(datetime.timezone.utc)
    metric = aws("cloudwatch", "get-metric-statistics", "--namespace", "AWS/RDS", "--metric-name", "FreeStorageSpace", "--dimensions", "Name=DBInstanceIdentifier,Value=statarena-postgres", "--start-time", (now-datetime.timedelta(minutes=20)).isoformat(), "--end-time", now.isoformat(), "--period", "300", "--statistics", "Minimum")
    points = sorted(metric["Datapoints"], key=lambda p:p["Timestamp"])
    if not points or points[-1]["Minimum"] < 8*1024**3:
        raise ValueError("No verified8GiB free-storage margin; stop before schema application")
    # Existing preconfigured parameter; values stay only in memory, never in logs/reports/argv.
    secret = json.loads(aws("ssm", "get-parameter", "--name", "/statarena/app/rds-admin", "--with-decryption")["Parameter"]["Value"])
    if secret["host"] != state["Endpoint"]["Address"]:
        raise ValueError("Configured RDS host mismatch")
    return psycopg.connect(host=secret["host"], dbname="statarena_prod", user=secret["username"], password=secret["password"],
                          sslmode="verify-full", sslrootcert=str(ROOT/"dashboard/backend/certs/rds-us-east-2.pem"),
                          connect_timeout=7, autocommit=True, application_name="statarena-orion-schema-migration")

def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--local", action="store_true")
    mode.add_argument("--rds", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = {"atUtc":datetime.datetime.now(datetime.timezone.utc).isoformat(), "mode":"local" if args.local else "existing-rds", "migrations":[], "passed":False}
    try:
        scripts = [(f, f.read_text(), hashlib.sha256(f.read_bytes()).hexdigest()) for f in FILES]
        with connect(args) as db:
            db.execute("SET statement_timeout='90s'")
            db.execute("SET lock_timeout='3s'")
            identity = db.execute("SELECT current_database(),current_user,current_setting('server_version')").fetchone()
            if not args.local and identity[0] != "statarena_prod":
                raise ValueError("Wrong application database")
            report["identity"] = identity
            db.execute("SELECT pg_advisory_lock(hashtextextended('statarena-orion-schema',0))")
            try:
                for path, body, digest in scripts:
                    version = path.name.split("_",1)[0]
                    with db.transaction():
                        exists = db.execute("SELECT to_regclass('ingest.schema_migrations') IS NOT NULL").fetchone()[0]
                        prior = db.execute("SELECT content_sha256 FROM ingest.schema_migrations WHERE version=%s", (version,)).fetchone() if exists else None
                        if prior:
                            if prior[0] != digest:
                                raise ValueError("Sealed migration checksum mismatch: " + version)
                            report["migrations"].append({"version":version,"action":"already-applied","sha256":digest})
                            continue
                        db.execute(body)
                        db.execute("INSERT INTO ingest.schema_migrations(version,content_sha256,applied_at,code_commit) VALUES (%s,%s,now(),%s)", (version,digest,os.environ.get("STATARENA_CODE_COMMIT")))
                        report["migrations"].append({"version":version,"action":"applied","sha256":digest})
            finally:
                db.execute("SELECT pg_advisory_unlock(hashtextextended('statarena-orion-schema',0))")
        report["passed"] = True
    except Exception as error:
        # Exception text may contain connection information; report only class and SQLSTATE.
        report["error"] = {"type":type(error).__name__, "sqlstate":getattr(error,"sqlstate",None)}
        if args.local:
            report["error"]["message"] = str(error)[:1800]
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,indent=2,default=str)+"\n")
    print(json.dumps(report,default=str))
    return 0 if report["passed"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
