"""Capture already-published typed metric evidence. Read no raw staging documents."""

import gzip, hashlib, json, sys, time
from pathlib import Path

folder = Path(__file__).resolve().parent
sys.path.insert(0, str(folder.parent / "aws-source-preflight-20261104"))
from db import connection

out = Path("/tmp/statarena-metric-values-20261104")
out.mkdir(mode=0o700, exist_ok=True)
report = {
    "command": "PYTHONPATH=/tmp/statarena-publication-test-python python3 docs/verification/aws-capacity-20261104/metrics_capture.py",
    "setup": "Single read-only verified TLS session, simple two sequential COPY reads of typed output tables from successful first job. 45MB ceiling.",
}
total = 0
with connection() as d, d.transaction():
    d.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
    for rel in ("half_stat_metrics", "player_stat_metrics"):
        size = 0
        n = 0
        h = hashlib.sha256()
        with (
            d.cursor().copy("COPY statarena_app." + rel + " TO STDOUT") as cur,
            gzip.open(out / (rel + ".tsv.gz"), "wb", compresslevel=1) as f,
        ):
            for b in cur:
                b = bytes(b)
                size += len(b)
                total += len(b)
                n += b.count(b"\n")
                if total > 45_000_000:
                    raise RuntimeError("Published fact capture limit exceeded")
                h.update(b)
                f.write(b)
        report[rel] = dict(rows=n, tsvBytes=size, sha256=h.hexdigest())
(folder / "published-metrics.json").write_text(json.dumps(report, indent=2) + "\n")
print(report)
