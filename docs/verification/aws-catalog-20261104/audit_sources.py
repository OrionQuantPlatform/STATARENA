"""Validate each versioned source against the worker's typed schema without DB writes."""

import gzip
import hashlib
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from inventory import BUCKET, client

folder = Path(__file__).resolve().parent
sys.path.insert(0, str(folder.parents[2] / "dashboard/scripts"))
from relational_catalog import models, normalize, rows_for
from relational_catalog_keys import records

local = Path("/tmp/statarena-catalog-source-audit-20261104")
local.mkdir(exist_ok=True)


def audit(row):
    name = row["path"]
    p = local / row["etag"]
    if not p.exists():
        resp = client.get_object(Bucket=BUCKET, Key="data/" + name, IfMatch=row["etag"])
        b = resp["Body"].read()
        if len(b) != row["bytes"]:
            raise ValueError("S3 length mismatch")
        p.write_bytes(b)
    b = p.read_bytes()
    result = {"path": name, "sha256": hashlib.sha256(b).hexdigest(), "records": 0}
    try:
        val = json.loads(gzip.decompress(b) if name.endswith(".gz") else b)
        for model, _, _, _, v in records(name, val):
            rows_for(models[model], normalize(model, v))
            result["records"] += 1
        if not result["records"]:
            result["emptyOrUnrecognized"] = True
    except (TypeError, ValueError, KeyError) as e:
        result["error"] = str(e)
    return result


if __name__ == "__main__":
    items = json.loads((folder / "source-inventory.json").read_text())
    with ThreadPoolExecutor(max_workers=3) as pool:
        out = list(pool.map(audit, items))
    errors = [x for x in out if "error" in x]
    (folder / ("source-audit-" + sys.argv[1] + ".json")).write_text(
        json.dumps(out, indent=2) + "\n"
    )
    print(
        len(out),
        "files",
        len(errors),
        "errors",
        [(x["path"], x["error"]) for x in errors[:18]],
    )
