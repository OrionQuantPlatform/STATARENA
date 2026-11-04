"""Check the CI contract without requiring infrastructure or credentials."""
import json
import sys
from pathlib import Path

import yaml

base = Path(__file__).resolve().parent
workflow = yaml.safe_load((base.parents[2] / ".github/workflows/verify-ingestion.yml").read_text())
job = workflow["jobs"]["relational"]
events = workflow.get("on", workflow.get(True, {}))
steps = job["steps"]
suite = "docs/verification/aws-wire-pages"
command = f"bun {suite}/disposable.mjs --ci"
checks = {
    "wire sources and harness trigger both events": all(
        target in events[event]["paths"]
        for event in ("push", "pull_request")
        for target in ("dashboard/frontend/src/packed_data.js", "dashboard/frontend/src/season_data.js",
                       "dashboard/backend/**", suite + "/disposable.mjs")
    ),
    "harness is in the sparse checkout": any(suite in s.get("with", {}).get("sparse-checkout", "").splitlines() for s in steps),
    "real compact HTTP workflow executes": any(s.get("run") == command for s in steps),
    "fresh CI receipts uploaded even on failure": any(s.get("if") == "always()" and
        "upload-artifact" in s.get("uses", "") and job["env"]["STATARENA_CI_EVIDENCE"] + "/"
        in s["with"]["path"].splitlines() for s in steps),
}
report = {"command": f"python3 {suite}/ci_definition.py {sys.argv[1]}",
          "expected": "all four durable controls pass", "checks": checks, "passed": all(checks.values())}
(base / ("ci-definition-" + sys.argv[1] + ".json")).write_text(json.dumps(report, indent=2) + "\n")
print(report)
sys.exit(not report["passed"])
