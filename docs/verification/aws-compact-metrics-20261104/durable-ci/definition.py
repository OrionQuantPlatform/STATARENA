import json, sys
from fnmatch import fnmatchcase
from pathlib import Path
import yaml

here = Path(__file__).resolve().parent
root = here.parents[3]
suite = "docs/verification/aws-compact-metrics-20261104"
workflow = yaml.safe_load((root / ".github/workflows/verify-ingestion.yml").read_text())
events = workflow.get("on", workflow.get(True, {}))
job = workflow["jobs"]["relational"]
steps = job["steps"]
checks = {
    "both events trigger on suite": all(
        any(fnmatchcase(suite + "/run.mjs", pattern) for pattern in events[k]["paths"])
        for k in ("push", "pull_request")
    ),
    "suite captured by sparse checkout": any(
        suite in s.get("with", {}).get("sparse-checkout", "").splitlines()
        for s in steps
    ),
    "actual 009 suite executes": any(
        "node " + suite + "/run.mjs ci" in s.get("run", "") for s in steps
    ),
    "always uploads new receipt": any(
        s.get("if") == "always()"
        and suite + "/ci/" in s.get("with", {}).get("path", "")
        for s in steps
    ),
    "job bounded and local": job.get("timeout-minutes") == 10
    and "id-token" not in job.get("permissions", {})
    and "secrets." not in str(job),
    "four durable inputs and manifest": all(
        (root / suite / "inputs" / n).is_file()
        for n in [
            "half_stat_groups.tsv.gz",
            "half_stat_metrics.tsv.gz",
            "player_stat_groups.tsv.gz",
            "player_stat_metrics.tsv.gz",
            "manifest.json",
        ]
    ),
}
r = {
    "command": "python3 " + suite + "/durable-ci/definition.py " + sys.argv[1],
    "expected": "all controls present",
    "checks": checks,
    "passed": sum(checks.values()),
    "total": len(checks),
}
(here / (sys.argv[1] + ".json")).write_text(json.dumps(r, indent=2) + "\n")
print(r["passed"], r["total"])
sys.exit(not all(checks.values()))

