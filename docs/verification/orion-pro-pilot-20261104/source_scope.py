"""Bounded, read-only AWS source scope; receipts contain metadata/shapes, never bodies.

Rerun: PYTHONPATH=/tmp/statarena-publication-test-python python3 docs/verification/orion-pro-pilot-20261104/source_scope.py
No provider, S3, Neon, DDL, DML, raw output or secret-reading code is used.
"""
from collections import Counter, defaultdict
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import time

import psycopg
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
LEAGUE = "l_3FJFUl"
SEASONS = ["2025/2026", "2026/2027"]
MAX_QUERIES = 20
MAX_BODY_BYTES = 1024 * 1024
COMMAND = "PYTHONPATH=/tmp/statarena-publication-test-python python3 docs/verification/orion-pro-pilot-20261104/source_scope.py"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def family(endpoint):
    return re.sub(r"[ltpms]_[A-Za-z0-9]{6}", "{id}", endpoint)


def shape(value):
    """Paths/types/states only, with [] replacing every array ordinal."""
    counts = defaultdict(Counter)

    def walk(v, path="$", depth=0):
        if depth > 16:
            counts[path]["depth_limit"] += 1
            return
        kind = ("null" if v is None else "boolean" if isinstance(v, bool)
                else "object" if isinstance(v, dict) else "array" if isinstance(v, list)
                else "number" if isinstance(v, (float, int)) else "string")
        counts[path][kind] += 1
        if v == "":
            counts[path]["empty_string"] += 1
        if type(v) in (int, float) and v == 0:
            counts[path]["zero"] += 1
        if isinstance(v, (dict, list)) and not v:
            counts[path]["empty_container"] += 1
        if isinstance(v, dict):
            for k, x in v.items():
                walk(x, path + "." + k, depth + 1)
        elif isinstance(v, list):
            for x in v:
                walk(x, path + "[]", depth + 1)

    walk(value)
    return {k: dict(sorted(v.items())) for k, v in sorted(counts.items())}


def identities(value):
    found = set()
    if isinstance(value, str) and re.fullmatch(r"[ltpms]_[A-Za-z0-9]{6}", value):
        found.add(value)
    elif isinstance(value, dict):
        for v in value.values():
            found.update(identities(v))
    elif isinstance(value, list):
        for v in value:
            found.update(identities(v))
    return found


def metadata_ref(row):
    ref = row.pop("ref", None) or {}
    row["refKeys"] = sorted(ref)
    row["refPath"] = ref.get("path")
    for key in ("sha256", "ordinal", "documentId", "format"):
        if key in ref:
            row["ref_" + key] = ref[key]
    return row


