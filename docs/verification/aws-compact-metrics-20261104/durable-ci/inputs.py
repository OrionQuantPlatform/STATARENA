"""Verify the exact compressed corpus and the COPY rows that PostgreSQL consumes."""

import gzip
import hashlib
import json
from pathlib import Path

suite = Path(__file__).resolve().parents[1]
manifest = json.loads((suite / "inputs/manifest.json").read_text())["files"]
proof = json.loads((suite / "after/results.json").read_text())["families"]
actual = {}
for family in ("half", "player"):
    for kind in ("metrics", "groups"):
        name = f"{family}_stat_{kind}.tsv.gz"
        raw = (suite / "inputs" / name).read_bytes()
        decoded = gzip.decompress(raw)
        record = dict(
            gzipBytes=len(raw),
            gzipSha256=hashlib.sha256(raw).hexdigest(),
            copyBytes=len(decoded),
            copySha256=hashlib.sha256(decoded).hexdigest(),
            rows=decoded.count(b"\n"),
        )
        if (
            record != manifest[name]
            or record["copySha256"]
            != proof[family]["inputSha256" if kind == "metrics" else "groupSha256"]
        ):
            raise ValueError("Metric corpus checksum mismatch: " + name)
        actual[name] = record
if set(actual) != set(manifest):
    raise ValueError("Unexpected metric corpus members")
print(json.dumps(actual, indent=2))
