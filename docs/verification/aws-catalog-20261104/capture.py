"""Offline read-only source capture. No application code imports this file."""

import gzip
import json
import os
import subprocess
from pathlib import Path

import psycopg

out = Path(__file__).parent / "captures"
out.mkdir(exist_ok=True)
cfg = json.loads(Path(os.environ["STATARENA_PROBE_CONFIG"]).read_text())
db = psycopg.connect(
    host=cfg["host"],
    user=cfg["username"],
    password=cfg["password"],
    dbname="statarena_prod",
    sslmode="verify-full",
    sslrootcert=os.environ["STATARENA_PROBE_CA"],
    options="-c default_transaction_read_only=on -c statement_timeout=5000",
    connect_timeout=5,
)

bucket = "statarena-football-333rosky-70db6e5f"


def capture(path, *, retain=True):
    dest = out / (path.replace("/", "__") + ".gz")
    if dest.exists():
        return json.loads(gzip.decompress(dest.read_bytes()))
    row = db.execute(
        "select document from statarena.current_file_documents where document_path=%s",
        (path,),
    ).fetchone()
    if row:
        value = row[0]
        src = "current PostgreSQL staging"
    else:
        b = subprocess.check_output(
            [
                "aws",
                "--profile",
                "statarena",
                "s3",
                "cp",
                "s3://" + bucket + "/data/" + path,
                "-",
                "--only-show-errors",
            ]
        )
        value = json.loads(gzip.decompress(b) if path.endswith(".gz") else b)
        src = "retained S3 original"
    raw = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()
    if retain:
        dest.write_bytes(gzip.compress(raw, mtime=0))
    print(
        path,
        src,
        len(raw),
        list(value)[:12] if isinstance(value, dict) else type(value).__name__,
        flush=True,
    )
    return value


if __name__ == "__main__":
    for name in [
        "openfootball/index",
        "historical-goals/index",
        "rankings/index",
        "rankings/club-links",
        "cup-worker/index",
        "supplemental-index",
    ]:
        capture("raw/" + name + ".json")

    def paths(prefix):
        return [
            x[0]
            for x in db.execute(
                "select path from statarena.objects where path>=%s and path<%s order by path limit 700",
                (prefix, prefix + "~"),
            )
        ]

    ranks = capture("raw/rankings/index.json")
    seen = set()
    for r in ranks["editions"]:
        k = r["kind"], r["provider"]
        if k not in seen:
            capture(r["path"])
            seen.add(k)
    for name in ("openfootball", "historical-goals"):
        idx = capture("raw/" + name + "/index.json")
        for r in [idx["seasons"][0], idx["seasons"][-1]]:
            capture(r["path"])
    for name in ("supplemental-index", "cup-worker/index"):
        c = capture("raw/" + name + ".json")["competitions"][0]
        for r in c["tables"].values():
            capture(r["path"])
    cup = paths("raw/cup-worker/")
    print("cup types", sorted({x.split("/")[2] for x in cup}))
    for k in (
        "native",
        "open",
        "open-cups",
        "standings",
        "openligadb",
        "nations-results",
    ):
        cand = [p for p in cup if p.startswith("raw/cup-worker/" + k + "/")]
        if cand:
            capture(cand[0])
    print("cup source names", cup[:12])
    sample = paths("computed/matchdays/")
    if sample:
        capture(sample[-1])
    for kind in ("leagues", "teams", "players"):
        prefix = "/" + kind + "/"
        rows = db.execute(
            """with cand as materialized (select r.endpoint,r.status,r.ref from statarena.resources r
           where endpoint>=%s and endpoint<%s and endpoint ~ %s and params='{}' and status=200 order by endpoint limit 120)
           select c.endpoint,c.ref,d.document from cand c join statarena.current_file_documents d on d.document_path=c.ref->>'path'
           where pg_column_size(d.document)<150000 limit 2""",
            (prefix, prefix + "~", "^" + prefix + "[ltp]_[0-9a-zA-Z]{6}$"),
        ).fetchall()
        if not rows:
            resources = db.execute(
                "select endpoint,status,ref,error from statarena.resources where endpoint>=%s and endpoint<%s and endpoint ~ %s and params='{}' and status=200 order by endpoint limit 1",
                (prefix, prefix + "~", "^" + prefix + "[ltp]_[0-9a-zA-Z]{6}$"),
            ).fetchall()
            rows = [
                (endpoint, ref, capture(ref["path"], retain=False))
                for endpoint, _, ref, _ in resources
            ]
        for endpoint, ref, doc in rows:
            if "ordinal" in ref:
                doc = doc[ref["ordinal"]]
            if ref.get("documentId"):
                doc = next(x for x in doc if x["documentId"] == ref["documentId"])
            doc = doc.get("observation", doc.get("response", doc))
            fn = out / ("profile__" + endpoint.strip("/").replace("/", "__") + ".gz")
            fn.write_bytes(
                gzip.compress(
                    json.dumps(
                        {
                            "status": 200,
                            "data": doc.get("data"),
                            "error": doc.get("error"),
                        },
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ).encode(),
                    mtime=0,
                )
            )
            print("profile", endpoint, str(list((doc.get("data") or {}).keys()))[:140])
    # Exercise one genuine non-empty goals table and additional archive vintages.
    source = capture("raw/supplemental-index.json")
    for comp in source["competitions"]:
        goals = comp["tables"]["goals"]
        if goals["rows"] > 0:
            for table in comp["tables"].values():
                capture(table["path"])
            break
    idx = capture("raw/openfootball/index.json")["seasons"]
    for label in ("2024/2025", "2026/2027", "2012/2013", "1985/1986"):
        for r in idx:
            if r["id"] == label:
                capture(r["path"])
    for stem in ("world-cup", "euro", "club-world-cup"):
        candidate = next((p for p in cup if "/open-cups/" + stem + "/" in p), None)
        if candidate:
            capture(candidate)
    r = db.execute(
        "select status,ref,error from statarena.resources where endpoint='/leagues' and params='{}'"
    ).fetchone()
    if r and r[1]:
        ref = r[1]
        val = capture(ref["path"], retain=False)
        if "ordinal" in ref:
            val = val[ref["ordinal"]]
        if ref.get("documentId"):
            val = next(x for x in val if x["documentId"] == ref["documentId"])
        val = val.get("observation", val.get("response", val))
        dest = out / "profile__leagues.gz"
        dest.write_bytes(
            gzip.compress(
                json.dumps(
                    {
                        "status": r[0],
                        "data": val.get("data"),
                        "error": r[2] or val.get("error"),
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode(),
                mtime=0,
            )
        )
    for r in ranks["editions"]:
        if r["kind"] == "uefa-clubs" and r["provider"] == "UEFA":
            capture(r["path"])
