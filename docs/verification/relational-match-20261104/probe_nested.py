"""Bounded read-only lookups of nested endpoints. SSM and CA paths stay external."""

import json
import os
from pathlib import Path

import psycopg

cfg = json.loads(Path(os.environ["STATARENA_PROBE_CONFIG"]).read_text())
evidence = Path(__file__).resolve().parent
db = psycopg.connect(
    host=cfg["host"],
    user=cfg["username"],
    password=cfg["password"],
    dbname=os.environ.get("STATARENA_PROBE_DB", "statarena_prod"),
    sslmode="verify-full",
    sslrootcert=os.environ["STATARENA_PROBE_CA"],
    connect_timeout=5,
    options="-c default_transaction_read_only=on -c statement_timeout=5000",
)
report = {
    "readOnly": db.execute("show transaction_read_only").fetchone()[0],
    "sample": [],
}
targets = [
    ("shot", "shots/s_[^/]+"),
    ("player", "players/p_[^/]+"),
    ("halves", "players/p_[^/]+/halves"),
    ("player_shots", "players/p_[^/]+/shots"),
    ("advanced", "advanced/players/p_[^/]+"),
]
observed = set()
for leading in ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "A", "B"):
    lower = "/matches/m_" + leading
    first = db.execute(
        "select endpoint from statarena.resources where endpoint >= %s and endpoint < %s order by endpoint limit 1",
        (lower, lower + "~"),
    ).fetchone()
    if not first:
        continue
    mid = first[0].split("/")[2]
    prefix = "/matches/" + mid + "/"
    for family, pattern in targets:
        if (family, 200) in observed:
            continue
        rows = db.execute(
            """with candidates as materialized (
         select endpoint,status,ref,error from statarena.resources
         where endpoint>=%s and endpoint<%s and endpoint ~ %s order by endpoint limit 600)
         select distinct on(c.status) c.endpoint,c.status,c.error,d.document
         from candidates c left join statarena.current_file_documents d
         on d.document_path=c.ref->>'path' and pg_column_size(d.document)<100000
         order by c.status,(d.document_path is not null) desc,c.endpoint""",
            (prefix, prefix + "z", "^" + prefix + pattern + "$"),
        ).fetchall()
        for endpoint, status, error, doc in rows:
            if (family, status) in observed:
                continue
            item = {
                "family": family,
                "endpoint": endpoint,
                "status": status,
                "indexed": doc is not None,
                "error": error,
            }
            if doc is not None:
                observed.add((family, status))
                item["sample"] = doc
            if doc is not None or not any(
                r["family"] == family and r["status"] == status
                for r in report["sample"]
            ):
                report["sample"].append(item)
    if all((f, 200) in observed for f, _ in targets):
        break
(evidence / "nested-source.json").write_text(json.dumps(report, indent=2) + "\n")
print([(s["endpoint"], s["status"], s["indexed"]) for s in report["sample"]])
