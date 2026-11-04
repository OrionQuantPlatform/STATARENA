"""Capture public supporting projection inputs from the AWS migration staging schema."""

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import psycopg

parser = argparse.ArgumentParser()
parser.add_argument("credentials", type=Path, help="private SSM runtime JSON file")
parser.add_argument("ca", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
runtime = json.loads(args.credentials.read_text())
with psycopg.connect(
    host=runtime["host"],
    user=runtime["username"],
    password=runtime["password"],
    dbname=runtime["database"],
    sslrootcert=str(args.ca),
    sslmode="verify-full",
    options="-c default_transaction_read_only=on -c statement_timeout=40000",
    application_name="statarena-support-readback",
) as db:
    if db.execute("show transaction_read_only").fetchone() != ("on",):
        raise RuntimeError("Read-only transaction required")
    rows = db.execute(
        "select name,params,body from statarena.projections where name=any(%s) order by name,params",
        (
            [
                "standings",
                "stadium",
                "club-wikidata",
                "coach-portrait",
                "player-honours",
                "nations-results",
                "open-cups",
                "openligadb",
            ],
        ),
    ).fetchall()
raw = json.dumps(
    rows, sort_keys=True, separators=(",", ":"), ensure_ascii=False
).encode()
args.output.write_bytes(gzip.compress(raw, mtime=0))
print(json.dumps({"keys": len(rows), "inputSha256": hashlib.sha256(raw).hexdigest()}))
