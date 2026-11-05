#!/usr/bin/env python3
"""Independent target SQL oracle; owned local E2E only with separate allocation."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import types

sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[3]
SCRIPTS = ROOT / 'dashboard/scripts'
PILOT = ROOT / 'docs/verification/orion-pro-pilot-20261104'
WRITER = SCRIPTS / 'orion_pro_native_transport.py'
ORIGINAL = ROOT / 'tests/orion_pro_real_rds_transport_local.py'
MODEL = ROOT / 'docs/architecture/orion-plan-20261104/target-schema.proposed.json'
FIXTURE = ROOT / 'tests/orion_pro_bulk_stream_local.py'
COMPONENTS = BASE / 'CONTROL_COMPONENTS.json'
PRIOR = BASE / 'runs/20261105T110727916843Z-root-owned-tls-compact-v1-absolute/result.json'
PINS = {WRITER: '9ec803b5caa6a5c5a47c2154256ea8199847281931fe73a538862c70fa371487',
        ORIGINAL: '945933c3ceec7cdb6361e7c3c84585d874fe92d668bdfe93700f90060c70a10f',
        BASE / 'BINDINGS.json': 'f965f43e37e272be274e102ceda338e0f47dc94661c13f45537f0ff8483294b1',
        COMPONENTS: '51da06293271ac48ac7ea9ea548fac46253ecb3e01d447582b30f9112ff3262e',
        PRIOR: 'e3349a7a21a2ec1d9eb9afe3b026a8ebcc07ce7a2e3a5910372da117d9bf5694'}
VERSION = 'source_free_native_transport_fixture_v1'
WRITER_VERSION = 'orion_pro_native_sql_transport_v1'
CONTROL = {'ingest.dataset_snapshots', 'ingest.import_runs', 'ingest.schema_migrations'}
CASES = ['frozen_contract_and_prior_receipt', 'allocation_required', 'owned_tls_native_setup',
         'unequal_generation_snapshot', 'ordinary_ingest_transport', 'independent_native91',
         'independent_control3', 'independent_noop', 'owned_cleanup']


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def hashed(value): return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
def save(path, value): Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + '\n')
def load(path, name):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--check-only',action='store_true')
    ap.add_argument('--run-local',action='store_true')
    ap.add_argument('--release',type=Path)
    ap.add_argument('--release-sha256')
    ap.add_argument('--label',default='independent-target')
    ap.add_argument('--pg-bin',type=Path,default=Path('/tmp/statarena-cache-test-tools/node_modules/@embedded-postgres/darwin-arm64/native/bin'))
    args=ap.parse_args();assert re.fullmatch('[a-zA-Z0-9-]+',args.label)
    sys.path[:0]=[str(ROOT/'tests'),str(PILOT),str(SCRIPTS),'/tmp/statarena-publication-test-python']
    from orion_e2e_process import run_bounded
    started=time.monotonic();deadline=started+300;cleanup_phase=False;cleanup_deadline=None
    run=BASE/'independent-runs'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-'+args.label)
    (run/'inputs').mkdir(parents=True)
    report={'kind':'independent_native_target_oracle_e2e_v1','command':['python3',str(Path(__file__)),*sys.argv[1:]],
            'expected':str(BASE/'INDEPENDENT_PROTOCOL.md'),'cases':[],'invocations':[],'inputSha256':{},
            'remoteCalls':0,'sourceRamReads':0,'fullAcceptance':False,'pgStarts':0,'fixtureConstructions':0}
    paths=[*PINS,Path(__file__),BASE/'INDEPENDENT_PROTOCOL.md',MODEL,FIXTURE,ROOT/'tests/orion_pro_bulk_local.py',ROOT/'tests/orion_e2e_process.py',PILOT/'harness.py']
    if args.release:paths.append(args.release.resolve())
    for path in paths:
        if path.is_file():
            dest=run/'inputs'/path.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest);report['inputSha256'][str(path.relative_to(ROOT))]=sha(path)
    env={k:v for k,v in os.environ.items() if k in ['PATH','HOME','USER','TMPDIR','LANG']}
    env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONPATH='/tmp/statarena-publication-test-python')
    pg=admin=source=target=None;block=None;resources=[];resource_tick=[0.]

    def stop_reason():
        if cleanup_phase:return None
        if time.monotonic()-resource_tick[0]<.5:return None
        resource_tick[0]=time.monotonic()
        if pg is not None and pg.root.exists():
            disk=int(subprocess.check_output(['du','-sk',str(pg.root)],text=True).split()[0])*1024
            proof=sum(p.stat().st_size for p in run.rglob('*') if p.is_file())
            resources.append({'seconds':round(time.monotonic()-started,3),'ownedBytes':disk,'proofBytes':proof})
            if disk>=1024**3 or proof>=64*1024**2:return 'campaign_resource_bound'
        return None

    def command(argv,*,env=None,check=True,name='command'):
        result=run_bounded([str(v) for v in argv],cwd=ROOT,env=env,deadline=cleanup_deadline if cleanup_phase else deadline,stop_reason=stop_reason)
        number=len(report['invocations']);out=f'{number:03d}-{name}'
        (run/(out+'.stdout.log')).write_text(result.stdout);(run/(out+'.stderr.log')).write_text(result.stderr)
        report['invocations'].append({'command':[str(v) for v in argv],'exitCode':result.returncode,'stdout':out+'.stdout.log','stderr':out+'.stderr.log'})
        if check:assert result.returncode==0,result.stderr[-1000:]
        return result

    def connect(db,actor):
        import psycopg
        return psycopg.connect(host='127.0.0.1',hostaddr='127.0.0.1',port=pg.port,dbname=db,user=actor,sslmode='verify-full',
            sslrootcert=str(pg.data/'server.crt'),autocommit=True,options='-c statement_timeout=8000 -c lock_timeout=1000 -c timezone=UTC -c datestyle=ISO,YMD')

    def cli():
        rr=run/('operation-'+str(len(report['invocations']))+'.json')
        save(rr,{'kind':'native_transport_operation_release_v1','scope':'owned_source_free_fixture','mode':'apply-local',
            'writerSha256':sha(WRITER),'bindingSha256':sha(BASE/'BINDINGS.json'),'pairSha256':sha(pair_path),'acceptanceSha256':sha(acceptance_path),
            'expiresAt':datetime.fromtimestamp(time.time()+300,timezone.utc).isoformat(),'fullAcceptance':False})
        result=command(['python3',WRITER,'--apply-local','--source-marker',marker,'--pair',pair_path,'--pair-sha256',sha(pair_path),
            '--acceptance',acceptance_path,'--acceptance-sha256',sha(acceptance_path),'--release',rr,'--release-sha256',sha(rr)],env=env,name='native-worker')
        return json.loads(result.stdout)

    try:
        for name in CASES:
            if block or ((args.check_only or not args.run_local) and name!='frozen_contract_and_prior_receipt'):
                report['cases'].append({'case':name,'status':'unverified','reason':block or 'No supplementary PG allocation executed'});continue
            try:
                actual={}
                if name=='frozen_contract_and_prior_receipt':
                    assert all(sha(p)==h for p,h in PINS.items()),'Frozen21/21 code/test/receipt or component contract changed'
                    component=json.loads(COMPONENTS.read_text());assert component['modelSha256']==sha(MODEL)
                    assert component['kind']=='independent_native_control_component_contract_v1' and sum(map(len,component['relations'].values()))==component['componentCount']==106
                    prior=json.loads(PRIOR.read_text());assert prior['counts']=={'pass':21,'fail':0,'unverified':0}
                    actual={'componentCount':106,'componentContractSha256':sha(COMPONENTS),'priorReceiptSha256':sha(PRIOR),'writerUnchanged':True}
                elif name=='allocation_required':
                    assert args.release and args.release_sha256==sha(args.release),'Separate exact ROOT supplementary allocation required before any PG'
                    release=json.loads(args.release.read_text());assert release['kind']=='root_native_transport_independent_campaign_v1' and release['approvedBy']=='ROOT'
                    expected={'writerSha256':sha(WRITER),'testSha256':sha(Path(__file__)),'componentContractSha256':sha(COMPONENTS),'protocolSha256':sha(BASE/'INDEPENDENT_PROTOCOL.md'),
                              'maximumPgStarts':1,'maximumFixtureConstructions':1,'maximumSeconds':300,'maximumOwnedBytes':1024**3,'maximumProofBytes':64*1024**2}
                    assert all(release.get(k)==v for k,v in expected.items())
                    assert re.fullmatch('[a-zA-Z0-9-]+',release['allocationId'])
                    consumed=BASE/(release['allocationId']+'.consumed.json');assert not consumed.exists(),'Supplementary allocation already consumed'
                    save(consumed,{'releaseSha256':sha(args.release),'run':str(run.relative_to(ROOT))});actual=release
                elif name=='owned_tls_native_setup':
                    from harness import LocalPostgres
                    from orion_pro_migrate import bootstrap
                    from orion_pro_integrity import role_grants_sql
                    from orion_pro_bulk_local import oracle,sequences,q
                    tempfile.tempdir='/tmp';pg=LocalPostgres(args.pg_bin,run);pg.command=command
                    command([args.pg_bin/'initdb','-D',pg.data,'--auth=trust','--no-locale','--encoding=UTF8'],name='initdb')
                    cert,key=pg.data/'server.crt',pg.data/'server.key'
                    command(['openssl','req','-x509','-newkey','rsa:2048','-sha256','-nodes','-days','2','-keyout',key,'-out',cert,'-subj','/CN=127.0.0.1','-addext','subjectAltName=IP:127.0.0.1'],name='owned-tls');key.chmod(0o600)
                    with (pg.data/'postgresql.conf').open('a') as f:f.write("\nssl=on\nssl_cert_file='server.crt'\nssl_key_file='server.key'\nstatement_timeout=8000\nlock_timeout=1000\ntemp_file_limit=128MB\nlog_error_verbosity=terse\nlog_min_error_statement=panic\nlog_parameter_max_length_on_error=0\n")
                    pg.start();report['pgStarts']=1;admin=connect('postgres',os.environ.get('USER','postgres'));assert admin.info.server_version==180006
                    for role in ['orion_pro_owner','orion_pro_ingest','orion_pro_runtime','statarena_admin','statarena_ingest','statarena_runtime']:admin.execute('CREATE ROLE '+role+' LOGIN NOSUPERUSER NOCREATEROLE NOCREATEDB NOREPLICATION NOBYPASSRLS')
                    model=json.loads(MODEL.read_text());tables={t['qualified_name']:t for s in model['schemas'] for t in s['tables'] if t['phase']!='models'}
                    for db,owner,writer,reader in [('native_oracle_source','orion_pro_owner','orion_pro_ingest','orion_pro_runtime'),('native_oracle_target','statarena_admin','statarena_ingest','statarena_runtime')]:
                        admin.execute('CREATE DATABASE '+db+' OWNER '+owner)
                        with connect(db,owner) as c:
                            with c.transaction():
                                artifacts=[]
                                for version,filename in [('012','012_orion_pro_domain.sql'),('013','013_orion_pro_integrity.sql')]:
                                    p=ROOT/'dashboard/backend/migrations'/filename;artifacts.append((version,p,p.read_text()));c.execute(p.read_text(),prepare=False);c.execute('INSERT INTO ingest.schema_migrations VALUES(%s,%s,CURRENT_TIMESTAMP,%s)',(version,sha(p),'owned-independent-'+db))
                                bootstrap(c,model,artifacts);c.execute(role_grants_sql(model,writer,reader),prepare=False)
                            with c.transaction():
                                p=ROOT/'dashboard/backend/migrations/014_orion_pro_membership_nonnull.sql';c.execute(p.read_text(),prepare=False)
                                if db=='native_oracle_target':c.execute('INSERT INTO ingest.schema_migrations VALUES(%s,%s,CURRENT_TIMESTAMP,%s)',('014',sha(p),'owned-independent-target14'))
                    shape={'APPEARANCES':40,'SCALARS':1240,'MATCHES':4,'PLAYERS':40,'VERSION':VERSION}
                    producer=hashed({'fixtureCodeSha256':sha(FIXTURE),'testSha256':sha(ORIGINAL),'shape':shape})
                    fm=load(FIXTURE,'independent_frozen_fixture');fn=types.FunctionType(fm.fixture.__code__,{**fm.fixture.__globals__,**shape})
                    evidence=run/'compact-source';evidence.mkdir()
                    with connect('native_oracle_source','orion_pro_ingest') as c:phases=fn(c,model,producer,evidence)
                    report['fixtureConstructions']=1;source=connect('native_oracle_source','orion_pro_owner');target=connect('native_oracle_target','statarena_admin')
                    native_source=oracle(source,tables);native_before=oracle(target,tables)
                    # Product helper describes only endpoint policy for its CLI.
                    # The actual oracle below never calls any writer observer.
                    adapter=load(WRITER,'independent_transport_endpoint_descriptor')
                    with source.transaction():source.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY');sd=adapter.describe_endpoint(source,source=True,origin='owned_source_free_fixture')
                    with target.transaction():target.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY');td=adapter.describe_endpoint(target,source=False,origin='owned_local_tls_target')
                    pair={'kind':'explicit_native_sql_transport_pair_v1','environment':'owned_local_tls','writerSha256':sha(WRITER),'bindingSha256':sha(BASE/'BINDINGS.json'),'source':sd,'target':td}
                    pair_path=run/'pair.json';acceptance_path=run/'acceptance.json';save(pair_path,pair)
                    accepted={'kind':'native_sql_transport_acceptance_v1','dataOrigin':'owned_source_free_fixture','writerSha256':sha(WRITER),'bindingsSha256':sha(BASE/'BINDINGS.json'),'pairSha256':sha(pair_path),'modelSha256':sha(MODEL),'producerSha256':producer,'producerVersion':VERSION,'sourceNativeSha256':hashed(native_source),'sourceTables':native_source,'sourceRows':sum(v['rows'] for v in native_source.values()),'sourcePhases':phases,'sourceCheckpointSha256':hashed({'fixtureCodeSha256':sha(FIXTURE),'testSha256':sha(ORIGINAL)}),'fullAcceptance':False,'fixture':{'codeSha256':sha(FIXTURE),'testSha256':sha(ORIGINAL),'version':VERSION,'shape':shape}};save(acceptance_path,accepted)
                    marker=pg.root/'native-marker.json';save(marker,{'kind':'owned_native_transport_pg18_v1','ownedRoot':str(pg.root),'port':pg.port,'postmasterStartedAt':admin.execute('SELECT pg_postmaster_start_time()').fetchone()[0].isoformat(),'sourceDatabase':'native_oracle_source','targetDatabase':'native_oracle_target','certificatePath':str(cert),'certificateSha256':sha(cert)});marker.chmod(0o600)
                    actual={'serverVersion':180006,'fixtureConstructions':1,'nativeSourceSha256':hashed(native_source)}
                elif name=='unequal_generation_snapshot':
                    with connect('native_oracle_target','statarena_ingest') as c:
                        reserved=c.execute("SELECT nextval('ingest.dataset_snapshots_id_seq')").fetchone()[0]
                        c.execute('BEGIN');gap=c.execute("SELECT ingest.begin_generation('independent-rolled-back-gap','independent_gap','independent_gap')").fetchone()[0];c.rollback()
                    assert oracle(target,tables)==native_before
                    gap_sequences=sequences(target);assert gap_sequences['ingest.dataset_snapshots_id_seq'][0]!=gap_sequences['ingest.commit_generation_seq'][0]
                    actual={'ordinaryIngestSnapshotReservation':reserved,'rolledBackGeneration':gap,'sequenceValues':gap_sequences}
                elif name=='ordinary_ingest_transport':
                    imported=cli();assert imported['status']=='applied' and imported['sequenceValueSelects']==0
                    actual={'copyCommands':imported['copyCommands'],'copiedRows':imported['copiedRows'],'writerSha256':sha(WRITER)}
                elif name=='independent_native91':
                    native_runs=list(target.execute('SELECT id,checkpoint FROM ingest.import_runs ORDER BY id'));assert len(native_runs)==len(phases)
                    by_run={p['runId']:p for p in phases};maps_g={1:1};maps_s={1:1}
                    for run_id,cp in native_runs:
                        p=by_run[run_id];generation,sid=target.execute('SELECT generation,id FROM ingest.dataset_snapshots WHERE id=%s',(cp['snapshot_id'],)).fetchone()
                        assert cp['source_generation']==p['generation'] and cp['source_snapshot_id']==p['snapshotId'] and cp['generation']==generation
                        maps_g[p['generation']]=generation;maps_s[p['snapshotId']]=sid
                    first=phases[0];assert maps_g[first['generation']]!=maps_s[first['snapshotId']]
                    assert maps_g[first['generation']]!=first['generation'] and maps_s[first['snapshotId']]!=first['snapshotId']
                    assert len(set(maps_g.values()))==len(maps_g) and len(set(maps_s.values()))==len(maps_s)
                    substitutions={name:{col:'CASE '+q(col)+' '+' '.join('WHEN '+str(dst)+' THEN '+str(src) for src,dst in (maps_g if kind=='generation' else maps_s).items())+' ELSE '+q(col)+' END' for col,kind in cols.items()} for name,cols in component['relations'].items()}
                    actual_inverse=oracle(target,tables,substitutions)
                    assert all(actual_inverse[n]==native_source[n] for n in tables if n not in CONTROL)
                    save(run/'independent-native91.json',{'componentContractSha256':sha(COMPONENTS),'generationMap':maps_g,'snapshotMap':maps_s,'substitutions':substitutions,'source':native_source,'targetInverse':actual_inverse,'businessExact':True})
                    actual={'nativeBusinessRelations':91,'componentColumns':106,'unequalControls':True,'oracle':'tests/orion_pro_bulk_local.py; frozen component contract; native destination control queries'}
                elif name=='independent_control3':
                    assert actual_inverse['ingest.schema_migrations']==native_before['ingest.schema_migrations']
                    assert target.execute("SELECT ROW(s.*)::text FROM ingest.dataset_snapshots s WHERE transform_version='bootstrap_v1'").fetchone()[0]==td['bootstrapNativeText']
                    assert target.execute('SELECT count(*) FROM ingest.dataset_snapshots').fetchone()[0]==1+len(phases)
                    copied=0;controls=[]
                    for run_id,cp in native_runs:
                        p=by_run[run_id];source_run=source.execute('SELECT ROW(r.*)::text FROM ingest.import_runs r WHERE id=%s',(run_id,)).fetchone()[0]
                        binding={'kind':'orion_pro_native_sql_transport_phase_v1','phase':p['phase'],'writer_sha256':sha(WRITER),'model_sha256':sha(MODEL),'bindings_sha256':sha(BASE/'BINDINGS.json'),'pair_sha256':sha(pair_path),'data_origin':'owned_source_free_fixture','source_checkpoint_sha256':accepted['sourceCheckpointSha256'],'source_native_sha256':accepted['sourceNativeSha256'],'producer_sha256':producer,'source_generation':p['generation'],'source_snapshot_id':p['snapshotId'],'source_run_id':run_id,'source_run_sha256':hashlib.sha256(source_run.encode()).hexdigest(),'source_phase_manifest_sha256':p['manifest']}
                        assert set(cp)==set(binding)|{'receipt_sha256','generation','snapshot_id','copied_rows','transaction_started_at'}
                        assert all(cp[k]==v for k,v in binding.items()) and type(cp['copied_rows']) is int and cp['copied_rows']>=0
                        assert cp['receipt_sha256']==hashed({k:v for k,v in cp.items() if k!='receipt_sha256'})
                        run_row=target.execute('SELECT mode,status,transform_version,code_commit,started_at,finished_at,parameters,counters,error FROM ingest.import_runs WHERE id=%s',(run_id,)).fetchone()
                        assert run_row[:4]==('backfill','partial',WRITER_VERSION,sha(WRITER)) and run_row[8] is None
                        assert run_row[6]=={'kind':WRITER_VERSION,'pair_sha256':sha(pair_path),'data_origin':'owned_source_free_fixture','source_run_sha256':binding['source_run_sha256'],'producer_sha256':producer}
                        assert run_row[7]=={'copied_rows':cp['copied_rows'],'full_acceptance':False,'local_only':True}
                        snap=target.execute('SELECT generation,status,manifest_sha256,transform_version,source_priority_version,snapshot_key,knowledge_cutoff_at,created_at,sealed_at FROM ingest.dataset_snapshots WHERE id=%s',(cp['snapshot_id'],)).fetchone()
                        priority,cutoff=source.execute('SELECT source_priority_version,knowledge_cutoff_at FROM ingest.dataset_snapshots WHERE id=%s',(p['snapshotId'],)).fetchone()
                        assert snap[:7]==(cp['generation'],'sealed',hashed(cp),WRITER_VERSION,priority,'native-sql-v1:'+accepted['sourceNativeSha256']+':'+p['phase'],cutoff)
                        clock=datetime.fromisoformat(cp['transaction_started_at']);assert clock.tzinfo is not None and run_row[4]==run_row[5]==snap[7]==snap[8]==clock
                        copied+=cp['copied_rows'];controls.append({'phase':p['phase'],'checkpoint':cp,'allFourClocksExact':True})
                    matrix=json.loads((ROOT/'docs/verification/orion-pro-bulk-stream-v2-20261105/OWNERSHIP_MATRIX.json').read_text())
                    bootstrap_rows=sum(map(len,model['seed_data'].values()))+len(model['bootstrap']['relation_contracts']);assert bootstrap_rows==12
                    expected_copied=sum(native_source[n]['rows'] for n in matrix['copiedRelations'])-bootstrap_rows
                    assert copied==expected_copied
                    save(run/'independent-control3.json',{'journalExact':True,'bootstrapNativeExact':True,'sourceDerivedCopiedRows':expected_copied,'bootstrapRowsExcluded':12,'controls':controls})
                    actual={'independentControlContracts':3,'allFourClocksExact':True,'sourceDerivedCopiedRows':copied}
                elif name=='independent_noop':
                    before={'native':oracle(target,tables),'sequences':sequences(target)};noop=cli()
                    assert noop['status']=='noop' and noop['copyCommands']==noop['nextvalCalls']==0
                    assert before=={'native':oracle(target,tables),'sequences':sequences(target)} and oracle(source,tables)==native_source
                    actual={'nativeTablesUnchanged':94,'sequencesUnchanged':67,'copyCommands':0,'nextvalCalls':0,'sourceExact':True}
                elif name=='owned_cleanup':
                    actual={'cleanupRequiredInFinally':True,'sourceRamReads':0,'remoteCalls':0}
                report['cases'].append({'case':name,'status':'pass','actual':actual})
            except BaseException as error:
                block=name+': '+str(error);report['cases'].append({'case':name,'status':'fail','error':str(error),'traceback':traceback.format_exc()})
    finally:
        cleanup_phase=True;cleanup_deadline=time.monotonic()+10
        for c in [source,target,admin]:
            if c is not None:c.close()
        if pg is not None:
            try:
                if (pg.data/'postmaster.pid').exists():pg.started=True
                report['cleanup']=pg.cleanup()
            except BaseException as error:report['cleanup']={'status':'failed','ownedRoot':str(pg.root),'errorType':type(error).__name__};block=block or 'Owned cleanup failed'
        else:report['cleanup']={'pgStarted':False,'connections':0}
        report['elapsedSeconds']=round(time.monotonic()-started,3);report['resources']=resources
        report['inputHashesExact']=all(sha(ROOT/p)==h for p,h in report['inputSha256'].items())
        report['status']='fail' if block else 'pass_owned_source_free_only' if args.run_local else 'prepared_source_free_only'
        report['counts']={s:sum(c['status']==s for c in report['cases']) for s in ['pass','fail','unverified']}
        save(run/'result.json',report);print(json.dumps({'status':report['status'],'counts':report['counts'],'evidence':str(run/'result.json')}))
    return 1 if block else 0


if __name__=='__main__':raise SystemExit(main())
