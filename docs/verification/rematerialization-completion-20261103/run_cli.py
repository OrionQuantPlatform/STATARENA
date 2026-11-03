"""Run an inspectable Playwright CLI snippet without shell interpolation."""
from pathlib import Path
import subprocess
import sys
import json
from datetime import datetime, timezone

folder = Path(__file__).resolve().parent
name = sys.argv[1]
options = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
script = "async (page) => {\nconst TEST_OPTIONS = " + json.dumps(options) + ";\n" + (folder / (name + ".js")).read_text() + "\n}"
result = subprocess.run(
    ["/Users/lemonnierhugo/.codex/skills/playwright/scripts/playwright_cli.sh", "-s=statarena-production", "run-code", script],
    cwd=folder,
    text=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
)
stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
log = folder / (name + "-" + stamp + ".log")
log.write_text(result.stdout)
marker = "### Result\n"
if marker not in result.stdout:
    print(result.stdout)
    raise SystemExit(result.returncode or 1)
report, _ = json.JSONDecoder().raw_decode(result.stdout.split(marker, 1)[1])
(folder / (name + "-" + stamp + ".json")).write_text(json.dumps(report, indent=2, ensure_ascii=False)+"\n")
print(json.dumps({"log":str(log),"report":report},indent=2,ensure_ascii=False))
raise SystemExit(result.returncode or (1 if report.get("status") == "failed" else 0))
