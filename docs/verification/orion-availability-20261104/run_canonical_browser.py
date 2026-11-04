"""Canonical desktop/mobile acceptance with exact saved setup and cleanup."""
from pathlib import Path
import datetime as dt
import json
import subprocess
HERE=Path(__file__).resolve().parent
CLI="/Users/lemonnierhugo/.codex/skills/playwright/scripts/playwright_cli.sh"
CONFIG=HERE.parent/"rematerialization-completion-20261103/cli-headless.config.json"
URL="https://statarena-analytics.vercel.app/?season=2026%2F2027&focus=europe&league=l_3FJFUl"
def cli(*args):return subprocess.run([CLI,"-s=orion-live-canonical",*args],capture_output=True,text=True,timeout=150,cwd=HERE)
r={"atUtc":dt.datetime.now(dt.timezone.utc).isoformat(),"command":"python3 docs/verification/orion-availability-20261104/run_canonical_browser.py","setup":"Canonical alias after promotion, actual deployed build, desktop1600x1000 and historicmobile390x844. Existing production data; no shim.","inputs":{"url":URL,"workflow":"canonical_browser_e2e.js"},"expected":"Current desktop and historicalmobile display saved data without horizontaloverflow.","passed":False}
try:
    opened=cli("open",URL,"--config="+str(CONFIG));(HERE/"canonical-browser-open.log").write_text(opened.stdout+opened.stderr)
    if opened.returncode:raise RuntimeError("Browser could not open")
    code=(HERE/"canonical_browser_e2e.js").read_text().replace("async (page) => {","async (page) => {\nconst SCREEN="+json.dumps(str(HERE/"canonical-browser"))+";",1)
    run=cli("run-code",code);(HERE/"canonical-browser.log").write_text(run.stdout+run.stderr)
    marker="### Result\n"
    if marker not in run.stdout:raise RuntimeError("No browser result")
    d,_=json.JSONDecoder().raw_decode(run.stdout.split(marker,1)[1]);r.update(d)
except Exception as e:r["error"]=str(e)
finally:
    close=cli("close");(HERE/"canonical-browser-close.log").write_text(close.stdout+close.stderr)
    (HERE/"canonical-browser.json").write_text(json.dumps(r,indent=2)+"\n");print(json.dumps(r))
raise SystemExit(not r["passed"])
