"""Exercise the real immutable Vercel build with the same UI workflows, no shim."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import subprocess
from urllib.parse import urlsplit

p=argparse.ArgumentParser();p.add_argument("url");args=p.parse_args()
u=urlsplit(args.url)
if u.scheme!="https" or not u.hostname or not u.hostname.startswith("statarena-analytics-") or not u.hostname.endswith(".vercel.app") or u.path not in ("","/") or u.query or u.fragment or u.username:p.error("expected immutable StatArena Vercel deployment origin")
HERE=Path(__file__).resolve().parent
CLI="/Users/lemonnierhugo/.codex/skills/playwright/scripts/playwright_cli.sh"
CONFIG=HERE.parent/"rematerialization-completion-20261103/cli-headless.config.json"
prefix=HERE/("vercel-browser-"+dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
report={"command":["python3","docs/verification/orion-availability-20261104/run_deployed_browser.py",args.url],"setup":"Real staged production Vercel URL and its existing server-side Neon credentials. No local server, shim, provider collection or env change. Browser network confined to this exact deployment host; optional external images/telemetry blocked.","expected":"Same12 UI workflows pass on actual NodeVercel runtime: current/historic data, match/player/scouting/club/competition/calendar/archives/ranking/method desktop/mobile. No page exceptions.","status":"failed"}
def cli(*a):return subprocess.run([CLI,"-s=orion-live-stage",*a],cwd=HERE,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=240)
try:
    source=(HERE/"bridge_browser_e2e.js").read_text();report["browserWorkflowSha256"]=hashlib.sha256(source.encode()).hexdigest()
    assert source.count('u.hostname==="127.0.0.1"')==2
    source=source.replace('u.hostname==="127.0.0.1"','u.hostname===new URL(BASE).hostname')
    source=source.replace('Current Next frontend against the local legacy compatibility bridge and existing Neon saved data. Browser network restricted to localhost.','Real staged Vercel current frontend and saved Neon data; no local shim. Network restricted to the exact deployment host.')
    opened=cli("open","about:blank","--config="+str(CONFIG));Path(str(prefix)+"-open.log").write_text(opened.stdout)
    if opened.returncode:raise RuntimeError("Browser could not open")
    code="async (page) => {\nconst BASE="+json.dumps(args.url.rstrip("/"))+";\nconst ARTIFACT_PREFIX="+json.dumps(str(prefix))+";\n"+source+"\n}"
    run=cli("run-code",code);Path(str(prefix)+"-run.log").write_text(run.stdout)
    marker="### Result\n"
    if marker not in run.stdout:raise RuntimeError("Browser returned no evidence")
    data,_=json.JSONDecoder().raw_decode(run.stdout.split(marker,1)[1]);report.update(data)
except Exception as error:report["error"]=type(error).__name__+": "+str(error)
finally:
    close=cli("close");Path(str(prefix)+"-close.log").write_text(close.stdout)
    report["limits"]=["Representative12workflows, not every row/asset/route permutation.","External images/telemetry blocked; data/UI contract acceptance only."]
    artifact=Path(str(prefix)+".json");artifact.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({"artifact":str(artifact),"status":report.get("status"),"error":report.get("error"),"checks":report.get("checks")},ensure_ascii=False))
raise SystemExit(report.get("status")!="passed")
