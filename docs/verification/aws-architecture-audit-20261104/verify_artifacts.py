"""Validate saved audit artifacts locally; this does not exercise the application."""
import ast
import datetime
import json
from pathlib import Path
import re

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
report = ROOT / "docs/AUDIT_ARCHITECTURE_2026-11-04.md"
parsed = []
for path in sorted(OUT.glob("*.json")):
    json.loads(path.read_text())
    parsed.append(path.name)
compiled = []
for path in OUT.glob("*.py"):
    ast.parse(path.read_text(), filename=str(path))
    compiled.append(path.name)
links = []
for path in (report, OUT / "README.md"):
    for target in re.findall(r"\]\(([^)]+)\)", path.read_text()):
        if target.startswith(("https://", "http://", "#")):
            continue
        links.append({"from": str(path.relative_to(ROOT)), "target": target,
                      "exists": (path.parent / target.split("#")[0]).exists()})
assert all(x["exists"] for x in links), links
db = json.loads((OUT / "databases.json").read_text())
model = json.loads((OUT / "model-analysis.json").read_text())
domain = json.loads((OUT / "domain-integrity.json").read_text())
s3 = json.loads((OUT / "s3.json").read_text())
assert not db["errors"] and all(not v["errors"] for v in db["databases"].values())
assert s3["complete"]
assert s3["objects"] == sum(v["objects"] for v in s3["classes"].values())
assert s3["bytes"] == sum(v["bytes"] for v in s3["classes"].values())
assert model["entities"]["fixtures"]["schema"] == "statarena_app"
assert len(model["entities"]["fixtures"]["columns"]) == 21
assert not model["servingDocumentColumns"]
assert not any("error" in x for x in domain["results"].values())
result = {
    "atUtc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "command": "python3 docs/verification/aws-architecture-audit-20261104/verify_artifacts.py",
    "setup": "Local saved audit snapshots, report and scripts only; no cloud connection or service change.",
    "expected": "Valid JSON/Python, resolved local Markdown links, complete S3 inventory with matching class totals and no inventory/domain-query execution errors. Architectural findings need not be zero.",
    "actual": {"jsonFilesParsed": parsed, "pythonFilesParsed": sorted(compiled),
               "localLinks": links, "domainQueryErrors": 0, "s3InventoryComplete": True},
    "passed": True,
    "limits": "Local artifact consistency only; not an application E2E, full source reconciliation or deployment validation.",
}
(OUT / "artifact-validation.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"passed": True, "jsonFiles": len(parsed), "pythonFiles": len(compiled), "links": len(links)}))
