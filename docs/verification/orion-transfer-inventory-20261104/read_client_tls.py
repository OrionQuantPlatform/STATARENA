"""Client TLS readback without SQL; retain the earlier unsupported-attribute error."""
from metadata_inventory import OUT, NOW, connect_neon, save, sanitized_error
import json

if (OUT / "client-tls-readback-final.json").exists():
    raise SystemExit("Final TLS readback already exists; preserve it")
record = {"startedAt": NOW(), "sqlStatements": 0, "remoteWrites": [],
    "previousFailure": "client-tls-readback.json retained: unsupported ssl_attribute_names capture; no conclusion about TLS from that helper failure"}
connection = None
try:
    connection = connect_neon()
    parameters = connection.info.get_parameters()
    record["clientSslInUse"] = connection.pgconn.ssl_in_use
    record["parameters"] = {k: parameters.get(k) for k in ["host", "dbname", "sslmode", "sslrootcert"]}
    record["status"] = "pass" if record["clientSslInUse"] and parameters.get("sslmode") == "verify-full" else "fail"
except Exception as error:
    record.update(status="blocked", errorType=type(error).__name__, error=sanitized_error(error))
finally:
    if connection is not None:
        connection.close()
    record["finishedAt"] = NOW()
    save("client-tls-readback-final.json", record)
print(json.dumps(record))
