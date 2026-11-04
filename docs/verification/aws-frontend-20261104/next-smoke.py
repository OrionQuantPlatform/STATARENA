"""Build and run the real frontend, and read a rendered archive row over distinct HTTP origins."""
from pathlib import Path
import json,os,socket,subprocess,tempfile,time,urllib.request
here=Path(__file__).resolve().parent
root=here.parents[2]
dashboard=root/"dashboard"
nextcli=dashboard/"node_modules/next/dist/bin/next"
wrapper=Path.home()/".codex/skills/playwright/scripts/playwright_cli.sh"
pw=[str(wrapper),"-s=statarena-archive-render"]
config=root/"docs/verification/rematerialization-completion-20261103/cli-headless.config.json"
report={"command":"python3 docs/verification/aws-frontend-20261104/next-smoke.py"}
fixture=subprocess.Popen(["bun",str(here/"server.mjs")],cwd=root,stdout=subprocess.PIPE,text=True)
app=None
def read(url):
    return json.load(urllib.request.urlopen(url,timeout=4))
with tempfile.TemporaryDirectory() as browser:
    try:
        base=fixture.stdout.readline().strip()
        origin=read(base+"/config")["api"]
        env={**os.environ,"NEXT_PUBLIC_API_ORIGIN":origin,"NEXT_TELEMETRY_DISABLED":"1"}
        with (here/"build.log").open("w") as log:
            subprocess.run(["node",str(nextcli),"build","frontend"],cwd=dashboard,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1",0));port=sock.getsockname()[1]
        app=subprocess.Popen(["node",str(nextcli),"start","frontend","-H","127.0.0.1","-p",str(port)],cwd=dashboard,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        url=f"http://127.0.0.1:{port}/archives"
        for _ in range(45):
            try:
                urllib.request.urlopen(url,timeout=2).close();break
            except OSError:time.sleep(.2)
        subprocess.run([*pw,"open",url,"--config",str(config)],cwd=browser,capture_output=True,check=True,timeout=45)
        js="""async page=>{await page.getByText('Test Athletic',{exact:true}).first().waitFor({timeout:15000});return await page.evaluate(()=>({text:document.querySelector('.archive-results tbody tr')?.innerText,reads:performance.getEntriesByType('resource').map(x=>x.name).filter(x=>/\\/(api|data)\\//.test(x))}));}"""
        cli=subprocess.run([*pw,"run-code",js],cwd=browser,capture_output=True,text=True,check=True,timeout=40)
        raw=cli.stdout.partition('### Result\n')[2].partition('\n###')[0]
        if not raw:raise RuntimeError(cli.stdout[:1200])
        ui=json.loads(raw);report.update(ui)
        traces=read(base+"/trace");report.update(traces)
        expect=["/api/archives/index?kind=goals","/api/archives/index?kind=results",
                "/api/archives/season?kind=results&season=2020%2F2021","/api/archives/season?kind=goals&season=2020%2F2021"]
        report["passed"]=all(x in traces["trace"] for x in expect) and "Blue United" in ui["text"] and "2 – 0" in ui["text"] and all(x.startswith(origin+"/api/") for x in ui["reads"]) and not traces["bad"]
    except Exception as e:report.update(passed=False,error=str(e))
    finally:
        subprocess.run([*pw,"close"],cwd=browser,capture_output=True,timeout=30)
        for proc in [app,fixture]:
            if proc:proc.terminate();proc.wait()
(here/"next-smoke.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report));raise SystemExit(0 if report["passed"] else 1)
