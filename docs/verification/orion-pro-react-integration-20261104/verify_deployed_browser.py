"""Run the established saved-data UI workflows on the bound Vercel candidate."""
import datetime as dt
import hashlib
import json
from pathlib import Path
import subprocess
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASELINE = HERE.parent / "orion-availability-20261104"
receipt_path = HERE / "deployments/candidate-74ea3f76de.json"
receipt = json.loads(receipt_path.read_text())
deployment = receipt["deployment"]
assert deployment["project"]["id"] == "prj_DhaqrVkH3Gi4uysT7IRsm9fB2bjR"
assert deployment["meta"]["githubCommitSha"] == "74ea3f76de622315cb3df787c3c748bc73357e60"
assert deployment["target"] == "production" and deployment["state"] == "READY"
origin = "https://" + deployment["url"]
url = urlsplit(origin)
assert url.hostname and url.hostname.endswith(".vercel.app") and not url.username and not url.query
assert subprocess.run(["which", "npx"], capture_output=True).returncode == 0
run = HERE / "output/playwright" / (dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-vercel-candidate")
run.mkdir(parents=True)
cli_path = "/Users/lemonnierhugo/.codex/skills/playwright/scripts/playwright_cli.sh"
config = HERE.parent / "rematerialization-completion-20261103/cli-headless.config.json"
report = {
    "command": "python3 docs/verification/orion-pro-react-integration-20261104/verify_deployed_browser.py",
    "setup": "Bound real staged production deployment, existing saved-data bridge; no local server, football mock, source collection or environment change. Optional external image/telemetry requests blocked; exact deployment host allowed.",
    "expected": "Established twelve complete desktop/mobile saved-data UI workflows pass without application exceptions.",
    "deployment": deployment, "receiptSha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
    "status": "failed",
}
def cli(name, *args):
    result = subprocess.run([cli_path, "-s=orion-react-candidate-74ea", *args], cwd=ROOT, capture_output=True, text=True, timeout=240)
    (run / (name + ".log")).write_text(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError("Browser CLI step failed: " + name)
    return result.stdout
try:
    cli("open", "open", "about:blank", "--config=" + str(config))
    setup = "async (page) => { const BASE=" + json.dumps(origin) + "; await page.route('**/*',r=>new URL(r.request().url()).origin===BASE?r.continue():r.abort()); await page.goto(BASE+'/?season=2026%2F2027&focus=europe&league=l_3FJFUl'); await page.locator('.home-motw').waitFor({timeout:60000}); return {url:page.url()}; }"
    cli("grounded-initial-page", "run-code", setup)
    cli("initial-snapshot", "snapshot")
    source = (BASELINE / "bridge_browser_e2e.js").read_text()
    report["workflowOriginalSha256"] = hashlib.sha256(source.encode()).hexdigest()
    assert source.count('u.hostname==="127.0.0.1"') == 2
    source = source.replace('u.hostname==="127.0.0.1"', 'u.hostname===new URL(BASE).hostname')
    source = source.replace("Current Next frontend against the local legacy compatibility bridge and existing Neon saved data. Browser network restricted to localhost.", "Real staged Vercel frontend and existing saved Neon data. No local football shim; browser network restricted to exact deployment host.")
    code = "async (page) => {\nconst BASE=" + json.dumps(origin) + ";\nconst ARTIFACT_PREFIX=" + json.dumps(str(run / "workflow")) + ";\n" + source + "\n}"
    (run / "executed-workflow.js").write_text(code)
    output = cli("workflow", "run-code", code)
    marker = "### Result\n"
    if marker not in output:
        raise RuntimeError("No structured browser result")
    actual, _ = json.JSONDecoder().raw_decode(output.split(marker, 1)[1])
    report.update(actual)
    cli("final-snapshot", "snapshot")
except Exception as error:
    report["error"] = {"type": type(error).__name__, "message": str(error)}
finally:
    try:
        cli("close", "close")
        report["browserClosed"] = True
    except Exception as error:
        report["browserClosed"] = False
        report["cleanupError"] = str(error)
        report["status"] = "failed"
    report["limits"] = ["Representative twelve workflows; not all rows/assets or source fidelity", "Existing legacy bridge is exercised, not new typed SQL activation", "Warm initial browser navigation; no latency speedup measured"]
    report["finishedAtUtc"] = dt.datetime.now(dt.timezone.utc).isoformat()
    (run / "result.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"result": str(run / "result.json"), "status": report["status"], "checks": len(report.get("checks", [])), "error": report.get("error")}))
raise SystemExit(report["status"] != "passed")
