"""Capture bounded structural metadata over one read-only RDS connection."""

import gzip
import hashlib
import json
from pathlib import Path
import sys, time

folder = Path(__file__).resolve().parent
sys.path.insert(0, str(folder.parent / "aws-source-preflight-20261104"))
from db import connection

out = Path("/tmp/statarena-prepare-meta-20261104")
out.mkdir(mode=0o700, exist_ok=True)
queries = {
    "fixtures": "SELECT id,league_id,season FROM statarena.fixtures",
    "observations": "SELECT id,shard,ordinal FROM statarena.observations",
    "shards": "SELECT id,ref FROM statarena.shards",
    "objects": "SELECT path FROM statarena.objects",
    "resources": """SELECT endpoint,params,status,ref->>'path',ref->>'ordinal',ref->>'documentId',(ref?'sha256')::int,error FROM statarena.resources""",
}
log = {
    "setup": "One verify-full read-only RDS snapshot, excludes all object/fixture/resource payloads. Physical object SHA and source timestamps synthesized at fixture load.",
    "command": "PYTHONPATH=/tmp/statarena-publication-test-python python3 docs/verification/aws-prepare-20261104/capture.py",
    "tables": {},
    "maxRawBytes": 140_000_000,
}
total = 0
try:
    with connection() as d, d.transaction():
        d.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        log["snapshot"] = str(d.execute("SELECT now()").fetchone()[0])
        log["workMem"] = d.execute("SHOW work_mem").fetchone()[0]
        for name, sql in queries.items():
            n = size = 0
            h = hashlib.sha256()
            start = time.monotonic()
            with (
                d.cursor().copy("COPY (" + sql + ") TO STDOUT") as cur,
                gzip.open(out / (name + ".tsv.gz"), "wb", compresslevel=1) as file,
            ):
                for chunk in cur:
                    s = bytes(chunk)
                    n += s.count(b"\n")
                    size += len(s)
                    total += len(s)
                    if total > log["maxRawBytes"]:
                        raise ValueError("Metadata transfer limit reached")
                    h.update(s)
                    file.write(s)
            log["tables"][name] = {
                "rows": n,
                "rawBytes": size,
                "copySec": round(time.monotonic() - start, 2),
                "sha256": h.hexdigest(),
            }
            print(name, n, size, flush=True)
except BaseException as e:
    log["failure"] = str(e)
    raise
finally:
    log["totalRawBytes"] = total
    (folder / "source-metadata.json").write_text(json.dumps(log, indent=2) + "\n")
