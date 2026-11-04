"""Sample import-ready, bounded profile resource references and validate their typed fields."""

import json
import os
import sys
from pathlib import Path

import psycopg

folder = Path(__file__).resolve().parent
sys.path.insert(0, str(folder.parents[2] / "dashboard/scripts"))
from relational_catalog import models, rows_for

cfg = json.loads(Path(os.environ["STATARENA_PROBE_CONFIG"]).read_text())
report = {"scanned": [], "unmapped": []}
with psycopg.connect(
    host=cfg["host"],
    user=cfg["username"],
    password=cfg["password"],
    dbname="statarena_prod",
    sslmode="verify-full",
    sslrootcert=os.environ["STATARENA_PROBE_CA"],
    options="-c default_transaction_read_only=on -c statement_timeout=5000",
) as db:
    for kind in ("leagues", "teams", "players"):
        prefixes = [
            "/" + kind + "/" + kind[0] + "_" + c for c in "0123456789ABCDEFabcdef"
        ]
        cases = db.execute(
            """WITH candidates AS MATERIALIZED (
        SELECT r.* FROM unnest(%s::text[]) p
        CROSS JOIN LATERAL(SELECT endpoint,status,ref,error FROM statarena.resources WHERE endpoint>=p AND endpoint<p||'~'
        AND length(endpoint)=length(p)+5 AND params='{}' ORDER BY endpoint LIMIT 10) r)
        SELECT r.endpoint,r.status,r.error,
        CASE WHEN r.ref ? 'ordinal' THEN d.document->(r.ref->>'ordinal')::integer ELSE d.document END
        FROM candidates r JOIN statarena.current_file_documents d ON d.document_path=r.ref->>'path'
        WHERE NOT(r.ref ? 'documentId') AND (r.ref ? 'ordinal' OR pg_column_size(d.document)<100000)""",
            (prefixes,),
        ).fetchall()
        for endpoint, status, error, doc in cases:
            if not isinstance(doc, dict):
                continue
            raw = doc.get("response", doc.get("observation", doc))
            envelope = {
                "status": status,
                "data": raw.get("data"),
                "error": error or raw.get("error"),
            }
            item = {"endpoint": endpoint, "status": status}
            try:
                rows_for(models["profile_" + kind], envelope)
            except (TypeError, ValueError) as e:
                item["error"] = str(e)
                report["unmapped"].append({"endpoint": endpoint, "envelope": envelope})
            report["scanned"].append(item)
(folder / "profile-shape-audit.json").write_text(json.dumps(report, indent=2) + "\n")
print(
    len(report["scanned"]),
    len(report["unmapped"]),
    [s.get("error") for s in report["scanned"] if s.get("error")][:5],
)
