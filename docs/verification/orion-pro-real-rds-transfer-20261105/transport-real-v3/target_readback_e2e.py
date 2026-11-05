#!/usr/bin/env python3
"""Before-code whole-CLI check of the ROOT-only target descriptor helper."""
from datetime import datetime,timezone
import hashlib,json,os,shutil,sys,tempfile,time,traceback
from pathlib import Path
sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[3];HELPER=BASE/'target_readback.py'
CASES=['implementation_available','offline_default','offline_exact_policy_plan']
def main():
 sys.path.insert(0,str(ROOT/'tests'));from orion_e2e_process import run_bounded
 run=BASE/'target-helper-runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');(run/'inputs').mkdir(parents=True);report={'kind':'target015_readback_source_free_cli_e2e_v1','command':[sys.executable,str(Path(__file__))],'expected':str(BASE/'TARGET_READBACK_PROTOCOL.md'),'cases':[],'connections':0,'realCalls':0};p=None;block=None
 for f in [Path(__file__),BASE/'TARGET_READBACK_PROTOCOL.md',HELPER,BASE/'TARGET_POLICY.json',BASE/'target_policy.py']:
  if f.is_file():shutil.copy2(f,run/'inputs'/f.name)
 try:
  for name in CASES:
   if block:report['cases'].append({'case':name,'status':'unverified','reason':block});continue
   try:
    if name=='implementation_available':
     assert HELPER.is_file(),'Target015 readback helper absent (expected precode RED)';p=Path(tempfile.mkdtemp(prefix='orion-p2-target-tripwire-',dir='/tmp'));(p/'sitecustomize.py').write_text("import builtins,os,socket,subprocess\nfrom pathlib import Path\nold=builtins.__import__\ndef deny(*a,**k):\n Path(os.environ['P2_TARGET_TRIPWIRE']).touch()\n raise RuntimeError('offline target attempted an external action')\ndef imports(n,*a,**k):\n if n.split('.')[0] in {'psycopg','psycopg2','boto3','botocore','requests'}:return deny()\n return old(n,*a,**k)\nbuiltins.__import__=imports\nsocket.getaddrinfo=deny\nsocket.socket.connect=deny\nsubprocess.Popen=deny\n");env={k:v for k,v in os.environ.items() if not k.startswith('PG')};env.update(PYTHONPATH=str(p),P2_TARGET_TRIPWIRE=str(p/'forbidden'),PYTHONDONTWRITEBYTECODE='1');actual={'helperSha256':hashlib.sha256(HELPER.read_bytes()).hexdigest()}
    else:
     flags=[] if name=='offline_default' else ['--check-plan'];cmd=[sys.executable,str(HELPER),*flags];r=run_bounded(cmd,cwd=ROOT,env=env,deadline=time.monotonic()+20,output_limit=1024**2);(run/(name+'.stdout.log')).write_text(r.stdout);(run/(name+'.stderr.log')).write_text(r.stderr);assert r.returncode==0 and not(p/'forbidden').exists(),r.stderr;actual=json.loads(r.stdout);assert actual['connections']==0 and actual['realTargetObserved'] is False and actual['status'] in ['offline_plan','prepared_actual_adoption_inputs_only']
    report['cases'].append({'case':name,'status':'pass','actual':actual})
   except BaseException as e:block=name;report['cases'].append({'case':name,'status':'fail','error':str(e),'traceback':traceback.format_exc()})
 finally:
  if p:shutil.rmtree(p)
  report['cleanup']={'privateTripwireRemoved':p is None or not p.exists()};report['counts']={s:sum(c['status']==s for c in report['cases']) for s in ['pass','fail','unverified']};report['status']='fail' if block else 'pass_source_free_only';(run/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':report['status'],'counts':report['counts'],'evidence':str(run/'result.json')}))
 return 1 if block else 0
if __name__=='__main__':raise SystemExit(main())
