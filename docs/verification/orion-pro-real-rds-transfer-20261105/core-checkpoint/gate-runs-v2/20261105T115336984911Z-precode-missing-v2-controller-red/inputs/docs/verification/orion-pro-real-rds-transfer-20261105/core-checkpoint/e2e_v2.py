#!/usr/bin/env python3
"""Before-code E2E gates for the distinct v2 readonly owner recovery."""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import time
import traceback

sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[3]
CONTROLLER=BASE/'controller_v2.py'
CASES=['implementation_available','offline_default','release_before_external_operations','unknown_routes_and_spatial_refused']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):Path(p).write_text(json.dumps(v,indent=2,default=str)+'\n')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--precode-only',action='store_true');ap.add_argument('--source-free',action='store_true')
    ap.add_argument('--run-recovery',action='store_true');ap.add_argument('--release',type=Path);ap.add_argument('--release-sha256');ap.add_argument('--label',default='readonly-core')
    args=ap.parse_args();assert args.label.replace('-','').isalnum()
    if args.run_recovery:
        assert args.release and args.release_sha256,'Exact separate ROOT release required'
        os.execv(sys.executable,[sys.executable,str(CONTROLLER),'--recover','--release',str(args.release.resolve()),'--release-sha256',args.release_sha256])
    sys.path.insert(0,str(ROOT/'tests'));from orion_e2e_process import run_bounded
    run=BASE/'gate-runs-v2'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-'+args.label);(run/'inputs').mkdir(parents=True)
    report={'kind':'real_core_readonly_cli_e2e_v2','command':[sys.executable,str(Path(__file__)),*sys.argv[1:]],'expected':str(BASE/'PROTOCOL_V2.md'),
            'cases':[],'invocations':[],'inputSha256':{},'pgStarts':0,'sourceRamReads':0,'remoteCalls':0,'fullAcceptance':False}
    for p in [Path(__file__),BASE/'PROTOCOL_V2.md',BASE/'PINS_V2.json',CONTROLLER,ROOT/'tests/orion_e2e_process.py']:
        if p.is_file():
            dest=run/'inputs'/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest);report['inputSha256'][str(p.relative_to(ROOT))]=sha(p)
    guard=run/'tripwire';guard.mkdir()
    (guard/'sitecustomize.py').write_text("import socket,subprocess\ndef deny(*a,**k):raise RuntimeError('UNEXPECTED_EXTERNAL_OPERATION')\nsocket.socket.connect=deny\nsocket.getaddrinfo=deny\nsubprocess.Popen=deny\n")
    (guard/'psycopg.py').write_text("raise RuntimeError('UNEXPECTED_DRIVER_IMPORT')\n")
    env={k:v for k,v in os.environ.items() if k in ['PATH','HOME','USER','TMPDIR','LANG']};env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(guard))
    deadline=time.monotonic()+30;block=None
    def cli(flags):
        argv=[sys.executable,str(CONTROLLER),*map(str,flags)];r=run_bounded(argv,cwd=ROOT,env=env,deadline=deadline)
        n=len(report['invocations']);(run/f'{n}.stdout.log').write_text(r.stdout);(run/f'{n}.stderr.log').write_text(r.stderr)
        report['invocations'].append({'command':argv,'exitCode':r.returncode,'stdout':f'{n}.stdout.log','stderr':f'{n}.stderr.log'})
        assert 'UNEXPECTED_' not in r.stdout+r.stderr,r.stderr
        return r,json.loads(r.stdout) if r.stdout.startswith('{') else None
    for case in CASES:
        if block or (args.precode_only and case!='implementation_available'):
            report['cases'].append({'case':case,'status':'unverified','reason':block or 'Precode mode only'});continue
        try:
            if case=='implementation_available':assert CONTROLLER.is_file(),'Readonly core recovery controller is absent';actual={'controllerSha256':sha(CONTROLLER)}
            elif case=='offline_default':
                env.update(PGHOSTADDR='203.0.113.44',PGOPTIONS='-c statement_timeout=0');r,data=cli([]);env.pop('PGHOSTADDR');env.pop('PGOPTIONS')
                assert r.returncode==0 and data['status']=='offline_plan' and data['pgStarts']==data['connections']==data['sourceRamReads']==0;actual=data
            elif case=='release_before_external_operations':
                actual=[]
                for flags in [['--recover'],['--noop-worker'],['--recover','--release',run/'absent.json','--release-sha256','0'*64]]:
                    r,data=cli(flags);assert r.returncode!=0 and data['reasonCode']=='RELEASE' and data['pgStarts']==data['connections']==data['sourceRamReads']==0;actual.append(data)
            else:
                actual=[]
                for flags in [['--root','/tmp/another-root'],['--host','external.invalid'],['--spatial'],['--construct'],['--dsn','postgresql://external.invalid/x']]:
                    r,data=cli(flags);assert r.returncode!=0 and data is None;actual.append(flags)
            report['cases'].append({'case':case,'status':'pass','actual':actual})
        except BaseException as error:
            block=str(error);report['cases'].append({'case':case,'status':'fail','error':str(error),'traceback':traceback.format_exc()})
    report['counts']={s:sum(c['status']==s for c in report['cases']) for s in ['pass','fail','unverified']};report['status']='fail' if block else 'pass_source_free_only'
    report['cleanup']={'pgStarted':False,'connections':0,'corpusTouched':False};save(run/'result.json',report);print(json.dumps({'status':report['status'],'counts':report['counts'],'evidence':str(run/'result.json')}))
    return 1 if block else 0

if __name__=='__main__':raise SystemExit(main())
