"""Typed pilot inputs and complete database workflows, specified before guard code.

The small normalizer below is a fixture driver. It is not the production collector.
It reads/writes typed columns only and never stores its synthetic HTTP response bodies.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import threading
import time


MODEL = Path(__file__).resolve().parents[2] / "architecture/orion-plan-20261104/target-schema.proposed.json"
SHA = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
NOW = datetime(2026, 11, 4, 17, 0, tzinfo=timezone.utc)


def hashed(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()


class PilotWorkflow:
    def __init__(self, conn, dsn, evidence, psycopg):
        self.conn, self.dsn, self.evidence, self.psycopg = conn, dsn, evidence, psycopg
        self.model = json.loads(MODEL.read_text())
        self.tables = {t["qualified_name"]: t for s in self.model["schemas"] for t in s["tables"]}
        self.g, self.counter, self.audit = None, 0, []
        self.ids, self.editions, self.matches, self.sides, self.participants, self.stats = {}, {}, {}, {}, {}, {}

    def _log(self, item):
        self.audit.append(item)
        (self.evidence / "workflow-observations.json").write_text(json.dumps(self.audit, indent=2, default=str)+"\n")

    def _row(self, table, where, params=()):
        cur = self.conn.execute(f"SELECT * FROM {table} WHERE {where}", params)
        row = cur.fetchone()
        return dict(zip((c.name for c in cur.description),row)) if row else None

    def _insert(self, table, **values):
        columns = self.tables[table]["columns"]
        common = {"contract_version":"pilot_v1", "transform_version":"pilot_v1", "transform_code_sha256":SHA,
                  "canonical_policy_version":"pilot_v1", "variant_key":"pilot:primary", "is_canonical":True,
                  "provenance_kind":"manual", "recorded_from_gen":self.g,
                  "raw_position_code_state":"absent", "shirt_number_state":"absent"}
        data = {k:v for k,v in common.items() if k in columns}
        data.update(values)
        if data.get("source_id") is not None and data.get("source_record_id") is not None and "provenance_kind" in columns and "provenance_kind" not in values:
            data["provenance_kind"] = "provider"
        unknown = set(data)-set(columns)
        assert not unknown, (table,unknown)
        names = list(data)
        sql = f"INSERT INTO {table} ({','.join(names)}) VALUES ({','.join(['%s']*len(names))}) RETURNING *"
        cur = self.conn.execute(sql,tuple(data[k] for k in names))
        row = dict(zip((c.name for c in cur.description),cur.fetchone()))
        return row

    def _begin(self, label, conn=None):
        self.counter += 1
        return (conn or self.conn).execute("SELECT ingest.begin_generation(%s,%s,%s)",
            (f"pilot:{label}:{self.counter}","pilot_v1","pilot_priority_v1")).fetchone()[0]

    @contextmanager
    def _generation(self, label):
        previous = self.g
        with self.conn.transaction():
            self.g = self._begin(label)
            try:
                yield self.g
                self.conn.execute("SELECT ingest.seal_generation(%s,%s)",(self.g,hashed({"label":label,"generation":self.g})))
            finally:
                self.g = previous

    def _replace(self, table, row, **changes):
        pk = self.tables[table]["primary_key"]["columns"]
        where = " AND ".join(f"{k}=%s" for k in pk)
        self.conn.execute(f"UPDATE {table} SET recorded_to_gen=%s WHERE {where}",(self.g,*[row[k] for k in pk]))
        data = {k:v for k,v in row.items() if not self.tables[table]["columns"][k].get("identity")}
        data.update(recorded_from_gen=self.g,recorded_to_gen=None)
        data.update(changes)
        return self._insert(table,**data)

    def _reject(self, label, action, *, generation=True, states=None):
        accepted = states or {"23503","23505","23514","P0001","55000","42501","40001","22023"}
        prior = self.g
        try:
            with self.conn.transaction():
                if generation:
                    self.g = self._begin(label)
                action()
                if generation:
                    self.conn.execute("SELECT ingest.seal_generation(%s,%s)",(self.g,hashed(label)))
                self.conn.execute("SET CONSTRAINTS ALL IMMEDIATE")
        except self.psycopg.Error as exc:
            assert exc.sqlstate in accepted, f"{label}: unintended SQL error {exc.sqlstate}: {exc}"
            result = {"rejected":label,"sqlstate":exc.sqlstate,"constraint":exc.diag.constraint_name,"message":str(exc).splitlines()[0]}
            self._log(result)
            return result
        finally:
            self.g = prior
        raise AssertionError(f"{label}: invalid workflow was accepted")

    def _record(self, source, dataset, key, content=None, request=None):
        content_sha = content or hashed({"fixture":key})
        fingerprint = request or hashed({"method":"GET","path":f"/pilot/{key}","canon":"v1"})
        document = self._insert("ingest.source_documents",dataset_id=dataset,source_id=source,
                                retrieved_at=NOW,content_sha256=content_sha,request_fingerprint=fingerprint,
                                byte_length=17,source_url=f"https://fixture.invalid/{key}")
        record = self._insert("ingest.source_records",source_id=source,document_id=document["id"],
                              locator_kind="whole_document",locator="",record_kind="pilot",external_key=key)
        return document,record

    def _coverage(self, key, feature, state="empty", count=0, **extra):
        match = self.matches[key]
        return self._insert("ingest.match_coverage",match_id=match["id"],match_revision_id=match["revision_id"],
             source_id=self.ids["source"],source_record_id=self.ids["record"],feature_code=feature,
             coverage_state="available" if count else "empty_response",collection_state=state,
             observed_row_count=count,checked_at=NOW,**extra)

    def typed_shared_editions(self):
        with self.conn.transaction():
            for name,t in self.tables.items():
                if "relation_code" in t["columns"] and "contract_version" in t["columns"]:
                    self.conn.execute("INSERT INTO ingest.relation_contracts(relation_code,relation_name,contract_version,grain_definition) VALUES(%s,%s,'pilot_v1',%s) ON CONFLICT DO NOTHING",(name,name,t["grain"]))
            a = self._insert("ingest.sources",code="pilot_primary",name="Synthetic primary provider")
            b = self._insert("ingest.sources",code="pilot_other",name="Synthetic other provider")
            da = self._insert("ingest.source_datasets",source_id=a["id"],dataset_key="pilot",contract_version="pilot_v1")
            db = self._insert("ingest.source_datasets",source_id=b["id"],dataset_key="pilot",contract_version="pilot_v1")
            doc,record = self._record(a["id"],da["id"],"typed_fixture")
            otherdoc,otherrecord = self._record(b["id"],db["id"],"other_provider")
            run = self._insert("ingest.import_runs",mode="repair",transform_version="pilot_v1",code_commit=SHA)
            self.ids.update(source=a["id"],other_source=b["id"],dataset=da["id"],other_dataset=db["id"],
                 document=doc["id"],record=record["id"],other_record=otherrecord["id"],run=run["id"])
        with self._generation("base_fixture") as g:
            self.g1 = g
            teams = [self._insert("football.teams",slug=f"pilot-team-{i}",name=f"Pilot team {i}",team_type="club",gender="men") for i in range(5)]
            players = [self._insert("football.players",display_name=f"Pilot player {i}") for i in range(4)]
            self.ids.update(teams=teams,players=players)
            self.profiles = []
            for i,p in enumerate(players):
                self.profiles.append(self._insert("football.player_profile_versions",player_id=p["id"],
                  external_profile_version_id=f"pilot-profile-{i}",display_name=f"Pilot player {i}",observed_at=NOW,
                  profile_content_sha256=hashed([i,"v1"]),profile_context="global",primary_position_code="FWD",
                  primary_position_definition_version="bootstrap_v1"))
            self.team_profiles = [self._insert("football.team_profile_versions",team_id=t["id"],display_name=t["name"],
                 observed_at=NOW,profile_context="global",slug=t["slug"],team_type="club",gender="men") for t in teams]
            self.mapping = self._insert("football.position_mappings",source_id=self.ids["source"],raw_position_code="9",mapping_version="pilot_v1",
                 position_code="FWD",position_definition_version="bootstrap_v1",status="validated")
            self.metric = self._insert("football.metric_definitions",code="pilot_xg",label="Pilot expected goals",definition="Synthetic exact xG fixture",unit="goals",
                 scope="player",aggregation="sum",allows_negative=False,definition_version="pilot_v1")
            competition = self._insert("football.competitions",name="Pilot league",slug="pilot-league",competition_type="league",gender="men")
            for i,key in enumerate("ABC"):
                edition = self._insert("football.competition_seasons",competition_id=competition["id"],competition_revision_id=competition["revision_id"],
                    season_key=f"pilot-{key}",label=f"Edition {key}",status="completed")
                self.editions[key] = edition
                match = self._insert("football.matches",competition_season_id=edition["id"],competition_season_revision_id=edition["revision_id"],
                     kickoff_precision="date",match_date=NOW.date(),status="finished",publication_state="published",source_id=self.ids["source"],source_record_id=self.ids["record"])
                self.matches[key] = match
                home = teams[0] if key in "AB" else teams[3]
                away = teams[i+1] if key in "AB" else teams[4]
                self.sides[key] = {}
                for side,t in [("home",home),("away",away)]:
                    self.sides[key][side] = self._insert("football.match_teams",match_id=match["id"],match_revision_id=match["revision_id"],side=side,team_id=t["id"])
                self.participants[key],self.stats[key] = [],[]
                for j,p in enumerate(players[:2] if key in "AB" else players[2:]):
                    profile = self.profiles[j if key in "AB" else j+2]
                    participant = self._insert("football.match_players",match_id=match["id"],team_id=home["id"],player_id=p["id"],profile_version_id=profile["id"],
                        match_team_revision_id=self.sides[key]["home"]["revision_id"],squad_status="starter",played=True,participation_evidence="fixture appearance",
                        source_id=self.ids["source"],source_record_id=self.ids["record"],raw_position_code="9",raw_position_code_state="string",
                        position_code="FWD",position_definition_version="bootstrap_v1",position_mapping_version="pilot_v1")
                    self.participants[key].append(participant)
                    self.stats[key].append(self._insert("football.player_match_stats",match_id=match["id"],player_id=p["id"],team_id=home["id"],
                        match_player_revision_id=participant["revision_id"],period_code="full_match",period_definition_version="bootstrap_v1",
                        xg=Decimal("0.82") if key=="A" and j==0 else Decimal("0.18"),minutes_played=90,
                        source_id=self.ids["source"],source_record_id=self.ids["record"]))
                self._coverage(key,"player_stats",state="present",count=2)
                self._insert("ingest.public_aliases",route_kind="match",public_key=f"pilot-match-{key}",match_id=match["id"],match_revision_id=match["revision_id"])
            self._insert("ingest.public_aliases",route_kind="player",public_key="pilot-shared-player",player_id=players[0]["id"])
            self._insert("ingest.public_aliases",route_kind="team",public_key="pilot-shared-team",team_id=teams[0]["id"])
        self.before = {key:self._cohort(key,self.g1) for key in "ABC"}
        self.builds = {key:self._build(key,self.g1,self.before[key]) for key in "ABC"}
        self._publish(self.builds,"initial_publications")
        self._log({"fixture":"base","generation":self.g1,"edition_ids":{k:v["id"] for k,v in self.editions.items()},"cohorts":self.before,"builds":self.builds})
        return {"generation":self.g1,"editions":3,"shared_editions":["A","B"],"players":4,"teams":5,"typed_stats":6,"aliases":5,"builds":self.builds}

    def _cohort(self,key,g):
        match,edition = self.matches[key],self.editions[key]
        pred = "recorded_from_gen<=%s AND (recorded_to_gen IS NULL OR %s<recorded_to_gen)"
        rows = list(self.conn.execute(f"SELECT player_id,team_id,xg,minutes_played,period_code,period_definition_version,match_player_revision_id FROM football.player_match_stats WHERE match_id=%s AND is_canonical AND NOT is_deleted AND {pred} ORDER BY player_id",(match["id"],g,g)))
        players = [r[0] for r in rows]
        teams = [r[1] for r in rows]
        deps = {"stats":rows}
        for name,columns,filter_sql,params in [
          ("football.player_profile_versions","player_id,id,display_name,primary_position_code,primary_position_definition_version","player_id=ANY(%s) AND is_canonical AND NOT is_deleted",(players,)),
          ("football.team_profile_versions","team_id,id,display_name,slug","team_id=ANY(%s) AND is_canonical AND NOT is_deleted",(teams,)),
          ("football.match_players","match_id,player_id,team_id,revision_id,position_code,position_definition_version,position_mapping_version,raw_position_code","match_id=%s AND is_canonical AND NOT is_deleted",(match["id"],)),
          ("football.periods","code,definition_version,definition","code='full_match'",()),
          ("football.positions","code,definition_version,definition","code='FWD'",()),
          ("football.position_mappings","source_id,raw_position_code,mapping_version,position_code,position_definition_version","source_id=%s AND raw_position_code='9'",(self.ids["source"],)),
          ("football.metric_definitions","code,definition_version,definition,aggregation","code='pilot_xg'",()),
          ("ingest.match_coverage","match_id,source_id,feature_code,collection_state,observed_row_count","match_id=%s AND feature_code='player_stats' AND is_canonical",(match["id"],)),
        ]:
            deps[name] = list(self.conn.execute(f"SELECT {columns} FROM {name} WHERE {filter_sql} AND {pred} ORDER BY 1,2",(*params,g,g)))
        assert len(rows)==2 and all(r[3]==90 for r in rows)
        assert len(deps["football.player_profile_versions"])==2 and len(deps["football.team_profile_versions"])==1
        assert all(deps[n] for n in deps)
        # Synthetic deterministic aggregate verifies the whole cohort; no Orion formula.
        result = sum((r[2] for r in rows),Decimal(0))
        return {"generation":g,"edition_id":edition["id"],"dependencies":deps,"dependencies_sha256":hashed(deps),"sum_xg":str(result),"players":players,"threshold_minutes":45,"numeric_policy":"exact_decimal_order_by_player_id"}

    def _build(self,key,g,cohort,status="ready",snapshot_id=None,catalog_snapshot_id=None):
        snapshot = self.conn.execute("SELECT id FROM ingest.dataset_snapshots WHERE generation=%s",(g,)).fetchone()[0]
        with self.conn.transaction():
            build = self._insert("analytics.aggregation_builds",competition_season_id=self.editions[key]["id"],competition_season_revision_id=self.editions[key]["revision_id"],
                dataset_snapshot_id=snapshot_id or snapshot,catalog_snapshot_id=catalog_snapshot_id or snapshot,representation_version="pilot_v1",code_commit=SHA,
                code_content_sha256=SHA,dependencies_sha256=cohort["dependencies_sha256"],environment_sha256=hashed({"python":"decimal","order":"player_id"}),
                metrics_contract_version="pilot_v1",status="building")
            p=self.participants[key][0]
            self._insert("analytics.player_competition_team_stats",build_id=build["id"],competition_season_id=self.editions[key]["id"],player_id=p["player_id"],team_id=p["team_id"],appearances=1,minutes_played=90)
            match=self.matches[key]
            sides={r[0]:r[1:] for r in self.conn.execute("""SELECT side,team_id,participant_label FROM football.match_teams
                WHERE match_id=%s AND recorded_from_gen<=%s AND (recorded_to_gen IS NULL OR %s<recorded_to_gen)
                AND is_canonical AND NOT is_deleted""",(match["id"],g,g))}
            self._insert("analytics.match_summary",build_id=build["id"],competition_season_id=self.editions[key]["id"],match_id=match["id"],match_revision_id=match["revision_id"],
                match_date=match["match_date"],kickoff_at=match["kickoff_at"],status=match["status"],home_team_id=sides["home"][0],away_team_id=sides["away"][0],home_label=sides["home"][1],away_label=sides["away"][1])
            self._insert("analytics.competition_summary",build_id=build["id"],competition_season_id=self.editions[key]["id"],matches_count=1,finished_matches_count=1,teams_count=2,players_count=2)
            if status!="building": self.conn.execute("UPDATE analytics.aggregation_builds SET status=%s,finished_at=CURRENT_TIMESTAMP WHERE id=%s",(status,build["id"]))
        return build["id"]

    def _publication(self,key,build,**changes):
        b=self._row("analytics.aggregation_builds","id=%s",(build,))
        data=dict(competition_season_id=self.editions[key]["id"],build_id=build,catalog_snapshot_id=b["catalog_snapshot_id"],representation_version=b["representation_version"],published_from_gen=self.g)
        data.update(changes)
        return self._insert("analytics.publication_versions",**data)

    def _publish(self,builds,label):
        with self._generation(label):
            for key,build in builds.items():
                self.conn.execute("UPDATE analytics.publication_versions SET published_to_gen=%s WHERE competition_season_id=%s AND published_to_gen IS NULL",(self.g,self.editions[key]["id"]))
                self._publication(key,build)

    def retained_xg_and_cohort(self):
        with self._generation("xg_and_shared_profiles") as g:
            self.g2=g
            self.stats["A"][0]=self._replace("football.player_match_stats",self.stats["A"][0],xg=Decimal("0.67"))
            self.profiles[0]=self._replace("football.player_profile_versions",self.profiles[0],display_name="Corrected player",profile_content_sha256=hashed("corrected-profile"),external_profile_version_id="pilot-profile-corrected")
            self.team_profiles[0]=self._replace("football.team_profile_versions",self.team_profiles[0],display_name="Corrected shared team")
        self.after={key:self._cohort(key,self.g2) for key in "ABC"}
        affected=[key for key in "ABC" if self.before[key]["dependencies_sha256"]!=self.after[key]["dependencies_sha256"]]
        assert affected==["A","B"],affected
        assert self._cohort("A",self.g1)==self.before["A"]
        assert self.before["A"]["sum_xg"]=="1.00" and self.after["A"]["sum_xg"]=="0.85"
        current=self.conn.execute("SELECT xg FROM football.player_match_stats_current WHERE match_id=%s AND player_id=%s",(self.matches["A"]["id"],self.ids["players"][0]["id"])).fetchone()
        assert current==(Decimal("0.67"),),current
        newbuilds={key:self._build(key,self.g2,self.after[key]) for key in affected}
        c_before=self.conn.execute("SELECT build_id FROM analytics.publication_versions WHERE competition_season_id=%s AND published_to_gen IS NULL",(self.editions["C"]["id"],)).fetchone()[0]
        self._publish(newbuilds,"corrected_publications")
        assert self.conn.execute("SELECT build_id FROM analytics.publication_versions WHERE competition_season_id=%s AND published_to_gen IS NULL",(self.editions["C"]["id"],)).fetchone()[0]==c_before
        oldbuild=self._row("analytics.aggregation_builds","id=%s",(self.builds["A"],))
        assert oldbuild["dependencies_sha256"]==self._cohort("A",self.g1)["dependencies_sha256"]
        self._log({"correction":{"old":self.before["A"],"new":self.after["A"]},"affected":affected,"independent_build":c_before})
        return {"old_xg":"0.82","current_xg":"0.67","old_sum":self.before["A"]["sum_xg"],"new_sum":self.after["A"]["sum_xg"],"affected":affected,"old_dependency_hash_reproduced":True,"C_build_preserved":c_before}

    def _counts(self):
        return {name:self.conn.execute(f"SELECT count(*) FROM {name}").fetchone()[0] for name in ["ingest.dataset_snapshots","football.player_match_stats","analytics.publication_versions"]}

    def no_op_reimport(self):
        before=self._counts()
        row=self.stats["A"][0]
        selected=self._row("football.player_match_stats","revision_id=%s",(row["revision_id"],))
        # Equality is checked before begin_generation; this protocol does not allocate for equal content.
        assert selected["xg"]==Decimal("0.67") and selected["period_definition_version"]=="bootstrap_v1"
        assert self._cohort("A",self.g2)["dependencies_sha256"]==self.after["A"]["dependencies_sha256"]
        assert self._counts()==before
        self._log({"no_op_protocol":"fixture equality before generation allocation","before":before,"after":self._counts()})
        return {"counts_unchanged":before,"scope":"local fixture equality protocol; production normalizer unverified"}

    def _fetch(self,document,fingerprint,attempt,state="available",status=200):
        return self._insert("ingest.resource_fetches",run_id=self.ids["run"],source_id=self.ids["source"],endpoint="/pilot/dedup",request_fingerprint=fingerprint,
                 attempt_no=attempt,requested_at=NOW,finished_at=NOW,http_status=status,response_state=state,document_id=document)

    def http_dedup(self):
        fingerprint,content=hashed("GET /pilot/dedup canon-v1"),hashed("same bytes")
        ids=[]
        with self.conn.transaction():
            for attempt in (1,2):
                row=self.conn.execute("""INSERT INTO ingest.source_documents(dataset_id,source_id,content_sha256,request_fingerprint,retrieved_at)
                    VALUES(%s,%s,%s,%s,%s) ON CONFLICT (dataset_id,request_fingerprint,content_sha256) WHERE origin_kind='http_response' DO NOTHING RETURNING id""",
                    (self.ids["dataset"],self.ids["source"],content,fingerprint,NOW)).fetchone()
                document=row[0] if row else self.conn.execute("SELECT id FROM ingest.source_documents WHERE dataset_id=%s AND request_fingerprint=%s AND content_sha256=%s",(self.ids["dataset"],fingerprint,content)).fetchone()[0]
                ids.append(document);self._fetch(document,fingerprint,attempt)
            second=self._insert("ingest.source_documents",dataset_id=self.ids["dataset"],source_id=self.ids["source"],content_sha256=content,request_fingerprint=hashed("other request"),retrieved_at=NOW)
            self._fetch(None,fingerprint,3,state="failed",status=503)
        assert ids[0]==ids[1] and second["id"]!=ids[0]
        count=self.conn.execute("SELECT count(*) FROM ingest.resource_fetches WHERE request_fingerprint=%s",(fingerprint,)).fetchone()[0]
        assert count==3
        rejection=self._reject("http missing fingerprint",lambda:self._insert("ingest.source_documents",dataset_id=self.ids["dataset"],source_id=self.ids["source"],content_sha256=hashed("missing fingerprint"),retrieved_at=NOW),generation=False)
        # Different byte hashes with equal typed content add receipts/attempts only.
        before=self._counts()
        with self.conn.transaction():
            changed=self._insert("ingest.source_documents",dataset_id=self.ids["dataset"],source_id=self.ids["source"],content_sha256=hashed("different bytes equal typed content"),request_fingerprint=fingerprint,retrieved_at=NOW)
            self._fetch(changed["id"],fingerprint,4)
        assert self._counts()==before
        return {"same_request_documents":len(set(ids)),"distinct_request_document_id":second["id"],"attempts_including_failure":4,"rejected":rejection,"typed_counts_after_equal_normalization":before}

    def typed_states_and_profiles(self):
        observed=[]
        with self._generation("profile_scalar_states"):
            p=self.ids["players"][0]
            for i,(state,value,number) in enumerate([("absent",None,None),("null",None,None),("string","",None),("number","0",Decimal(0)),("string","09",None)]):
                row=self._insert("football.player_profile_versions",player_id=p["id"],external_profile_version_id=f"state-{i}",display_name="State fixture",observed_at=NOW,
                    profile_content_sha256=hashed([state,value,number]),profile_context=f"state-{i}",raw_position_code_state=state,raw_position_code=value,raw_position_code_source_number=number)
                observed.append([row["raw_position_code_state"],row["raw_position_code"],row["raw_position_code_source_number"]])
        rejection=self._reject("profile numeric/string mismatch",lambda:self._insert("football.player_profile_versions",player_id=self.ids["players"][0]["id"],external_profile_version_id="invalid-state",display_name="Bad state",observed_at=NOW,profile_content_sha256=hashed("bad state"),profile_context="bad-state",raw_position_code_state="number",raw_position_code="0",raw_position_code_source_number=Decimal(1)))
        zero=self._reject("xg NaN",lambda:self._insert("football.player_match_stats",**self._stats_input("A",0,xg=Decimal("NaN"),variant_key="pilot:NaN",is_canonical=False)))
        return {"profile_states":observed,"rejected":[rejection,zero],"unverified":["approved model lacks xg_state/xg_source_text: absent/null/empty/numeric-string xG fidelity"]}

    def _stats_input(self,key,index,**changes):
        p=self.participants[key][index]
        values=dict(match_id=self.matches[key]["id"],player_id=p["player_id"],team_id=p["team_id"],match_player_revision_id=p["revision_id"],period_code="full_match",period_definition_version="bootstrap_v1",xg=Decimal("0.1"),minutes_played=90)
        values.update(changes);return values

    def contract_and_seed_versions(self):
        tests=[self._reject("wrong relation contract",lambda:self._insert("football.player_match_stats",**self._stats_input("A",0,contract_version="not_registered",variant_key="pilot:bad-contract",is_canonical=False))),
          self._reject("missing period definition",lambda:self._insert("football.player_match_stats",**self._stats_input("A",0,period_definition_version="missing",variant_key="pilot:bad-period",is_canonical=False))),
          self._reject("period null version",lambda:self._insert("football.player_match_stats",**self._stats_input("A",0,period_definition_version=None,variant_key="pilot:null-period",is_canonical=False)),states={"23502","23503","23514","P0001"}),
          self._reject("immutable relation contract",lambda:self.conn.execute("UPDATE ingest.relation_contracts SET grain_definition='changed' WHERE relation_code='football.periods' AND contract_version='bootstrap_v1'"),generation=False),
          self._reject("immutable bootstrap definition",lambda:self.conn.execute("UPDATE football.periods SET label='changed' WHERE code='full_match' AND definition_version='bootstrap_v1'"))]
        return {"rejected":tests}

    def wrong_parent_provider_h2h(self):
        a=self.participants["A"][0];b=self.participants["B"][0]
        rejected=[self._reject("wrong match participant anchor",lambda:self._insert("football.player_match_stats",**self._stats_input("A",0,match_player_revision_id=b["revision_id"],variant_key="pilot:wrong-match",is_canonical=False))),
          self._reject("wrong player participant anchor",lambda:self._insert("football.player_match_stats",**self._stats_input("A",0,player_id=self.participants["A"][1]["player_id"],variant_key="pilot:wrong-player",is_canonical=False))),
          self._reject("wrong provider record",lambda:self._insert("football.player_match_stats",**self._stats_input("A",0,source_id=self.ids["source"],source_record_id=self.ids["other_record"],variant_key="pilot:wrong-provider",is_canonical=False)))]
        def h2h():
            self._coverage("A","h2h",state="present",count=1)
            self._insert("football.match_h2h_entries",match_id=self.matches["A"]["id"],match_revision_id=self.matches["A"]["revision_id"],entry_ordinal=0,
               source_id=self.ids["source"],source_record_id=self.ids["other_record"],feature_code="h2h",variant_key="pilot:primary",recorded_from_gen=self.g)
        rejected.append(self._reject("H2H foreign provider",h2h))
        return {"rejected":rejected}

    def parent_selection_consistency(self):
        home=self.sides["A"]["home"]
        def invalid():
            self._replace("football.match_teams",home,team_id=self.ids["teams"][4]["id"])
        failure=self._reject("selected parent changed membership",invalid)
        with self._generation("same_membership_new_anchor"):
            replacement=self._replace("football.match_teams",home,participant_label="Refined label same team")
        self.sides["A"]["home"]=replacement
        assert self.conn.execute("SELECT count(*) FROM football.player_match_stats WHERE match_id=%s AND recorded_to_gen IS NULL AND is_canonical",(self.matches["A"]["id"],)).fetchone()[0]==2
        return {"incompatible_membership":failure,"compatible_membership_new_revision":replacement["revision_id"],"old_children_retained":2}

    def _shot(self,**changes):
        data=dict(match_id=self.matches["A"]["id"],team_id=self.sides["A"]["home"]["team_id"],match_team_revision_id=self.sides["A"]["home"]["revision_id"],external_shot_id="pilot-shot")
        data.update(changes);return self._insert("football.shots",**data)

    def shot_profiles(self):
        tests=[self._reject("profile without shooter",lambda:self._shot(player_profile_version_id=self.profiles[0]["id"])),
          self._reject("profile without keeper",lambda:self._shot(keeper_profile_version_id=self.profiles[1]["id"])),
          self._reject("wrong shooter profile",lambda:self._shot(player_id=self.ids["players"][1]["id"],player_profile_version_id=self.profiles[0]["id"]))]
        with self._generation("identity_without_profile"):
            shot=self._shot(player_id=self.ids["players"][0]["id"])
        return {"rejected":tests,"identity_only_shot":shot["id"]}

    def _heatmap(self,**changes):
        data=dict(match_id=self.matches["A"]["id"],team_id=self.sides["A"]["home"]["team_id"],match_team_revision_id=self.sides["A"]["home"]["revision_id"],period_code="full_match",period_definition_version="bootstrap_v1",map_kind="touches",grid_columns=2,grid_rows=2,cell_length_m=5.0,cell_width_m=5.0,coordinate_frame="pitch_m",cells_state="available")
        data.update(changes);return self._insert("football.match_heatmaps",**data)

    def _network(self,**changes):
        data=dict(match_id=self.matches["A"]["id"],team_id=self.sides["A"]["home"]["team_id"],match_team_revision_id=self.sides["A"]["home"]["revision_id"],window_kind="full_match")
        data.update(changes);return self._insert("football.pass_networks",**data)

    def atomic_heatmaps_networks(self):
        def duplicate():
            h=self._heatmap()
            for ordinal in (0,1):self._insert("football.match_heatmap_cells",heatmap_id=h["id"],cell_ordinal=ordinal,column_index=0,row_index=0,action_count=1)
        def bounds():
            h=self._heatmap()
            self._insert("football.match_heatmap_cells",heatmap_id=h["id"],cell_ordinal=0,column_index=2,row_index=0,action_count=1)
        tests=[self._reject("duplicate heatmap coordinates",duplicate),self._reject("heatmap outside actual grid",bounds)]
        with self._generation("atomic_spatial_versions"):
            heatmaps=[]
            for variant in ("pilot:primary","pilot:alternative"):
                h=self._heatmap(variant_key=variant,is_canonical=variant=="pilot:primary")
                self._insert("football.match_heatmap_cells",heatmap_id=h["id"],cell_ordinal=0,column_index=0,row_index=0,action_count=1)
                heatmaps.append(h)
            networks=[]
            for variant in ("pilot:primary","pilot:alternative"):
                n=self._network(variant_key=variant,is_canonical=variant=="pilot:primary")
                self._insert("football.pass_network_nodes",network_id=n["id"],player_id=self.ids["players"][0]["id"])
                if variant=="pilot:primary":self._insert("football.pass_network_nodes",network_id=n["id"],player_id=self.ids["players"][1]["id"])
                networks.append(n)
            self._insert("football.pass_network_edges",network_id=networks[0]["id"],from_player_id=self.ids["players"][0]["id"],to_player_id=self.ids["players"][1]["id"],passes=3)
        tests.append(self._reject("cross-network edge",lambda:self._insert("football.pass_network_edges",network_id=networks[1]["id"],from_player_id=self.ids["players"][0]["id"],to_player_id=self.ids["players"][1]["id"],passes=1)))
        tests.append(self._reject("sealed heatmap child mutation",lambda:self.conn.execute("UPDATE football.match_heatmap_cells SET action_count=99 WHERE heatmap_id=%s",(heatmaps[0]["id"],))))
        return {"rejected":tests,"independent_heatmap_versions":[h["id"] for h in heatmaps],"same_coordinates_across_versions":"accepted","networks":[n["id"] for n in networks]}

    def atomic_collections(self):
        with self._generation("atomic_events") as generation:
            cover=self._coverage("A","events",state="present",count=1)
            event=self._insert("football.match_events",match_id=self.matches["A"]["id"],match_revision_id=self.matches["A"]["revision_id"],event_seq=0,event_type="goal",source_ordinal=0,
              source_id=self.ids["source"],source_record_id=self.ids["record"],feature_code="events",variant_key="pilot:primary",recorded_from_gen=generation)
            for key,state in [("B","null"),("C","absent")]:self._coverage(key,"events",state=state,count=None)
            self._coverage("A","momentum",state="empty",count=0)
        def wrong_family():
            self._coverage("B","h2h",state="present",count=1)
            self._insert("football.match_h2h_entries",match_id=self.matches["B"]["id"],match_revision_id=self.matches["B"]["revision_id"],entry_ordinal=0,
                source_id=self.ids["source"],source_record_id=self.ids["record"],feature_code="events",variant_key="pilot:primary",recorded_from_gen=self.g)
        tests=[self._reject("collection family mismatch",wrong_family),self._reject("mixed collection generation",lambda:self._insert("football.match_events",match_id=self.matches["A"]["id"],match_revision_id=self.matches["A"]["revision_id"],event_seq=1,event_type="goal",source_ordinal=1,source_id=self.ids["source"],source_record_id=self.ids["record"],feature_code="events",variant_key="pilot:primary",recorded_from_gen=self.g))]
        self._fetch(None,hashed("failed events"),1,state="failed",status=503)
        assert self.conn.execute("SELECT count(*) FROM football.match_events WHERE match_id=%s AND recorded_from_gen=%s",(self.matches["A"]["id"],generation)).fetchone()[0]==1
        return {"collection_generation":generation,"accepted_events_after_failure":1,"states":["present","empty","null","absent"],"rejected":tests}

    def _standing(self,revision,points=10):
        s=self._insert("football.standing_snapshots",competition_season_id=self.editions["A"]["id"],competition_season_revision_id=self.editions["A"]["revision_id"],scope="overall",observed_at=NOW,
            source_id=self.ids["source"],source_record_id=self.ids["record"],data_revision=revision)
        self._insert("football.standing_rows",snapshot_id=s["id"],team_id=self.ids["teams"][0]["id"],rank=1,points=Decimal(points),played=5)
        return s

    def _ranking(self,revision,points=100):
        r=self._insert("football.ranking_snapshots",system_id=self.ranking_system["id"],subject_kind="team",edition_key="pilot-rank",retrieved_at=NOW,revision=revision,source_document_id=self.ids["document"])
        self._insert("football.team_ranking_entries",snapshot_id=r["id"],team_id=self.ids["teams"][0]["id"],rank=1,points=Decimal(points),source_record_id=self.ids["record"])
        return r

    def append_only_parser_correction(self):
        with self._generation("append_original") as oldg:
            self.ranking_system=self._insert("football.ranking_systems",code="pilot_rank",authority="Synthetic fixture",subject_kind="team",gender="men",methodology_version="pilot_v1")
            oldstanding=self._standing(10,10);oldranking=self._ranking(10,100)
            self._insert("football.match_observation_details",source_record_id=self.ids["record"],resolution_state="unresolved",source_home_label="old parser label")
        with self._generation("append_parser_correction") as newg:
            newstanding=self._standing(20,11);newranking=self._ranking(20,101)
            self._insert("football.match_observation_details",source_record_id=self.ids["record"],resolution_state="resolved",source_home_label="corrected parser label",match_id=self.matches["A"]["id"],match_revision_id=self.matches["A"]["revision_id"])
        selected=[]
        for g in [oldg,newg]:
            standing=self.conn.execute("SELECT id,data_revision FROM football.standing_snapshots WHERE source_record_id=%s AND competition_season_id=%s AND recorded_from_gen<=%s ORDER BY recorded_from_gen DESC LIMIT 1",(self.ids["record"],self.editions["A"]["id"],g)).fetchone()
            ranking=self.conn.execute("SELECT id,revision FROM football.ranking_snapshots WHERE system_id=%s AND edition_key='pilot-rank' AND recorded_from_gen<=%s ORDER BY recorded_from_gen DESC LIMIT 1",(self.ranking_system["id"],g)).fetchone()
            detail=self.conn.execute("SELECT source_home_label FROM football.match_observation_details WHERE source_record_id=%s AND recorded_from_gen<=%s ORDER BY recorded_from_gen DESC LIMIT 1",(self.ids["record"],g)).fetchone()[0]
            selected.append({"generation":g,"standing":standing,"ranking":ranking,"detail":detail})
        assert selected[0]["standing"]==(oldstanding["id"],10) and selected[1]["standing"]==(newstanding["id"],20)
        assert selected[0]["ranking"]==(oldranking["id"],10) and selected[1]["ranking"]==(newranking["id"],20)
        assert selected[0]["detail"]=="old parser label" and selected[1]["detail"]=="corrected parser label"
        before=self._counts()
        assert selected[1]["detail"]=="corrected parser label" and self._counts()==before
        def two_same_generation():
            self._standing(21,12);self._standing(22,13)
        tests=[self._reject("standing lower revision later generation",lambda:self._standing(15,12)),self._reject("ranking lower revision later generation",lambda:self._ranking(15,102)),
          self._reject("two standing revisions same generation",two_same_generation),
          self._reject("append child mutation",lambda:self.conn.execute("UPDATE football.standing_rows SET points=999 WHERE snapshot_id=%s",(oldstanding["id"],))),
          self._reject("append observation mutation",lambda:self.conn.execute("UPDATE football.match_observation_details SET source_home_label='overwritten' WHERE source_record_id=%s AND recorded_from_gen=%s",(self.ids["record"],oldg)))]
        self._log({"append_selections":selected,"same_source_record":self.ids["record"]})
        return {"selections":selected,"same_source_record":self.ids["record"],"rejected":tests,"no_op_scope":"fixture equality protocol"}

    def generation_guards(self):
        row=self.stats["A"][0];original=self._row("football.player_match_stats","revision_id=%s",(row["revision_id"],))
        def sealed_reuse():
            self._insert("football.player_match_stats",**self._stats_input("A",0,recorded_from_gen=self.g1,variant_key="pilot:sealed",is_canonical=False))
        def overlap():
            old=self._row("football.player_match_stats","match_id=%s AND player_id=%s AND recorded_to_gen IS NOT NULL",(row["match_id"],row["player_id"]))
            self._insert("football.player_match_stats",**self._stats_input("A",0,recorded_from_gen=old["recorded_from_gen"],recorded_to_gen=self.g,variant_key="pilot:primary",is_canonical=False))
        tests=[self._reject("sealed generation reuse",sealed_reuse),self._reject("historical overlap/backdate",overlap),
          self._reject("canonical duplicate variant",lambda:self._insert("football.player_match_stats",**self._stats_input("A",0,variant_key="pilot:another",is_canonical=True))),
          self._reject("past typed value mutation",lambda:self.conn.execute("UPDATE football.player_match_stats SET xg=0.99 WHERE revision_id=%s",(row["revision_id"],))),
          self._reject("past row deletion",lambda:self.conn.execute("DELETE FROM football.player_match_stats WHERE revision_id=%s",(row["revision_id"],))),
          self._reject("sealed receipt mutation",lambda:self.conn.execute("UPDATE ingest.dataset_snapshots SET transform_version='changed' WHERE generation=%s",(self.g1,)),generation=False)]
        old=self.conn.execute("SELECT revision_id FROM football.player_match_stats WHERE match_id=%s AND player_id=%s AND recorded_to_gen IS NOT NULL",(row["match_id"],row["player_id"])).fetchone()[0]
        tests.append(self._reject("closed interval reopened",lambda:self.conn.execute("UPDATE football.player_match_stats SET recorded_to_gen=NULL WHERE revision_id=%s",(old,))))
        assert self._row("football.player_match_stats","revision_id=%s",(row["revision_id"],))==original
        # Noncanonical retained variant + atomic canonical selection change.
        with self._generation("alternative_variant"):
            alt=self._insert("football.player_match_stats",**self._stats_input("B",0,xg=Decimal("0.21"),variant_key="pilot:alternative",is_canonical=False))
        with self._generation("variant_selection"):
            oldcanonical=self.stats["B"][0]
            self._replace("football.player_match_stats",oldcanonical,is_canonical=False)
            self._replace("football.player_match_stats",alt,is_canonical=True)
        assert self.conn.execute("SELECT xg FROM football.player_match_stats_current WHERE match_id=%s AND player_id=%s",(self.matches["B"]["id"],self.participants["B"][0]["player_id"])).fetchone()==(Decimal("0.21"),)
        return {"rejected":tests,"retained_variant_selection":"0.21","old_snapshot_preserved":self._cohort("A",self.g1)==self.before["A"]}

    def concurrent_generation_order(self):
        first=self.psycopg.connect(self.dsn,autocommit=True);second=self.psycopg.connect(self.dsn,autocommit=True)
        entered=threading.Event();finished=threading.Event();result={}
        def worker():
            try:
                with second.transaction():
                    entered.set();result["second_generation"]=self._begin("writer-two",second)
                    second.execute("SELECT ingest.seal_generation(%s,%s)",(result["second_generation"],hashed("writer2")))
            except Exception as exc:result["error"]=str(exc)
            finally:finished.set()
        try:
            with first.transaction():
                result["first_generation"]=self._begin("writer-one",first)
                thread=threading.Thread(target=worker);thread.start();assert entered.wait(3)
                time.sleep(0.2)
                assert not finished.is_set(),"second writer did not wait for transaction lock"
                first.execute("SELECT ingest.seal_generation(%s,%s)",(result["first_generation"],hashed("writer1")))
            thread.join(5);assert not thread.is_alive() and "error" not in result,result
            assert result["second_generation"]>result["first_generation"]
            rollback_key="pilot:rollback-owned-generation"
            try:
                with first.transaction():
                    g=first.execute("SELECT ingest.begin_generation(%s,'pilot_v1','pilot_v1')",(rollback_key,)).fetchone()[0]
                    raise RuntimeError("intentional transaction abort")
            except RuntimeError:pass
            assert not self.conn.execute("SELECT 1 FROM ingest.dataset_snapshots WHERE snapshot_key=%s",(rollback_key,)).fetchone()
        finally:first.close();second.close()
        return {**result,"blocking_observed_ms":200,"rollback_receipt_absent":True}

    def publication_guards(self):
        building=self._build("A",self.g2,self.after["A"],status="building")
        ready=self.builds["A"]
        def publish_building():
            self.conn.execute("UPDATE analytics.publication_versions SET published_to_gen=%s WHERE competition_season_id=%s AND published_to_gen IS NULL",(self.g,self.editions["A"]["id"]))
            self._publication("A",building)
        def wrong_catalogue():
            self.conn.execute("UPDATE analytics.publication_versions SET published_to_gen=%s WHERE competition_season_id=%s AND published_to_gen IS NULL",(self.g,self.editions["A"]["id"]))
            sid=self.conn.execute("SELECT id FROM ingest.dataset_snapshots WHERE generation=%s",(self.g2,)).fetchone()[0]
            self._publication("A",ready,catalog_snapshot_id=sid)
        def wrong_representation():
            self.conn.execute("UPDATE analytics.publication_versions SET published_to_gen=%s WHERE competition_season_id=%s AND published_to_gen IS NULL",(self.g,self.editions["A"]["id"]))
            self._publication("A",ready,representation_version="wrong")
        def draft_build():
            receipt=self.conn.execute("SELECT id FROM ingest.dataset_snapshots WHERE generation=%s",(self.g,)).fetchone()[0]
            self._build("A",self.g2,self.after["A"],snapshot_id=receipt)
        tests=[self._reject("publish non-ready build",publish_building),self._reject("publication catalogue mismatch",wrong_catalogue),self._reject("publication representation mismatch",wrong_representation),
          self._reject("ready build with draft snapshot",draft_build),
          self._reject("wrong edition build",lambda:self._publication("B",ready)),
          self._reject("ready build mutation",lambda:self.conn.execute("UPDATE analytics.aggregation_builds SET dependencies_sha256=%s WHERE id=%s",(hashed("changed"),ready)),generation=False),
          self._reject("ready aggregate mutation",lambda:self.conn.execute("UPDATE analytics.player_competition_team_stats SET appearances=99 WHERE build_id=%s",(ready,)),generation=False)]
        return {"rejected":tests,"frozen_old_build_id":ready,"old_dependencies_sha256":self._row("analytics.aggregation_builds","id=%s",(ready,))["dependencies_sha256"]}

    def readonly_role(self):
        # The migration supplies a real, least-privilege NOLOGIN role.
        role=self.conn.execute("SELECT rolname,rolcanlogin,rolsuper FROM pg_roles WHERE rolname='orion_pro_web'").fetchone()
        assert role==("orion_pro_web",False,False),role
        with self.conn.transaction():
            self.conn.execute("SET LOCAL ROLE orion_pro_web")
            count=self.conn.execute("SELECT count(*) FROM football.player_match_stats_current").fetchone()[0]
        def sql(statement):
            self.conn.execute("SET LOCAL ROLE orion_pro_web");self.conn.execute(statement)
        tests=[self._reject("web role insert",lambda:sql("INSERT INTO ingest.sources(code,name) VALUES('forbidden','forbidden')"),generation=False,states={"42501"}),
          self._reject("web role update",lambda:sql("UPDATE football.player_match_stats SET xg=0"),generation=False,states={"42501"}),
          self._reject("web role delete",lambda:sql("DELETE FROM football.player_match_stats"),generation=False,states={"42501"}),
          self._reject("web role generation helper",lambda:sql("SELECT ingest.begin_generation('forbidden','v1','v1')"),generation=False,states={"42501"})]
        return {"role":role,"read_rows":count,"rejected":tests}

    def queue_lease(self):
        # Helper contract is intentionally small: an owned row is returned, not a JSON record registry.
        self._insert("ingest.collection_jobs",source_id=self.ids["source"],endpoint="/pilot/lease",params="{}",priority=1)
        with self.conn.transaction():
            leased=self.conn.execute("SELECT * FROM ingest.claim_collection_job(%s,%s)",("worker-a",60)).fetchone()
            assert leased is not None
        other=self.conn.execute("SELECT count(*) FROM ingest.claim_collection_job(%s,%s)",("worker-b",60)).fetchone()[0]
        assert other==0
        def nonowner():
            self.conn.execute("SELECT ingest.complete_collection_job(%s,%s,%s,%s,%s,%s)",(self.ids["source"],"/pilot/lease","{}","worker-b","done",1))
        rejected=self._reject("queue nonowner completion",nonowner,generation=False)
        # Direct lease mutation is privileged test setup for an expired worker.
        self.conn.execute("UPDATE ingest.collection_jobs SET lease_expires_at=CURRENT_TIMESTAMP-interval '1 second' WHERE source_id=%s AND endpoint='/pilot/lease'",(self.ids["source"],))
        reclaimed=self.conn.execute("SELECT * FROM ingest.claim_collection_job(%s,%s)",("worker-b",60)).fetchone()
        assert reclaimed is not None
        stale=self._reject("queue stale claimed attempt",lambda:self.conn.execute("SELECT ingest.complete_collection_job(%s,%s,%s,%s,%s,%s)",(self.ids["source"],"/pilot/lease","{}","worker-b","done",1)),generation=False)
        self.conn.execute("SELECT ingest.complete_collection_job(%s,%s,%s,%s,%s,%s)",(self.ids["source"],"/pilot/lease","{}","worker-b","done",2))
        state=self.conn.execute("SELECT state,attempts,lease_owner,lease_expires_at FROM ingest.collection_jobs WHERE source_id=%s AND endpoint='/pilot/lease'",(self.ids["source"],)).fetchone()
        assert state==("done",2,None,None),state
        negative=self._reject("queue negative attempts",lambda:self._insert("ingest.collection_jobs",source_id=self.ids["source"],endpoint="/pilot/bad-lease",params="{}",attempts=-1),generation=False)
        return {"final_state":state,"nonowner":rejected,"stale_attempt":stale,"negative_attempts":negative,"concurrent_duplicate_leases":0}
