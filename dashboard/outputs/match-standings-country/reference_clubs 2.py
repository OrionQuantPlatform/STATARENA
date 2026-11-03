"""Independent raw-data reference for the Clubs browser E2E checks.

Rerun from dashboard: python3 outputs/match-standings-country/reference_clubs.py
"""
import gzip
import json
from pathlib import Path

root = Path(__file__).resolve().parents[3]
result = {}
for season in ["2026-2027", "2024-2025"]:
    result[season] = {}
    for league in ["l_1Isor4", "l_3hvsne", "l_47077Y", "l_3FJFUl", "l_0275VP", "l_0bfbkO"]:
        files = list((root / "data/raw/seasons" / season / "matches").glob(league + "--*.json.gz"))
        matches = json.load(gzip.open(files[0])) if files else []
        clubs = {}
        for match in matches:
            for team in [match["home"], match["away"]]:
                row = clubs.setdefault(team["id"], {"name": team["name"], "matches": 0})
                row["matches"] += 1
        result[season][league] = {"source": str(files[0].relative_to(root)) if files else None, "matches": len(matches), "clubs": clubs}
Path(__file__).with_name("clubs-reference.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
print({season: {league: len(value["clubs"]) for league, value in leagues.items()} for season, leagues in result.items()})
