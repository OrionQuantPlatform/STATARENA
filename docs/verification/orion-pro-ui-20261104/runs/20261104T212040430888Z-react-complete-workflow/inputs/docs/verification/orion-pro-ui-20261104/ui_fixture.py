"""Source-free UI fixture: retain sealed reader inputs, publish 61 A matches locally."""
from datetime import date
from pathlib import Path
import sys

READERS = Path(__file__).resolve().parent.parent / "orion-pro-readers-20261104"
sys.path.insert(0, str(READERS))
from fixture import ReaderFixture, NOW


class BrowserFixture(ReaderFixture):
    def _insert(self, table, **values):
        if table == "football.matches":
            values["status"] = "finished"
        teams = self.ids.get("teams", [])
        if (getattr(self, "preparing_initial", False) and table == "football.team_profile_versions"
                and len(teams) > 2 and values.get("team_id") == teams[2]["id"]
                and values.get("profile_context") == "global"):
            values["display_name"] = None
        if (getattr(self, "preparing_initial", False) and table == "football.shots"
                and values.get("source_event_type") == "" and values.get("is_canonical", True)):
            values["xg"] = 0.0
        return super()._insert(table, **values)

    def prepare(self):
        self.preparing_initial = True
        super().prepare()
        self.preparing_initial = False
        edition = self.editions["A"]
        teams = self.ids["teams"][:2]
        with self._generation("ui_61_match_dataset") as generation:
            self.data1 = generation
            for ordinal in range(6, 64):
                public_id = f"m_{ordinal:06d}"
                match = self._insert(
                    "football.matches", competition_season_id=edition["id"],
                    competition_season_revision_id=edition["revision_id"],
                    match_date=date(2026, 11, 4), kickoff_precision="date",
                    status="finished", publication_state="published",
                    source_id=self.ids["source"], source_record_id=self.ids["record"],
                )
                self.match_rows[public_id], self.match_keys[public_id] = match, "A"
                self._insert("ingest.public_aliases", route_kind="match", public_key=public_id,
                             match_id=match["id"], match_revision_id=match["revision_id"])
                sides = {}
                for side, team in zip(("home", "away"), teams):
                    sides[side] = self._insert(
                        "football.match_teams", match_id=match["id"], match_revision_id=match["revision_id"],
                        side=side, team_id=team["id"], participant_label=f"{side} observed label",
                        source_id=self.ids["source"], source_record_id=self.ids["record"],
                    )
                    self.scores[(public_id, side)] = self._insert(
                        "football.match_scores", match_id=match["id"], side=side,
                        match_team_revision_id=sides[side]["revision_id"],
                        score_scope="final_without_shootout", goals=0, score_basis="played",
                        source_id=self.ids["source"], source_record_id=self.ids["record"],
                    )
                self.sides[public_id] = sides
                self.coverages[public_id] = self._insert(
                    "ingest.match_coverage", match_id=match["id"], match_revision_id=match["revision_id"],
                    source_id=self.ids["source"], source_record_id=self.ids["record"],
                    feature_code="shots", coverage_state="empty_response", collection_state="empty",
                    observed_row_count=0, checked_at=NOW,
                )
        self.initial_builds = {key: self.build(key, self.data1, self.data1) for key in "ABC"}
        self.publish(self.initial_builds, "ui_61_match_publication")
        actual = {key: sum(value == key for value in self.match_keys.values()) for key in "ABC"}
        assert actual == {"A": 61, "B": 1, "C": 1}, actual
        return {**self.describe(), "matchCounts": actual,
                "nullableProfile": {"edition": "B", "team": "t_000003", "display_name": None},
                "typedShot": {"xg": 0, "xgot": 0, "is_goal": True, "event_type": "", "x_m": 52.5, "y_m": 34}}
