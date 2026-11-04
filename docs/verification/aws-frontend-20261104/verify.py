import json, os, subprocess, sys, tempfile, urllib.request
from pathlib import Path

here = Path(__file__).resolve().parent
root = here.parents[2]
phase = sys.argv[1]
if phase not in ("red", "green", "catalog-red"):
    raise SystemExit(2)
wrapper = Path.home() / ".codex/skills/playwright/scripts/playwright_cli.sh"
prefix = [str(wrapper), "-s=statarena-aws-loaders"]
config = (
    root
    / "docs/verification/rematerialization-completion-20261103/cli-headless.config.json"
)
report = {
    "command": "python3 docs/verification/aws-frontend-20261104/verify.py " + phase
}
with tempfile.TemporaryDirectory() as d:
    server = subprocess.Popen(
        ["bun", str(here / "server.mjs")], stdout=subprocess.PIPE, text=True, cwd=root
    )
    try:
        url = server.stdout.readline().strip()
        if not url.startswith("http://127.0.0.1:"):
            raise ValueError("fixture startup failed")
        subprocess.run(
            [*prefix, "open", url, "--config", str(config)],
            cwd=d,
            capture_output=True,
            check=True,
            timeout=75,
        )
        js = "async page=>{await page.waitForFunction(()=>window.result);return await page.evaluate(()=>window.result)}"
        res = subprocess.run(
            [*prefix, "run-code", js],
            cwd=d,
            capture_output=True,
            text=True,
            timeout=50,
            check=True,
        )
        report["browserLog"] = res.stdout
        report["console"] = [line for log in Path(d).glob(".playwright-cli/console-*.log") for line in log.read_text().splitlines()]
        report.update(json.load(urllib.request.urlopen(url + "/trace")))
        report["passed"] = (
            '"ok":true' in res.stdout.replace(" ", "")
            and not report["bad"]
            and report["starts"] == 3
        )
    except Exception as e:
        report.update(error=str(e), passed=False)
    finally:
        subprocess.run([*prefix, "close"], cwd=d, capture_output=True, timeout=40)
        server.terminate()
        server.wait()
(here / (phase + ".json")).write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report))
sys.exit(0 if report["passed"] else 1)
