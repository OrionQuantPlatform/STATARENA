"""Exercise the worker's actual catalog queue and checksum paths on PostgreSQL."""

import gzip, hashlib, json, os, sys
from pathlib import Path
from types import SimpleNamespace
import psycopg
from psycopg.types.json import Jsonb

out = Path(__file__).resolve().parent / sys.argv[1]
root = out.parents[3]
sys.path.insert(0, str(root / "dashboard/scripts"))
from relational_materialize import Inputs, catalog_batch, install, compact

url = os.environ["TEST_DATABASE_URL"]
assert "@127.0.0.1:" in url and url.endswith("/publication_fixture")
report = {
    "command": "node docs/verification/aws-source-preflight-20261104/run.mjs "
    + sys.argv[1],
    "setup": "PROTOCOL.md; migrations 001–006 and local PostgreSQL 18; actual catalog batch writes typed SQL and acknowledges jobs transactionally",
    "cases": [],
}
with psycopg.connect(url, autocommit=True) as d:
    d.execute((root / "dashboard/backend/migrations/001_neon.sql").read_text())
    d.execute((root / "dashboard/backend/migrations/002_aws_documents.sql").read_text())
    install(d)
    d.execute(
        "CREATE TEMP TABLE work_catalog(kind text,key text,digest text,ref jsonb,status int,error jsonb)"
    )
    source = {"data": {"id": "p_000001", "name": "Éliot", "position_id": 8}}
    raw = compact(source).encode()
    logical = hashlib.sha256(raw).hexdigest()
    compressed = gzip.compress(raw, mtime=0)
    physical = hashlib.sha256(compressed).digest()
    prefix = "raw/pitchapi-world/blobs/"

    def unexpected(*_):
        raise AssertionError("unexpected fallback read")

    for name, path, claim, body, ok in [
        ("legacy logical hash", prefix + logical + ".json.gz", logical, source, True),
        ("wrong logical hash", prefix + logical + ".json.gz", "0" * 64, source, False),
        (
            "wrong immutable basename",
            prefix + "0" * 64 + ".json.gz",
            logical,
            source,
            False,
        ),
        (
            "unrelated source namespace",
            "raw/other/" + logical + ".json.gz",
            logical,
            source,
            False,
        ),
        (
            "incorrect indexed JSON",
            prefix + logical + ".json.gz",
            logical,
            {"data": {"id": "p_000001", "name": "incorrect"}},
            False,
        ),
        (
            "physical final byte hash",
            "raw/new/physical.json.gz",
            physical.hex(),
            source,
            True,
        ),
    ]:
        d.execute("DELETE FROM work_catalog")
        d.execute("DELETE FROM statarena_app.worker_inputs")
        d.execute("DELETE FROM statarena_app.catalog_editions")
        d.execute(
            "INSERT INTO statarena.objects(path,size,sha256,etag) VALUES(%s,%s,%s,'local') ON CONFLICT DO NOTHING",
            (path, len(compressed), physical),
        )
        d.execute(
            "INSERT INTO statarena.file_document_sources(source_path,source_sha256,status,document_count,error_count) VALUES (%s,%s,'ready',1,0) ON CONFLICT DO NOTHING",
            (path, physical),
        )
        d.execute(
            "INSERT INTO statarena.file_documents(document_path,source_path,source_sha256,format,document) VALUES(%s,%s,%s,'json',%s) ON CONFLICT(document_path) DO UPDATE SET document=excluded.document",
            (path, path, physical, Jsonb(body)),
        )
        d.execute(
            "INSERT INTO work_catalog VALUES('profile','/players/p_000001','d',%s,200,NULL)",
            (Jsonb({"path": path, "sha256": claim}),),
        )
        try:
            catalog_batch(Inputs(SimpleNamespace(db=d, json=unexpected)), 1)
            error = None
        except ValueError as e:
            error = str(e)
        receipt = d.execute(
            "SELECT count(*) FROM statarena_app.worker_inputs"
        ).fetchone()[0]
        waiting = d.execute("SELECT count(*) FROM work_catalog").fetchone()[0]
        value = d.execute(
            "SELECT statarena_app.catalog_response(c) FROM statarena_app.catalog_editions c"
        ).fetchone()
        passed = (
            (error is None) == ok
            and receipt == int(ok)
            and waiting == int(not ok)
            and (
                value[0]["data"] == source["data"]
                if ok and value
                else (not ok and value is None)
            )
        )
        report["cases"].append(
            dict(
                name=name,
                passed=passed,
                queue=waiting,
                receipt=receipt,
                error=error,
                typed=value,
            )
        )
report["passed"] = sum(x["passed"] for x in report["cases"])
(out / "results.json").write_text(json.dumps(report, indent=2) + "\n")
print(
    report["passed"],
    "/",
    len(report["cases"]),
    [r["name"] for r in report["cases"] if not r["passed"]],
)
sys.exit(report["passed"] != len(report["cases"]))
