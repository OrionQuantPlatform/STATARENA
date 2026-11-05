#!/usr/bin/env python3
"""Recover one stopped committed core by reads only; offline unless released."""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import time
import traceback

sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[3]
PINS=BASE/'PINS.json'
PINS_SHA='427ae883f6c55504bce7c8e074a6be46fe638f3c24c7cf74b95001179abfe976'
FROZEN=ROOT/'docs/verification/orion-pro-real-native-spatial-20261104'
PRIOR=ROOT/'docs/verification/orion-pro-real-rds-transfer-20261105/source-runs/20261105T111626302849Z'
TYPED_ROOT=Path('/var/folders/8z/mp96_9353w79bsgv7kftgk2h0000gn/T/orion-pro-e2e-939fcgo9')
PG_BIN=Path('/tmp/statarena-cache-test-tools/node_modules/@embedded-postgres/darwin-arm64/native/bin')
RAM=Path('/tmp/orion-real-rds-source-20261105-v3/source.sock')
OPTIONS=('-c default_transaction_read_only=on -c statement_timeout=8000 -c lock_timeout=1000 '
         '-c idle_in_transaction_session_timeout=15000 -c search_path=pg_catalog -c timezone=UTC '
         '-c datestyle=ISO,YMD -c intervalstyle=iso_8601 -c client_encoding=UTF8 -c extra_float_digits=3')

class Refusal(Exception):
    def __init__(self,code,message):self.code=code;super().__init__(message)
