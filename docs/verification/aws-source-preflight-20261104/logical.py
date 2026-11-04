"""Audit the historical world-collector checksum against genuine retained envelopes."""

import hashlib, json, re, sys
from collections import Counter
from pathlib import Path
from db import connection, ROOT

sys.path.insert(0, str(ROOT / "dashboard/scripts"))
from relational_materialize import compact, envelope, PROFILE
from relational_catalog import models, rows_for

sql = """SELECT r.endpoint,r.params,r.status,r.error,r.ref,encode(o.sha256,'hex') FROM statarena.resources r
JOIN statarena.objects o ON o.path=r.ref->>'path'
WHERE r.ref?'sha256' AND r.ref->>'sha256'<>encode(o.sha256,'hex') AND """
folder = Path(__file__).resolve().parent
report = dict(
    command="PYTHONPATH=/tmp/statarena-publication-test-python python3 docs/verification/aws-source-preflight-20261104/logical.py",
    setup="PROTOCOL.md and git show 4a7b08dacc:dashboard/scripts/collect_pitchapi_world.py",
    categories={},
)
with connection() as d, d.transaction():
    d.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
    report["allStagingMismatches"] = [
        list(r)
        for r in d.execute(
            """SELECT split_part(endpoint,'/',2), r.ref->>'path' ~ '^raw/pitchapi-world/blobs/[a-f0-9]{64}\\.json\\.gz$', count(*),count(distinct o.path) FROM statarena.resources r JOIN statarena.objects o ON o.path=r.ref->>'path' WHERE r.ref?'sha256' AND r.ref->>'sha256'<>encode(o.sha256,'hex') GROUP BY 1,2 ORDER BY 1,2"""
        )
    ]
    for category, clause, params in [
        ("allEligibleProfiles", "r.params='{}' AND r.endpoint~%s", (PROFILE,)),
        (
            "sampleOfOtherResources",
            "r.endpoint LIKE '/matches/%%' ORDER BY r.endpoint,r.params LIMIT 128",
            (),
        ),
    ]:
        refs = d.execute(sql + clause, params).fetchall()
        err = []
        bytecount = 0
        valid = 0
        kindcounts = Counter()
        paths = sorted({r[4]["path"] for r in refs})
        docs = {}
        for i in range(0, len(paths), 128):
            docs.update(
                d.execute(
                    "SELECT document_path,document FROM statarena.current_file_documents WHERE document_path=ANY(%s) AND source_path=document_path",
                    (paths[i : i + 128],),
                ).fetchall()
            )
        rows = [(*r, docs.get(r[4]["path"])) for r in refs]
        for endpoint, params, status, error, ref, physical, doc in rows:
            logical = hashlib.sha256(compact(doc).encode()).hexdigest()
            bytecount += len(compact(doc).encode())
            kind = endpoint.split("/")[1]
            try:
                if (
                    doc is None
                    or ref["sha256"] != logical
                    or ref["path"] != "raw/pitchapi-world/blobs/" + logical + ".json.gz"
                ):
                    raise ValueError("canonical digest or pathname mismatch")
                valid += 1
                if category == "allEligibleProfiles":
                    rows_for(
                        models["profile_" + kind], envelope(doc, ref, status, error)
                    )
                kindcounts[kind] += 1
            except (ValueError, KeyError, TypeError) as e:
                err.append([endpoint, params, str(e)])
        report["categories"][category] = dict(
            rows=len(rows),
            logicalHashValidated=valid,
            validByFamily=kindcounts,
            sourceDocumentJsonBytes=bytecount,
            errors=err,
        )
(folder / "logical.json").write_text(json.dumps(report, indent=2) + "\n")
print(compact(report)[:2200])
