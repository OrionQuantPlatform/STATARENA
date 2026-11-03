"""Rerun the complete browser workflows serially and save the final receipt."""
from pathlib import Path
from datetime import datetime, timezone
import subprocess,sys,json
folder=Path(__file__).resolve().parent
cases=['navigation','preferences','layout','finishing','loading','ranking-links','widget-layout','country-filters','personal-fixtures','extra-country-filters']
results=[]
for case in cases:
 before=set(folder.glob(case+'-20*.json'))
 run=subprocess.run([sys.executable,str(folder/'run_cli.py'),case],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 if run.returncode:
  print(run.stdout[-2500:],flush=True)
 files=sorted(set(folder.glob(case+'-20*.json'))-before)
 f=files[-1] if files else None
 doc=json.loads(f.read_text()) if f else {}
 result={'case':case,'exitCode':run.returncode,'report':f.name if f else None,'status':doc.get('status','failed'),'checks':len(doc.get('checks',[]))}
 results.append(result);print(json.dumps(result),flush=True)
 if result['exitCode'] or result['status']!='passed': break
report={'setup':'Local Next server and read-only Neon data, dedicated Chromium session. Personal-fixture workflow uses explicitly controlled browser-only packed responses.','command':'python3 output/playwright/page-seasons-layout-20261103/run_all.py','expected':'All ten complete browser workflows pass.','results':results,'assertions':sum(r['checks'] for r in results),'status':'passed' if len(results)==len(cases) and all(r['status']=='passed' and r['exitCode']==0 for r in results) else 'failed','completedAt':datetime.now(timezone.utc).isoformat()}
(folder/'final-e2e.json').write_text(json.dumps(report,indent=2)+'\n');raise SystemExit(report['status']!='passed')
