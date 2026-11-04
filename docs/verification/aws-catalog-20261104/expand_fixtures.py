"""Repack pinned local audit inputs into small reproducible HTTP fixture subsets."""

import gzip
import json
from pathlib import Path

folder = Path(__file__).resolve().parent
items = json.loads((folder / "source-inventory.json").read_text())
before = json.loads((folder / "source-audit-before.json").read_text())
seen = set()
extra = set()
for row in before:
    error = row.get("error")
    if error and error not in seen:
        seen.add(error)
        extra.add(row["path"])
bundle = {}
for it in items:
    name = it["path"]
    if name not in extra and "/supplemental_" not in name:
        continue
    raw = (
        Path("/tmp/statarena-catalog-source-audit-20261104") / it["etag"]
    ).read_bytes()
    data = json.loads(gzip.decompress(raw) if name.endswith(".gz") else raw)
    if name in extra:
        dest = folder / "captures" / (name.replace("/", "__") + ".gz")
        dest.write_bytes(
            gzip.compress(
                json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode(),
                mtime=0,
            )
        )
    if "/supplemental_" in name:
        bundle[name] = data
(folder / "supplemental-full.json.gz").write_bytes(
    gzip.compress(
        json.dumps(bundle, ensure_ascii=False, separators=(",", ":")).encode(), mtime=0
    )
)
