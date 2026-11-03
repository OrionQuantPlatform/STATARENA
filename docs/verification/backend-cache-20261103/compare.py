"""Rebuild the descriptive before/after artifact; no production access."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
before = json.loads((HERE / "before-final/results.json").read_text())
after = json.loads((HERE / "after-final/results.json").read_text())
keys = ["sql_count", "sql_body_bytes", "sql_json_rows", "object_bytes", "gzip_bytes", "parse_bytes"]


def observations(report, name, last=None):
    groups = [x["rows"] for x in report["observations"] if x["scenario"] == name]
    if last:
        groups = groups[-last:]
    return [row for group in groups for row in group]


def metrics(report, name, last=None):
    rows = observations(report, name, last)
    return {key: sum(row.get("metrics", {}).get(key, 0) for row in rows) for key in keys}


names = [
    ("cold inline bytes", None),
    ("304 after metadata expiry", None),
    ("retained body after metadata expiry", None),
    ("parsed version retained after expiry", 1),
    ("projection HEAD avoids JSON bodies", None),
    ("1/5/20 concurrent public reads", 3),
]
before_paths = [(x["path"], x["method"]) for x in before["requests"]]
after_paths = [(x["path"], x["method"]) for x in after["requests"] if not x["scenario"].startswith("Next production")]
result = {
    "command": "python3 docs/verification/backend-cache-20261103/compare.py",
    "scope": "Same local deterministic PostgreSQL/S3 fixtures; source-body bytes, not provider wire egress or production latency.",
    "same_http_workload_excluding_extra_next_checks": before_paths == after_paths,
    "before_requests": len(before_paths),
    "after_comparable_requests": len(after_paths),
    "before_scenarios": len(before["checks"]),
    "before_unmet_assertions": [x["name"] for x in before["checks"] if x["status"] != "passed"],
    "after_scenarios": len(after["checks"]),
    "after_passed": after["status"] == "passed",
    "comparisons": [{"scenario": name, "before": metrics(before, name, last), "after": metrics(after, name, last)} for name, last in names],
    "limits": [
        "Baseline has expected failed acceptance assertions; new error telemetry and the bounded repeated-publication behavior are new requirements, not all old product defects.",
        "Cold inline reads add one SQL query; no latency win is inferred from this tiny local workload.",
        "Continuous inline writes fail closed after two attempts; original one-query inline reads could return an older valid snapshot.",
        "Two extra Next production transport checks run only on the corrected build.",
    ],
}
(HERE / "comparison.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
