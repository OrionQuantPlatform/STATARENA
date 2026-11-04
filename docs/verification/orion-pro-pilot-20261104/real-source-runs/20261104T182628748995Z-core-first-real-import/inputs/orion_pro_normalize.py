"""Existing AWS source documents -> disposable LOCAL approved typed PostgreSQL.

No remote mutation, provider request, source-body file, or alternate source store.
Core import is an explicitly bounded projection. Native/family gaps prevent full
acceptance; the model is never patched by this importer.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import json
import math
import os
from pathlib import Path
import re
import time

import psycopg
from psycopg.types.json import Jsonb

ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT / "docs/architecture/orion-plan-20261104/target-schema.proposed.json"
VERSION = "real_source_core_v1"
SHA = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
MISSING = object()
CORE_METRICS = {
    "goals":"goals", "assists":"assists", "shots":"shots", "shotsOnTarget":"shots_on_target",
    "chancesCreated":"chances_created", "bigChancesCreated":"big_chances_created",
    "passesAccurate":"passes_completed", "passesAttempted":"passes_attempted", "passesFinalThird":"passes_final_third",
    "defensiveActions":"defensive_actions", "interceptions":"interceptions", "tackles":"tackles", "recoveries":"recoveries",
    "duelsWon":"duels_won", "duelsLost":"duels_lost", "aerialsWon":"aerial_duels_won", "aerialDuels":"aerial_duels_attempted",
    "touches":"touches", "touchesBox":"touches_box", "clearances":"clearances", "blocks":"blocks",
    "dribbles":"dribbles_completed", "dribblesAttempted":"dribbles_attempted", "saves":"saves",
    "xg":"xg", "npxg":"non_penalty_xg", "xa":"xa", "xgot":"xgot", "minutes":"minutes_played",
    "rating":"provider_rating", "goalsPrevented":"goals_prevented",
}
SHOT_MAP = {"xg":"xg", "xgot":"xgot", "minute":"minute", "minuteAdded":"minute_added",
            "isGoal":"is_goal", "isOwnGoal":"is_own_goal", "isOnTarget":"is_on_target",
            "isBlocked":"is_blocked", "insideBox":"is_inside_box", "shotType":"source_shot_type",
            "type":"source_event_type", "situation":"situation"}
PERFORMANCE_STRUCTURAL = {"id","playerRef","playerId","teamId","team","matchId","leagueId","league","country","season","date","role","positionId","rawPitchX","rawPitchY","shirtNumber","starter","statsReliable","isCaptain"}
PERIODS = {"1":"first_half", "1st":"first_half", "first_half":"first_half", "2":"second_half", "2nd":"second_half", "second_half":"second_half",
           "ALL":"full_match", "all":"full_match", "full_match":"full_match", "1H":"first_half", "2H":"second_half"}


def normalized(value):
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("Non-finite source number")
        return {"number":format(value.normalize(), "f")}
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Non-finite typed number")
        return {"number":format(Decimal(str(value)).normalize(), "f")}
    if type(value) is int:
        return {"number":str(value)}
    if isinstance(value, dict):
        return {k:normalized(v) for k,v in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [normalized(v) for v in value]
    if isinstance(value, (datetime,date)):
        return value.isoformat()
    return value


def hashed(value):
    return hashlib.sha256(json.dumps(normalized(value), sort_keys=True, separators=(",",":"), ensure_ascii=False).encode()).hexdigest()


class MappingError(ValueError):
    """Metadata-only, never includes a source body or PostgreSQL row detail."""


class SourceReader:
    def __init__(self, evidence):
        self.evidence = Path(evidence)
        self.ledger = self.evidence.parents[1] / "real-source-budget.json"
        self.total = json.loads(self.ledger.read_text()) if self.ledger.exists() else {"queries":0,"decodedBytes":0,"runs":[]}
        self.start_queries, self.start_bytes = self.total["queries"], self.total["decodedBytes"]
        self.receipts, self.cache, self.meta = [], {}, {}

    def __enter__(self):
        self.db = psycopg.connect(host="statarena-postgres.clcy2iqyajbl.us-east-2.rds.amazonaws.com", dbname="statarena_prod", user="statarena_ingest",
            sslmode="verify-full", sslrootcert=str(ROOT / "dashboard/backend/certs/rds-us-east-2.pem"), connect_timeout=7, autocommit=True,
            options="-c default_transaction_read_only=on -c statement_timeout=8000 -c lock_timeout=1000 -c max_parallel_workers_per_gather=0",
            application_name="statarena-real-source-local-pilot")
        self.db.execute("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY")
        rows = self.query("source_identity", "SELECT current_database(),current_user,current_setting('transaction_read_only'),pg_current_snapshot()::text,(SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid())")
        if rows[0][0:3] != ("statarena_prod","statarena_ingest","on") or rows[0][-1] is not True:
            raise MappingError("Unexpected AWS read-only source identity")
        return self

    def query(self, name, sql, params=(), *, body_column=None):
        if self.total["queries"] >= 100:
            raise MappingError("Cumulative100-query AWS source budget exhausted")
        self.total["queries"] += 1
        self.ledger.write_text(json.dumps(self.total,indent=2)+"\n")
        started = time.monotonic()
        item = {"name":name,"sql":sql,"parameters":params,"globalQueryNumber":self.total["queries"]}
        try:
            rows = self.db.execute(sql,params).fetchall()
            safe = []
            for row in rows:
                if body_column is not None:
                    text = row[body_column]
                    amount = len(text.encode()) if text is not None else 0
                    self.total["decodedBytes"] += amount
                    if self.total["decodedBytes"] > 256*1024*1024:
                        raise MappingError("Cumulative256MiB decoded AWS source budget exhausted")
                    safe.append(list(row[:body_column])+[{"decodedBytes":amount,"decodedSha256":hashlib.sha256(text.encode()).hexdigest() if text else None}]+list(row[body_column+1:]))
                else:
                    safe.append(row)
            item.update(rowCount=len(rows),metadata=safe)
            return rows
        except psycopg.Error as error:
            item.update(errorType=type(error).__name__,sqlstate=error.sqlstate)
            raise MappingError("AWS source query failed: " + name + ": " + str(error.sqlstate)) from None
        finally:
            item["elapsedMs"] = round((time.monotonic()-started)*1000,3)
            self.receipts.append(item)
            self.ledger.write_text(json.dumps(self.total,indent=2)+"\n")
            (self.evidence / "source-queries.json").write_text(json.dumps(self.receipts,indent=2,default=str)+"\n")

    def documents(self, expected):
        missing = [p for p in expected if p not in self.cache]
        for offset in range(0,len(missing),16):
            paths = missing[offset:offset+16]
            rows = self.query("indexed_source_documents", """SELECT p.path,encode(o.sha256,'hex'),s.status,s.error_count,o.size,o.updated_at,
                d.document::text FROM unnest(%s::text[]) p(path)
                LEFT JOIN statarena.objects o ON o.path=p.path
                LEFT JOIN statarena.file_document_sources s ON s.source_path=p.path AND s.source_sha256=o.sha256
                LEFT JOIN statarena.file_documents d ON d.document_path=p.path AND d.source_path=p.path AND d.source_sha256=o.sha256 AND d.error IS NULL
                ORDER BY p.path""", (paths,), body_column=6)
            for path,sha,status,errors,size,updated,text in rows:
                if sha != expected[path] or status != "ready" or errors != 0 or text is None:
                    raise MappingError("Current source version mismatch/unavailable: " + path)
                self.cache[path] = json.loads(text,parse_float=Decimal,parse_int=Decimal)
                self.meta[path] = {"path":path,"physicalSha256":sha,"bytes":size,"updatedAt":updated}
        return {p:self.cache[p] for p in expected}

    def profile_versions(self, parts, scope):
        provider_ids = {r["playerId"] for p in parts for r in p["tables"]["players"]}
        endpoints = ["/players/"+p for p in sorted(provider_ids)]
        rows = self.query("exact_scoped_profile_resource_versions", """SELECT r.endpoint,r.status,r.ref->>'path',r.ref->>'ordinal',encode(o.sha256,'hex'),s.status,s.error_count
            FROM statarena.resources r LEFT JOIN statarena.objects o ON o.path=r.ref->>'path'
            LEFT JOIN statarena.file_document_sources s ON s.source_path=o.path AND s.source_sha256=o.sha256
            WHERE r.endpoint=ANY(%s) AND r.params='{}' ORDER BY r.endpoint""", (endpoints,))
        available = {r[0].split('/')[-1] for r in rows if r[1]==200 and r[4] and r[5]=="ready" and r[6]==0}
        gaps = sorted(provider_ids-available)
        if set(gaps) != set(scope["sourceSummary"]["missingPlayerResourceLookupIds"]):
            raise MappingError("Scoped player profile lookup keys changed from the pinned source audit")
        return gaps

    def budget(self):
        return {"queries":self.total["queries"],"decodedBytes":self.total["decodedBytes"],
                "runQueries":self.total["queries"]-self.start_queries,"runDecodedBytes":self.total["decodedBytes"]-self.start_bytes,
                "limits":{"queries":100,"decodedBytes":256*1024*1024},"sourceConnection":"one verified-TLS repeatable-read READ ONLY connection"}

    def __exit__(self, typ, value, traceback):
        try:
            self.db.execute("ROLLBACK")
        finally:
            self.db.close()
            self.total["runs"].append({"evidence":self.evidence.name,"queries":self.total["queries"]-self.start_queries,"decodedBytes":self.total["decodedBytes"]-self.start_bytes})
            self.ledger.write_text(json.dumps(self.total,indent=2)+"\n")


def unpack(table):
    dictionaries = table.get("dictionaries",{})
    result = []
    for i,values in enumerate(table["rows"]):
        absent = set(int(v) for v in table.get("missing",{}).get(str(i),[]))
        result.append({key:(dictionaries[str(j)][int(values[j])] if str(j) in dictionaries and values[j] is not None else values[j])
                       for j,key in enumerate(table["keys"]) if j not in absent})
    return result


class TypedCore:
    def __init__(self, conn, evidence, source):
        self.conn, self.evidence, self.source = conn, Path(evidence), source
        self.model = json.loads(MODEL.read_text())
        self.tables = {t["qualified_name"]:t for s in self.model["schemas"] for t in s["tables"]}
        self.ids, self.documents, self.records, self.aliases = {}, {}, {}, set()
        self.matches, self.sides, self.people, self.teams, self.profiles, self.stats = {}, {}, {}, {}, {}, {}
        self.field_counts, self.numeric, self.unverified = Counter(), defaultdict(Counter), Counter()
        self.g = None

    def number(self, value, sql_type, path):
        if value is None:
            return None
        if isinstance(value,bool) or not isinstance(value,(Decimal,int,float)):
            raise MappingError("Non-numeric native value for numeric target: " + path)
        dec = value if isinstance(value,Decimal) else Decimal(str(value))
        if not dec.is_finite():
            raise MappingError("Non-finite number: " + path)
        scale = max(0,-dec.as_tuple().exponent)
        self.numeric[path]["observations"] += 1
        self.numeric[path]["maximumDecimalPlaces"] = max(self.numeric[path]["maximumDecimalPlaces"],scale)
        if sql_type in {"integer","smallint","bigint"}:
            bound = {"smallint":2**15,"integer":2**31,"bigint":2**63}[sql_type]
            if dec != dec.to_integral_value() or not -bound <= dec < bound:
                raise MappingError("Non-integral or overflowing integer: " + path)
            return int(dec)
        if sql_type.startswith("numeric("):
            precision,scale_limit = map(int,re.findall(r"\d+",sql_type))
            if dec != dec.quantize(Decimal(1).scaleb(-scale_limit)) or abs(dec) >= Decimal(10)**(precision-scale_limit):
                raise MappingError("Unrepresentable fixed-scale numeric; rounding prohibited: " + path)
        if sql_type == "double precision":
            floating = float(dec)
            if not math.isfinite(floating) or Decimal(str(floating)) != dec:
                raise MappingError("Source decimal cannot round-trip through double precision: " + path)
            return floating
        return dec

    def native(self, row, key, target):
        value = row.get(key,MISSING)
        state = "absent" if value is MISSING else "null" if value is None else "number" if isinstance(value,(Decimal,int,float)) and not isinstance(value,bool) else "string" if isinstance(value,str) else "invalid"
        self.field_counts[(target,state)] += 1
        if state == "invalid":
            raise MappingError("Unapproved native scalar form: " + target)
        return {target+"_state":state,target:None if value is MISSING or value is None else str(value),
                target+"_source_number":self.number(value,"numeric",target) if state=="number" else None}

    def insert(self, table, **values):
        columns = self.tables[table]["columns"]
        defaults = {"recorded_from_gen":self.g,"variant_key":"legacy:primary","is_canonical":True,
                    "contract_version":VERSION,"transform_version":VERSION,"transform_code_sha256":SHA,
                    "canonical_policy_version":VERSION,"provenance_kind":"derived"}
        data = {k:v for k,v in defaults.items() if k in columns}
        data.update(values)
        if self.ids.get("source") and "source_id" in columns and "source_id" not in data:
            data["source_id"] = self.ids["source"]
        if set(data)-set(columns):
            raise MappingError("Unknown target columns: " + table + ": " + ",".join(sorted(set(data)-set(columns))))
        for key,value in list(data.items()):
            kind = columns[key]["type"]
            if kind.startswith(("numeric","double precision","integer","smallint","bigint")) and value is not None:
                data[key] = self.number(value,kind,table+"."+key)
        keys = list(data)
        params = tuple(Jsonb(data[k]) if columns[k]["type"]=="jsonb" and data[k] is not None else data[k] for k in keys)
        cursor = self.conn.execute(f"INSERT INTO {table} ({','.join(keys)}) VALUES ({','.join(['%s']*len(keys))}) RETURNING *",params)
        return dict(zip((c.name for c in cursor.description),cursor.fetchone()))

    def record(self, path, locator, kind, key):
        cache = path,locator
        if cache not in self.records:
            if path not in self.documents:
                meta = self.source.meta[path]
                self.documents[path] = self.insert("ingest.source_documents",source_id=self.ids["source"],dataset_id=self.ids["dataset"],
                    content_sha256=meta["physicalSha256"],retrieved_at=meta["updatedAt"],source_updated_at=meta["updatedAt"],
                    storage_provider="aws_s3",origin_kind="legacy_file",retention_state="staged",legacy_object_path=path,
                    byte_length=meta["bytes"],import_run_id=self.ids["run"])["id"]
            self.records[cache] = self.insert("ingest.source_records",source_id=self.ids["source"],document_id=self.documents[path],
                locator_kind="json_pointer",locator=locator,record_kind=kind,external_key=key)["id"]
        return self.records[cache]

    def alias(self, kind, key, **binding):
        if (kind,key) not in self.aliases:
            self.insert("ingest.public_aliases",route_kind=kind,public_key=key,**binding)
            self.aliases.add((kind,key))

    def stats_values(self, row):
        result = {}
        for source,target in CORE_METRICS.items():
            self.field_counts[("performances."+source,"absent" if source not in row else "null" if row[source] is None else "present")] += 1
            if source in row:
                result[target] = row[source]
        for key in set(row)-set(CORE_METRICS)-PERFORMANCE_STRUCTURAL:
            self.unverified["performances."+key] += 1
        return result

    def import_core(self, parts):
        manifest = hashed({"source":[(p["path"],self.source.meta[p["path"]]["physicalSha256"]) for p in parts],"transform":SHA})
        snapshot_key = "real-source:"+manifest
        existing = self.conn.execute("SELECT generation,status FROM ingest.dataset_snapshots WHERE snapshot_key=%s",(snapshot_key,)).fetchone()
        if existing:
            if existing[1] != "sealed":
                raise MappingError("Existing real-source generation is not sealed")
            return {"generation":existing[0],"reused":True,"newFactRevisions":0,"duplicateRows":0}
        with self.conn.transaction():
            self.g = self.conn.execute("SELECT ingest.begin_generation(%s,%s,%s)",(snapshot_key,VERSION,VERSION)).fetchone()[0]
            for name,table in self.tables.items():
                if "relation_code" in table["columns"] and table["phase"] != "models":
                    self.conn.execute("INSERT INTO ingest.relation_contracts(relation_code,relation_name,contract_version,grain_definition) VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING",(name,name,VERSION,table["grain"]))
            self.ids["source"] = self.insert("ingest.sources",code="pitchapi_saved",name="PitchAPI existing legacy observations",base_url="https://pitchapi.dev")["id"]
            self.ids["dataset"] = self.insert("ingest.source_datasets",source_id=self.ids["source"],dataset_key="ligue1-two-seasons-normalized-comparison",contract_version=VERSION)["id"]
            self.ids["run"] = self.insert("ingest.import_runs",mode="rebuild",transform_version=VERSION,code_commit=SHA)["id"]
            league_record = self.record(parts[0]["path"],"/tables/competitions","competition","l_3FJFUl")
            competition = self.insert("football.competitions",name="Ligue 1",slug="l_3FJFUl",competition_type="league",gender="unknown",source_record_id=league_record)
            self.alias("competition","l_3FJFUl",competition_id=competition["id"],competition_revision_id=competition["revision_id"],source_record_id=league_record)
            # Stable identities are shared; profile observations retain their own variant IDs.
            all_players, all_teams = {}, {}
            for p in parts:
                for row in p["tables"]["players"]:
                    all_players[row["playerId"]] = row
                for row in p["tables"]["teams"]:
                    all_teams[row["id"]] = row
            for pid,row in sorted(all_players.items()):
                self.people[pid] = self.insert("football.players",display_name=row.get("name"))
                self.alias("player",pid,player_id=self.people[pid]["id"])
            for tid,row in sorted(all_teams.items()):
                self.teams[tid] = self.insert("football.teams",slug=tid,name=row.get("name"),team_type="unknown",gender="unknown")
                self.alias("team",tid,team_id=self.teams[tid]["id"])
            latest_profile = {}
            for p in parts:
                for row in p["tables"]["players"]:
                    latest_profile[row["playerId"]] = row["id"]
            editions = {}
            for p in parts:
                path, season = p["path"],p["season"]
                edition_record = self.record(path,"/meta/season","competition_season",season)
                editions[season] = self.insert("football.competition_seasons",competition_id=competition["id"],competition_revision_id=competition["revision_id"],
                    season_key=season,label=season,status="unknown",source_record_id=edition_record)
                for i,row in enumerate(p["tables"]["players"]):
                    if row["id"] in self.profiles:
                        continue
                    record = self.record(path,f"/tables/players/rows/{i}","normalized_player_profile",row["id"])
                    profile = self.insert("football.player_profile_versions",player_id=self.people[row["playerId"]]["id"],external_profile_version_id=row["id"],
                        display_name=row["name"],observed_at=self.source.meta[path]["updatedAt"],profile_context="legacy_normalized_global",
                        variant_key=row["id"],is_canonical=latest_profile[row["playerId"]]==row["id"],profile_content_sha256=hashed(row),
                        raw_position_code_state="absent",shirt_number_state="absent",source_record_id=record)
                    self.profiles[row["id"]] = profile
                    self.alias("profile",row["id"],player_id=profile["player_id"],profile_version_id=profile["id"],source_record_id=record)
                    if "imageUrl" in row:self.unverified["players.imageUrl.media_reference"] += 1
                for i,fixture in enumerate(p["tables"]["fixtures"]):
                    mid = fixture["id"]
                    record = self.record(path,f"/tables/fixtures/rows/{i}","fixture",mid)
                    day = date.fromisoformat(fixture["date"][:10]) if fixture.get("date") else None
                    match = self.insert("football.matches",competition_season_id=editions[season]["id"],competition_season_revision_id=editions[season]["revision_id"],
                        match_date=day,kickoff_precision="date" if day else "unknown",status=fixture.get("status") or "unknown",round_label=fixture.get("round_name"),
                        publication_state="draft",source_record_id=record)
                    self.matches[mid] = match
                    self.alias("match",mid,match_id=match["id"],match_revision_id=match["revision_id"],source_record_id=record)
                    for side in ("home","away"):
                        team = fixture.get(side+"_team") or {}
                        if not team.get("id") or team["id"] not in self.teams:
                            raise MappingError("Fixture team not in scoped typed team identities: " + mid + ":" + side)
                        member = self.insert("football.match_teams",match_id=match["id"],match_revision_id=match["revision_id"],side=side,team_id=self.teams[team["id"]]["id"],source_record_id=record)
                        self.sides[(mid,team["id"])] = member
                        if "score_"+side in fixture:
                            self.insert("football.match_scores",match_id=match["id"],side=side,score_scope="final_without_shootout",score_basis="unknown",
                                goals=fixture["score_"+side],match_team_revision_id=member["revision_id"],source_record_id=record)
                    for key in set(fixture)-{"id","date","status","round_name","home_team","away_team","score_home","score_away"}:
                        self.unverified["fixtures."+key] += 1
                for i,row in enumerate(p["tables"]["performances"]):
                    mid,pid,tid = row["matchId"],row["playerId"],row["teamId"]
                    record = self.record(path,f"/tables/performances/rows/{i}","performance",row["id"])
                    starter = row.get("starter")
                    participant = self.insert("football.match_players",match_id=self.matches[mid]["id"],player_id=self.people[pid]["id"],team_id=self.teams[tid]["id"],
                        profile_version_id=self.profiles[row["playerRef"]]["id"],match_team_revision_id=self.sides[(mid,tid)]["revision_id"],
                        squad_status="starter" if starter is True else "observed",is_starter=starter,played=None,source_record_id=record,
                        is_captain=row.get("isCaptain"),**self.native(row,"positionId","raw_position_code"),**self.native(row,"shirtNumber","shirt_number"))
                    self.stats[row["id"]] = self.insert("football.player_match_stats",match_id=participant["match_id"],player_id=participant["player_id"],team_id=participant["team_id"],
                        match_player_revision_id=participant["revision_id"],period_code="full_match",period_definition_version="bootstrap_v1",source_record_id=record,**self.stats_values(row))
                for i,row in enumerate(p["tables"]["shots"]):
                    mid,tid = row["matchId"],row.get("teamId")
                    if tid not in self.teams or (mid,tid) not in self.sides:
                        raise MappingError("Shot team is not a scoped match side: " + mid)
                    record = self.record(path,f"/tables/shots/rows/{i}","shot",str(row["id"]))
                    values = {target:row[source] for source,target in SHOT_MAP.items() if source in row}
                    period = row.get("period")
                    if period is not None:
                        if str(period) not in PERIODS:
                            self.unverified["shots.period."+str(period)] += 1
                        else:
                            values.update(period_code=PERIODS[str(period)],period_definition_version="bootstrap_v1")
                    pid = row.get("playerId")
                    keeper = row.get("keeperId")
                    values.update(player_id=self.people[pid]["id"] if pid in self.people else None,
                                  keeper_id=self.people[keeper]["id"] if keeper in self.people else None)
                    self.insert("football.shots",match_id=self.matches[mid]["id"],team_id=self.teams[tid]["id"],external_shot_id=str(row["id"]),
                        match_team_revision_id=self.sides[(mid,tid)]["revision_id"],source_record_id=record,source_ordinal=i,**values)
                    for key in set(row)-set(SHOT_MAP)-{"id","matchId","teamId","playerId","keeperId","period"}:
                        self.unverified["shots."+key] += 1
                    if keeper and keeper not in self.people:self.unverified["shots.unresolved_keeper_id"] += 1
            for pid in self.source.profile_gaps:
                self.insert("ingest.quality_issues",run_id=self.ids["run"],rule_code="missing_full_profile_resource_lookup",severity="warning",
                    context={"provider_id":pid,"source_lookup":"/players/{id},{}","scope":"Missing exact resource lookup; not global AWS absence"})
            self.conn.execute("SELECT ingest.seal_generation(%s,%s)",(self.g,manifest))
        return {"generation":self.g,"reused":False,"facts":{"fixtures":len(self.matches),"performances":len(self.stats)},"manifestSha256":manifest}


def load_parts(source, scope):
    queries = {q["name"]:q for q in scope["queries"]}
    pointers = queries["current_manifest_pilot_pointers"]["rows"][0]["selectedPointers"]
    expected = {p["path"]:p["sha256"] for p in pointers}
    docs = source.documents(expected)
    return [{"season":p["season"],"path":p["path"],"tables":{key:unpack(value) for key,value in docs[p["path"]]["tables"].items()}}
            for p in sorted(pointers,key=lambda p:p["season"])]


def oracle_comparisons(conn, parts):
    """Read explicit typed SQL projections, separate from insert/mapper functions."""
    comparisons = []
    for kind,expected,sql in [
        ("fixtures",[(r["id"],r.get("status"),r.get("date")) for p in parts for r in p["tables"]["fixtures"]],
         "SELECT a.public_key,m.status,m.match_date::text FROM ingest.public_aliases_current a JOIN football.matches_current m ON m.id=a.match_id WHERE a.route_kind='match' ORDER BY a.public_key"),
        ("performances",[(r["id"],r.get("xg"),r.get("minutes"),r.get("goals"),r.get("assists")) for p in parts for r in p["tables"]["performances"]],
         "SELECT r.external_key,s.xg,s.minutes_played,s.goals,s.assists FROM football.player_match_stats_current s JOIN ingest.source_records r ON r.id=s.source_record_id ORDER BY r.external_key"),
        ("shots",[(str(r["id"]),r["matchId"],r.get("xg"),r.get("xgot"),r.get("minute")) for p in parts for r in p["tables"]["shots"]],
         "SELECT s.external_shot_id,a.public_key,s.xg,s.xgot,s.minute FROM football.shots_current s JOIN ingest.public_aliases_current a ON a.match_id=s.match_id AND a.route_kind='match' ORDER BY a.public_key,s.external_shot_id"),
    ]:
        rows = list(conn.execute(sql))
        order = lambda r:json.dumps(normalized(r[:2]),sort_keys=True)
        expected,rows = sorted(expected,key=order),sorted(rows,key=order)
        comparisons.append({"kind":kind,"sourceRows":len(expected),"typedRows":len(rows),"sourceSha256":hashed(expected),"typedSha256":hashed(rows),"sql":sql})
    expected_aliases = set()
    for p in parts:
        for kind,table,key in (("match","fixtures","id"),("player","players","playerId"),("profile","players","id"),("team","teams","id"),("competition","competitions","id")):
            expected_aliases.update((kind,r[key]) for r in p["tables"][table])
    rows = list(conn.execute("SELECT route_kind,public_key FROM ingest.public_aliases_current ORDER BY route_kind,public_key"))
    comparisons.append({"kind":"public_aliases","sourceRows":len(expected_aliases),"typedRows":len(rows),"sourceSha256":hashed(sorted(expected_aliases)),"typedSha256":hashed(sorted(rows))})
    return comparisons


def run_real_pilot(conn, evidence, source_scope, phase="core"):
    evidence = Path(evidence)
    scope = json.loads(Path(source_scope).read_text())
    if hashlib.sha256(MODEL.read_bytes()).hexdigest() != scope["modelSha256"]:
        raise MappingError("Approved model digest drift")
    # Ownership/engine verification is performed by the caller's shared local harness.
    local_host = conn.info.host
    if local_host not in {"127.0.0.1","localhost","::1"} or conn.info.server_version != 180006:
        raise MappingError("Only owned LOCAL PostgreSQL18.6 is supported")
    directory = Path(conn.execute("SHOW data_directory").fetchone()[0]).resolve()
    if not any(p.name.startswith(("orion-pro-e2e-","statarena-orion-pro-local-")) for p in directory.parents):
        raise MappingError("Refusing an unowned local PostgreSQL directory")
    conn.execute("SET ROLE orion_pro_ingest")
    role = conn.execute("SELECT current_user").fetchone()[0]
    with SourceReader(evidence) as source:
        parts = load_parts(source,scope)
        source.profile_gaps = source.profile_versions(parts,scope)
        importer = TypedCore(conn,evidence,source)
        result = {"role":role,"phase":phase,"transformSha256":SHA,"fullAcceptance":False}
        try:
            result["import"] = importer.import_core(parts)
            result["oracleComparisons"] = oracle_comparisons(conn,parts)
            result["noop"] = importer.import_core(parts)
            result["nativeShapes"] = {"missingProfileResourceCount":conn.execute("SELECT count(*) FROM ingest.quality_issues WHERE rule_code='missing_full_profile_resource_lookup'").fetchone()[0],
                "missingToZeroCoercions":0,"opaqueSourceBodiesStored":0,"numericRoundingCoercions":0,
                "numericPolicy":"Decimal parse; unconstrained numeric exact; double precision only if Decimal(str(float(v)))==v; fixed scale rejects rounding",
                "stateCounts":[{"path":k[0],"state":k[1],"count":v} for k,v in sorted(importer.field_counts.items())]}
            result["correction"] = exercise_correction(importer,parts)
            result["reads"] = measured_reads(conn)
            result["mapping"] = {"unknownUsefulFieldsSilentlyDropped":0,
                "dispositions":[{"field":field,"status":"unverified","observations":n} for field,n in sorted(importer.unverified.items())],
                "rejected":[],"unverified":["Common metric absent/null state fidelity is not represented by approved target columns", "Raw13-family normalization and full native-field inventory are pending", "Shot coordinate units/frame and source-profile/media fields require approved mapping"]}
        except Exception as error:
            result["failure"] = {"class":type(error).__name__,"sqlstate":getattr(error,"sqlstate",None),
                "reason":str(error) if isinstance(error,MappingError) else getattr(getattr(error,"diag",None),"message_primary",None),
                "constraint":getattr(getattr(error,"diag",None),"constraint_name",None)}
            raise
        finally:
            result["sourceBudget"] = source.budget()
            result["precisionInventory"] = {k:dict(v) for k,v in sorted(importer.numeric.items())}
            (evidence / "normalizer-report.json").write_text(json.dumps(result,indent=2,default=str)+"\n")
    return result


def exercise_correction(importer, parts):
    # A labelled in-memory mutation of an actual source performance; same mapper.
    row = next(r for p in parts for r in p["tables"]["performances"] if r.get("xg") is not None)
    prior = importer.stats[row["id"]]
    old_value = Decimal(str(row["xg"]))
    new_value = old_value + Decimal("0.01")
    changed = dict(row,xg=new_value)
    with importer.conn.transaction():
        importer.g = importer.conn.execute("SELECT ingest.begin_generation(%s,%s,%s)",("real-source-simulated-correction:"+SHA,VERSION,VERSION)).fetchone()[0]
        importer.conn.execute("UPDATE football.player_match_stats SET recorded_to_gen=%s WHERE revision_id=%s",(importer.g,prior["revision_id"]))
        base = {key:value for key,value in prior.items() if not importer.tables["football.player_match_stats"]["columns"][key].get("identity")}
        base.update(importer.stats_values(changed),recorded_from_gen=importer.g,recorded_to_gen=None,provenance_kind="manual")
        fresh = importer.insert("football.player_match_stats",**base)
        importer.conn.execute("SELECT ingest.seal_generation(%s,%s)",(importer.g,hashed({"label":"simulated actual source performance correction","field":"xg","record":row["id"],"new":new_value})))
    old = importer.conn.execute("SELECT xg FROM football.player_match_stats WHERE match_id=%s AND player_id=%s AND period_code='full_match' AND recorded_from_gen<=%s AND (recorded_to_gen IS NULL OR %s<recorded_to_gen)",(prior["match_id"],prior["player_id"],prior["recorded_from_gen"],prior["recorded_from_gen"])).fetchone()[0]
    new = importer.conn.execute("SELECT xg FROM football.player_match_stats_current WHERE revision_id=%s",(fresh["revision_id"],)).fetchone()[0]
    return {"throughActualNormalizer":True,"syntheticChangeToRealSourceRecord":True,"sourceRecordKey":row["id"],"field":"xg",
            "oldValue":str(old_value),"newValue":str(new_value),"oldSnapshotValue":str(old),"newSnapshotValue":str(new),"newGeneration":importer.g}


def measured_reads(conn):
    result = []
    sqls = {
        "list":"SELECT a.public_key,m.match_date,m.status FROM football.matches_current m JOIN ingest.public_aliases_current a ON a.match_id=m.id AND a.route_kind='match' ORDER BY m.match_date,a.public_key LIMIT100",
        "player":"SELECT p.player_id,count(*),sum(s.xg),sum(s.minutes_played) FROM football.match_players_current p JOIN football.player_match_stats_current s ON s.match_player_revision_id=p.revision_id GROUP BY p.player_id ORDER BY p.player_id LIMIT20",
        "club":"SELECT team_id,count(*),sum(xg) FROM football.player_match_stats_current GROUP BY team_id ORDER BY team_id",
        "match":"SELECT match_id,count(*),sum(xg),sum(minutes_played) FROM football.player_match_stats_current GROUP BY match_id ORDER BY match_id LIMIT20",
    }
    for kind,sql in sqls.items():
        sql = re.sub(r"LIMIT(\d)",r"LIMIT \1",sql)
        start = time.monotonic()
        rows = list(conn.execute(sql))
        result.append({"kind":kind,"environment":"local","sql":sql,"rows":len(rows),"resultSha256":hashed(rows),"elapsedMs":round((time.monotonic()-start)*1000,3)})
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--local",action="store_true",required=True)
    parser.add_argument("--source-scope",type=Path,required=True)
    parser.add_argument("--phase",choices=["core","families"],default="core")
    parser.add_argument("--evidence",type=Path,required=True)
    args = parser.parse_args()
    from orion_pro_migrate import local_connection
    args.evidence.mkdir(parents=True,exist_ok=True)
    try:
        with local_connection(psycopg) as conn:
            result = run_real_pilot(conn,args.evidence,args.source_scope,args.phase)
        print(json.dumps({"status":"local_core_projection","fullAcceptance":result["fullAcceptance"],"sourceBudget":result["sourceBudget"]}))
        return 0
    except Exception as error:
        print(json.dumps({"status":"failed","errorType":type(error).__name__,"sqlstate":getattr(error,"sqlstate",None),"reason":str(error) if isinstance(error,MappingError) else None}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
