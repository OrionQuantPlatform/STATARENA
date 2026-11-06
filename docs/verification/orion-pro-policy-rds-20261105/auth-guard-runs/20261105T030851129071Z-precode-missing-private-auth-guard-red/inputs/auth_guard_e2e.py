#!/usr/bin/env python3
"""Pre-code real-file qualification for NEW private auth helpers only; zero PG."""
from __future__ import annotations
import argparse, builtins, hashlib, importlib.util, json, os, shutil, socket, sys, tempfile
from contextlib import contextmanager, ExitStack
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parent
CASE_NAMES=['new_auth_guard_available','missing_empty','relative_dsn','missing_leaf','nonregular_leaf','leaf_symlink','file_modes','parent_modes','parent_symlink','wrong_uid','valid_no_body','pg_options','explicit_kwargs','redacted_errors','no_home_fallback']
def save(p,x):Path(p).write_text(json.dumps(x,indent=2)+'\n')
def load_adapter():
    spec=importlib.util.spec_from_file_location('auth_guard_candidate',BASE/'adapter.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def run_cases(adapter,evidence):
    evidence=Path(evidence);evidence.mkdir(parents=True,exist_ok=True)
    report={'kind':'new_private_passfile_guard_real_files_v1','scope':'NEW metadata guard/kwargs only; synthetic files; no SQL mock','cases':[],'postgresStarts':0,'cloudCalls':0,'sourceOrRamReads':0,'rawCredentialBodiesRead':False,'fullAcceptance':False}
    if not callable(getattr(adapter,'validated_rds_passfile',None)) or not callable(getattr(adapter,'_rds_connection_kwargs',None)):
        report['cases']=[{'case':CASE_NAMES[0],'status':'fail','reason':'NEW private auth guard/kwargs helpers absent'}]+[{'case':n,'status':'unverified','reason':'New guard absent'} for n in CASE_NAMES[1:]]
    else:
        report['cases'].append({'case':CASE_NAMES[0],'status':'pass'});counts={'dns':0,'driver':0,'bodyRead':0}
        sys.path.insert(0,'/tmp/statarena-publication-test-python');import psycopg
        @contextmanager
        def tripwires():
            def stop(name):
                def fail(*a,**k):counts[name]+=1;raise AssertionError('Forbidden guard side effect')
                return fail
            with ExitStack() as stack:
                for target,name in [('socket.getaddrinfo','dns'),('psycopg.connect','driver'),('builtins.open','bodyRead'),('os.open','bodyRead'),('pathlib.Path.read_text','bodyRead'),('pathlib.Path.read_bytes','bodyRead')]:stack.enter_context(patch(target,stop(name)))
                yield
        def call(env):
            with tripwires():return adapter.validated_rds_passfile(env)
        def refusal(env,code='AUTH'):
            try:call(env)
            except adapter.Refusal as e:assert e.code==code;assert 'DUMMY_PRIVATE_' not in str(e);return
            raise AssertionError('Expected auth metadata refusal')
        root=Path(tempfile.mkdtemp(prefix='orion-rds-auth-',dir='/tmp'));os.chmod(root,0o700)
        file=root/'private.pgpass';file.write_text('DUMMY_PRIVATE_PASSFILE_NOT_A_REAL_PASSWORD\n');file.chmod(0o600);env=lambda p:{'ORION_RDS_PASSFILE':str(p)}
        def missing_empty():
            for value in [None,'']:
                refusal({} if value is None else {'ORION_RDS_PASSFILE':value})
        def relative_dsn():
            for value in ['relative.pgpass','postgresql://DUMMY_PRIVATE_INVALID@remote.invalid/db']:refusal(env(value))
        def missing_leaf():refusal(env(root/'absent'))
        def nonregular_leaf():
            d=root/'directory';d.mkdir(mode=0o700);refusal(env(d));fifo=root/'fifo';os.mkfifo(fifo,0o600);refusal(env(fifo));s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
            try:s.bind(str(root/'socket'));refusal(env(root/'socket'))
            finally:s.close()
        def leaf_symlink():
            link=root/'link';link.symlink_to(file);refusal(env(link));broken=root/'broken';broken.symlink_to(root/'absent');refusal(env(broken))
        def file_modes():
            try:
                for mode in [0o644,0o400,0,0o700]:file.chmod(mode);refusal(env(file))
            finally:file.chmod(0o600)
        def parent_modes():
            try:
                for mode in [0o755,0o770,0o710]:root.chmod(mode);refusal(env(file))
            finally:root.chmod(0o700)
        def parent_symlink():
            d=root/'real_parent';d.mkdir(mode=0o700);p=d/'private.pgpass';p.write_text('DUMMY_PRIVATE_NESTED\n');p.chmod(0o600);alias=root/'parent_alias';alias.symlink_to(d,target_is_directory=True);refusal(env(alias/'private.pgpass'))
        def wrong_uid():
            p=root/'other_uid';p.write_text('DUMMY_PRIVATE_UID\n');p.chmod(0o600);target=1 if os.getuid()==0 else 0
            try:os.chown(p,target,-1)
            except PermissionError:return {'status':'unisolated','reason':'OS cannot create a sole-wrong-UID private-file fixture'}
            assert p.lstat().st_uid!=os.getuid();refusal(env(p))
        def valid_no_body():
            assert call(env(file))==str(file);assert counts=={'dns':0,'driver':0,'bodyRead':0}
        def pg_options():
            for key in ['PGHOSTADDR','PGOPTIONS','PGSERVICE','PGPASSFILE']:refusal({**env(file),key:'DUMMY_PRIVATE_ROUTE'},'ROUTE')
        def explicit_kwargs():
            path=call(env(file))
            with tripwires():k=adapter._rds_connection_kwargs(path,'192.0.2.9')
            assert k['passfile']==str(file) and 'password' not in k and k['host']==adapter.HOST and k['hostaddr']=='192.0.2.9' and k['port']==5432 and k['dbname']=='statarena_prod' and k['user']=='statarena_admin' and k['sslmode']=='verify-full' and k['sslrootcert']==str(adapter.CA)
            assert 'statement_timeout=8000' in k['options'] and 'lock_timeout=1000' in k['options'] and 'default_transaction_read_only=on' in k['options']
        def redacted_errors():
            try:call(env(root/'DUMMY_PRIVATE_SECRET_PATH'))
            except adapter.Refusal as e:assert e.code=='AUTH' and str(root) not in str(e) and 'DUMMY_PRIVATE_' not in str(e)
            else:raise AssertionError('Missing file accepted')
        def no_home_fallback():
            home=root/'synthetic_home';home.mkdir(mode=0o700);p=home/'.pgpass';p.write_text('DUMMY_PRIVATE_HOME\n');p.chmod(0o600);refusal({'HOME':str(home)})
        try:
            functions=[missing_empty,relative_dsn,missing_leaf,nonregular_leaf,leaf_symlink,file_modes,parent_modes,parent_symlink,wrong_uid,valid_no_body,pg_options,explicit_kwargs,redacted_errors,no_home_fallback]
            for function in functions:
                try:
                    extra=function() or {};report['cases'].append({'case':function.__name__,'status':extra.pop('status','pass'),**extra})
                except Exception as e:report['cases'].append({'case':function.__name__,'status':'fail','errorType':type(e).__name__,'code':getattr(e,'code',None)})
        finally:shutil.rmtree(root);report['privateFixtureRemoved']=not root.exists()
        report['tripwires']=counts
    report['counts']={k:sum(c['status']==k for c in report['cases']) for k in ['pass','fail','unverified','unisolated']}
    report['status']='pass_with_uid_unisolated' if report['counts']=={'pass':14,'fail':0,'unverified':0,'unisolated':1} and next(c for c in report['cases'] if c['status']=='unisolated')['case']=='wrong_uid' else 'pass' if report['counts']=={'pass':15,'fail':0,'unverified':0,'unisolated':0} else 'fail'
    save(evidence/'result.json',report);return report

def main():
    p=argparse.ArgumentParser();p.add_argument('--label',required=True);args=p.parse_args();assert args.label and all(c.isalnum() or c=='-' for c in args.label)
    run=BASE/'auth-guard-runs'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-'+args.label);(run/'inputs').mkdir(parents=True)
    for path in [Path(__file__),BASE/'AUTH_GUARD_PROTOCOL.md',BASE/'adapter.py']:shutil.copy2(path,run/'inputs'/path.name)
    result=run_cases(load_adapter(),run);result['command']=[sys.executable,str(Path(__file__)),*sys.argv[1:]];result['inputSha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (run/'inputs').iterdir()};save(run/'result.json',result)
    print(json.dumps({'status':result['status'],'counts':result['counts'],'evidence':str(run/'result.json')}));return 0 if result['status']!='fail' else 1
if __name__=='__main__':raise SystemExit(main())
