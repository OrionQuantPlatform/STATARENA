"""Offline fixture worker for exact production-capture compatibility."""

import json
import os
import sys
from pathlib import Path

import psycopg

root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(root / "dashboard/scripts"))
from relational_match import publish_match_details

samples = root / "dashboard/outputs/data-completeness"
with psycopg.connect(os.environ["LOCAL_FIXTURE_DB"]) as db:
    if len(sys.argv) > 1:
        record = json.loads((samples / "production-archive.json").read_text())
        endpoints = record.pop("endpoints")
        mid = record["fixture"]["id"]
        if sys.argv[1] == "context":
            record["competition_name"] = "Edited publication"
            publish_match_details(db, mid, {}, record)
        elif sys.argv[1] == "family":
            publish_match_details(
                db,
                mid,
                {
                    "momentum": {
                        "status": 200,
                        "data": {"match_id": mid, "points": []},
                        "error": None,
                    }
                },
            )
        else:
            raise ValueError("unknown operation")
        db.commit()
        sys.exit(0)
    publish_match_details(
        db,
        "m_ZZZZZZ",
        {
            "match": {
                "status": 200,
                "data": {"stadium": "x" * (2 * 1024 * 1024)},
                "error": None,
            }
        },
    )
    for filename in (
        "production-archive",
        "browser-upcoming-archive",
        "browser-historical-archive",
    ):
        data = json.loads((samples / (filename + ".json")).read_text())
        mid = data["fixture"]["id"]
        endpoints = data.pop("endpoints")
        publish_match_details(db, mid, endpoints, data)
        publish_match_details(db, mid, endpoints, data)
    data = json.loads((samples / "production-archive.json").read_text())
    mid = data["fixture"]["id"]
    variant = data["endpoints"]["heatmaps"]["data"].copy()
    variant["grid"] = dict(variant["grid"], frame="acting_ltr")
    publish_match_details(
        db,
        mid,
        {"heatmaps": {"status": 200, "data": variant, "error": None}},
        params={"frame": "acting_ltr"},
    )
    try:
        with db.transaction():
            publish_match_details(
                db,
                mid,
                {
                    "momentum": {
                        "status": 200,
                        "data": {"match_id": mid, "unexpected_source_field": 123},
                    }
                },
            )
    except ValueError:
        pass
    else:
        raise AssertionError("unknown fields must not be silently dropped")
    publish_match_details(
        db,
        "m_000001",
        {
            "momentum": {
                "status": 429,
                "error": {"code": "RATE_LIMIT", "message": "retry"},
            }
        },
    )
    publish_match_details(
        db,
        "m_000001",
        {
            "shots": {
                "status": 200,
                "data": {"match_id": "m_000001", "periods": []},
                "error": None,
            }
        },
    )
    from relational_match import publish_match_resource

    for item in json.loads((Path(__file__).parent / "nested-source.json").read_text())[
        "sample"
    ]:
        doc = item.get("sample", {})
        response = {
            "status": item["status"],
            "data": doc.get("data"),
            "error": item["error"] or doc.get("error"),
        }
        assert publish_match_resource(db, item["endpoint"], {}, response)
