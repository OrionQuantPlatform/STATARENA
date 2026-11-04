"""Read the promoted canonical site with the existing desktop/mobile workflow."""
from pathlib import Path
import datetime as dt
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent
BASELINE = HERE.parent / "orion-availability-20261104"
run = HERE / "output/playwright" / (dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-canonical")
run.mkdir(parents=True)
cli = "/Users/lemonnierhugo/.codex/skills/playwright/scripts/playwright_cli.sh"
config = HERE.parent / "rematerialization-completion-20261103/cli-headless.config.json"
origin = "https://statarena-analytics.vercel.app"
report = {"atUtc": dt.datetime.now(dt.timezone.utc).isoformat(), "command": "python3 docs/verification/orion-pro-react-integration-20261104/verify_canonical_browser.py", "setup": "Promoted canonical alias, actual saved-data bridge, desktop1600x1000 and historical mobile390x844; no local football mock.", "expected": "Current desktop and historical mobile render data, correct season and no horizontal page overflow.", "passed": False}
def invoke(name, *args):
    result = subprocess.run([cli, "-s=orion-react-canonical-74ea", *args], capture_output=True, text=True, cwd=run, timeout=180)
    (run / (name + ".log")).write_text(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError("Browser step failed: " + name)
    return result.stdout
try:
    invoke("open", "open", origin + "/?season=2026%2F2027&focus=europe&league=l_3FJFUl", "--config=" + str(config))
    invoke("initial-snapshot", "snapshot")
    source = (BASELINE / "canonical_browser_e2e.js").read_text()
    report["workflowSha256"] = hashlib.sha256(source.encode()).hexdigest()
    source = source.replace("async (page) => {", "async (page) => {\nconst SCREEN=" + json.dumps(str(run / "canonical")) + ";", 1)
    (run / "executed-workflow.js").write_text(source)
    output = invoke("workflow", "run-code", source)
    marker = "### Result\n"
    if marker not in output:
        raise RuntimeError("No browser result")
    actual, _ = json.JSONDecoder().raw_decode(output.split(marker, 1)[1])
    report.update(actual)
except Exception as error:
    report["error"] = str(error)
finally:
    try:
        invoke("close", "close")
        report["browserClosed"] = True
    except Exception as error:
        report["browserClosed"] = False
        report["passed"] = False
        report["cleanupError"] = str(error)
    (run / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"result": str(run / "result.json"), "passed": report["passed"], "error": report.get("error")}))
raise SystemExit(not report["passed"])
