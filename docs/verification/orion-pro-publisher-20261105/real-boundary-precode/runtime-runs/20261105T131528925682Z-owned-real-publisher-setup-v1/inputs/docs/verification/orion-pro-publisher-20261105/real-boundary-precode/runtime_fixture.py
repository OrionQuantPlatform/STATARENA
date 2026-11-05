"""Declared synthetic native inputs for real-adapter E2E, never RDS admission."""
from __future__ import annotations

import ast
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[3]
sys.path[:0] = [str(BASE.parent / "qualified-precode"), str(ROOT / "dashboard/scripts")]
from typed_inputs import TypedInputs
from typed_oracle import TypedOracle, tagged, sha

POLICY = "real_source_core_v2_native31"
FIXTURE_VERSION = "owned_real_publication_fixture_v1"
SELF_SHA = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
NOW = datetime(2026, 11, 5, 10, 0, tzinfo=timezone.utc)


class RealFixture(TypedInputs):
    def _insert(self, table, **values):
        columns = self.tables[table]["columns"]
        if "transform_version" in columns:
            values.setdefault("transform_version", FIXTURE_VERSION)
        if "transform_code_sha256" in columns:
            values.setdefault("transform_code_sha256", SELF_SHA)
        return super()._insert(table, **values)

    def _begin(self, label, conn=None):
        self.counter += 1
        return (conn or self.conn).execute("SELECT ingest.begin_generation(%s,%s,%s)",
            ("owned-real-publication:" + label + ":" + str(self.counter), FIXTURE_VERSION, POLICY)).fetchone()[0]

    def at(self, table, extra="TRUE", params=()):
        spec = self.tables[table]
        where = [extra]
        args = list(params)
        if "recorded_from_gen" in spec["columns"]:
            where.append("recorded_from_gen<=%s AND (recorded_to_gen IS NULL OR %s<recorded_to_gen)")
            args += [self.data_generation, self.data_generation]
        if "is_canonical" in spec["columns"]:
            where.append("is_canonical")
        if "is_deleted" in spec["columns"]:
            where.append("NOT is_deleted")
        cur = self.conn.execute("SELECT * FROM " + table + " WHERE " + " AND ".join(where), args)
        return [dict(zip([x.name for x in cur.description], row)) for row in cur.fetchall()]

    def refresh(self):
        self.data_generation = self.conn.execute("SELECT max(generation) FROM ingest.dataset_snapshots WHERE status='sealed'").fetchone()[0]
        self.catalog_generation = self.data_generation
        aliases = {r["match_id"]: r["public_key"] for r in self.at("ingest.public_aliases", "route_kind='match'")}
        self.match_rows = {aliases[r["id"]]: r for r in self.at("football.matches") if r["id"] in aliases}
        for mid, row in self.match_rows.items():
            self.sides[mid] = {r["side"]: r for r in self.at("football.match_teams", "match_id=%s", (row["id"],))}
        self.coverages = {mid: next(iter(self.at("ingest.match_coverage", "match_id=%s AND feature_code='shots'", (row["id"],))), None)
                          for mid, row in self.match_rows.items()}
        self.scores = {(mid, side): next(iter(self.at("football.match_scores", "match_id=%s AND side=%s AND score_scope='final_without_shootout'", (row["id"], side))), None)
                       for mid, row in self.match_rows.items() for side in ["home", "away"]}
        self.shot_rows = {mid: next(iter(self.at("football.shots", "match_id=%s", (row["id"],))), None)
                          for mid, row in self.match_rows.items()}

    def prepare_raw(self):
        self.prepare_inputs()
        self.minimum_source = {}
        with self._generation("raw_draft_minimum") as g:
            self.data_generation = self.catalog_generation = g
            for mid, old in list(self.match_rows.items()):
                kickoff = datetime(2026, 11, 4, 13, 45, 7, tzinfo=timezone.utc) if old["match_date"] else None
                row = self._replace("football.matches", old, publication_state="draft", kickoff_at=kickoff,
                                    kickoff_precision="second" if kickoff else "unknown", data_revision=old["data_revision"] + 1)
                alias = self._row("ingest.public_aliases", "route_kind='match' AND public_key=%s AND recorded_to_gen IS NULL", (mid,))
                self._replace("ingest.public_aliases", alias, match_revision_id=row["revision_id"])
                self.match_rows[mid] = row
                self.minimum_source[mid] = {"timeState": "available" if kickoff else "null",
                    "kickoffSha256": sha(tagged(kickoff)), "sourceXyState": "numeric_units_unqualified",
                    "sourceFrameState": "absent", "unresolvedActorIds": []}
            # An additional genuinely unknown fixture remains unknown while the
            # five other matches exercise a streamed >5000-row scope later.
            edition = self.editions["A"]
            extra = self._insert("football.matches", competition_season_id=edition["id"],
                competition_season_revision_id=edition["revision_id"], kickoff_precision="unknown",
                status="not_started", publication_state="draft", source_id=self.ids["source"], source_record_id=self.ids["record"])
            self.match_rows["m_000006"] = extra
            self._insert("ingest.public_aliases", route_kind="match", public_key="m_000006", match_id=extra["id"], match_revision_id=extra["revision_id"])
            self.sides["m_000006"] = {}
            for side, team in zip(["home", "away"], self.ids["teams"][:2]):
                self.sides["m_000006"][side] = self._insert("football.match_teams", match_id=extra["id"], match_revision_id=extra["revision_id"],
                    side=side, team_id=team["id"], source_id=self.ids["source"], source_record_id=self.ids["record"])
            self.minimum_source["m_000006"] = {"timeState": "null", "kickoffSha256": sha(tagged(None)),
                "sourceXyState": "absent", "sourceFrameState": "absent", "unresolvedActorIds": []}
            self.expected["m_000006"] = {"key": "A", "date": None, "status": "not_started", "home": None, "away": None,
                "homePenalty": None, "awayPenalty": None, "shots": "unknown", "scoreObserved": False}
            for row in self.at("football.competition_teams"):
                self._replace("football.competition_teams", row, is_canonical=False)
            for row in self.at("football.match_players"):
                self._replace("football.match_players", row, played=None, squad_status="observed", participation_evidence=None,
                              data_revision=row["data_revision"] + 1)
            for row in self.at("football.team_profile_versions"):
                self._replace("football.team_profile_versions", row, is_canonical=False)
            for row in self.at("football.match_teams"):
                if row["participant_label"] is not None:
                    self._replace("football.match_teams", row, participant_label=None, data_revision=row["data_revision"] + 1)
            node = ast.parse((ROOT / "dashboard/scripts/orion_pro_normalize.py").read_text())
            fields = next(ast.literal_eval(n.value) for n in node.body if isinstance(n, ast.Assign)
                          and any(isinstance(t, ast.Name) and t.id == "CORE_METRICS" for t in n.targets))
            self.metric_fields = fields
            for field in fields:
                self._insert("football.metric_definitions", code="legacy_normalized_" + field, label=field,
                    definition="Synthetic owned complete native scalar observation", unit="source_native", scope="player",
                    aggregation="none", allows_negative=field in ["rating", "goalsPrevented"], definition_version=FIXTURE_VERSION,
                    source_id=self.ids["source"], source_record_id=self.ids["record"])
            self.minute_rows, self.stat_rows = {}, {}
            for participant in self.at("football.match_players"):
                pair = (participant["match_id"], participant["player_id"])
                bench = participant["player_id"] == self.ids["players"][1]["id"]
                minutes = None if bench else Decimal("12.5")
                stats = self._insert("football.player_match_stats", match_id=pair[0], player_id=pair[1], team_id=participant["team_id"],
                    match_player_revision_id=participant["revision_id"], period_code="full_match", period_definition_version="bootstrap_v1",
                    minutes_played=float(minutes) if minutes is not None else None, source_id=self.ids["source"], source_record_id=self.ids["record"])
                self.stat_rows[pair] = stats
                for field in fields:
                    kind = "number" if field == "minutes" and minutes is not None else "null" if field == "minutes" else "absent"
                    metric = self._insert("football.player_match_metric_values", match_id=pair[0], player_id=pair[1], team_id=participant["team_id"],
                        match_player_revision_id=participant["revision_id"], period_code="full_match", period_definition_version="bootstrap_v1",
                        family_code="standard", metric_code="legacy_normalized_" + field, metric_definition_version=FIXTURE_VERSION,
                        value_kind=kind, numeric_value=minutes if field == "minutes" else None,
                        source_id=self.ids["source"], source_record_id=self.ids["record"])
                    if field == "minutes":
                        self.minute_rows[pair] = metric
            big_id = 9007199254740993
            self.conn.execute("INSERT INTO football.players(id,display_name) OVERRIDING SYSTEM VALUE VALUES(%s,%s)", (big_id, "Owned BIGINT identity"))
            self._insert("ingest.public_aliases", route_kind="player", public_key="p_Big001", player_id=big_id)
            extra_home = self.sides["m_000006"]["home"]
            precise = Decimal("9007199254740993.12500000000000000001")
            self._insert("football.match_players", match_id=extra["id"], player_id=big_id, team_id=extra_home["team_id"],
                match_team_revision_id=extra_home["revision_id"], squad_status="observed", played=None,
                shirt_number_state="number", shirt_number_source_number=precise, shirt_number=format(precise, "f"),
                source_id=self.ids["source"], source_record_id=self.ids["record"])
            for key in self.editions:
                self.mark_dirty(key, g)
        self.refresh()
        self.oracle = TypedOracle(self.conn, self.model)
        self.raw_match_rows = list(self.match_rows.values())
        self.expected_labels = {(m["id"], side): next(t["name"] for t in self.ids["teams"] if t["id"] == self.sides[mid][side]["team_id"])
                                for mid, m in self.match_rows.items() for side in ["home", "away"]}
        for mid, want in self.expected.items():
            for side in ["home", "away"]:
                want[side + "Name"] = self.expected_labels[(self.match_rows[mid]["id"], side)]
        self.expected_played = {pair: (None if pair[1] == self.ids["players"][1]["id"] else True) for pair in self.minute_rows}
        self.expected_played[(extra["id"], big_id)] = None
        self.bench_pair = next(pair for pair in self.minute_rows if pair[1] == self.ids["players"][1]["id"])

    def mutate_minutes(self, kind):
        pair = self.bench_pair
        old = self.at("football.player_match_metric_values", "match_id=%s AND player_id=%s AND metric_code='legacy_normalized_minutes'", pair)[0]
        values = {"null": ("null", None, None, None), "absent": ("absent", None, None, None),
                  "string": ("string", None, "unknown", None), "boolean": ("boolean", None, None, False),
                  "zero": ("number", Decimal(0), None, None), "positive": ("number", Decimal("3.25"), None, None)}
        state, number, text, boolean = values[kind]
        if (old["value_kind"], old["numeric_value"], old["text_value"], old["boolean_value"]) == (state, number, text, boolean):
            return
        with self._generation("minutes_" + kind) as g:
            self.data_generation = self.catalog_generation = g
            self._replace("football.player_match_metric_values", old, value_kind=state, numeric_value=number,
                          text_value=text, boolean_value=boolean)
            stats = self.at("football.player_match_stats", "match_id=%s AND player_id=%s", pair)[0]
            projected = float(number) if state == "number" else None
            if stats["minutes_played"] != projected:
                self._replace("football.player_match_stats", stats, minutes_played=projected, data_revision=stats["data_revision"] + 1)
            self.mark_dirty("B", g)
        self.refresh()

    def add_shot_participant(self):
        mid = "m_000002"
        match, side = self.match_rows[mid], self.sides[mid]["home"]
        player = self.ids["players"][0]["id"]
        with self._generation("accepted_shot_without_performance") as g:
            self.data_generation = self.catalog_generation = g
            parent = self.coverages[mid]
            self._replace("ingest.match_coverage", parent, collection_state="present", coverage_state="available",
                          observed_row_count=1, data_revision=parent["data_revision"] + 1)
            self._insert("football.shots", match_id=match["id"], team_id=side["team_id"], match_team_revision_id=side["revision_id"],
                         player_id=player, external_shot_id="s_derived_participation", period_code=None,
                         source_ordinal=0, source_id=self.ids["source"], source_record_id=self.ids["record"])
            self.mark_dirty("A", g)
        self.expected_played[(match["id"], player)] = True
        self.expected[mid]["shots"] = "present"
        self.refresh()
        return {"pair": (match["id"], player)}

    def stream_family(self):
        with self._generation("streamed_family_over_old_cap") as g:
            self.data_generation = self.catalog_generation = g
            self.conn.execute("UPDATE football.shots SET recorded_to_gen=%s WHERE recorded_to_gen IS NULL", (g,))
            for mid, match in list(self.match_rows.items()):
                if mid == "m_000006":
                    continue
                if match["status"] != "finished":
                    match = self._replace("football.matches", match, status="finished", data_revision=match["data_revision"] + 1)
                    alias = self._row("ingest.public_aliases", "route_kind='match' AND public_key=%s AND recorded_to_gen IS NULL", (mid,))
                    self._replace("ingest.public_aliases", alias, match_revision_id=match["revision_id"])
                    self.match_rows[mid] = match
                    self.expected[mid]["status"] = "finished"
                old = self.coverages[mid]
                values = dict(collection_state="present", coverage_state="available", observed_row_count=1000, variant_key="owned:streamed")
                if old:
                    self._replace("ingest.match_coverage", old, data_revision=old["data_revision"] + 1, **values)
                else:
                    self._insert("ingest.match_coverage", match_id=match["id"], match_revision_id=match["revision_id"],
                        feature_code="shots", checked_at=NOW, source_id=self.ids["source"], source_record_id=self.ids["record"], **values)
                side = self.sides[mid]["home"]
                self.conn.execute("""INSERT INTO football.shots (match_id,team_id,match_team_revision_id,external_shot_id,source_ordinal,
                    source_id,source_record_id,recorded_from_gen,variant_key,is_canonical,contract_version,transform_version,transform_code_sha256,provenance_kind)
                    SELECT %s,%s,%s,'owned_stream_'||i,i,%s,%s,%s,'owned:streamed',true,'pilot_v1',%s,%s,'provider'
                    FROM generate_series(1,1000) i""", (match["id"], side["team_id"], side["revision_id"], self.ids["source"], self.ids["record"], g,
                        FIXTURE_VERSION,
                        self.at("football.matches", "id=%s", (match["id"],))[0]["transform_code_sha256"]))
                self.expected[mid]["shots"] = "present"
            for key in self.editions:
                self.mark_dirty(key, g)
        self.refresh()
        return {"selectedRows": len(self.at("football.shots")) + len(self.at("football.match_players"))}

    def clear_coordinates(self):
        with self._generation("unqualified_coordinate_fixture") as g:
            self.data_generation = self.catalog_generation = g
            for shot in self.at("football.shots"):
                self._replace("football.shots", shot, x_m=None, y_m=None, coordinate_frame=None,
                              pitch_length_m=None, pitch_width_m=None, data_revision=shot["data_revision"] + 1)
            for key in self.editions:
                self.mark_dirty(key, g)
        self.refresh()
