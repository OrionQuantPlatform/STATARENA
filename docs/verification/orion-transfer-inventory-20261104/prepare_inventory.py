"""Prepare the bounded metadata-only query plan; no remote access."""
import datetime
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
SOURCE = ROOT / "docs/verification/orion-pro-pilot-20261104/source_scope.json"
REPORT = ROOT / "docs/verification/orion-pro-pilot-20261104/real-source-runs/20261104T190755631159Z-final-reviewed-exact-numbers-and-collections/normalizer-report.json"
source = json.loads(SOURCE.read_text())
report = json.loads(REPORT.read_text())
profile_ids = sorted(set(source["sourceSummary"]["missingPlayerResourceLookupIds"] + ["p_1JuxKR"]))
archive = next(q for q in source["queries"] if q["name"] == "archive_relation_source_versions")
archive_paths = sorted(set(archive["params"][0]))
manifest = next(q for q in source["queries"] if q["name"] == "current_manifest_pilot_pointers")["rows"][0]
static_paths = sorted(set([manifest["source_path"], *[p["path"] for p in manifest["selectedPointers"]], *[p["path"] for p in report["fullProfiles"]["conflicts"]]]))
q = lambda s: "'" + s.replace("'", "''") + "'"
arr = lambda values: "ARRAY[" + ",".join(q(s) for s in values) + "]::text[]"
profiles = arr(["/players/" + p for p in profile_ids])
paths = arr(archive_paths + static_paths)
predicate = """(r.endpoint IN ('/leagues/l_3FJFUl','/leagues/l_3FJFUl/matches')
 OR (r.endpoint LIKE '/matches/%%' AND split_part(r.endpoint,'/',3) IN
    (SELECT id FROM statarena.fixtures WHERE league_id='l_3FJFUl' AND season IN ('2025/2026','2026/2027')))
 OR r.endpoint=ANY(PROFILES))""".replace("PROFILES", profiles).replace("%%", "%")
scope_paths = """WITH scoped_paths AS (
 SELECT unnest(PATHS) path
 UNION SELECT coalesce(r.ref->>'path',r.ref->>'shard') FROM statarena.resources r WHERE PREDICATE
)""".replace("PATHS", paths).replace("PREDICATE", predicate)
identity = """SELECT clock_timestamp() AS observed_at,current_database() AS database,current_user AS role,
 pg_current_snapshot()::text AS snapshot,current_setting('transaction_read_only') AS read_only,
 current_setting('transaction_isolation') AS isolation,current_setting('statement_timeout') AS statement_timeout,
 current_setting('lock_timeout') AS lock_timeout,(SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()) AS ssl,
 (SELECT jsonb_agg(jsonb_build_object('table',table_name,'column',column_name,'type',data_type) ORDER BY table_name,ordinal_position)
  FROM information_schema.columns WHERE table_schema='statarena' AND table_name IN
  ('objects','resources','observations','fixtures','projections','file_documents','file_document_sources')) AS metadata_columns"""
fixtures = """SELECT id,league_id,season,day::text,status,updated_at,count(*) OVER() AS total_rows
 FROM statarena.fixtures WHERE league_id='l_3FJFUl' AND season IN ('2025/2026','2026/2027')
 ORDER BY season,id LIMIT 1000"""
resources = """SELECT r.endpoint,left(r.params,2048) AS params,length(r.params) AS params_length,r.status,
 left(coalesce(r.ref->>'path',r.ref->>'shard'),1024) AS ref_path,
 length(coalesce(r.ref->>'path',r.ref->>'shard')) AS ref_path_length,
 left(r.ref->>'ordinal',32) AS ref_ordinal,left(r.ref->>'id',128) AS ref_id,
 r.error IS NOT NULL AS has_error,r.updated_at,
 r.endpoint=ANY(PROFILES) AS is_profile,count(*) OVER() AS total_rows
 FROM statarena.resources r WHERE PREDICATE
 ORDER BY is_profile DESC,r.endpoint,r.params LIMIT 4000""".replace("PROFILES", profiles).replace("PREDICATE", predicate)
