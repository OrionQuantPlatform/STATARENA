"""Real Playwright CLI acceptance using a previously saved public API and SQL receipt."""

import argparse, datetime as dt, json, subprocess, tempfile
from pathlib import Path
from urllib.parse import urlsplit

here = Path(__file__).resolve().parent
p = argparse.ArgumentParser()
p.add_argument("--frontend", required=True)
p.add_argument("--api-report", type=Path, required=True)
p.add_argument("--artifact", type=Path)
args = p.parse_args()
url = urlsplit(args.frontend)
if (
    not url.hostname
    or url.scheme != "https"
    or url.username
    or url.password
    or url.query
    or url.fragment
):
    p.error("supply the HTTPS production frontend origin")
api = json.loads(args.api_report.read_text())
if api.get("mode") != "production" or not api.get("stack", {}).get("ApiOrigin"):
    p.error("supply an actual production API receipt, not a fixture or preflight")
run = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
art = (args.artifact or here / ("ui-" + run)).resolve()
art.mkdir(parents=True, exist_ok=False)
config = here.parent / "rematerialization-completion-20261103/cli-headless.config.json"
pw = [
    str(Path.home() / ".codex/skills/playwright/scripts/playwright_cli.sh"),
    "-s=statarena-public-" + run[9:15],
]
opts = dict(
    frontend=args.frontend,
    api=api["stack"]["ApiOrigin"],
    selections=api.get("selections", {}),
    artifact=str(art),
)
source = (
    "async page=>{const OPTIONS="
    + json.dumps(opts)
    + ";\n"
    + (here / "ui.js").read_text()
    + "\n}"
)
report = dict(
    command=[
        "python3",
        "docs/verification/aws-production-20261104/verify_ui.py",
        "--frontend",
        args.frontend,
        "--api-report",
        str(args.api_report),
    ],
    start=run,
    production=opts,
)
with tempfile.TemporaryDirectory() as work:
    try:
        subprocess.run(
            [*pw, "open", "about:blank", "--config", str(config)],
            cwd=work,
            capture_output=True,
            check=True,
            timeout=70,
        )
        result = subprocess.run(
            [*pw, "run-code", source],
            cwd=work,
            capture_output=True,
            text=True,
            timeout=720,
        )
        if "### Result\n" not in result.stdout:
            raise RuntimeError(
                "Playwright did not return an evidence object: " + result.stdout[:350]
            )
        value, _ = json.JSONDecoder().raw_decode(
            result.stdout.split("### Result\n", 1)[1]
        )
        report.update(value)
    except Exception as e:
        report.update(passed=False, error=str(e)[:500])
    finally:
        subprocess.run([*pw, "close"], cwd=work, capture_output=True, timeout=40)
(art / "result.json").write_text(
    json.dumps(report, indent=2, ensure_ascii=False) + "\n"
)
print(
    json.dumps(
        dict(
            artifact=str(art),
            passed=report.get("passed"),
            views=len(report.get("views", [])),
            missing=report.get("missing", []),
            violations=len(report.get("violations", [])),
        )
    )
)
raise SystemExit(0 if report.get("passed") else 1)
