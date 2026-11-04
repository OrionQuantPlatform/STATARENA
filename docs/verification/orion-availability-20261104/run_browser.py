"""Run the old deployment's bounded read-only browser flow using Playwright CLI."""
import datetime as dt
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
CLI = "/Users/lemonnierhugo/.codex/skills/playwright/scripts/playwright_cli.sh"
CONFIG = HERE.parent / "rematerialization-completion-20261103/cli-headless.config.json"
SESSION = "orion-availability-e2e"
stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
prefix = HERE / ("browser-e2e-" + stamp)


def invoke(*args):
    return subprocess.run([CLI, "-s=" + SESSION, *args], cwd=HERE, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=100)


opened = invoke("open", "about:blank", "--config=" + str(CONFIG))
(HERE / ("browser-e2e-open-" + stamp + ".log")).write_text(opened.stdout)
if opened.returncode:
    print(json.dumps({"status":"failed", "phase":"open", "log":str(HERE / ("browser-e2e-open-" + stamp + ".log"))}))
    raise SystemExit(opened.returncode)
try:
    code = "async (page) => {\nconst ARTIFACT_PREFIX = " + json.dumps(str(prefix)) + ";\n" + (HERE / "browser_e2e.js").read_text() + "\n}"
    result = invoke("run-code", code)
    (HERE / ("browser-e2e-run-" + stamp + ".log")).write_text(result.stdout)
    marker = "### Result\n"
    if marker not in result.stdout:
        print(json.dumps({"status":"failed","phase":"run","log":str(HERE / ("browser-e2e-run-" + stamp + ".log"))}))
        raise SystemExit(result.returncode or 1)
    report, _ = json.JSONDecoder().raw_decode(result.stdout.split(marker,1)[1])
    (HERE / ("browser-e2e-" + stamp + ".json")).write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({"status":report.get("status"),"error":report.get("error"),"artifact":str(HERE / ("browser-e2e-" + stamp + ".json")),"checks":report.get("checks")},ensure_ascii=False))
    exit_code = result.returncode or (report.get("status") != "passed")
finally:
    closed = invoke("close")
    (HERE / ("browser-e2e-close-" + stamp + ".log")).write_text(closed.stdout)
raise SystemExit(exit_code)
