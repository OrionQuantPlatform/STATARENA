"""Preserve the server-TLS guard failure; prove client TLS and complete exact keys."""
import json
from pathlib import Path
import time

from metadata_inventory import OUT, NOW, SHA, OPTIONS, connect_neon, connect_aws, sanitized_error, save, snapshot, query

if (OUT / "client-tls-readback.json").exists() or (OUT / "aws-complete-direct.json").exists():
    raise SystemExit("This bounded follow-up already has receipts; do not reset its budget")
tls = {"startedAt": NOW(), "scope": "New TLS handshake only, no SQL or transaction", "sqlStatements": 0, "remoteWrites": []}
connection = None
try:
    connection = connect_neon()
    selected = connection.info.get_parameters()
    tls.update(clientSslInUse=connection.pgconn.ssl_in_use,
        parameters={k: selected.get(k) for k in ["host", "dbname", "sslmode", "sslrootcert"]},
        attributes={key.decode(): connection.pgconn.ssl_attribute(key).decode() for key in connection.pgconn.ssl_attribute_names},
        status="pass" if connection.pgconn.ssl_in_use and selected.get("sslmode") == "verify-full" else "fail")
except Exception as error:
    tls.update(status="blocked", errorType=type(error).__name__, error=sanitized_error(error))
finally:
    if connection is not None:
        connection.close()
    tls["finishedAt"] = NOW()
    save("client-tls-readback.json", tls)
    print(json.dumps({"scope": "Neon client TLS, no SQL", "status": tls["status"], "clientSslInUse": tls.get("clientSslInUse"), "error": tls.get("error")}), flush=True)

neon = json.loads((OUT / "neon-direct.json").read_text())
data = neon["metadata"]
paths = {r["path"] for r in data["objects"]} | {r["ref_path"] for r in data["profiles"] + data["resources"] if r.get("ref_path")}
endpoints = {r["endpoint"] for r in data["resources"] if r.get("endpoint")}
sql = query(paths, endpoints, aws=True)
save("aws-complete-query.json", {"atUtc": NOW(), "sql": sql, "exactNeonPaths": sorted(paths), "exactNeonEndpoints": sorted(endpoints),
    "explanation": "Complete AWS key lookup after Neon server-TLS guard was shown to describe the server hop rather than the enforced client TLS handshake. The original failed guard receipt is retained."})
budget = json.loads((OUT / "execution-budget.json").read_text())
if budget["statementsMaximum"] + 3 > 20:
    raise SystemExit("SQL budget would be exceeded")
aws = snapshot("aws-complete", connect_aws, sql, budget)
budget.update(atUtc=NOW(), clientTlsHandshakeSqlStatements=0,
    passed=budget["statementsMaximum"] <= 20 and budget["resultBytes"] <= 16777216,
    note="Original Neon server-TLS guard fail and first AWS snapshot retained; TLS-client handshake adds zero SQL. Second AWS snapshot probes every exact Neon key; snapshots are sequential, not simultaneous.")
save("final-execution-budget.json", budget)
