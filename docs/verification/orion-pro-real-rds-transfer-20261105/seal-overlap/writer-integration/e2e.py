#!/usr/bin/env python3
"""Precode source-free sequencing workflow through the unchanged apply implementation."""
from datetime import datetime, timezone
import hashlib,importlib.util,json,os,shutil,sys,tempfile,time,traceback
from pathlib import Path

sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[4]
MODULE=BASE/'planner_apply.py'
CASES=['implementation_available','offline_and_code_audit','scoped_success','noop_and_copy_rollback','seal_and_ack_failures']

def child(case):
    sys.path.insert(0,str(ROOT/'dashboard/scripts'))
    spec=importlib.util.spec_from_file_location('planned_apply_child',MODULE);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    phase={'phase':'core','generation':2,'snapshotId':2,'runId':1}
    completed=[{'phase':'core','sourceGeneration':2,'sourceSnapshotId':2,'generation':3,'snapshotId':7,'runId':1}]
    class NativeError(RuntimeError):
        sqlstate='57014'
    class Source:
        def __init__(self,owner):self.owner=owner
        def commit(self):self.owner.calls.append('source_rr_closed')
        def rollback(self):self.owner.calls.append('source_rollback')
    class Target:
        def __init__(self,owner):self.owner=owner;self.local=False;self.in_txn=False
        def execute(self,sql,params=()):
            log=self.owner.calls
            if sql=='BEGIN':
                assert not self.local and not self.in_txn;self.in_txn=True;log.append('begin');return self
            if sql=='SET LOCAL enable_nestloop=off':
                assert self.in_txn and not self.local and log[-1]=='receipt_update'
                self.local=True;log.append('scope');return self
            if sql.startswith('SELECT ingest.seal_generation'):
                assert self.local and self.in_txn and log[-1]=='scope'
                log.append('seal')
                if self.owner.mode=='seal_error':raise NativeError('bounded native seal')
                return self
            assert not self.local
            if sql.startswith('SELECT transaction_timestamp'):self.result=(datetime(2031,1,2,tzinfo=timezone.utc),)
            elif sql.startswith('SELECT ingest.begin_generation'):self.result=(3,)
            elif sql.startswith('SELECT id FROM ingest.dataset_snapshots'):self.result=(7,)
            elif sql.startswith('UPDATE ingest.import_runs'):log.append('receipt_update')
            return self
        def fetchone(self):return self.result
        def rollback(self):
            self.local=self.in_txn=False;self.owner.calls.append('rollback')
        def commit(self):
            assert self.local and self.in_txn and self.owner.calls[-1]=='seal'
            self.local=self.in_txn=False;self.owner.calls.append('commit')
            if self.owner.mode=='lost_ack':raise OSError('synthetic lost reply')
    class Flow:
        def __init__(self,mode):
            self.mode=mode;self.calls=[];self.source=Source(self);self.target=Target(self)
            self.report={'sourcePrefixOracleMs':[],'copiedRows':0,'sourceTransactionsClosedBeforeTargetAdmission':0,'sealMs':[],'commitMs':[]}
            self.phases=[phase];self.phase_rows={2:1};self.phase_contracts={2:('fixture',None)}
            self.maps_g={1:1};self.maps_s={1:1};self.order=['fixture.scalar'];self.matrix={'copiedRelations':['fixture.scalar']}
            self.accepted={'writerSha256':'a'*64}
        def source_reopen(self):self.calls.append('source_rr_open')
        def business(self,conn,owners):
            assert conn is self.source and owners=={0,2};return 'native_fixture_digest'
        def snapshot_key(self,p):return 'fixture-native-v4'
        def reserve(self):self.calls.append('reservation')
        def parameters(self,p):return {'kind':'fixture_metadata'}
        def copy_table(self,name,g,fault):
            assert self.target.in_txn and not self.target.local and g==2 and fault is None
            self.calls.append('copy')
            if self.mode=='copy_error':raise RuntimeError('synthetic copy')
            self.report['copiedRows']=1
        def verify_business(self,digest,applying):
            assert digest=='native_fixture_digest' and applying and self.calls[-1]=='source_rr_closed'
            self.calls.append('target_oracle')
        def control_binding(self,p):return {'phase':'core'}
        def counters(self,rows):return {'copied_rows':rows}
        def prefix(self):self.calls.append('postcommit_prefix');return completed
    actual=[]
    for mode in {'scoped_success':['normal'],'noop_and_copy_rollback':['noop','copy_error'],'seal_and_ack_failures':['seal_error','lost_ack']}[case]:
        flow=Flow(mode);error=None
        try:m.apply_candidate(flow,completed if mode=='noop' else [],None)
        except Exception as caught:error=caught
        assert not flow.target.local and not flow.target.in_txn
        if mode=='normal':
            assert error is None and flow.report['status']=='applied' and flow.maps_g[2]==3 and flow.maps_s[2]==7
            assert flow.calls==['source_rr_open','begin','reservation','copy','source_rr_closed','target_oracle','receipt_update','scope','seal','commit','postcommit_prefix']
        elif mode=='noop':
            assert error is None and not flow.calls and flow.report['status']=='noop'
        elif mode=='copy_error':
            assert isinstance(error,RuntimeError) and flow.calls[-3:]==['copy','source_rollback','rollback'] and 'scope' not in flow.calls
        elif mode=='seal_error':
            assert isinstance(error,NativeError) and flow.calls[-4:]==['scope','seal','source_rollback','rollback'] and 'commit' not in flow.calls
        else:
            assert getattr(error,'code',None)=='COMMIT_ACK_UNKNOWN' and flow.report['commitOutcome']=='unknown'
            assert flow.calls[-5:]==['scope','seal','commit','source_rollback','rollback']
        actual.append({'mode':mode,'calls':flow.calls,'errorType':type(error).__name__ if error else None})
    return {'fixtureMetadataOnly':True,'simulatedWorkflows':actual,'connections':0}


