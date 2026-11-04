import json,subprocess,sys,os
from pathlib import Path
p=Path(__file__).parent;mode=sys.argv[1];cli=str(Path.home()/'.codex/skills/playwright/scripts/playwright_cli.sh');name='statarena-private-detail-'+mode
def call(args,timeout=100):
 r=subprocess.run([cli,'-s='+name,*args],cwd=p,capture_output=True,text=True,timeout=timeout);return r.stdout+r.stderr
(p/(mode+'-open.log')).write_text(call(['open','about:blank','--config',str(p/'playwright.json')]))
try:
 source='async page=>{ const mode='+json.dumps(mode)+';'+(p/('comparison-race.js' if mode.startswith('pair') else 'cross.js' if mode.startswith(('foreign','native','cancel')) else 'panels.js' if mode in ('shots','upcoming','standings') else 'interactions.js' if mode in ('intent','warm') else 'browser.js')).read_text()+'}'
 log=call(['run-code',source],160);(p/(mode+'-browser.log')).write_text(log);print(log[-600:])
finally:call(['close'])
