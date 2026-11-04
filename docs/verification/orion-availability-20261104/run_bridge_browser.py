"""Run the current frontend in a temporary checkout against a local read-only bridge."""
import datetime as dt
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
CLI="/Users/lemonnierhugo/.codex/skills/playwright/scripts/playwright_cli.sh"
CONFIG=HERE.parent/"rematerialization-completion-20261103/cli-headless.config.json"
stamp=dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
prefix=HERE/("bridge-browser-"+stamp)
report={"command":"python3 docs/verification/orion-availability-20261104/run_bridge_browser.py",
        "setup":"Temporary copy of the current Next frontend running its Vercel branch; local test shims relay only the old immutable Neon-backed deployment. No production alias/configuration changes or football-provider calls.",
        "expected":"The current UI renders home, match, player, club, competition, ranking/scouting and historic mobile paths with saved data.","status":"failed"}
processes=[]


def port():
    with socket.socket() as s:
        s.bind(("127.0.0.1",0));return s.getsockname()[1]


def spawn(args,env,log,cwd):
    stream=open(log,"w");p=subprocess.Popen(args,cwd=cwd,env=env,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
    processes.append((p,stream));return p


def wait_http(url,seconds=55):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        try:
            with urllib.request.urlopen(url,timeout=3) as r:
                if r.status==200:return
        except Exception:time.sleep(.25)
    raise RuntimeError("Local service did not become ready: "+url)


def cli(*args):
    return subprocess.run([CLI,"-s=orion-bridge-ui",*args],cwd=HERE,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)


try:
  with tempfile.TemporaryDirectory(prefix="statarena-bridge-ui-") as tmp:
    dst=Path(tmp)/"dashboard";front=dst/"frontend";front.mkdir(parents=True)
    for part in ("src","app","public"):shutil.copytree(ROOT/"dashboard/frontend"/part,front/part)
    for part in ("package.json","next.config.mjs"):shutil.copy2(ROOT/"dashboard/frontend"/part,front/part)
    shutil.copytree(ROOT/"dashboard/shared",dst/"shared");shutil.copytree(ROOT/"dashboard/backend",dst/"backend")
    shutil.copy2(ROOT/"dashboard/package.json",dst/"package.json");os.symlink(ROOT/"dashboard/node_modules",dst/"node_modules")
    # The checkout declares flag-icons@7.6.0 but its installed node_modules lacks it.
    # Install only that package inside the temporary frontend, never the workspace.
    flags=front/"node_modules/flag-icons";flags.mkdir(parents=True)
    packed=subprocess.run(["npm","pack","flag-icons@7.6.0","--pack-destination",tmp],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=90)
    Path(str(prefix)+"-dependency.log").write_text(packed.stdout)
    if packed.returncode:raise RuntimeError("Temporary flag-icons package unavailable")
    archive=next(Path(tmp).glob("flag-icons-7.6.0.tgz"))
    subprocess.run(["tar","-xzf",str(archive),"--strip-components=1","-C",str(flags)],check=True)
    adapter_port,front_port=port(),port()
    (dst/"backend/legacy-app.js").write_text("export async function handleRequest(req) { const u=new URL(req.url); const p=new URLSearchParams({path:u.pathname+u.search}); return fetch('http://127.0.0.1:"+str(adapter_port)+"/__legacy?'+p,{method:req.method,headers:req.headers}); }\n")
    (dst/"backend/services/data-store.js").write_text("export async function dataJson(path) { const p=new URLSearchParams({path}); const r=await fetch('http://127.0.0.1:"+str(adapter_port)+"/__object?'+p); if(!r.ok) { const e=Error('Saved object unavailable'); e.code=r.status===404?'ENOENT':'UPSTREAM'; throw e; } return r.json(); }\n")
    env=os.environ.copy()
    for key in ("NEXT_PUBLIC_API_ORIGIN","VERCEL","DATABASE_URL","STATARENA_DATA_PROVIDER"):env.pop(key,None)
    env.update(ORION_BRIDGE_TEST_PORT=str(adapter_port),NEXT_TELEMETRY_DISABLED="1")
    spawn(["bun",str(HERE/"bridge_local_server.mjs")],env,str(prefix)+"-adapter.log",ROOT)
    wait_http(f"http://127.0.0.1:{adapter_port}/api/dashboard/manifest")
    env.update(VERCEL="1")
    spawn(["node",str(dst/"node_modules/next/dist/bin/next"),"dev","frontend","--webpack","--hostname","127.0.0.1","--port",str(front_port)],env,str(prefix)+"-next.log",dst)
    wait_http(f"http://127.0.0.1:{front_port}/")
    opened=cli("open","about:blank","--config="+str(CONFIG));Path(str(prefix)+"-open.log").write_text(opened.stdout)
    if opened.returncode:raise RuntimeError("Playwright failed to open")
    try:
      code="async (page) => {\nconst BASE="+json.dumps(f"http://127.0.0.1:{front_port}")+";\nconst ARTIFACT_PREFIX="+json.dumps(str(prefix))+";\n"+(HERE/"bridge_browser_e2e.js").read_text()+"\n}"
      result=cli("run-code",code);Path(str(prefix)+"-run.log").write_text(result.stdout)
      marker="### Result\n"
      if marker not in result.stdout:raise RuntimeError("Playwright did not return a report")
      value,_=json.JSONDecoder().raw_decode(result.stdout.split(marker,1)[1]);report.update(value)
    finally:
      closed=cli("close");Path(str(prefix)+"-close.log").write_text(closed.stdout)
except Exception as error:report["error"]=type(error).__name__+": "+str(error)
finally:
  for process,stream in reversed(processes):
    try:os.killpg(process.pid,signal.SIGTERM)
    except ProcessLookupError:pass
    try:process.wait(timeout=5)
    except subprocess.TimeoutExpired:
      try:os.killpg(process.pid,signal.SIGKILL)
      except ProcessLookupError:pass
      process.wait()
    stream.close()
  path=Path(str(prefix)+".json");path.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
  print(json.dumps({"status":report.get("status"),"error":report.get("error"),"artifact":str(path),"checks":report.get("checks")},ensure_ascii=False))
raise SystemExit(report.get("status")!="passed")