def main():
    if (OUT / "source_scope.json").exists():
        raise ValueError("Preserve existing receipts; use --out-dir with a new directory for a rerun")
    report = {
        "atUtc": dt.datetime.now(dt.timezone.utc).isoformat(), "command": COMMAND,
        "modelSha256": hashlib.sha256((ROOT / "docs/architecture/orion-plan-20261104/target-schema.proposed.json").read_bytes()).hexdigest(),
        "scope": {"leagueId": LEAGUE, "seasons": SEASONS},
        "limits": {"connections": 1, "queries": MAX_QUERIES, "statementTimeoutMs": 8000,
                   "lockTimeoutMs": 1000, "singleBodyBytes": MAX_BODY_BYTES,
                   "sampleMatchIdsPerSeason": 3, "sampleDocuments": 32, "sampleProfiles": 12},
        "setup": "Existing pgpass is used by libpq without reading its file; verified TLS; one repeatable-read read-only snapshot; no remote write, provider call, second transfer or raw body persisted.",
        "queries": [], "errors": [], "documentShapes": [], "profileShapes": [],
    }
    resource_rows = []
    sampled_ids = set()
    query_count = 0

    def run(db, name, sql, params=(), transform=None):
        nonlocal query_count
        query_count += 1
        assert query_count <= MAX_QUERIES
        item = {"number": query_count, "name": name, "sql": sql, "params": params}
        start = time.monotonic()
        try:
            with db.transaction():
                rows = db.execute(sql, params).fetchall()
                safe_rows = transform(rows) if transform else rows
                item.update(rows=safe_rows, rowCount=len(rows), receiptSha256=hashlib.sha256(canonical(safe_rows).encode()).hexdigest())
            return rows
        except psycopg.Error as error:
            item["error"] = {"class": type(error).__name__, "sqlstate": error.sqlstate}
            report["errors"].append({"query": name, **item["error"]})
            return []
        finally:
            item["elapsedMs"] = round(1000 * (time.monotonic() - start), 3)
            report["queries"].append(item)
            print(canonical({"query": name, "elapsedMs": item["elapsedMs"], "rowCount": item.get("rowCount"), "error": item.get("error")}), flush=True)

    with psycopg.connect(
        host="statarena-postgres.clcy2iqyajbl.us-east-2.rds.amazonaws.com",
        dbname="statarena_prod", user="statarena_ingest", sslmode="verify-full",
        sslrootcert=str(ROOT / "dashboard/backend/certs/rds-us-east-2.pem"),
        connect_timeout=7, autocommit=True, row_factory=dict_row,
        options="-c default_transaction_read_only=on -c statement_timeout=8000 -c lock_timeout=1000 -c max_parallel_workers_per_gather=0",
        application_name="statarena-orion-pro-source-scope",
    ) as db:
        db.execute("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY")
        run(db, "identity_and_catalog", """SELECT current_database() database,current_user role,
            current_setting('server_version') version,current_setting('transaction_read_only') read_only,
            current_setting('statement_timeout') statement_timeout,pg_current_snapshot()::text snapshot,
            (SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()) ssl,
            (SELECT jsonb_agg(jsonb_build_object('schema',schemaname,'table',tablename,'index',indexname,'definition',indexdef) ORDER BY schemaname,tablename,indexname)
             FROM pg_indexes WHERE (schemaname='statarena' AND tablename IN ('objects','resources','fixtures','file_documents','file_document_sources','projections'))
             OR (schemaname='statarena_app' AND tablename IN ('partitions','matches','appearances','match_resources','match_families'))) indexes,
            (SELECT jsonb_agg(jsonb_build_object('table',table_name,'column',column_name,'type',data_type) ORDER BY table_name,ordinal_position)
             FROM information_schema.columns WHERE table_schema='statarena' AND table_name IN ('objects','resources','file_documents','file_document_sources','fixtures','projections')) columns""")
        scopes = run(db, "competition_season_presence", """WITH scope(season) AS (SELECT unnest(%s::text[]))
            SELECT scope.season,
              (SELECT count(*) FROM statarena.fixtures f WHERE f.league_id=%s AND f.season=scope.season) source_fixtures,
              (SELECT jsonb_object_agg(status,n) FROM (SELECT status,count(*) n FROM statarena.fixtures f WHERE f.league_id=%s AND f.season=scope.season GROUP BY status)t) source_status_counts,
              (SELECT array_agg(id ORDER BY day,id) FROM statarena.fixtures f WHERE f.league_id=%s AND f.season=scope.season AND f.status='finished') finished_ids,
              (SELECT array_agg(id ORDER BY day,id) FROM statarena.fixtures f WHERE f.league_id=%s AND f.season=scope.season AND f.status='not_started') upcoming_ids,
              (SELECT jsonb_build_object('digest',source_digest,'publishedAt',published_at) FROM statarena_app.partitions p WHERE p.league_id=%s AND p.season=scope.season) serving_partition,
              (SELECT count(*) FROM statarena_app.matches m WHERE m.league_id=%s AND m.season=scope.season) serving_matches,
              (SELECT count(*) FROM statarena_app.fixtures f WHERE f.league_id=%s AND f.season=scope.season) serving_fixtures
            FROM scope ORDER BY scope.season""", (SEASONS, *([LEAGUE] * 7)))
        print(canonical({"earlyAvailability": [{k: v for k, v in r.items() if not k.endswith("_ids")} for r in scopes]}), flush=True)
        league_resources = run(db, "competition_resource_versions", """SELECT endpoint,params,status,ref,updated_at
            FROM statarena.resources WHERE endpoint=ANY(%s) ORDER BY endpoint,params LIMIT 32""",
            ([f"/leagues/{LEAGUE}", f"/leagues/{LEAGUE}/matches"],),
            lambda rows: [metadata_ref(dict(r)) for r in rows])
        resource_rows.extend(league_resources)
        prefixes = [f"computed/dashboard/{s.replace('/', '-')}/{LEAGUE}-" for s in SEASONS]
        prefixes += [f"computed/dashboard/seasons/{s.replace('/', '-')}/{LEAGUE}" for s in SEASONS]
        objects = run(db, "competition_partition_object_versions", """SELECT o.path,o.size,encode(o.sha256,'hex') sha256,o.content_type,o.updated_at,
            s.status document_status,s.document_count,s.error_count,encode(s.source_sha256,'hex') indexed_sha256
            FROM unnest(%s::text[]) prefix
            JOIN LATERAL (SELECT * FROM statarena.objects WHERE path>=prefix AND path<prefix||chr(127) ORDER BY path LIMIT 16) o ON true
            LEFT JOIN statarena.file_document_sources s ON s.source_path=o.path ORDER BY o.path""", (prefixes,))
        selected_matches = []
        for row in scopes:
            finished = row.get("finished_ids") or []
            upcoming = row.get("upcoming_ids") or []
            ids = ([finished[0], finished[-1]] if finished else []) + upcoming[:1]
            selected_matches += [{"season": row["season"], "id": m} for m in dict.fromkeys(ids)]
        report["selectedMatches"] = selected_matches
        match_prefixes = [f"/matches/{m['id']}" for m in selected_matches]
        match_resources = run(db, "representative_match_resource_versions", """SELECT r.endpoint,r.params,r.status,r.ref,r.updated_at
            FROM unnest(%s::text[]) prefix JOIN LATERAL
              (SELECT endpoint,params,status,ref,updated_at FROM statarena.resources
               WHERE endpoint>=prefix AND endpoint<prefix||chr(127) ORDER BY endpoint,params LIMIT 256) r ON true
            ORDER BY r.endpoint,r.params""", (match_prefixes,), lambda rows: [metadata_ref(dict(r)) for r in rows])
        resource_rows.extend(match_resources)
        report["representativeResourceFamilies"] = [dict(family=k[0], status=k[1], count=v) for k, v in sorted(Counter((family(r["endpoint"]), r["status"]) for r in match_resources).items())]
        refs = {r["ref"]["path"] for r in resource_rows if isinstance(r.get("ref"), dict) and r["ref"].get("path")}
        refs.update(r["path"] for r in objects)
        source_meta = run(db, "exact_source_version_availability", """SELECT p.path,o.size,encode(o.sha256,'hex') sha256,o.content_type,
            s.status,s.document_count,s.error_count,encode(s.source_sha256,'hex') indexed_sha256,
            (SELECT count(*) FROM statarena.file_documents d WHERE d.source_path=p.path AND d.source_sha256=o.sha256 AND d.error IS NULL) current_error_free_documents
            FROM unnest(%s::text[]) p(path)
            LEFT JOIN statarena.objects o ON o.path=p.path
            LEFT JOIN statarena.file_document_sources s ON s.source_path=p.path ORDER BY p.path""", (sorted(refs),))
        # One resource for each endpoint family/season, not every player endpoint.
        candidates = {}
        match_seasons = {m["id"]: m["season"] for m in selected_matches}
        for r in resource_rows:
            mid = next((m for m in match_seasons if "/" + m in r["endpoint"]), None)
            key = (match_seasons.get(mid, "league"), family(r["endpoint"]), r["params"])
            if r["status"] == 200 and r.get("ref", {}).get("path"):
                candidates.setdefault(key, r)
        sample_paths = [r["ref"]["path"] for r in candidates.values()][:32]
        path_families = {r["ref"]["path"]: family(r["endpoint"]) for r in candidates.values()}

        def summarize_docs(rows, target):
            safe = []
            for r in rows:
                doc = r["document"]
                sampled_ids.update(identities(doc))
                item = {k: v for k, v in r.items() if k != "document"}
                item["family"] = path_families.get(r["source_path"])
                item["canonicalSha256"] = hashlib.sha256(canonical(doc).encode()).hexdigest()
                item["fieldVariantMatrix"] = shape(doc)
                target.append(item)
                safe.append({k: v for k, v in item.items() if k != "fieldVariantMatrix"})
            return safe

        run(db, "representative_source_document_shapes", """SELECT d.source_path,d.document_path,d.format,
            encode(d.source_sha256,'hex') source_sha256,pg_column_size(d.document) stored_jsonb_bytes,d.document
            FROM unnest(%s::text[]) p(path)
            JOIN statarena.objects o ON o.path=p.path
            JOIN statarena.file_document_sources s ON s.source_path=p.path AND s.source_sha256=o.sha256 AND s.status='ready'
            JOIN LATERAL (SELECT * FROM statarena.file_documents d WHERE d.source_path=p.path AND d.source_sha256=o.sha256 AND d.error IS NULL AND pg_column_size(d.document)<=%s ORDER BY d.document_path LIMIT 1) d ON true
            ORDER BY d.source_path""", (list(dict.fromkeys(sample_paths)), MAX_BODY_BYTES), lambda rows: summarize_docs(rows, report["documentShapes"]))
        player_ids = sorted(i for i in sampled_ids if i.startswith("p_"))[:8]
        team_ids = sorted(i for i in sampled_ids if i.startswith("t_"))[:4]
        report["profileProbeIds"] = player_ids + team_ids
        profile_resources = run(db, "representative_profile_resource_versions", """SELECT endpoint,params,status,ref,updated_at
            FROM statarena.resources WHERE endpoint=ANY(%s) ORDER BY endpoint,params LIMIT 24""",
            ([f"/players/{p}" for p in player_ids] + [f"/teams/{t}" for t in team_ids],), lambda rows: [metadata_ref(dict(r)) for r in rows])
        profile_paths = [r["ref"]["path"] for r in profile_resources if r["status"] == 200 and r.get("ref", {}).get("path")]
        path_families.update({r["ref"]["path"]: family(r["endpoint"]) for r in profile_resources if r.get("ref", {}).get("path")})
        run(db, "representative_profile_source_shapes", """SELECT p.path source_path,d.document_path,d.format,
            o.size,encode(o.sha256,'hex') source_sha256,s.status,s.document_count,s.error_count,
            pg_column_size(d.document) stored_jsonb_bytes,d.document
            FROM unnest(%s::text[]) p(path)
            LEFT JOIN statarena.objects o ON o.path=p.path
            LEFT JOIN statarena.file_document_sources s ON s.source_path=p.path AND s.source_sha256=o.sha256
            LEFT JOIN LATERAL (SELECT * FROM statarena.file_documents d WHERE d.source_path=p.path AND d.source_sha256=o.sha256 AND d.error IS NULL AND pg_column_size(d.document)<=%s ORDER BY d.document_path LIMIT 1) d ON s.status='ready'
            ORDER BY p.path""", (list(dict.fromkeys(profile_paths))[:12], MAX_BODY_BYTES), lambda rows: summarize_docs(rows, report["profileShapes"]))
        run(db, "fixture_native_shapes", """SELECT id,season,body FROM statarena.fixtures WHERE id=ANY(%s) ORDER BY id""",
            ([m["id"] for m in selected_matches],), lambda rows: [{"id": r["id"], "season": r["season"], "canonicalSha256": hashlib.sha256(canonical(r["body"]).encode()).hexdigest(), "fieldVariantMatrix": shape(r["body"])} for r in rows])
        run(db, "standing_projection_shapes", """SELECT name,params,body FROM statarena.projections
            WHERE name='standings' AND params LIKE %s AND pg_column_size(body)<=%s ORDER BY params LIMIT 8""",
            ("%" + LEAGUE + "%", MAX_BODY_BYTES), lambda rows: [{"name": r["name"], "params": r["params"], "canonicalSha256": hashlib.sha256(canonical(r["body"]).encode()).hexdigest(), "fieldVariantMatrix": shape(r["body"])} for r in rows])
        run(db, "representative_serving_families", """SELECT f.match_id,f.family,f.status FROM statarena_app.match_families f WHERE match_id=ANY(%s) ORDER BY match_id,family""",
            ([m["id"] for m in selected_matches],))
        db.execute("ROLLBACK")
    report["finishedUtc"] = dt.datetime.now(dt.timezone.utc).isoformat()
    report["queryCount"] = query_count
    report["limitations"] = [
        "Metadata describes one snapshot; no claim of complete Neon/AWS reconciliation or transfer completion.",
        "Document field matrices sample at most32 documents and12 profiles, <=1MiB stored JSONB each; missing sample variants remain unverified.",
        "Object physical SHA, source-reference logical SHA and canonical decoded JSON SHA are separate contracts; equality is not assumed.",
        "Computed partition bodies are not sampled or persisted. Prefix metadata does not prove every partition row or dependency is complete.",
        "No S3 payload download, no second Neon transfer, no new raw copy, no schema application, no typed import or E2E acceptance.",
    ]
    (OUT / "source_scope.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str) + "\n")
    print(canonical({"receipt": str(OUT / "source_scope.json"), "queries": query_count, "errors": report["errors"], "sourceVersionPaths": len(source_meta), "documentShapes": len(report["documentShapes"]), "profileShapes": len(report["profileShapes"])}))
    return 1 if report["errors"] else 0


def supplement():
    """Continue the preserved12-query receipt with six bounded queries.

    This is an explicit second sequential snapshot, not a claim that both
    observations were atomic together. No concurrent connection is opened.
    """
    initial = OUT / "source_scope.initial.json"
    if initial.exists():
        raise ValueError("Supplement already recorded; preserve the original audit instead of silently replacing it")
    raw = (OUT / "source_scope.json").read_text()
    report = json.loads(raw)
    assert report["queryCount"] == 12
    initial.write_text(raw)
    report["supplementAtUtc"] = dt.datetime.now(dt.timezone.utc).isoformat()
    report["supplementCommand"] = COMMAND + " --supplement"
    report["limits"].update(supplementQueries=6, computedDecodedBodyBytes=16 * 1024 * 1024,
                            archiveSampleDocuments=32, sequentialSnapshots=2)
    by_name = {q["name"]: q for q in report["queries"]}
    scopes = by_name["competition_season_presence"]["rows"]
    all_ids = [m for r in scopes for k in ("finished_ids", "upcoming_ids") for m in (r[k] or [])]
    pointers, partitions, relations, shapes = [], [], [], []
    profile_ids = set()

    def run(db, name, sql, params=(), transform=None):
        report["queryCount"] += 1
        assert report["queryCount"] <= MAX_QUERIES
        item = {"number": report["queryCount"], "snapshot": 2, "name": name, "sql": sql, "params": params}
        start = time.monotonic()
        try:
            with db.transaction():
                rows = db.execute(sql, params).fetchall()
                safe = transform(rows) if transform else rows
                item.update(rows=safe, rowCount=len(rows), receiptSha256=hashlib.sha256(canonical(safe).encode()).hexdigest())
            return rows
        except psycopg.Error as error:
            item["error"] = {"class": type(error).__name__, "sqlstate": error.sqlstate}
            report["errors"].append({"query": name, **item["error"]})
            return []
        finally:
            item["elapsedMs"] = round(1000 * (time.monotonic() - start), 3)
            report["queries"].append(item)
            print(canonical({"query": name, "elapsedMs": item["elapsedMs"], "rowCount": item.get("rowCount"), "error": item.get("error")}), flush=True)

    def manifest(rows):
        result = []
        for r in rows:
            doc = r.pop("document") or {}
            for season in doc.get("seasons", []):
                if season.get("id") in SEASONS:
                    for chunk in season.get("chunks", []):
                        if chunk.get("leagueId") == LEAGUE:
                            pointers.append(dict(season=season["id"], **chunk))
            result.append(dict(**r, selectedPointers=pointers))
        return result

    def unpack(table):
        dictionaries = table.get("dictionaries", {})
        return [{key: dictionaries[str(j)][values[j]] if str(j) in dictionaries and values[j] is not None else values[j]
                 for j, key in enumerate(table["keys"]) if j not in table.get("missing", {}).get(str(i), [])}
                for i, values in enumerate(table["rows"])]

    def partition_summary(rows):
        result = []
        for r in rows:
            doc = r.pop("document")
            if doc is None:
                result.append(dict(**r, skipped="decoded body exceeds16MiB"))
                continue
            tables = {k: unpack(v) for k, v in doc.get("tables", {}).items()}
            season = next((p["season"] for p in pointers if p["path"] == r["source_path"]), None)
            matches = tables.get("matches", [])
            match_ids = [m["id"] for m in matches]
            ids = set(match_ids)
            fixtures = tables.get("fixtures", [])
            source = next((s for s in scopes if s["season"] == season), {})
            source_ids = set((source.get("finished_ids") or []) + (source.get("upcoming_ids") or []))
            count_by_match = Counter()
            for table in ("performances", "shots", "team_statistics"):
                for entry in tables.get(table, []):
                    if entry.get("matchId"):
                        count_by_match[entry["matchId"]] += 1
            richest = sorted(matches, key=lambda m: (-count_by_match[m["id"]], m["id"]))[:2]
            item = dict(**r, season=season, canonicalSha256=hashlib.sha256(canonical(doc).encode()).hexdigest(),
                        tables={k: {"rows": len(v), "fields": sorted(set().union(*(set(x) for x in v))) if v else [],
                                    "canonicalSha256": hashlib.sha256(canonical(v).encode()).hexdigest(),
                                    "fieldVariantMatrix": shape(v)} for k, v in tables.items()},
                        matchIds=match_ids, richestMatchIds=[m["id"] for m in richest],
                        sourceFinishedWithoutNormalizedMatchIds=sorted(set(source.get("finished_ids") or []) - ids),
                        sourceFixtureIdsWithoutNormalizedFixtureIds=sorted(source_ids - {f["id"] for f in fixtures}),
                        normalizedMatchIdsWithoutSourceFixture=sorted(ids - source_ids))
            partitions.append(item)
            profile_ids.update(sorted(identities(tables.get("players", [])))[:4])
            profile_ids.update(sorted(identities(tables.get("teams", [])))[:2])
            result.append(item)
        return result

    with psycopg.connect(
        host="statarena-postgres.clcy2iqyajbl.us-east-2.rds.amazonaws.com", dbname="statarena_prod",
        user="statarena_ingest", sslmode="verify-full", sslrootcert=str(ROOT / "dashboard/backend/certs/rds-us-east-2.pem"),
        connect_timeout=7, autocommit=True, row_factory=dict_row,
        options="-c default_transaction_read_only=on -c statement_timeout=8000 -c lock_timeout=1000 -c max_parallel_workers_per_gather=0",
        application_name="statarena-orion-pro-source-scope-supplement",
    ) as db:
        db.execute("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY")
        run(db, "current_manifest_pilot_pointers", """SELECT current_database() database,current_user role,
            current_setting('transaction_read_only') read_only,pg_current_snapshot()::text snapshot,
            d.source_path,encode(d.source_sha256,'hex') source_sha256,d.document
            FROM statarena.file_documents d JOIN statarena.objects o ON o.path=d.source_path AND o.sha256=d.source_sha256
            WHERE d.document_path='computed/dashboard/index.json' AND d.error IS NULL""", transform=manifest)
        if len(pointers) != 2:
            raise ValueError("The AWS current manifest does not resolve exactly two selected partitions")
        run(db, "current_partition_counts_and_native_shapes", """SELECT d.source_path,encode(d.source_sha256,'hex') source_sha256,
            octet_length(d.document::text) decoded_bytes,
            CASE WHEN octet_length(d.document::text)<=%s THEN d.document END document
            FROM unnest(%s::text[]) p(path) JOIN statarena.file_documents d ON d.document_path=p.path AND d.source_path=p.path
            JOIN statarena.objects o ON o.path=p.path AND o.sha256=d.source_sha256 WHERE d.error IS NULL ORDER BY d.source_path""",
            (16 * 1024 * 1024, [p["path"] for p in pointers]), partition_summary)
        relation_rows = run(db, "exact_partition_observation_relations", """SELECT f.id,f.season,o.shard,o.ordinal,s.ref
            FROM unnest(%s::text[]) p(id) JOIN statarena.fixtures f ON f.id=p.id
            LEFT JOIN statarena.observations o ON o.id=f.id LEFT JOIN statarena.shards s ON s.id=o.shard
            ORDER BY f.season,f.id""", (all_ids,))
        relations.extend(relation_rows)
        path_refs = {}
        for r in relations:
            ref = r.get("ref") or {}
            for name, item in {"documents": ref.get("document", {}), **ref.get("tables", {})}.items():
                if item.get("path"):
                    path_refs[item["path"]] = item
        assert len(path_refs) <= 512
        run(db, "archive_relation_source_versions", """SELECT p.path,o.size,encode(o.sha256,'hex') sha256,
            s.status,s.document_count,s.error_count,encode(s.source_sha256,'hex') indexed_sha256,
            (SELECT count(*) FROM statarena.file_documents d WHERE d.source_path=p.path AND d.source_sha256=o.sha256 AND d.error IS NULL) current_error_free_documents
            FROM unnest(%s::text[]) p(path) LEFT JOIN statarena.objects o ON o.path=p.path
            LEFT JOIN statarena.file_document_sources s ON s.source_path=p.path ORDER BY p.path""", (sorted(path_refs),))
        chosen = {}
        for p in partitions:
            preferred = p["richestMatchIds"]
            for r in sorted((r for r in relations if r["season"] == p["season"] and r.get("ref")), key=lambda r: (r["id"] not in preferred, r["id"])):
                for fam, ref in r["ref"].get("tables", {}).items():
                    chosen.setdefault((p["season"], fam), {"season": p["season"], "family": fam, "matchId": r["id"], "documentId": r["ref"].get("documentId"), "path": ref["path"]})
        choices = list(chosen.values())[:32]
        report["archiveShapeChoices"] = choices

        def archive_shapes(rows):
            result = []
            for r in rows:
                doc = r.pop("document")
                for chosen in (c for c in choices if c["path"] == r["source_path"]):
                    entries = doc if isinstance(doc, list) else [doc]
                    hits = [x for x in entries if x.get("documentId") == chosen["documentId"]]
                    item = dict(**r, **chosen, matchedEntries=len(hits), canonicalSha256=hashlib.sha256(canonical(hits).encode()).hexdigest(), fieldVariantMatrix=shape(hits))
                    result.append(item)
                    shapes.append(item)
            return result

        run(db, "selected_archive_family_native_shapes", """SELECT d.source_path,encode(d.source_sha256,'hex') source_sha256,
            pg_column_size(d.document) stored_jsonb_bytes,d.document FROM unnest(%s::text[]) p(path)
            JOIN statarena.objects o ON o.path=p.path JOIN statarena.file_document_sources s ON s.source_path=p.path AND s.source_sha256=o.sha256 AND s.status='ready'
            JOIN LATERAL (SELECT * FROM statarena.file_documents d WHERE d.source_path=p.path AND d.source_sha256=o.sha256 AND d.error IS NULL AND pg_column_size(d.document)<=%s ORDER BY d.document_path LIMIT 1) d ON true
            ORDER BY d.source_path""", (sorted({c["path"] for c in choices}), MAX_BODY_BYTES), archive_shapes)

        def selected_profiles(rows):
            result = []
            for r in rows:
                doc = r.pop("document")
                ref = r["ref"] or {}
                selected = doc[ref["ordinal"]] if doc is not None and "ordinal" in ref else doc
                if selected is not None and "documentId" in ref:
                    selected = next((x for x in selected if x.get("documentId") == ref["documentId"]), None)
                envelope = (selected or {}).get("observation", (selected or {}).get("response", selected or {}))
                data = envelope.get("data") or {}
                expected_id = r["endpoint"].split("/")[-1]
                item = metadata_ref(dict(r))
                item.update(expectedId=expected_id, actualId=data.get("id"), idMatches=data.get("id") == expected_id,
                            selectedStatus=envelope.get("status"), selectedErrorCode=(envelope.get("error") or {}).get("code"),
                            canonicalSha256=hashlib.sha256(canonical(selected).encode()).hexdigest(), fieldVariantMatrix=shape(selected))
                result.append(item)
            return result

        endpoints = [('/players/' if p.startswith('p_') else '/teams/') + p for p in sorted(profile_ids) if p.startswith(('p_', 't_'))][:12]
        run(db, "exact_selected_profile_versions", """SELECT r.endpoint,r.params,r.status,r.ref,r.updated_at,
            encode(o.sha256,'hex') physical_sha256,s.status indexed_status,d.document
            FROM unnest(%s::text[]) p(endpoint) LEFT JOIN statarena.resources r ON r.endpoint=p.endpoint AND r.params='{}'
            LEFT JOIN statarena.objects o ON o.path=r.ref->>'path'
            LEFT JOIN statarena.file_document_sources s ON s.source_path=o.path AND s.source_sha256=o.sha256
            LEFT JOIN LATERAL (SELECT d.document FROM statarena.file_documents d WHERE d.source_path=o.path AND d.source_sha256=o.sha256 AND d.error IS NULL AND pg_column_size(d.document)<=%s ORDER BY d.document_path LIMIT 1) d ON s.status='ready'
            ORDER BY p.endpoint""", (endpoints, MAX_BODY_BYTES), selected_profiles)
        db.execute("ROLLBACK")
    report["archiveFamilyShapes"] = shapes
    report["finishedUtc"] = dt.datetime.now(dt.timezone.utc).isoformat()
    report["limitations"].append("Supplement is a second sequential read-only snapshot. Initial receipt is preserved byte-for-byte; archive/manifest reads do not imply the friend's transfer is complete.")
    (OUT / "source_scope.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str) + "\n")
    print(canonical({"queries": report["queryCount"], "errors": report["errors"], "currentPartitions": len(partitions), "relations": len(relations), "archiveSourcePaths": len(path_refs), "archiveShapes": len(shapes)}))
    return 1 if report["errors"] else 0


def resolve_archive_members():
    """Preserve the failed documentId selection; verify matchId membership in q19.

    The20-query task budget includes the final exact scoped profile inventory.
    """
    prior = OUT / "source_scope.supplement18.json"
    if prior.exists():
        raise ValueError("Final resolution receipt already exists")
    raw = (OUT / "source_scope.json").read_text()
    report = json.loads(raw)
    assert report["queryCount"] == 18
    prior.write_text(raw)
    report["resolutionAtUtc"] = dt.datetime.now(dt.timezone.utc).isoformat()
    report["resolutionCommand"] = COMMAND + " --resolve-archive-members"
    report["limits"].update(sequentialSnapshots=3, finalResolutionQueries=2)
    report["selectorFailure"] = {
        "query": 17, "expected": "One selected archive entry per family and season",
        "actual": "26 selected source files existed, but zero entries matched a nonexistent documentId in the shard ref",
        "reason": "Shard ref contains family paths and document path; documentId belongs to the document/member, not shard ref",
        "correction": "Resolve selected archive member by its explicit matchId, retain actual documentId and response status; do not infer missing source data from the helper failure",
        "preservedReceipt": prior.name,
    }
    choices = report["archiveShapeChoices"]
    by_name = {q["name"]: q for q in report["queries"]}
    pointers = by_name["current_manifest_pilot_pointers"]["rows"][0]["selectedPointers"]
    fixed_shapes = []

    def run(db, name, sql, params=(), transform=None):
        report["queryCount"] += 1
        assert report["queryCount"] <= MAX_QUERIES
        item = {"number": report["queryCount"], "snapshot": 3, "name": name, "sql": sql, "params": params}
        start = time.monotonic()
        try:
            with db.transaction():
                rows = db.execute(sql, params).fetchall()
                safe = transform(rows) if transform else rows
                item.update(rows=safe, rowCount=len(rows), receiptSha256=hashlib.sha256(canonical(safe).encode()).hexdigest())
            return rows
        except psycopg.Error as error:
            item["error"] = {"class": type(error).__name__, "sqlstate": error.sqlstate}
            report["errors"].append({"query": name, **item["error"]})
            return []
        finally:
            item["elapsedMs"] = round(1000 * (time.monotonic() - start), 3)
            report["queries"].append(item)
            print(canonical({"query": name, "elapsedMs": item["elapsedMs"], "rowCount": item.get("rowCount"), "error": item.get("error")}), flush=True)

    def archive_shapes(rows):
        result = []
        for r in rows:
            doc = r.pop("document")
            for chosen in (c for c in choices if c["path"] == r["source_path"]):
                entries = doc if isinstance(doc, list) else [doc]
                hits = [x for x in entries if x.get("matchId") == chosen["matchId"]]
                response = hits[0].get("response", {}) if len(hits) == 1 else {}
                data = response.get("data")
                item = dict(**r, **{k: v for k, v in chosen.items() if k != "documentId"},
                            matchedEntries=len(hits), documentIds=[x.get("documentId") for x in hits],
                            responseStatus=response.get("status"), responseHasData=data is not None,
                            errorCode=(response.get("error") or {}).get("code"),
                            canonicalSha256=hashlib.sha256(canonical(hits).encode()).hexdigest(), fieldVariantMatrix=shape(hits))
                result.append(item)
                fixed_shapes.append(item)
        return result

    with psycopg.connect(
        host="statarena-postgres.clcy2iqyajbl.us-east-2.rds.amazonaws.com", dbname="statarena_prod",
        user="statarena_ingest", sslmode="verify-full", sslrootcert=str(ROOT / "dashboard/backend/certs/rds-us-east-2.pem"),
        connect_timeout=7, autocommit=True, row_factory=dict_row,
        options="-c default_transaction_read_only=on -c statement_timeout=8000 -c lock_timeout=1000 -c max_parallel_workers_per_gather=0",
        application_name="statarena-orion-pro-source-scope-resolution",
    ) as db:
        db.execute("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY")
        run(db, "resolved_archive_family_native_shapes", """SELECT current_setting('transaction_read_only') read_only,
            pg_current_snapshot()::text snapshot,d.source_path,encode(d.source_sha256,'hex') source_sha256,
            pg_column_size(d.document) stored_jsonb_bytes,d.document FROM unnest(%s::text[]) p(path)
            JOIN statarena.objects o ON o.path=p.path JOIN statarena.file_document_sources s ON s.source_path=p.path AND s.source_sha256=o.sha256 AND s.status='ready'
            JOIN LATERAL (SELECT * FROM statarena.file_documents d WHERE d.source_path=p.path AND d.source_sha256=o.sha256 AND d.error IS NULL AND pg_column_size(d.document)<=%s ORDER BY d.document_path LIMIT 1) d ON true
            ORDER BY d.source_path""", (sorted({c["path"] for c in choices}), MAX_BODY_BYTES), archive_shapes)
        run(db, "all_scoped_player_team_profile_source_versions", """WITH partitions AS (
              SELECT d.document->'tables' tables FROM unnest(%s::text[]) p(path)
              JOIN statarena.file_documents d ON d.document_path=p.path AND d.source_path=p.path
              JOIN statarena.objects o ON o.path=p.path AND o.sha256=d.source_sha256 WHERE d.error IS NULL
            ), packed AS (
              SELECT key table_name,value table_value FROM partitions CROSS JOIN LATERAL jsonb_each(tables)
              WHERE key IN ('players','teams')
            ), columns AS (
              SELECT p.*,k.ordinality::int-1 key_index FROM packed p CROSS JOIN LATERAL jsonb_array_elements_text(table_value->'keys') WITH ORDINALITY k(key_name,ordinality)
              WHERE (table_name='players' AND key_name='playerId') OR (table_name='teams' AND key_name='id')
            ), identities AS (
              SELECT DISTINCT table_name, CASE WHEN table_value->'dictionaries' ? key_index::text
                THEN table_value->'dictionaries'->(key_index::text)->>(row_value->>key_index)::int
                ELSE row_value->>key_index END provider_id
              FROM columns CROSS JOIN LATERAL jsonb_array_elements(table_value->'rows') row_value
            ) SELECT i.table_name,i.provider_id,r.status,r.updated_at,r.ref->>'path' source_path,
              r.ref->>'ordinal' source_ordinal,encode(o.sha256,'hex') physical_sha256,
              s.status indexed_status,s.document_count,s.error_count,encode(s.source_sha256,'hex') indexed_sha256
            FROM identities i LEFT JOIN statarena.resources r ON r.endpoint=(CASE WHEN i.table_name='players' THEN '/players/' ELSE '/teams/' END)||i.provider_id AND r.params='{}'
            LEFT JOIN statarena.objects o ON o.path=r.ref->>'path'
            LEFT JOIN statarena.file_document_sources s ON s.source_path=o.path ORDER BY i.table_name,i.provider_id""",
            ([p["path"] for p in pointers],))
        db.execute("ROLLBACK")
    report["resolvedArchiveFamilyShapes"] = fixed_shapes
    report["finishedUtc"] = dt.datetime.now(dt.timezone.utc).isoformat()
    report["limitations"].append("Final member resolution/profile inventory is a third sequential snapshot; q17's failed helper resolution remains preserved, q19 supplies actual archive member shapes. This exhausts the20-query budget.")
    (OUT / "source_scope.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str) + "\n")
    print(canonical({"queries": report["queryCount"], "errors": report["errors"], "resolvedArchiveShapes": len(fixed_shapes), "nonUniqueMembers": sum(s["matchedEntries"] != 1 for s in fixed_shapes)}))
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--supplement", action="store_true", help="Add six bounded queries to the preserved initial12-query receipt")
    parser.add_argument("--resolve-archive-members", action="store_true", help="Preserve the failed helper selector and use the remaining two queries")
    parser.add_argument("--out-dir", type=Path, help="Fresh metadata-receipt directory for an independently authorized rerun")
    args = parser.parse_args()
    if args.out_dir:
        OUT = args.out_dir.resolve()
    OUT.mkdir(parents=True, exist_ok=True)
    raise SystemExit(resolve_archive_members() if args.resolve_archive_members else supplement() if args.supplement else main())
