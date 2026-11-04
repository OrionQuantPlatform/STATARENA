"""Bounded, sequential metadata snapshots. Never select or stage source bodies."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import time

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
PLAN = json.loads((OUT / "query-plan.json").read_text())
SCOPE = PLAN["scope"]
BASE = ROOT / "docs/verification/orion-pro-pilot-20261104"
SOURCE = json.loads((BASE / "source_scope.json").read_text())
REPORT = json.loads((BASE / "real-source-runs/20261104T190755631159Z-final-reviewed-exact-numbers-and-collections/normalizer-report.json").read_text())
PREFIXES = sorted(set(next(q for q in SOURCE["queries"] if q["name"] == "representative_match_resource_versions")["params"][0]
                      + ["/matches/" + mid for mid in {x["matchId"] for x in REPORT["families"]["leafDispositions"]}]))
OPTIONS = "-c default_transaction_read_only=on -c default_transaction_isolation=repeatable\\ read -c statement_timeout=8000 -c lock_timeout=1000 -c idle_in_transaction_session_timeout=15000 -c max_parallel_workers_per_gather=0"
NOW = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
SHA = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
quote = lambda s: "'" + s.replace("'", "''") + "'"
array = lambda values: "ARRAY[" + ",".join(quote(s) for s in sorted(set(values))) + "]::text[]"


def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n")


def sanitized_error(error):
    text = re.sub(r"postgres(?:ql)?://[^\s'\"]+", "[REDACTED_DSN]", str(error))
    return re.sub(r"(?i)(password\s*=\s*)[^\s]+", r"\1[REDACTED]", text)


def query(extra_paths=(), extra_endpoints=(), aws=False):
    known = SCOPE["knownArchivePaths"] + SCOPE["historicalManifestObjectPaths"] + list(extra_paths)
    profiles = array(SCOPE["profileIds"])
    prefixes = array(PREFIXES)
    paths = array(known)
    extra = array(extra_endpoints)
    index_fields = ",s.status AS indexed_status,encode(s.source_sha256,'hex') AS indexed_sha256,s.document_count,s.error_count,s.indexed_at" if aws else ""
    index_join = " LEFT JOIN statarena.file_document_sources s ON s.source_path=o.path" if aws else ""
    sql = f"""WITH wanted_profiles AS (SELECT unnest({profiles}) AS provider_id),
 profile_rows AS (
  SELECT p.provider_id,r.endpoint,r.params,r.status,r.updated_at,coalesce(r.ref->>'path',r.ref->>'shard') AS ref_path,
   r.ref->>'ordinal' AS ref_ordinal,r.error IS NOT NULL AS has_error,
   encode(o.sha256,'hex') AS object_sha256,o.size AS object_size,o.updated_at AS object_updated_at
  FROM wanted_profiles p LEFT JOIN statarena.resources r ON r.endpoint='/players/'||p.provider_id AND r.params='{{}}'
  LEFT JOIN statarena.objects o ON o.path=coalesce(r.ref->>'path',r.ref->>'shard')
 ), representative_resources AS (
  SELECT r.endpoint,left(r.params,2048) AS params,length(r.params) AS params_length,r.status,
   coalesce(r.ref->>'path',r.ref->>'shard') AS ref_path,r.ref->>'ordinal' AS ref_ordinal,
   r.error IS NOT NULL AS has_error,r.updated_at,r.total_per_prefix
  FROM unnest({prefixes}) p(prefix) CROSS JOIN LATERAL
   (SELECT r.*,count(*) OVER() AS total_per_prefix FROM statarena.resources r
    WHERE r.endpoint>=prefix AND r.endpoint<prefix||chr(127) ORDER BY r.endpoint,r.params LIMIT 128) r
  UNION ALL SELECT r.endpoint,left(r.params,2048),length(r.params),r.status,coalesce(r.ref->>'path',r.ref->>'shard'),r.ref->>'ordinal',r.error IS NOT NULL,r.updated_at,NULL::bigint
   FROM statarena.resources r WHERE r.endpoint IN ('/leagues/l_3FJFUl','/leagues/l_3FJFUl/matches') OR r.endpoint=ANY({extra})
 ), object_keys AS (
  SELECT unnest({paths}) AS path UNION SELECT ref_path FROM profile_rows UNION SELECT ref_path FROM representative_resources
 ), object_rows AS (
  SELECT o.path,o.size,encode(o.sha256,'hex') AS sha256,o.etag,o.content_type,o.updated_at{index_fields},count(*) OVER() AS total_rows
  FROM statarena.objects o{index_join}
  WHERE o.path IN (SELECT path FROM object_keys WHERE path IS NOT NULL)
   OR (o.path>='computed/dashboard/2025-2026/l_3FJFUl-' AND o.path<'computed/dashboard/2025-2026/l_3FJFUl.')
   OR (o.path>='computed/dashboard/2026-2027/l_3FJFUl-' AND o.path<'computed/dashboard/2026-2027/l_3FJFUl.')
  ORDER BY o.path LIMIT 2000
 ), fixture_rows AS (
  SELECT id,league_id,season,day::text,status,updated_at,count(*) OVER() AS total_rows
  FROM statarena.fixtures WHERE league_id='l_3FJFUl' AND season IN ('2025/2026','2026/2027') ORDER BY season,id LIMIT 1000
 ), inventory AS (SELECT jsonb_build_object(
  'identity',jsonb_build_object('observed_at',clock_timestamp(),'database',current_database(),'role',current_user,
   'snapshot',pg_current_snapshot()::text,'read_only',current_setting('transaction_read_only'),
   'isolation',current_setting('transaction_isolation'),'statement_timeout',current_setting('statement_timeout'),
   'lock_timeout',current_setting('lock_timeout'),'ssl',(SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid())),
  'fixtures',coalesce((SELECT jsonb_agg(to_jsonb(f)) FROM fixture_rows f),'[]'::jsonb),
  'profiles',coalesce((SELECT jsonb_agg(to_jsonb(p) ORDER BY provider_id) FROM profile_rows p),'[]'::jsonb),
  'resources',coalesce((SELECT jsonb_agg(to_jsonb(r) ORDER BY endpoint,params) FROM representative_resources r),'[]'::jsonb),
  'objects',coalesce((SELECT jsonb_agg(to_jsonb(o)) FROM object_rows o),'[]'::jsonb)
 ) AS value)
 SELECT CASE WHEN octet_length(value::text)<=2097152 THEN value
  ELSE jsonb_build_object('error','metadata_result_byte_cap_exceeded','bytes',octet_length(value::text)) END AS metadata FROM inventory"""
    return sql


def connect_neon():
    import psycopg
    from psycopg.rows import dict_row
    line = next(x for x in (ROOT / "dashboard/.env").read_text().splitlines() if x.strip().startswith("NEON_DATABASE_URL="))
    dsn = line.split("=", 1)[1].strip().strip('"').strip("'")
    # The administration API proved this direct hostname is the same existing endpoint.
    dsn = dsn.replace("ep-steep-boat-bekuqo4w-pooler.", "ep-steep-boat-bekuqo4w.")
    return psycopg.connect(dsn, sslmode="verify-full", sslrootcert="/etc/ssl/cert.pem", options=OPTIONS,
        connect_timeout=7, autocommit=False, row_factory=dict_row, application_name="statarena-transfer-metadata-ro")


def connect_aws():
    import psycopg
    from psycopg.rows import dict_row
    return psycopg.connect(host="statarena-postgres.clcy2iqyajbl.us-east-2.rds.amazonaws.com", dbname="statarena_prod",
        user="statarena_ingest", sslmode="verify-full", sslrootcert=str(ROOT / "dashboard/backend/certs/rds-us-east-2.pem"),
        options=OPTIONS, connect_timeout=7, autocommit=False, row_factory=dict_row, application_name="statarena-transfer-metadata-ro")


def snapshot(name, factory, sql, budget):
    record = {"startedAt": NOW(), "source": name, "sqlSha256": hashlib.sha256(sql.encode()).hexdigest(),
        "statementBudgetMaximumIncludingBeginRollback": 3, "remoteWrites": [], "bodyColumnsSelected": [], "status": "unverified"}
    connection = None
    begin = time.monotonic()
    try:
        connection = factory()
        budget["statementsMaximum"] += 3
        if budget["statementsMaximum"] > 20:
            raise RuntimeError("SQL statement budget exhausted before SELECT")
        row = connection.execute(sql).fetchone()
        metadata = row["metadata"]
        byte_count = len(json.dumps(metadata, ensure_ascii=False, default=str).encode())
        budget["resultBytes"] += byte_count
        record.update(metadata=metadata, resultBytes=byte_count)
        identity = metadata.get("identity", {})
        valid = identity.get("read_only") == "on" and identity.get("isolation") == "repeatable read" and identity.get("ssl") is True and identity.get("statement_timeout") == "8s"
        record["status"] = "pass" if valid and "error" not in metadata and budget["resultBytes"] <= 16777216 else "fail"
    except Exception as error:
        record.update(errorType=type(error).__name__, error=sanitized_error(error), sqlState=getattr(error, "sqlstate", None), status="blocked")
    finally:
        if connection is not None:
            try:
                connection.rollback()
                record["cleanup"] = "ROLLBACK then close"
            finally:
                connection.close()
        record.update(finishedAt=NOW(), elapsedMs=round((time.monotonic()-begin)*1000, 3))
        save(name + "-direct.json", record)
        print(json.dumps({"source": name, "status": record["status"], "elapsedMs": record["elapsedMs"], "error": record.get("error"), "resultBytes": record.get("resultBytes")}), flush=True)
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    plan = {"atUtc": NOW(), "statementMaximumAlreadyCharged": 10, "newStatementMaximum": 6, "totalMaximum": 16,
        "options": OPTIONS, "connectionPolicy": "Existing credentials in memory only; verified TLS; sequential clients; RR/RO; no service reconfiguration",
        "representativeMatchPrefixes": PREFIXES, "neonSql": query(), "awsSqlInitial": query(aws=True),
        "note": "Final AWS statement additionally probes exact resource/object keys returned by Neon, saved before AWS connection"}
    if args.prepare_only:
        save("fallback-query-plan.json", plan)
        print(json.dumps({"prepared": True, "profiles": len(SCOPE["profileIds"]), "representativeMatchPrefixes": len(PREFIXES), "totalStatementMaximum": 16}))
        return
    if any((OUT / name).exists() for name in ["neon-direct.json", "aws-direct.json"]):
        raise SystemExit("This pass already has a direct-run receipt; no implicit budget reset or overwrite")
    if not (OUT / "fallback-query-plan.json").exists():
        raise SystemExit("Prepare and review the fallback query plan before connecting")
    connector = json.loads((OUT / "neon-run.json").read_text())["result"]
    budget = {"statementsMaximum": 10, "resultBytes": len(json.dumps(connector, ensure_ascii=False).encode()), "limitStatements": 20, "limitResultBytes": 16777216}
    neon = snapshot("neon", connect_neon, plan["neonSql"], budget)
    data = neon.get("metadata", {}) if neon["status"] == "pass" else {}
    extra_paths = {x["path"] for x in data.get("objects", [])} | {x["ref_path"] for x in data.get("profiles", []) + data.get("resources", []) if x.get("ref_path")}
    extra_endpoints = {x["endpoint"] for x in data.get("resources", []) if x.get("endpoint")}
    aws_sql = query(extra_paths, extra_endpoints, aws=True)
    save("aws-fallback-query.json", {"atUtc": NOW(), "sql": aws_sql, "neonDiscoveredExtraPaths": sorted(extra_paths), "neonDiscoveredExtraEndpoints": sorted(extra_endpoints)})
    aws = snapshot("aws", connect_aws, aws_sql, budget)
    save("execution-budget.json", {"atUtc": NOW(), **budget, "neonConnectorTimeoutMaximumCharged": 10,
        "passed": budget["statementsMaximum"] <= 20 and budget["resultBytes"] <= 16777216,
        "note": "Connector charge is conservative; failed submission has no usable partial result. New direct connections are sequential and each always rolls back."})


if __name__ == "__main__":
    main()
