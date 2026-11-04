"""Build the current frontend in a disposable checkout with the Vercel legacy route."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
stamp=dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
prefix=HERE/("bridge-build-"+stamp)
report={"command":"python3 docs/verification/orion-availability-20261104/run_bridge_build.py",
        "setup":"Disposable copy of current frontend/backend/shared source, existing node_modules through webpack, temporary flag-icons@7.6.0. VERCEL=1, AWS public origin absent, no production credentials or writes.",
        "expected":"Next production build includes the current UI and legacy compatibility route without deployment.","status":"failed"}
try:
  with tempfile.TemporaryDirectory(prefix="statarena-bridge-build-") as tmp:
    dst=Path(tmp)/"dashboard";front=dst/"frontend";front.mkdir(parents=True)
    for part in ("src","app","public"):shutil.copytree(ROOT/"dashboard/frontend"/part,front/part)
    for part in ("package.json","next.config.mjs"):shutil.copy2(ROOT/"dashboard/frontend"/part,front/part)
    shutil.copytree(ROOT/"dashboard/shared",dst/"shared");shutil.copytree(ROOT/"dashboard/backend",dst/"backend")
    shutil.copy2(ROOT/"dashboard/package.json",dst/"package.json");os.symlink(ROOT/"dashboard/node_modules",dst/"node_modules")
    flags=front/"node_modules/flag-icons";flags.mkdir(parents=True)
    packed=subprocess.run(["npm","pack","flag-icons@7.6.0","--pack-destination",tmp],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=90)
    Path(str(prefix)+"-dependency.log").write_text(packed.stdout)
    if packed.returncode:raise RuntimeError("Temporary flag-icons package unavailable")
    archive=next(Path(tmp).glob("flag-icons-7.6.0.tgz"));subprocess.run(["tar","-xzf",str(archive),"--strip-components=1","-C",str(flags)],check=True)
    files=["dashboard/frontend/src/server/legacy-compat.js","dashboard/frontend/src/server/bun-proxy.js","dashboard/frontend/src/season_data.js","dashboard/frontend/src/services/football-client.js","dashboard/frontend/src/views/CompetitionsPage.jsx","dashboard/backend/services/relational-core.js"]
    report["sourceSha256"]={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in files}
    env=os.environ.copy()
    for key in ("NEXT_PUBLIC_API_ORIGIN","DATABASE_URL","NEON_DATABASE_URL","NEON_STORAGE_ENDPOINT","NEON_STORAGE_ACCESS_KEY_ID","NEON_STORAGE_SECRET_ACCESS_KEY"):env.pop(key,None)
    env.update(VERCEL="1",NEXT_TELEMETRY_DISABLED="1")
    result=subprocess.run(["node",str(dst/"node_modules/next/dist/bin/next"),"build","frontend","--webpack"],cwd=dst,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)
    Path(str(prefix)+".log").write_text(result.stdout)
    report["exitCode"]=result.returncode
    if result.returncode==0:report["status"]="passed"
except Exception as error:report["error"]=type(error).__name__+": "+str(error)
finally:
  out=Path(str(prefix)+".json");out.write_text(json.dumps(report,indent=2)+"\n")
  print(json.dumps({"status":report["status"],"error":report.get("error"),"exitCode":report.get("exitCode"),"artifact":str(out)}))
raise SystemExit(report["status"]!="passed")