def main():
    if len(sys.argv)==3 and sys.argv[1]=='--child':print(json.dumps(child(sys.argv[2])));return 0
    sys.path.insert(0,str(ROOT/'tests'));from orion_e2e_process import run_bounded
    out=BASE/'runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');(out/'inputs').mkdir(parents=True)
    report={'kind':'scoped_apply_sequencing_precode_e2e_v1','command':[sys.executable,str(Path(__file__))],'expected':str(BASE/'PROTOCOL.md'),
            'cases':[],'invocations':[],'connections':0,'sourceReads':0,'providerCalls':0,'businessWrites':0,'fullAcceptance':False}
    for p in [Path(__file__),MODULE,BASE/'PROTOCOL.md',BASE/'PINS.json']:
        if p.is_file():shutil.copy2(p,out/'inputs'/p.name)
    private=None;block=None;start=time.monotonic()
    try:
        for case in CASES:
            if block:report['cases'].append({'case':case,'status':'unverified','reason':block});continue
            try:
                if case=='implementation_available':
                    assert MODULE.is_file(),'Scoped apply candidate absent (expected precode RED)'
                    private=Path(tempfile.mkdtemp(prefix='orion-planner-apply-tripwire-',dir='/tmp'))
                    (private/'sitecustomize.py').write_text("""import builtins,os,socket,subprocess
from pathlib import Path
old=builtins.__import__
def deny(*a,**k):
 Path(os.environ['PLAN_APPLY_TRIPWIRE']).touch()
 raise RuntimeError('Forbidden offline action')
def guarded(name,*a,**k):
 if name.split('.')[0] in {'psycopg','psycopg2','boto3','botocore','requests'}:return deny()
 return old(name,*a,**k)
builtins.__import__=guarded
socket.getaddrinfo=socket.socket.connect=socket.socket.connect_ex=subprocess.Popen=deny
""")
                    env={k:v for k,v in os.environ.items() if k in {'PATH','HOME','USER','TMPDIR','LANG'}}
                    env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(private),PLAN_APPLY_TRIPWIRE=str(private/'attempted'))
                    actual={'sha256':hashlib.sha256(MODULE.read_bytes()).hexdigest()}
                else:
                    cmds=[([sys.executable,str(MODULE)],0),([sys.executable,str(MODULE),'--audit'],0),([sys.executable,str(MODULE),'--apply-rds'],2)] if case=='offline_and_code_audit' else [([sys.executable,str(Path(__file__)),'--child',case],0)]
                    actual=[]
                    for idx,(cmd,code) in enumerate(cmds):
                        r=run_bounded(cmd,cwd=ROOT,env=env,deadline=start+45,output_limit=1024**2);key=f'{case}-{idx}'
                        (out/(key+'.stdout.log')).write_text(r.stdout);(out/(key+'.stderr.log')).write_text(r.stderr)
                        report['invocations'].append({'command':cmd,'exitCode':r.returncode,'stdout':key+'.stdout.log','stderr':key+'.stderr.log'})
                        assert r.returncode==code and not(private/'attempted').exists(),(r.stdout,r.stderr)
                        if code==0:
                            val=json.loads(r.stdout);assert val['connections']==0
                            if case=='offline_and_code_audit' and idx==1:assert val['onlyAddedSql']=='SET LOCAL enable_nestloop=off' and val['originalAstRestored']
                            actual.append(val)
                report['cases'].append({'case':case,'status':'pass','actual':actual})
            except BaseException as e:
                block=case;report['cases'].append({'case':case,'status':'fail','error':str(e),'traceback':traceback.format_exc()})
    finally:
        if private:shutil.rmtree(private)
        report['privateTripwireRemoved']=private is None or not private.exists();report['status']='fail' if block else 'pass_source_free_only'
        report['counts']={s:sum(x['status']==s for x in report['cases']) for s in ('pass','fail','unverified')}
        report['elapsedSeconds']=round(time.monotonic()-start,3);(out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({'status':report['status'],'counts':report['counts'],'evidence':str(out/'result.json')}))
    return 1 if block else 0
if __name__=='__main__':raise SystemExit(main())
