"""Bounded offline sample of imported staging shapes; no app or production writes."""

import json
import os
import sys
from pathlib import Path

import psycopg

folder = Path(__file__).resolve().parent
sys.path.insert(0, str(folder.parents[2] / "dashboard/scripts"))
from relational_match import _PARENT_SUFFIXES, prepare

cfg = json.loads(Path(os.environ["STATARENA_PROBE_CONFIG"]).read_text())
report = {"cases": [], "totalBytes": 0, "unindexed": 0}
with psycopg.connect(
    host=cfg["host"],
    user=cfg["username"],
    password=cfg["password"],
    dbname=os.environ.get("STATARENA_PROBE_DB", "statarena_prod"),
    sslmode="verify-full",
    sslrootcert=os.environ["STATARENA_PROBE_CA"],
    connect_timeout=5,
    options="-c default_transaction_read_only=on -c statement_timeout=5000",
) as db:
    report["transactionReadOnly"] = db.execute("show transaction_read_only").fetchone()[
        0
    ]
    for leading in ("0", "1", "2", "3", "9", "A", "X", "z"):
        lower = "/matches/m_" + leading
        first = db.execute(
            "select endpoint from statarena.resources where endpoint >= %s and endpoint < %s order by endpoint limit 1",
            (lower, lower + "~"),
        ).fetchone()
        if not first:
            continue
        mid = first[0].split("/")[2]
        names = {
            "/matches/" + mid + ("/" + suffix if suffix else ""): family
            for suffix, family in _PARENT_SUFFIXES.items()
        }
        if report["totalBytes"] > 7_400_000:
            break
        refs = db.execute(
            """select r.endpoint,r.status,r.error,d.document_path,octet_length(d.document::text)
        from statarena.resources r left join statarena.current_file_documents d on d.document_path=r.ref->>'path'
        where r.endpoint=any(%s) and r.params='{}'""",
            (list(names),),
        ).fetchall()
        for endpoint, status, error, path, size in refs:
            if path is None:
                report["unindexed"] += 1
                continue
            if size > 600000 or report["totalBytes"] + size > 8000000:
                continue
            doc = db.execute(
                "select document from statarena.current_file_documents where document_path=%s",
                (path,),
            ).fetchone()[0]
            if "observation" in doc:
                doc = doc["observation"]
            family = names[endpoint]
            item = {"match": mid, "family": family, "status": status, "bytes": size}
            try:
                prepare(
                    family,
                    {
                        "status": status,
                        "error": error or doc.get("error"),
                        "data": doc.get("data"),
                    },
                )
            except (TypeError, ValueError) as exc:
                item["error"] = str(exc)
            report["cases"].append(item)
            report["totalBytes"] += size
(folder / "shape-audit.json").write_text(json.dumps(report, indent=2) + "\n")
print(
    len(report["cases"]),
    report["totalBytes"],
    [r for r in report["cases"] if "error" in r],
)
