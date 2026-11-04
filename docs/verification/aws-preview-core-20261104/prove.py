"""Acquire only this preview's browser cookie in a private tempdir and run the real UI checks."""
import datetime as dt,http.cookiejar,json,os,subprocess,sys,tempfile
from pathlib import Path
from urllib.parse import urlsplit
here=Path(__file__).resolve().parent;root=here.parents[2]
site="https://statarena-analytics-nebu2r505-hlemonniers-projects.vercel.app"
src=json.loads((here/'source.json').read_text());run=dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
art=here/run;art.mkdir();os.umask(0o077)
report=dict(deployment=site,api='https://d317dq37z1tacb.cloudfront.net',commit='2a419',started=run,scope='(one published match and player, preview only)',passed=False)
pw=[str(Path.home()/'.codex/skills/playwright/scripts/playwright_cli.sh'),'-s=statarena-preview-'+run[9:15]]
with tempfile.TemporaryDirectory(prefix='statarena-preview-private-') as tmp:
 d=Path(tmp);jarpath=d/'cookies.txt';jarpath.touch(mode=0o600);opened=False
 try:
  response=subprocess.run(['npx','--yes','vercel@latest','--scope','team_IYt7KqupdSTtMuQuMvNa9wiJ','curl',site+'/','--','--silent','--show-error','--output',os.devnull,'--cookie-jar',str(jarpath),'--header','x-vercel-set-bypass-cookie: true','--write-out','%{http_code}'],cwd=root,capture_output=True,text=True,timeout=90)
  report['cliExit']=response.returncode
  # Capture only a numeric HTTP status and count; never persist CLI stdout/stderr or header values.
  import re
  m=re.search(r'\b([1-5][0-9]{2})\s*$',response.stdout);report['authStatus']=int(m[1]) if m else None
  jar=http.cookiejar.MozillaCookieJar(str(jarpath));jar.load(ignore_expires=True,ignore_discard=True)
  host=urlsplit(site).hostname
  cookies=[dict(name=c.name,value=c.value,domain=host,path='/',secure=True,httpOnly=True,sameSite='Lax',expires=c.expires or -1) for c in jar if host==c.domain.lstrip('.') or host.endswith('.'+c.domain.lstrip('.'))]
  report['hostScopedCookieCount']=len(cookies)
  if not cookies:raise RuntimeError('Vercel CLI did not issue browser session cookie')
  state=d/'state.json';state.write_text(json.dumps({'cookies':cookies,'origins':[]}))
  config=json.loads((here.parent/'rematerialization-completion-20261103/cli-headless.config.json').read_text())
  config['browser']['contextOptions']['storageState']=str(state)
  cfg=d/'config.json';cfg.write_text(json.dumps(config))
  if '--auth-only' in sys.argv:
   report['authPrepared']=True
  else:
   start=subprocess.run([*pw,'open','about:blank','--config',str(cfg)],cwd=d,capture_output=True,timeout=60)
   opened=start.returncode==0
   if not opened:raise RuntimeError('Browser could not start with ephemeral context')
   opts={'site':site,'api':report['api'],'s':src,'out':str(art)}
   code="async page=>{const OPT="+json.dumps(opts)+";\n"+(here/'views.js').read_text()+"\n}"
   proc=subprocess.run([*pw,'run-code',code],cwd=d,capture_output=True,text=True,timeout=300)
   if '### Result\n' not in proc.stdout:raise RuntimeError('Browser automation did not produce a sanitized result')
   data,_=json.JSONDecoder().raw_decode(proc.stdout.split('### Result\n',1)[1]);report.update(data)
 except Exception as exc:
  report['error']=type(exc).__name__ + (': '+str(exc) if isinstance(exc,RuntimeError) else '')
 finally:
  if opened:subprocess.run([*pw,'close'],cwd=d,capture_output=True,timeout=35)
(art/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:report.get(k) for k in ('authStatus','hostScopedCookieCount','authPrepared','error','passed','checks') if k in report},ensure_ascii=False))
print(art/'result.json')
raise SystemExit(0 if report.get('passed') or report.get('authPrepared') else 1)
