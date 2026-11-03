#!/usr/bin/env python3
"""Read-only public availability probe; writes an inspectable receipt even on failure."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import urllib.error
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument("--origin", default="https://statarena-analytics.vercel.app")
parser.add_argument("--output", default="availability.json")
args = parser.parse_args()
checks = []
for route in ("/api/health", "/data/dashboard-manifest.json"):
    url = args.origin.rstrip("/") + route
    item = {"url": url, "expectedStatus": 200}
    request = urllib.request.Request(url, headers={"Cache-Control": "no-cache"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            item.update(status=response.status, body=response.read(8192).decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as error:
        item.update(status=error.code, body=error.read(8192).decode("utf-8", errors="replace"))
    except Exception as error:
        item.update(status=None, error=str(error))
    item["passed"] = item["status"] == 200
    checks.append(item)
report = {
    "checkedAt": datetime.now(timezone.utc).isoformat(),
    "setup": "Real public origin; read-only HTTPS GET requests with Cache-Control:no-cache; no mocks.",
    "inputs": {"origin": args.origin, "routes": ["/api/health", "/data/dashboard-manifest.json"], "timeoutSeconds": 30},
    "rerun": "python3 docs/verification/rematerialization-completion-20261103/quota-incident/check_availability.py --output /tmp/statarena-availability.json",
    "expected": "Both routes return HTTP 200.",
    "checks": checks,
    "passed": all(item["passed"] for item in checks),
}
output = Path(args.output)
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
print(json.dumps(report, ensure_ascii=False, indent=2))
raise SystemExit(0 if report["passed"] else 1)