def require(ok,code,message):
    if not ok:raise Refusal(code,message)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def hashed(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def save(p,v):Path(p).write_text(json.dumps(v,indent=2,default=str)+'\n')
def load(p,name):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def read_json(p,limit=8*1024**2):
    p=Path(p);info=p.lstat();require(stat.S_ISREG(info.st_mode) and info.st_size<=limit,'RELEASE','Regular bounded metadata file required');return json.loads(p.read_text())

def fixed_inputs():
    require(sha(PINS)==PINS_SHA,'INPUT','Fixed core recovery pins differ');pins=read_json(PINS)
    require(pins['kind']=='existing_real_core_readonly_recovery_pins_v1' and pins['ownedRoot']==str(TYPED_ROOT) and
            pins['port']==55467 and pins['captureSocket']==str(RAM),'INPUT','Only the retained committed-core root is supported')
    require(all(sha(ROOT/p)==h for p,h in pins['files'].items()),'INPUT','A frozen source, failure receipt or cloud ledger differs')
    return pins

def checked_release(args,worker=False):
    require(args.release and args.release_sha256,'RELEASE','Separate exact ROOT recovery release required')
    try:
        require(sha(args.release)==args.release_sha256,'RELEASE','Recovery release hash differs');r=read_json(args.release,16384)
    except (OSError,ValueError,TypeError):raise Refusal('RELEASE','Recovery release unavailable') from None
    expected={'kind':'root_committed_core_readonly_recovery_v1','approvedBy':'ROOT','controllerSha256':sha(Path(__file__)),
              'testSha256':sha(BASE/'e2e.py'),'protocolSha256':sha(BASE/'PROTOCOL.md'),'pinsSha256':sha(PINS),
              'ownedRoot':str(TYPED_ROOT),'port':55467,'maximumRestarts':1,'maximumRamReads':2,
              'sourceConstructions':0,'businessWrites':0,'maximumSeconds':300,'maximumOwnedBytes':3*1024**3,
              'maximumProofBytes':64*1024**2,'maximumIdleSeconds':3600}
    require(all(r.get(k)==v for k,v in expected.items()),'RELEASE','Exact ROOT source scope/code/bounds differ')
    require(isinstance(r.get('allocationId'),str) and re.fullmatch('[a-zA-Z0-9-]+',r['allocationId']),'RELEASE','Closed allocation ID required')
    require(not any(k.startswith('PG') for k in os.environ),'ROUTE','Inherited libpq settings refused')
    pins=fixed_inputs();allocation=BASE/(r['allocationId']+'.consumed.json')
    require(allocation.exists()==worker,'RELEASE','Recovery allocation already consumed or worker has no owned parent allocation')
    return pins,r,allocation

def retained_metadata(pins,*,running=False,marker=None):
    root=TYPED_ROOT.resolve();info=root.lstat();data=root/'data'
    require(root.name=='orion-pro-e2e-939fcgo9' and stat.S_ISDIR(info.st_mode) and info.st_uid==os.getuid() and
            stat.S_IMODE(info.st_mode)==0o700 and (data/'PG_VERSION').read_text().strip()=='18','OWNED','Retained root owner/engine differs')
    prior=read_json(PRIOR/'result.json');old=prior['marker'];recovery=read_json(PRIOR/'ROOT_CLEANUP_RECOVERY.json')
    require(Path(old['ownedRoot']).resolve()==root and old['port']==55467 and recovery['serverStopped'] is True and
            recovery['ownedRootRetainedStoppedForDiagnosis'] is True,'OWNED','Exact prior stopped-core evidence required')
    cert=Path(old['certificatePath']);require(cert.resolve().is_relative_to(root) and sha(cert)==old['certificateSha256'],'OWNED','Retained TLS certificate differs')
    if running:
        lines=(data/'postmaster.pid').read_text().splitlines();require(Path(lines[1]).resolve()==data and int(lines[3])==55467,'OWNED','Running retained data/port differs');os.kill(int(lines[0]),0)
        require(marker is not None and Path(marker['ownedRoot']).resolve()==root and marker['port']==55467 and marker['certificateSha256']==old['certificateSha256'],'OWNED','New owned marker differs')
    else:require(not (data/'postmaster.pid').exists(),'OWNED','Retained postmaster must be stopped before the sole restart')
    captured=read_json(FROZEN/'capture-v3/capture.json');ri=RAM.lstat()
    require(captured['ready'] is True and captured['socket']==str(RAM) and captured['pid']==29953 and
            stat.S_ISSOCK(ri.st_mode) and ri.st_uid==os.getuid() and stat.S_IMODE(RAM.parent.stat().st_mode)==0o700,
            'SOURCE','Exact private frozen RAM service must remain ready')
    os.kill(captured['pid'],0)
    return old

def allow_sql(sql,report):
    text=str(sql);stripped=text.lstrip();upper=stripped.upper()
    safe=upper.startswith(('SELECT ','SHOW ')) or bool(re.fullmatch(r'SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY',upper))
    mutator=re.search(r'\b(nextval|setval|begin_generation|seal_generation|claim_collection_job|complete_collection_job)\s*\(',text,re.I)
    require(safe and not mutator and ';' not in text,'READ_ONLY','Only single readonly SQL and the frozen core no-op path are permitted')
    report.setdefault('queries',[]).append(text);require(sum(len(v.encode()) for v in report['queries'])<=8*1024**2,'BOUND','Query evidence exceeds8MiB')

class ReadonlyCursor:
    def __init__(self,raw,report):self.raw,self.report=raw,report
    def __getattr__(self,k):return getattr(self.raw,k)
    def __setattr__(self,k,v):
        if k in ['raw','report']:object.__setattr__(self,k,v)
        else:setattr(self.raw,k,v)
    def __enter__(self):self.raw.__enter__();return self
    def __exit__(self,*args):return self.raw.__exit__(*args)
    def __iter__(self):return iter(self.raw)
    def execute(self,sql,*args,**kw):allow_sql(sql,self.report);self.raw.execute(sql,*args,**kw);return self
    def stream(self,sql,*args,**kw):allow_sql(sql,self.report);return self.raw.stream(sql,*args,**kw)

class ReadonlyConnection:
    def __init__(self,raw,report):self.raw,self.report=raw,report
    def __getattr__(self,k):return getattr(self.raw,k)
    def __enter__(self):self.raw.__enter__();return self
    def __exit__(self,*args):return self.raw.__exit__(*args)
    def execute(self,sql,*args,**kw):allow_sql(sql,self.report);return self.raw.execute(sql,*args,**kw)
    def cursor(self,*args,**kw):return ReadonlyCursor(self.raw.cursor(*args,**kw),self.report)

def connect(marker,actor,report):
    require(actor in ['orion_pro_runtime','orion_pro_ingest','orion_pro_owner'],'ROLE','Only the ordinary source roles are supported')
    import psycopg
    c=psycopg.connect(host='127.0.0.1',hostaddr='127.0.0.1',port=55467,dbname='postgres',user=actor,password='',passfile='/dev/null',
        sslmode='verify-full',sslrootcert=marker['certificatePath'],autocommit=True,connect_timeout=7,options=OPTIONS,application_name='real-core-readonly-checkpoint-v1')
    report['connections']+=1
    try:
        with c.transaction():
            c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
            row=c.execute("SELECT current_database(),current_user,session_user,current_setting('server_version_num'),current_setting('transaction_read_only'),current_setting('transaction_isolation'),current_setting('default_transaction_read_only'),current_setting('statement_timeout'),current_setting('lock_timeout'),current_setting('idle_in_transaction_session_timeout'),(SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()),pg_postmaster_start_time()").fetchone()
            require(row==('postgres',actor,actor,'180006','on','repeatable read','on','8s','1s','15s',True,datetime.fromisoformat(marker['postmasterStartedAt'])),'ROLE','Exact readonly TLS engine/actor/startup contract differs')
            flags=c.execute('SELECT rolsuper,rolcreaterole,rolcreatedb,rolreplication,rolbypassrls FROM pg_roles WHERE rolname=current_user').fetchone()
            members=c.execute("SELECT count(*) FROM pg_roles WHERE rolname<>current_user AND pg_has_role(current_user,oid,'MEMBER')").fetchone()[0]
            require(flags is not None and not any(flags) and members==0,'ROLE','Elevated or inherited source role refused')
            db_owner,readable,writable,owners=c.execute("SELECT pg_get_userbyid(d.datdba),has_table_privilege(current_user,'football.players','SELECT'),has_table_privilege(current_user,'football.players','INSERT'),(SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname IN ('ingest','football','analytics') AND c.relowner=current_user::regrole) FROM pg_database d WHERE d.datname=current_database()").fetchone()
            require(db_owner=='orion_pro_owner' and readable is True and writable==(actor!='orion_pro_runtime') and
                    (actor=='orion_pro_owner' or owners==0),'ROLE','Exact owner/reader/ingest privilege separation differs')
        return ReadonlyConnection(c,report)
    except BaseException:c.close();raise

def initial_marker(old,report):
    import psycopg
    c=psycopg.connect(host='127.0.0.1',hostaddr='127.0.0.1',port=55467,dbname='postgres',user='orion_pro_runtime',password='',passfile='/dev/null',
        sslmode='verify-full',sslrootcert=old['certificatePath'],autocommit=True,connect_timeout=7,options=OPTIONS)
    report['connections']+=1
    try:new={**old,'postmasterStartedAt':c.execute('SELECT pg_postmaster_start_time()').fetchone()[0].isoformat()}
    finally:c.close()
    return new

def noop_worker(args,pins,release,allocation):
    owned=read_json(allocation);run=Path(args.evidence).resolve();require(str(run)==owned['run'],'RELEASE','Worker must use the consumed parent evidence directory')
    marker=read_json(args.marker,16384);retained_metadata(pins,running=True,marker=marker)
    report={'kind':'readonly_fresh_core_noop_v1','connections':0,'sourceRamReads':0,'businessWrites':0,'queries':[],'fullAcceptance':False}
    snapshot=None
    try:
        require(not (run/'worker-ram-request.json').exists(),'SOURCE','This allocation already attempted its fresh worker RAM read')
        save(run/'worker-ram-request.json',{'socket':str(RAM),'attemptedAt':datetime.now(timezone.utc).isoformat(),'outcome':'requested_not_yet_decoded'})
        capture=load(FROZEN/'capture.py','readonly_core_frozen_capture_worker');snapshot=capture.fetch_snapshot(RAM);report['sourceRamReads']=1
        save(run/'worker-ram-read.json',{'socket':str(RAM),'captureCodeSha256':snapshot['captureCodeSha256'],'manifestSha256':snapshot['manifestSha256'],'documentCount':len(snapshot['cache']),'outcome':'decoded'})
        candidate=load(FROZEN/'candidate.py','readonly_core_frozen_candidate')
        with connect(marker,'orion_pro_ingest',report) as c:
            result=candidate.import_candidate(c,run,snapshot,core_only=True)
        core=result['core'];require(core['reused'] is True and core['newFactRevisions']==core['duplicateRows']==0 and 'spatial' not in result,
            'NOOP','Fresh readonly core path must reuse the exact prior source receipt')
        receipt=core['phaseReceipt'];require((receipt['generation'],receipt['snapshotId'],receipt['runId'])==(2,2,1),'NOOP','Fresh reused core identity differs')
        report.update(status='pass',coreReused=True,newFactRevisions=0,duplicateRows=0,spatialCalled=False,phaseReceipt=receipt)
    except BaseException as error:
        report.update(status='fail',reasonCode=getattr(error,'code','NOOP'),errorType=type(error).__name__,sqlstate=getattr(error,'sqlstate',None));raise
    finally:
        if snapshot is not None:snapshot.clear()
        report['ramReadOutcomeUnknown']=(run/'worker-ram-request.json').exists() and report['sourceRamReads']==0
        save(run/'fresh-noop.json',report)
    print(json.dumps({'status':'pass','sourceRamReads':1,'coreReused':True,'newFactRevisions':0,'spatialCalled':False}),flush=True)
    return 0

def main():
    ap=argparse.ArgumentParser(description=__doc__);m=ap.add_mutually_exclusive_group();m.add_argument('--recover',action='store_true');m.add_argument('--noop-worker',action='store_true')
    ap.add_argument('--release',type=Path);ap.add_argument('--release-sha256');ap.add_argument('--marker',type=Path);ap.add_argument('--evidence',type=Path);args=ap.parse_args()
    base_report={'kind':'committed_core_readonly_recovery_v1','pgStarts':0,'connections':0,'sourceRamReads':0,'sourceConstructions':0,'businessWrites':0,'remoteCalls':0,'fullAcceptance':False}
    if not (args.recover or args.noop_worker):print(json.dumps({**base_report,'status':'offline_plan'}));return 0
    try:pins,release,allocation=checked_release(args,worker=args.noop_worker)
    except BaseException as error:
        print(json.dumps({**base_report,'status':'refused','reasonCode':getattr(error,'code','RELEASE'),'errorType':type(error).__name__}));return 1
    sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'dashboard/scripts'),'/tmp/statarena-publication-test-python']
    if args.noop_worker:
        try:return noop_worker(args,pins,release,allocation)
        except BaseException as error:
            observed={}
            if args.evidence and Path(args.evidence).resolve().is_relative_to(BASE/'runs'):
                failure=Path(args.evidence)/'fresh-noop.json'
                if failure.is_file():
                    detail=read_json(failure);observed={k:detail[k] for k in ['connections','sourceRamReads','ramReadOutcomeUnknown'] if k in detail}
            print(json.dumps({**base_report,**observed,'status':'refused','reasonCode':getattr(error,'code','NOOP'),'errorType':type(error).__name__,'sqlstate':getattr(error,'sqlstate',None)}));return 1
    from orion_e2e_process import run_bounded
    started=time.monotonic();deadline=started+300;run=BASE/'runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');(run/'inputs').mkdir(parents=True)
    report={**base_report,'status':'running','command':[sys.executable,*sys.argv],'expected':str(BASE/'PROTOCOL.md'),'cases':[],'commands':[],'resources':[],'queries':[],'releaseSha256':args.release_sha256}
    for p in [PINS,Path(__file__),BASE/'e2e.py',BASE/'PROTOCOL.md',args.release.resolve(),*[ROOT/p for p in pins['files']]]:
        dest=run/'inputs'/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
    old=None;owned_started=False;start_attempted=False;control=None;control_dir=None;marker=None;cleanup=False;cleanup_deadline=None;last=[0.];clients=[]
    def resource_reason():
        if cleanup:return None
        now=time.monotonic()
        if now-last[0]<1:return None
        last[0]=now;disk=int(subprocess.check_output(['du','-sk',str(TYPED_ROOT)],text=True,timeout=5).split()[0])*1024;proof=sum(p.stat().st_size for p in run.rglob('*') if p.is_file())
        report['resources'].append({'seconds':round(now-started,3),'ownedBytes':disk,'proofBytes':proof})
        return 'resource_bound' if disk>=3*1024**3 or proof>=64*1024**2 else None
    def command(argv,label,check=True):
        got=run_bounded([str(v) for v in argv],cwd=ROOT,env={k:v for k,v in os.environ.items() if not k.startswith('PG')},deadline=cleanup_deadline if cleanup else deadline,stop_reason=resource_reason)
        n=len(report['commands']);(run/f'{n}-{label}.stdout.log').write_text(got.stdout);(run/f'{n}-{label}.stderr.log').write_text(got.stderr);report['commands'].append({'command':[str(v) for v in argv],'exitCode':got.returncode,'stdout':f'{n}-{label}.stdout.log','stderr':f'{n}-{label}.stderr.log'})
        require(not check or got.returncode==0,'PROCESS','Owned recovery child failed: '+label);return got
    def stage(name,fn):
        require(time.monotonic()<deadline and resource_reason() is None,'BOUND','Recovery active deadline/resource limit')
        tick=time.monotonic()
        try:value=fn()
        except BaseException as error:report['cases'].append({'case':name,'status':'fail','errorType':type(error).__name__,'sqlstate':getattr(error,'sqlstate',None)});raise
        report['cases'].append({'case':name,'status':'pass','seconds':round(time.monotonic()-tick,3),'actual':value});save(run/'progress.json',report);return value
    def interrupted(signum,frame):raise KeyboardInterrupt()
    def alarm(signum,frame):raise TimeoutError('Readonly core recovery active deadline')
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted);signal.signal(signal.SIGALRM,alarm);signal.setitimer(signal.ITIMER_REAL,max(.001,deadline-time.monotonic()))
    try:
        old=stage('retained_stopped_root',lambda:retained_metadata(pins))
        with allocation.open('x') as out:json.dump({'run':str(run),'releaseSha256':args.release_sha256,'state':'consumed','pgRestarts':1},out,indent=2)
        private=tempfile.mkdtemp(prefix='orion-core-checkpoint-',dir='/tmp');control_dir=Path(private);control_dir.chmod(0o700)
        # Startup flags affect this retained service; no config, schema or business SQL is written.
        start_attempted=True
        command([PG_BIN/'pg_ctl','-D',TYPED_ROOT/'data','-l',run/'postgres.log','-o',f'-h 127.0.0.1 -p 55467 -k {control_dir} -c fsync=on -c default_transaction_read_only=on -c statement_timeout=8000 -c lock_timeout=1000','-w','start'],'retained-start')
        owned_started=True;report['pgStarts']=1;marker=initial_marker(old,report);marker_path=TYPED_ROOT/'core-native-marker-v1.json';save(marker_path,marker);marker_path.chmod(0o600)
        checks=load(FROZEN/'e2e.py','readonly_core_frozen_independent_oracle');transport=load(ROOT/'dashboard/scripts/orion_pro_native_transport.py','readonly_core_transport_descriptor')
        model=read_json(ROOT/'docs/architecture/orion-plan-20261104/target-schema.proposed.json');tables={t['qualified_name']:t for s in model['schemas'] for t in s['tables'] if t['phase']!='models'}
        from orion_pro_bulk_local import oracle,sequences
        def identity_policy():
            with connect(marker,'orion_pro_runtime',report) as c:
                actual=checks.validator_metadata(c);expected=read_json(PRIOR/'local-validator-overlay.json')['after'];require(actual==expected,'POLICY','Retained P1 native validator metadata differs')
                foreign_keys=c.execute("SELECT count(*) FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname IN ('ingest','football','analytics') AND k.contype='f'").fetchone()[0]
                require(foreign_keys==431,'POLICY','Exact431native foreign keys required')
                journal=c.execute('SELECT version,content_sha256,applied_at::text,code_commit FROM ingest.schema_migrations ORDER BY version').fetchall()
                require([r[0] for r in journal]==['012','013'],'POLICY','Source journal must remain012013, without fabricated014')
                with c.transaction():c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY');descriptor=transport.describe_endpoint(c,source=True,origin='real_native_sql_checkpoint')
            counts=descriptor['nativeCatalogueCounts'];require(all(counts.get(k)==v for k,v in {'table':94,'column':1709,'constraint':2475,'view':46,'sequence':67}.items()),'POLICY','Native source catalogue count differs')
            save(run/'source-descriptor.json',descriptor);return {'validator':actual,'catalogueCounts':counts,'foreignKeys':foreign_keys,'catalogueSha256':descriptor['catalogueSha256'],'journal':journal}
        stage('exact_readonly_identity_and_policy',identity_policy)
        def core_phase():
            with connect(marker,'orion_pro_runtime',report) as c:
                counts={name:c.execute('SELECT count(*) FROM '+'.'.join('"'+v+'"' for v in name.split('.'))).fetchone()[0] for name in pins['expectedCounts']}
                require(counts==pins['expectedCounts'],'CORE','Committed core-only source counts differ')
                rows=c.execute("SELECT r.id,r.status,r.transform_version,r.code_commit,r.checkpoint->>'phase',s.id,s.generation,s.status,s.manifest_sha256 FROM ingest.import_runs r JOIN ingest.dataset_snapshots s ON s.id=(r.checkpoint->>'snapshot_id')::bigint ORDER BY s.generation").fetchall()
                require(len(rows)==1 and rows[0][:8]==(1,'partial','real_source_core_v2_native31',sha(ROOT/'dashboard/scripts/orion_pro_normalize.py'),'core',2,2,'sealed'),'CORE','One exact sealed original core phase is required')
            return {'counts':counts,'sourcePhases':[{'phase':'core','generation':2,'snapshotId':2,'runId':1,'manifest':rows[0][8]}]}
        core=stage('exact_single_committed_core',core_phase)
        save(run/'oracle-ram-request.json',{'socket':str(RAM),'attemptedAt':datetime.now(timezone.utc).isoformat(),'outcome':'requested_not_yet_decoded'})
        capture=load(FROZEN/'capture.py','readonly_core_frozen_capture');snapshot=capture.fetch_snapshot(RAM);report['sourceRamReads']+=1
        save(run/'oracle-ram-read.json',{'socket':str(RAM),'captureCodeSha256':snapshot['captureCodeSha256'],'manifestSha256':snapshot['manifestSha256'],'documentCount':len(snapshot['cache'])})
        parts=checks.unpack_independent(snapshot)
        def native31():
            with connect(marker,'orion_pro_runtime',report) as c:value,ok=checks.native_oracle(c,parts)
            save(run/'native31-oracle.json',value);require(ok and value['typedSlots']==478547 and value['sourcePerformances']==15437,'ORACLE','Independent source/native31 fidelity differs')
            return {'slots':value['typedSlots'],'sourceSha256':value['sourceSha256'],'typedSha256':value['typedSha256']}
        stage('independent_native31_core',native31);snapshot.clear();del parts
        def native_state():
            with connect(marker,'orion_pro_runtime',report) as c:native=oracle(c,tables)
            with connect(marker,'orion_pro_owner',report) as c:seq=sequences(c)
            return {'tables':native,'sequences':seq}
        before=stage('independent_native94_sequence67_before',native_state);save(run/'native94-before.json',before)
        got=stage('fresh_process_core_only_noop',lambda:command([sys.executable,Path(__file__),'--noop-worker','--release',args.release.resolve(),'--release-sha256',args.release_sha256,'--marker',marker_path,'--evidence',run],'fresh-core-noop').returncode)
        worker=read_json(run/'fresh-noop.json');require(worker['status']=='pass' and worker['sourceRamReads']==1,'NOOP','Fresh core-only worker not verified');report['sourceRamReads']+=1
        after=stage('independent_native94_sequence67_after',native_state);save(run/'native94-after.json',after);require(before==after,'NOOP','Core noop changed a native table or sequence value')
        require(all(sha(ROOT/p)==h for p,h in pins['files'].items()),'INPUT','Frozen source counters or input bytes changed')
        descriptor=read_json(run/'source-descriptor.json')
        checkpoint={'kind':'owned_real_typed_sql_checkpoint_v1','ready':True,'scope':'committed_core_only','marker':marker,'markerPath':str(marker_path),
            'sourceDescriptor':str(run/'source-descriptor.json'),'sourceDescriptorSha256':sha(run/'source-descriptor.json'),'producerSha256':sha(ROOT/'dashboard/scripts/orion_pro_normalize.py'),
            'producerVersion':'real_source_core_v2_native31','manifestSha256':sha(FROZEN/'MANIFEST.json'),'candidateSha256':sha(FROZEN/'candidate.py'),'captureCodeSha256':sha(FROZEN/'capture.py'),
            'sourcePhases':core['sourcePhases'],'native94Sha256':hashed(before['tables']),'native94Evidence':str(run/'native94-before.json'),'sourceRows':sum(v['rows'] for v in before['tables'].values()),
            'serverDefaultReadOnly':True,'sourceConstructions':0,'businessWrites':0,'sourceRamReads':2,'remoteCalls':0,'fullAcceptance':False,'rawBodiesPersisted':False,
            'unavailableFamilies':['spatial_heatmaps','remaining_detailed_families','full_leaf_fidelity'],'spatialFailureReceipt':str(PRIOR/'result.json'),'originalSourceLedgerUnchanged':True}
        save(run/'checkpoint.json',checkpoint);report.update(status='ready',constructionSeconds=round(time.monotonic()-started,3),checkpointSha256=sha(run/'checkpoint.json'))
        signal.setitimer(signal.ITIMER_REAL,0);save(run/'ready.json',report)
        control=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);control.bind(str(control_dir/'control.sock'));os.chmod(control_dir/'control.sock',0o600);control.listen(1);control.settimeout(1)
        print(json.dumps({'status':'ready','checkpoint':str(run/'checkpoint.json'),'checkpointSha256':sha(run/'checkpoint.json'),'control':str(control_dir/'control.sock'),'port':55467}),flush=True)
        idle_started=time.monotonic()
        while time.monotonic()-idle_started<3600:
            require(resource_reason() is None,'BOUND','Readonly retained source resource limit')
            try:client,_=control.accept()
            except socket.timeout:continue
            with client:
                client.settimeout(2)
                if client.recv(32)==b'STOP\n':report['status']='stopped_cleanly';break
        else:raise TimeoutError('Readonly core retained idle lifetime exhausted')
        report['idleServiceSeconds']=round(time.monotonic()-idle_started,3)
    except BaseException as error:
        report.update(status='fail',reasonCode=getattr(error,'code','RECOVERY'),errorType=type(error).__name__,sqlstate=getattr(error,'sqlstate',None),traceback=traceback.format_exc())
    finally:
        signal.setitimer(signal.ITIMER_REAL,0);cleanup=True;cleanup_deadline=time.monotonic()+15
        if control is not None:control.close()
        for c in clients:c.close()
        if start_attempted and (owned_started or (TYPED_ROOT/'data/postmaster.pid').exists()):
            try:
                result=command([PG_BIN/'pg_ctl','-D',TYPED_ROOT/'data','-m','fast','-w','stop'],'retained-stop');report['cleanup']={'serverStopped':result.returncode==0,'ownedRootRetained':TYPED_ROOT.exists(),'corpusDeleted':False}
            except BaseException as error:report['cleanup']={'serverStopped':False,'ownedRootRetained':True,'errorType':type(error).__name__};report['status']='fail'
        else:report['cleanup']={'pgStarted':False,'ownedRootRetained':True,'corpusDeleted':False}
        if control_dir is not None:
            try:
                if (TYPED_ROOT/'data/postmaster.pid').exists():report['cleanup']['privateControlRetained']=str(control_dir)
                else:
                    for child in control_dir.iterdir():
                        require(child.name in ['control.sock','.s.PGSQL.55467','.s.PGSQL.55467.lock'],'OWNED','Unexpected private control file retained')
                        child.unlink()
                    control_dir.rmdir()
            except BaseException as error:report['cleanup']['privateControlCleanupError']=type(error).__name__
        report['sourceRamReadAttempts']=sum((run/(label+'-ram-request.json')).exists() for label in ['oracle','worker'])
        report['sourceRamReads']=sum((run/(label+'-ram-read.json')).exists() for label in ['oracle','worker'])
        report['ramReadOutcomeUnknown']=report['sourceRamReadAttempts']!=report['sourceRamReads']
        report['elapsedSeconds']=round(time.monotonic()-started,3);report['inputHashesExact']=all(sha(ROOT/p)==h for p,h in pins['files'].items());save(run/'result.json',report)
        print(json.dumps({'status':report['status'],'evidence':str(run/'result.json'),'cleanup':report['cleanup']}),flush=True)
    return 0 if report['status']=='stopped_cleanly' else 1

if __name__=='__main__':raise SystemExit(main())
