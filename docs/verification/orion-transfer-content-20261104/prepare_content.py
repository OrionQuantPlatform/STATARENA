"""Prepare exact-version content scope and SQL; no remote access or body read."""
import datetime
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
OLD = ROOT / "docs/verification/orion-transfer-inventory-20261104"
MODEL = ROOT / "docs/architecture/orion-plan-20261104/target-schema.proposed.json"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
inventory = json.loads((OLD / "inventory.json").read_text())
assert sha(OLD / "inventory.json") == "03efac383d4c9bfdaedb483f13b2b1159636d657327fe9d15ba8a1e99d1fe4b3"
assert sha(MODEL) == "18da43f940870b7a3a3cb49323c847dd5e5174e5eea1f8ff0c8a159cf373cb08"
objects = {(source, row["key"]["path"]): row[source] for row in inventory["objects"]["rows"] for source in ["neon", "aws"] if row[source]}
selected = {("neon", row["key"]["path"]) for row in inventory["objects"]["rows"] if row["classification"] == "absent_in_aws"}
pairs = []
for row in inventory["resources"]["rows"]:
    if row["classification"] == "different_version_order_unverified":
        pairs.append({"kind": "resource", "key": row["key"], "neonPath": row["neon"]["ref_path"], "awsPath": row["aws"]["ref_path"]})
        selected.update((source, row[source]["ref_path"]) for source in ["neon", "aws"])
selected.update((source, "computed/dashboard/index.json") for source in ["neon", "aws"])
pairs.append({"kind": "manifest", "key": {"path": "computed/dashboard/index.json"}, "neonPath": "computed/dashboard/index.json", "awsPath": "computed/dashboard/index.json"})
targets = []
for source, path in sorted(selected):
    metadata = objects[(source, path)]
    selectors = [row[source] for row in inventory["resources"]["rows"] if row[source] and row[source]["ref_path"] == path]
    targets.append({"source": source, "path": path, "expectedPhysicalSha256": metadata["sha256"], "expectedPhysicalBytes": metadata["size"],
        "selectors": [{k: selector[k] for k in ["endpoint", "params", "status", "ref_path", "ref_ordinal"]} for selector in selectors],
        "kind": "manifest" if path == "computed/dashboard/index.json" else "observation"})
assert len(targets) == 14
limits = {"sqlInstructionsMaximum": 18, "sqlInstructionsNominal": 8, "decodedBytesMaximum": 33554432,
    "physicalObjectBytesMaximum": 2097152, "decodedObjectBytesMaximum": 8388608,
    "statementTimeoutMs": 8000, "lockTimeoutMs": 1000, "connectionsAtATime": 1}
scope = {"preparedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(), "previousInventoryCommit": "eab371a87c",
    "previousInventorySha256": sha(OLD / "inventory.json"), "modelSha256": sha(MODEL), "limits": limits,
    "targets": targets, "pairs": pairs, "advertisedPhysicalBytes": sum(t["expectedPhysicalBytes"] for t in targets),
    "noRemoteImport": True, "noBodyPersistence": True, "noProviderCalls": True}
(OUT / "scope-and-budget.json").write_text(json.dumps(scope, ensure_ascii=False, indent=2) + "\n")
(OUT / "protected-before.json").write_text(json.dumps({str(p.relative_to(ROOT)): sha(p) for p in sorted(OLD.rglob('*')) if p.is_file()}, indent=2) + "\n")
print(json.dumps({"targets": len(targets), "perSource": {source: sum(t['source'] == source for t in targets) for source in ['neon','aws']}, "physicalAdvertisedBytes": scope['advertisedPhysicalBytes'], "limits": limits}))
