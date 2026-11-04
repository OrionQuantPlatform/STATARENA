"""One bounded exact-handler SQL pair on RDS; no row contents are written."""
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import time
import psycopg
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
CAPTURE = HERE / "reader-sql-20261104T163921235Z.json"
HOST = "statarena-postgres.clcy2iqyajbl.us-east-2.rds.amazonaws.com"
BINDS = ["2026/2027", "l_0ALvwF", 100]
stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
report = {"atUtc":dt.datetime.now(dt.timezone.utc).isoformat(),
          "command":"PYTHONPATH=/tmp/statarena-publication-test-python python3 docs/verification/orion-availability-20261104/compare_rds.py",
          "setup":"One production RDS connection via existing .pgpass, verified TLS, explicit read-only repeatable-read snapshot, 8s statement timeout. One baseline and one candidate SQL query, no writes or provider calls. Only canonical result hashes and counts are saved.",
          "expected":"Exact handler-generated baseline and revised candidate produce equal semantic result hashes from one generation, and each completes under the existing server deadline. A timeout makes equivalence unverified.",
          "queries":[], "passed":False}


def bind_sql(sql):
    values = []
    def replace(match):
        values.append(BINDS[int(match.group(1)) - 1])
        return "%s"
    assert "%" not in sql
    return re.sub(r"\$([123])\b", replace, sql), values


try:
    captured = json.loads(CAPTURE.read_text())
    # This baseline is captured by compare_readers.mjs directly from the
    # b2ec973d deployed reader. Keep this rerun independent of earlier WIP
    # evidence folders that are not part of this delivery.
    assert captured["baseline"]["sha256"] == "87c3f6cc83710b1a1dd2c2a5d8893498cb0721ac9af20e0bbd36c63b62d72b1c"
    for statement in captured.values():
        assert hashlib.sha256(statement["sql"].encode()).hexdigest() == statement["sha256"]
    report["sourceSql"] = {name:captured[name]["sha256"] for name in ("baseline","candidate")}
    with psycopg.connect(host=HOST, dbname="statarena_prod", user="statarena_ingest", sslmode="verify-full",
                         sslrootcert=str(ROOT / "dashboard/backend/certs/rds-us-east-2.pem"), connect_timeout=7,
                         autocommit=True, row_factory=dict_row,
                         options="-c default_transaction_read_only=on -c statement_timeout=8000 -c lock_timeout=1000 -c idle_in_transaction_session_timeout=5000 -c jit=off",
                         application_name="statarena-availability-paired-audit") as db:
        db.execute("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY")
        identity = db.execute("SELECT current_database() AS db,current_setting('transaction_read_only') AS read_only,current_setting('statement_timeout') AS timeout,current_setting('transaction_isolation') AS isolation,current_setting('jit') AS jit").fetchone()
        report["identity"] = identity
        assert identity == {"db":"statarena_prod","read_only":"on","timeout":"8s","isolation":"repeatable read","jit":"off"}
        generation = db.execute("SELECT source_digest FROM statarena_app.partitions WHERE season=%s AND league_id=%s", BINDS[:2]).fetchone()
        assert generation and generation["source_digest"], "Missing partition"
        report["generation"] = generation["source_digest"]
        for name in ("baseline","candidate"):
            result = {"name":name,"sqlSha256":captured[name]["sha256"]}
            report["queries"].append(result)
            db.execute("SAVEPOINT scoped_read")
            sql, values = bind_sql(captured[name]["sql"])
            start = time.perf_counter()
            try:
                row = db.execute(sql, values).fetchone()
                result["clientFetchMs"] = round((time.perf_counter()-start)*1000,3)
                assert row, "Expected one partition row"
                assert row.get("version") == report["generation"], "Generation changed within snapshot"
                encoded = json.dumps(row,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode()
                result.update({"status":"ok","semanticSha256":hashlib.sha256(encoded).hexdigest(),
                               "canonicalBytes":len(encoded),"appearanceCount":len(row.get("appearances") or []),
                               "matchCount":len(row.get("matches") or [])})
            except Exception as error:
                result.update({"status":"error","sqlstate":getattr(error,"sqlstate",None),"errorType":type(error).__name__,
                               "clientFetchMs":round((time.perf_counter()-start)*1000,3)})
                db.execute("ROLLBACK TO SAVEPOINT scoped_read")
            finally:
                db.execute("RELEASE SAVEPOINT scoped_read")
        db.execute("ROLLBACK")
    a,b = report["queries"]
    report["semanticEqual"] = a["status"] == b["status"] == "ok" and a["semanticSha256"] == b["semanticSha256"]
    report["passed"] = report["semanticEqual"]
except Exception as error:
    report["error"] = {"type":type(error).__name__,"sqlstate":getattr(error,"sqlstate",None)}
finally:
    out = HERE / ("rds-pair-"+stamp+".json")
    out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({"artifact":str(out),"passed":report["passed"],"queries":report["queries"],"semanticEqual":report.get("semanticEqual"),"error":report.get("error")}))
raise SystemExit(not report["passed"])
