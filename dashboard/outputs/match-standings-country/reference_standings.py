"""Independent historical standings reference for the browser E2E.

Rerun from dashboard: python3 outputs/match-standings-country/reference_standings.py
"""
import gzip
import json
from pathlib import Path

root = Path(__file__).resolve().parents[3]
source = next((root / "data/raw/seasons/2024-2025/fixtures").glob("l_3FJFUl--*.json.gz"))
fixtures = json.load(gzip.open(source))
teams = {}
for match in fixtures:
    for side in ["home", "away"]:
        team = match[side + "_team"]
        teams.setdefault(team["id"], dict(name=team["name"], played=0, points=0, wins=0, draws=0, losses=0, **{"for": 0, "against": 0}))
    if match["status"] != "finished":
        continue
    home, away = match["home_team"]["id"], match["away_team"]["id"]
    hs, a_s = match["score_home"], match["score_away"]
    for team_id, scored, conceded in [(home, hs, a_s), (away, a_s, hs)]:
        row = teams[team_id]
        row["played"] += 1
        row["for"] += scored
        row["against"] += conceded
        row["wins"] += scored > conceded
        row["draws"] += scored == conceded
        row["losses"] += scored < conceded
        row["points"] += 3 if scored > conceded else 1 if scored == conceded else 0
rows = sorted(teams.values(), key=lambda r: (-r["points"], -(r["for"] - r["against"]), -r["for"], r["name"]))
Path(__file__).with_name("historical-reference.json").write_text(json.dumps(dict(fixturePath=str(source.relative_to(root)), matches=len(fixtures), matchId="m_3Sg5Uh", season="2024/2025", table=rows), ensure_ascii=False, indent=2) + "\n")
print(f"{len(fixtures)} fixtures, {len(rows)} teams; leader {rows[0]['name']}: {rows[0]['points']} points")
