import gzip
import json
import os
import sys
from pathlib import Path

import psycopg

folder = Path(__file__).resolve().parent
root = folder.parents[2]
sys.path.insert(0, str(root / "dashboard/scripts"))
from relational_catalog import publish_catalog

captured = []
for path in sorted((folder / "captures").glob("*.gz")):
    name = path.name[:-3].replace("__", "/")
    if name.startswith("raw/neon/"):
        continue
    if name.startswith("profile/"):
        name = name.removeprefix("profile")
    body = json.loads(gzip.decompress(path.read_bytes()))
    captured.append((name, body))
with psycopg.connect(os.environ["LOCAL_FIXTURE_DB"]) as db:
    if len(sys.argv) > 1 and sys.argv[1] == "change-supplemental":
        bundle = json.loads(
            gzip.decompress((folder / "supplemental-full.json.gz").read_bytes())
        )
        path = "raw/seasons/2026-2027/supplemental_goals/ENG_1_premier-league.json.gz"
        result = bundle[path]
        result[0]["scorer"] = "Updated sample"
        publish_catalog(db, [(path, result)])
        db.commit()
        sys.exit(0)
    if len(sys.argv) > 1 and sys.argv[1] == "supplemental":
        bundle = json.loads(
            gzip.decompress((folder / "supplemental-full.json.gz").read_bytes())
        )
        publish_catalog(db, bundle.items())
        db.commit()
        sys.exit(0)
    publish_catalog(
        db,
        [
            (
                "/players/p_FAIL00",
                {
                    "status": 404,
                    "error": {"code": "RESOURCE_NOT_FOUND", "message": "unavailable"},
                },
            )
        ],
    )
    publish_catalog(db, captured)
    publish_catalog(db, captured)
    try:
        publish_catalog(
            db,
            [
                (
                    "/players/p_XYZ123",
                    {"status": 200, "data": {"new_unknown_fact": 3}, "error": None},
                )
            ],
        )
    except (ValueError, TypeError):
        pass
    else:
        raise AssertionError("unknown source field lost")
