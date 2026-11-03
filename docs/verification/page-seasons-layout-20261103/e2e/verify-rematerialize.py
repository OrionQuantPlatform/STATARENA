"""Inspect the real manual workflow and execute the real CLI without DB access."""
from pathlib import Path
import os, sys, subprocess, json, tempfile
from datetime import datetime, timezone
import yaml
root=Path(__file__).resolve()
root=next(p for p in root.parents if (p/'.git').is_dir())
out=Path(__file__).resolve().parent
workflow=root/'.github/workflows/rematerialize.yml'
doc=yaml.load(workflow.read_text(),Loader=yaml.BaseLoader)
checks=[]
def check(name,passed,actual):
 checks.append(dict(name=name,passed=passed,actual=actual))
env={key:value for key,value in os.environ.items() if not key.startswith(('NEON_','PITCHAPI_','GITHUB_ACTIONS'))}
env['PYTHONPATH']='/tmp/statarena-rematerialize-deps-20261103'
command=[sys.executable,str(root/'dashboard/scripts/neon_materialize.py')]
help_run=subprocess.run(command+['--help'],env=env,text=True,capture_output=True)
guard_run=subprocess.run(command+['--minutes','0'],env=env,text=True,capture_output=True)
(out/'rematerialize-help.log').write_text(help_run.stdout+help_run.stderr)
(out/'rematerialize-local-guard.log').write_text(guard_run.stdout+guard_run.stderr)
check('real CLI help exposes all/batch/minutes',help_run.returncode==0 and all(x in help_run.stdout for x in ['--all','--batch','--minutes']),help_run.stdout)
check('real CLI refuses writes outside Actions before Store construction',guard_run.returncode!=0 and 'must run in GitHub Actions' in guard_run.stderr,guard_run.stderr)
check('manual workflow only',set(doc['on'])=={'workflow_dispatch'},list(doc['on']))
check('first checkbox defaults off',doc['on']['workflow_dispatch']['inputs']['queue_all']['type']=='boolean' and doc['on']['workflow_dispatch']['inputs']['queue_all']['default']=='false',doc['on']['workflow_dispatch']['inputs']['queue_all'])
check('shared ingestion concurrency',doc['concurrency']['group']=='statarena-neon-ingestion' and doc['concurrency']['cancel-in-progress']=='false',doc['concurrency'])
check('GitHub content permissions remain read-only',doc['permissions']=={'contents':'read'},doc['permissions'])
step=next(s for s in doc['jobs']['rematerialize']['steps'] if s.get('name')=='Rebuild from saved Neon responses')
shell=subprocess.run(['bash','-n'],input=step['run'],text=True,capture_output=True)
check('publication shell parses',shell.returncode==0,shell.stderr)
check('workflow invokes stored-data CLI and no provider collection', 'neon_materialize.py' in step['run'] and 'neon_ingest.py' not in workflow.read_text() and 'PITCHAPI' not in workflow.read_text(),step['run'])
report={'setup':'Real Python CLI using boto3 installed outside the repository; no GITHUB_ACTIONS, Neon or Pitch credentials in child processes. Workflow YAML and Bash checked locally.','rerun':['python3 -m pip install --target /tmp/statarena-rematerialize-deps-20261103 boto3==1.43.123','python3 output/playwright/page-seasons-layout-20261103/verify-rematerialize.py'],'expected':'CLI help works; local mutation attempt is refused before DB construction; manual workflow shares locking/permissions and invokes the existing stored-data-only CLI.','checks':checks,'productionWorkflowDispatched':False,'unverified':'GitHub Actions execution, writer secrets, full historical publication and remaining:0 are not verified.','status':'passed' if all(c['passed'] for c in checks) else 'failed'}
p=out/('rematerialize-check-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.json');p.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'report':str(p),'status':report['status'],'checks':len(checks)}));raise SystemExit(report['status']!='passed')
