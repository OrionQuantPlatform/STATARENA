"""Stage exact committed source on the existing Vercel project without aliasing."""
import argparse
import datetime as dt
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import tarfile
import tempfile

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
CLI=Path('/Users/lemonnierhugo/.npm/_npx/67eb4586ca667318/node_modules/vercel/dist/index.js')
p=argparse.ArgumentParser();p.add_argument('commit');a=p.parse_args()
if not re.fullmatch('[0-9a-f]{40}',a.commit):p.error('expected full committedmain SHA')
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()
if head!=a.commit or branch!='main':raise SystemExit('expected current main commit')
paths=['dashboard/frontend','dashboard/backend','dashboard/shared','dashboard/package.json','dashboard/bun.lock','.vercelignore','.gitignore']
archive=subprocess.check_output(['git','archive',a.commit,'--',*paths],cwd=ROOT)
stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');prefix=HERE/('vercel-stage-'+stamp)
r={'atUtc':dt.datetime.now(dt.timezone.utc).isoformat(),'command':['python3','docs/verification/orion-availability-20261104/stage_vercel.py',a.commit],'setup':'Exact tracked source exported from committedmain into disposable directory; no local dotenv/node_modules/untracked files. Existing Vercel production configuration. No domain assignment, env change or secret retrieval.','expected':'Upload candidate production build without assigning canonical aliases. Inspect/test immutable artifact before promote.','commit':a.commit,'team':'team_IYt7KqupdSTtMuQuMvNa9wiJ','project':'prj_DhaqrVkH3Gi4uysT7IRsm9fB2bjR','archiveSha256':hashlib.sha256(archive).hexdigest(),'status':'failed'}
try:
    with tempfile.TemporaryDirectory(prefix='statarena-vercel-stage-') as tmp:
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:tar.extractall(tmp,filter='data')
        tree=Path(tmp);files=sorted(x for x in tree.rglob('*') if x.is_file())
        r['files']={str(x.relative_to(tree)):hashlib.sha256(x.read_bytes()).hexdigest() for x in files};r['sourceBytes']=sum(x.stat().st_size for x in files)
        args=['node',str(CLI),'--scope',r['team'],'deploy',tmp,'--project',r['project'],'--prod','--skip-domain','--yes','--no-wait','--json','--meta','githubCommitSha='+a.commit,'--meta','githubCommitRef=main','--meta','githubRepo=STATARENA','--meta','githubOrg=OrionQuantPlatform']
        run=subprocess.run(args,cwd=tree,text=True,capture_output=True,timeout=180)
        Path(str(prefix)+'.log').write_text(run.stderr)
        r['exitCode']=run.returncode
        if run.returncode:raise RuntimeError('Vercel staging failed; inspect log')
        try:
            raw=json.loads(run.stdout);r['deployment']={k:raw.get(k) for k in ['id','uid','url','readyState','target']}
        except ValueError:
            match=re.search(r'https://statarena-analytics-[a-z0-9-]+\.vercel\.app',run.stdout)
            if not match:raise RuntimeError('Missing deployment URL')
            r['deployment']={'url':match.group(0)}
        r['status']='uploaded'
except Exception as error:r['error']=type(error).__name__+': '+str(error)
finally:
    out=Path(str(prefix)+'.json');out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'artifact':str(out),'status':r['status'],'deployment':r.get('deployment'),'error':r.get('error'),'sourceBytes':r.get('sourceBytes')}))
raise SystemExit(r['status']!='uploaded')