objects = scope_paths + """
 SELECT o.path,o.size,encode(o.sha256,'hex') AS sha256,o.etag,o.content_type,o.updated_at,
 count(*) OVER() AS total_rows FROM statarena.objects o
 WHERE o.path IN (SELECT path FROM scoped_paths WHERE path IS NOT NULL)
 OR (o.path>='computed/dashboard/2025-2026/l_3FJFUl-' AND o.path<'computed/dashboard/2025-2026/l_3FJFUl.' )
 OR (o.path>='computed/dashboard/2026-2027/l_3FJFUl-' AND o.path<'computed/dashboard/2026-2027/l_3FJFUl.' )
 ORDER BY o.path LIMIT 3000"""
observations = scope_paths + """, metadata AS (
 SELECT 'observation'::text AS kind,o.id AS key,o.shard AS path,o.ordinal::text AS params,NULL::timestamptz AS updated_at
 FROM statarena.observations o WHERE o.shard IN (SELECT path FROM scoped_paths WHERE path IS NOT NULL)
 UNION ALL SELECT 'projection',p.name,NULL,left(p.params,2048),p.updated_at FROM statarena.projections p
 WHERE p.params LIKE '%l_3FJFUl%' AND (p.params LIKE '%2025/2026%' OR p.params LIKE '%2026/2027%')
 ) SELECT *,count(*) OVER() AS total_rows FROM metadata ORDER BY kind,key,params LIMIT 5000"""
queries = [{"name": n, "sql": sql, "rowCap": cap} for n, sql, cap in [
    ("identity_catalogue", identity, 1), ("scoped_fixtures", fixtures, 1000),
    ("resource_pointers", resources, 4000), ("object_versions", objects, 3000),
    ("observation_projection_pointers", observations, 5000)]]
for item in queries:
    item["sql"] = "WITH bounded_metadata AS (SELECT q.*,sum(octet_length(to_jsonb(q)::text)+64) OVER (ROWS UNBOUNDED PRECEDING) AS serialized_bytes FROM (" + item["sql"] + ") q) SELECT * FROM bounded_metadata WHERE serialized_bytes<=524288"
    item["resultJsonBudgetBytes"] = 524288
plan = {"atUtc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "scope": {"leagueId": "l_3FJFUl", "seasons": ["2025/2026", "2026/2027"], "profileIds": profile_ids,
              "knownArchivePaths": archive_paths, "historicalManifestObjectPaths": static_paths,
              "knownProfileConflicts": report["fullProfiles"]["conflicts"]},
    "sourceInputsSha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in [SOURCE, REPORT]},
    "neon": {"project_id": "sweet-queen-11955006", "branch_id": "br-mute-bonus-be23014e", "compute_id": "ep-steep-boat-bekuqo4w", "database_name": "neondb"},
    "neonSetup": ["SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY", "SET LOCAL statement_timeout='8s'", "SET LOCAL lock_timeout='1s'"],
    "queries": queries,
    "budget": {"maximumSqlStatementsIncludingControls": 20, "maximumSerializedSqlResultBytes": 16777216, "plannedMaximumStatements": 19, "perSelectJsonBudgetBytes": 524288},
    "limitations": ["Historical archive/manifest keys bound the lookup and do not establish current provider coverage", "No body/member identity or current manifest pointer is inferred from file names", "Timestamps are not a supplier version order", "No other organization/archived branch is silently substituted"]}
(OUT / "query-plan.json").write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n")
print(json.dumps({"profileIds": len(profile_ids), "historicalArchivePaths": len(archive_paths), "queriesPerSnapshot": len(queries), "plannedMaximumStatements": 19, "planSha256": hashlib.sha256((OUT / 'query-plan.json').read_bytes()).hexdigest()}))
