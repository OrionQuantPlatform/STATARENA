"""Rebuild derived tables and model totals from the saved read-only snapshot."""
import collections
import csv
import json
from pathlib import Path
import re

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
inventory = json.loads((OUT / "databases.json").read_text())
migrations = {}
for path in sorted((ROOT / "dashboard/backend/migrations").glob("*.sql")):
    for schema, name in re.findall(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)\.(\w+)", path.read_text(), re.I):
        if schema == "statarena_app":
            migrations.setdefault(name, path.name)

db = inventory["databases"]["statarena_prod"]
schemas = collections.Counter()
classes = {}
for relation in db["relations"]:
    if relation["kind"] not in ("r", "p", "m"):
        continue
    schema, name = relation["schema"], relation["name"]
    schemas[schema] += relation["totalBytes"]
    group = schema if schema != "statarena_app" else migrations.get(name, "worker metadata / not declared in versioned DDL")
    bucket = classes.setdefault(group, {"tables": 0, "bytes": 0, "names": []})
    bucket["tables"] += 1
    bucket["bytes"] += relation["totalBytes"]
    bucket["names"].append(name)

entities = {}
for name in ("players", "teams", "matches", "fixtures", "competitions", "competition_seasons", "appearances", "match_players"):
    entities[name] = {
        "schema": "statarena_app",
        "columns": [{"name": c["column"], "type": c["nativeType"]}
                    for c in db["columns"] if c["schema"] == "statarena_app" and c["table"] == name],
        "constraints": [c for c in db["constraints"] if c["schema"] == "statarena_app" and c["table"] == name],
    }
report = {
    "atUtc": inventory["atUtc"],
    "command": "python3 docs/verification/aws-architecture-audit-20261104/summarize_inventory.py",
    "schemaPhysicalTotals": dict(schemas), "migrationClasses": classes, "entities": entities,
    "servingDocumentColumns": [c for c in db["columns"] if c["schema"] == "statarena_app" and c["nativeType"] in ("json", "jsonb", "bytea")],
    "storageRatios": {
        "fileDocumentsShareOfDbPercent": 100 * next(r["totalBytes"] for r in db["relations"] if r["schema"] == "statarena" and r["name"] == "file_documents") / db["bytes"],
        "stagingShareOfUserRelationsPercent": 100 * schemas["statarena"] / sum(schemas.values()),
    },
    "limits": "Table allocation includes indexes and TOAST; approximate row estimates are separate from exact counts. Sources and business rows are not reconciled by this local derivation. Entity columns/keys are scoped to statarena_app, avoiding identically named staging tables.",
}
(OUT / "model-analysis.json").write_text(json.dumps(report, indent=2) + "\n")
with (OUT / "tables.csv").open("w", newline="") as output:
    writer = csv.writer(output)
    writer.writerow(["database", "schema", "table", "kind", "approx_rows", "total_bytes", "created_by_migration"])
    for database, data in inventory["databases"].items():
        for relation in data["relations"]:
            writer.writerow([database, relation["schema"], relation["name"], relation["kind"], relation["rowsEstimate"], relation["totalBytes"], migrations.get(relation["name"], "") if relation["schema"] == "statarena_app" else ""])
print(json.dumps({"schemaPhysicalTotals": dict(schemas), "storageRatios": report["storageRatios"], "servingDocumentColumns": len(report["servingDocumentColumns"])}))
