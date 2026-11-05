#!/usr/bin/env python3
"""Precode whole-CLI boundaries for the isolated P2 operator. No PG/network."""
from datetime import datetime,timezone
import hashlib,json,os,shutil,sys,tempfile,traceback
from pathlib import Path

sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[3]
OPERATOR=BASE/'adopt_p2.py'
CASES=['implementation_available','offline_poisoned','offline_exact_plan','missing_release','wrong_target','wrong_code','historical_sequence_baseline','wrong_policy_alias','local_contract_as_real','consumed_ledger','pg_route_poison','unknown_host_option','missing_private_auth','real_fault_injection']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):Path(p).write_text(json.dumps(v,indent=2,default=str)+'\n')

def main():
    sys.path.insert(0,str(ROOT/'tests'));from orion_e2e_process import run_bounded
    run=BASE/'boundary-runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');(run/'inputs').mkdir(parents=True)
    report={'kind':'isolated_p2_adoption_cli_boundary_e2e_v1','command':[sys.executable,str(Path(__file__))],'expected':str(BASE/'PROTOCOL.md'),'cases':[],'pgStarts':0,'connections':0,'cloudCalls':0,'sourceCalls':0,'fullAcceptance':False,'structuralMetadataOnly':True}
    private=None;block=None
    for p in [Path(__file__),BASE/'PROTOCOL.md',OPERATOR,BASE/'P2_POLICY.json',BASE/'PINS.json']:
        if p.is_file():shutil.copy2(p,run/'inputs'/p.name)
    try:
        for case in CASES:
            if block:report['cases'].append({'case':case,'status':'unverified','reason':block});continue
            try:
                if case=='implementation_available':
                    assert OPERATOR.is_file(),'Isolated native015 operator absent (expected precode RED)'
                    private=Path(tempfile.mkdtemp(prefix='orion-p2-boundary-',dir='/tmp'));mirror=private/'repo';paths=[OPERATOR,BASE/'P2_POLICY.json',BASE/'PINS.json',*BASE.glob('*.py')]
                    pins=json.loads((BASE/'PINS.json').read_text());paths += [ROOT/p for p in pins['files']]
                    for path in set(paths):
                        dest=mirror/path.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
                    copied=mirror/OPERATOR.relative_to(ROOT);mb=copied.parent;release=mb/'ROOT_RDS_P2_RELEASE.json';ledger=mb/'RDS_P2_ONESHOT.json'
                    metadata=json.loads((BASE/'P2_POLICY.json').read_text())
                    release_template={'kind':'root_isolated_rds015_adoption_release_v1','authorizedBy':'ROOT','scope':'fixed015_one_function_one_journal_only','policyId':metadata['policyId'],'origin':'real_rds_bootstrap_after_accounted_reservations','operatorSha256':sha(OPERATOR),'pinsSha256':sha(BASE/'PINS.json'),'policySha256':sha(BASE/'P2_POLICY.json'),'migrationSha256':metadata['migration']['sha256'],'nativeBaselineSha256':metadata['baseline']['nativeSha256'],'beforeStateSha256':metadata['baseline']['stateSha256'],'target':metadata['target'],'codeCommit':'a'*40,'localReceiptPath':str(BASE/'owned-runs/not-executed-boundary-fixture/result.json'),'localReceiptSha256':'0'*64,'productionActivation':False,'collectorsEnabled':False,'fullAcceptance':False}
                    (private/'sitecustomize.py').write_text("import builtins,os,socket,subprocess\nfrom pathlib import Path\n_original=builtins.__import__\ndef forbidden(*a,**k):\n Path(os.environ['P2_TRIPWIRE']).touch()\n raise RuntimeError('forbidden_p2_boundary_external_action')\ndef imports(name,*a,**k):\n if name.split('.')[0] in {'psycopg','psycopg2','boto3','botocore','requests'}:return forbidden()\n return _original(name,*a,**k)\nbuiltins.__import__=imports\nsocket.getaddrinfo=forbidden\nsocket.socket.connect=forbidden\nsocket.socket.connect_ex=forbidden\nsubprocess.Popen=forbidden\n")
                    env={k:v for k,v in os.environ.items() if not k.startswith('PG')};env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(private),P2_TRIPWIRE=str(private/'forbidden'))
                    actual={'operatorSha256':sha(OPERATOR)}
                else:
                    for p in [release,ledger]:
                        if p.exists():p.unlink()
                    body=json.loads(json.dumps(release_template));args=['--execute-released-rds'];childenv=dict(env);expected=None
                    if case=='offline_poisoned':args=[];childenv.update(PGHOSTADDR='192.0.2.7',PGOPTIONS='-c statement_timeout=0')
                    elif case=='offline_exact_plan':args=['--check-plan']
                    elif case=='missing_release':expected='RELEASE'
                    elif case=='wrong_target':body['target']['database']='statarena';expected='RELEASE'
                    elif case=='wrong_code':body['operatorSha256']='0'*64;expected='RELEASE'
                    elif case=='historical_sequence_baseline':body['beforeStateSha256']='e24d2f4864f2a24c639d5556b4012d276b8958f5df3d02e2a80e52a601ae9a32';expected='BASELINE'
                    elif case=='wrong_policy_alias':body['policyId']='membership-original-restored-m18da43-local099-v1';expected='POLICY'
                    elif case=='local_contract_as_real':body['origin']='owned_local_policy_fixture';expected='ORIGIN'
                    elif case=='consumed_ledger':save(ledger,{'kind':'isolated_rds015_oneshot_v1','state':'consumed','executions':1});expected='CHECKPOINT'
                    elif case=='pg_route_poison':childenv['PGHOSTADDR']='192.0.2.9';expected='ROUTE'
                    elif case=='unknown_host_option':args+=['--host','external.invalid']
                    elif case=='missing_private_auth':expected='AUTH'
                    elif case=='real_fault_injection':args+=['--fault','after_function'];expected='MODE'
                    if case not in ['offline_poisoned','offline_exact_plan','missing_release']:save(release,body)
                    command=[sys.executable,str(copied),*args];result=run_bounded(command,cwd=mirror,env=childenv,deadline=__import__('time').monotonic()+20,output_limit=1024**2)
                    (run/(case+'.stdout.log')).write_text(result.stdout);(run/(case+'.stderr.log')).write_text(result.stderr);assert not(private/'forbidden').exists(),'Unreleased DNS/driver/provider/process attempted'
                    if case in ['offline_poisoned','offline_exact_plan']:
                        value=json.loads(result.stdout);assert result.returncode==0 and value['connections']==0 and value['status'] in ['offline_plan','prepared_not_applied']
                    else:
                        assert result.returncode==2,(case,result.returncode,result.stdout,result.stderr)
                        if expected:assert json.loads(result.stdout)['code']==expected,(case,result.stdout)
                    actual={'command':command,'exitCode':result.returncode,'expectedCode':expected,'forbiddenExternalActions':0}
                report['cases'].append({'case':case,'status':'pass','actual':actual})
            except BaseException as error:
                block=case;report['cases'].append({'case':case,'status':'fail','error':str(error),'traceback':traceback.format_exc()})
    finally:
        if private:shutil.rmtree(private)
        report['privateMirrorRemoved']=private is None or not private.exists();report['counts']={s:sum(c['status']==s for c in report['cases']) for s in ['pass','fail','unverified']};report['status']='pass_source_free_only' if report['counts']=={'pass':len(CASES),'fail':0,'unverified':0} else 'fail'
        save(run/'result.json',report);print(json.dumps({'status':report['status'],'counts':report['counts'],'evidence':str(run/'result.json')}))
    return 0 if report['status']=='pass_source_free_only' else 1

if __name__=='__main__':raise SystemExit(main())
