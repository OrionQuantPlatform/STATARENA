"""List only the source object families consumed by the catalog worker."""

import json
import subprocess
from pathlib import Path

import boto3

auth = json.loads(
    subprocess.check_output(
        [
            "aws",
            "configure",
            "export-credentials",
            "--profile",
            "statarena",
            "--format",
            "process",
        ]
    )
)
client = boto3.client(
    "s3",
    region_name="us-east-2",
    aws_access_key_id=auth["AccessKeyId"],
    aws_secret_access_key=auth["SecretAccessKey"],
    aws_session_token=auth.get("SessionToken"),
)
BUCKET = "statarena-football-333rosky-70db6e5f"
PREFIXES = (
    "raw/openfootball/",
    "raw/historical-goals/",
    "raw/rankings/",
    "raw/cup-worker/",
    "computed/matchdays/",
    "raw/seasons/2026-2027/supplemental_",
    "raw/supplemental-index.json",
)


def inventory():
    rows = []
    for prefix in PREFIXES:
        for page in client.get_paginator("list_objects_v2").paginate(
            Bucket=BUCKET, Prefix="data/" + prefix
        ):
            rows.extend(
                {"path": o["Key"][5:], "bytes": o["Size"], "etag": o["ETag"].strip('"')}
                for o in page.get("Contents", [])
                if o["Key"].endswith((".json", ".json.gz"))
            )
    return rows


if __name__ == "__main__":
    rows = inventory()
    out = Path(__file__).parent / "source-inventory.json"
    out.write_text(json.dumps(rows, indent=2) + "\n")
    print(
        [
            (
                p,
                sum(x["path"].startswith(p) for x in rows),
                sum(x["bytes"] for x in rows if x["path"].startswith(p)),
            )
            for p in PREFIXES
        ]
    )
