"""Load and replay all pinned catalog objects in the disposable PostgreSQL cluster."""

import gzip
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import psycopg

folder = Path(__file__).resolve().parent
sys.path.insert(0, str(folder.parents[2] / "dashboard/scripts"))
from relational_catalog import normalize, publish_catalog
from relational_catalog_keys import records

inventory = json.loads((folder / "source-inventory.json").read_text())
checksums = {
    x["path"]: x["sha256"]
    for x in json.loads((folder / "source-audit-after.json").read_text())
}
out = {
    "source": "source-inventory.json and source-audit-after.json",
    "command": "PYTHONPATH=/tmp/statarena-archive-remat-pg/python bun docs/verification/aws-catalog-20261104/verify.mjs after --all",
    "sources": [],
}
tmpdir = Path(
    os.environ.get(
        "STATARENA_CATALOG_AUDIT_CACHE", "/tmp/statarena-catalog-source-audit-20261104"
    )
)
started = time.monotonic()
try:
    with psycopg.connect(os.environ["LOCAL_FIXTURE_DB"]) as db:
        for src in inventory:
            name = src["path"]
            data = (tmpdir / src["etag"]).read_bytes()
            assert hashlib.sha256(data).hexdigest() == checksums[name]
            obj = json.loads(gzip.decompress(data) if name.endswith(".gz") else data)
            pub = publish_catalog(db, [(name, obj)])
            count = 0
            for model, kind, scope, version, body in records(name, obj):
                value = db.execute(
                    """SELECT statarena_app.catalog_response(c) FROM statarena_app.catalog_editions c
                WHERE c.catalog=%s AND c.scope=%s AND c.edition=%s""",
                    (kind, scope, version),
                ).fetchone()[0]
                assert value == normalize(model, body), (name, kind, scope, version)
                count += 1
            out["sources"].append({"path": name, "records": count, **pub})
        out["physicalCatalogBytes"] = db.execute(
            "SELECT sum(pg_total_relation_size(oid))::bigint FROM pg_class WHERE relnamespace='statarena_app'::regnamespace AND relkind='r'"
        ).fetchone()[0]
        out["publishedEditions"] = db.execute(
            "select catalog,count(*) from statarena_app.catalog_editions group by catalog order by catalog"
        ).fetchall()
    out["passed"] = True
except Exception as e:
    out["error"] = str(e)[:500]
    raise
finally:
    out["seconds"] = round(time.monotonic() - started, 3)
    (folder / "full-postgres-roundtrip.json").write_text(
        json.dumps(out, indent=2) + "\n"
    )
