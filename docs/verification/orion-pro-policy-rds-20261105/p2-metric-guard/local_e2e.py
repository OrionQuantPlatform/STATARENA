#!/usr/bin/env python3
"""Before-code operational E2E for isolated015. PG requires a new ROOT release."""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import hashlib,importlib.util,json,os,re,shutil,signal,sys,tempfile,threading,time,traceback
from pathlib import Path

sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[3];OPERATOR=BASE/'adopt_p2.py';MIG=ROOT/'dashboard/backend/migrations'
MODEL=ROOT/'docs/architecture/orion-plan-20261104/target-schema.proposed.json';DBS=['p2_policy_empty','p2_policy_companion'];ACTOR='statarena_admin'
OPTIONS='-c default_transaction_read_only=on -c statement_timeout=8000 -c lock_timeout=1000 -c idle_in_transaction_session_timeout=15000 -c search_path=pg_catalog -c timezone=UTC -c datestyle=ISO,YMD -c extra_float_digits=3'
CASES=['implementation_available','isolated_scope','released_owned_tls_setup','prepare_rollback_templates','origin_boundaries','foreign_business_refusal','lease_and_concurrency_refusals','atomic_failures','adoption_clock_and_preservation','lost_ack_independent_readback','fresh_cli_noop','native_catalogue_acl_refusals','journal_and_privilege_guards','sequence_drift_no_reset','bounded_observer','protected_inputs_and_cleanup']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):Path(p).write_text(json.dumps(v,indent=2,default=str)+'\n')
def load(p,n):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def q(v):assert re.fullmatch('[a-z_][a-z0-9_]*',v);return '"'+v+'"'

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--run-local',action='store_true');ap.add_argument('--check-only',action='store_true');ap.add_argument('--release',type=Path);ap.add_argument('--release-sha256');ap.add_argument('--pg-bin',type=Path,default=Path('/tmp/statarena-cache-test-tools/node_modules/@embedded-postgres/darwin-arm64/native/bin'));args=ap.parse_args();assert not(args.run_local and args.check_only)
 sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'dashboard/scripts'),str(ROOT/'docs/verification/orion-pro-pilot-20261104'),'/tmp/statarena-publication-test-python'];from orion_e2e_process import run_bounded
 started=time.monotonic();deadline=started+300;cleanup=False;cleanup_deadline=None;pg=None;clients=[];owners={};contracts={};marker=None;block=None;operator=None;psycopg=None;model=None;watch=None;watch_stop=threading.Event();budget_reason=[None];resources=[]
 run=BASE/'owned-runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');(run/'inputs').mkdir(parents=True)
 report={'kind':'isolated_native015_owned_operational_e2e_v1','command':[sys.executable,str(Path(__file__)),*sys.argv[1:]],'expected':str(BASE/'PROTOCOL.md'),'cases':[],'inputSha256':{},'invocations':[],'pgStarts':0,'databases':0,'maximumOpenConnections':0,'remoteCalls':0,'sourceCalls':0,'sourceRamReads':0,'setvalCalls':0,'productionMigrationInstalled':False,'fullAcceptance':False}
 paths=[Path(__file__),BASE/'PROTOCOL.md',BASE/'PINS.json',BASE/'P2_POLICY.json',OPERATOR]
 if (BASE/'PINS.json').is_file():paths += [ROOT/p for p in json.loads((BASE/'PINS.json').read_text())['files']]
 if args.release:paths.append(args.release.resolve())
 for p in set(paths):
  if p.is_file():d=run/'inputs'/p.relative_to(ROOT);d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,d);report['inputSha256'][str(p.relative_to(ROOT))]=sha(p)
 def tick():
  if not cleanup:assert time.monotonic()<deadline and budget_reason[0] is None,budget_reason[0] or '300-second global campaign deadline'
 def command(argv,*,env=None,check=True,name='command'):
  tick();r=run_bounded([str(x) for x in argv],cwd=ROOT,env=env,deadline=cleanup_deadline if cleanup else deadline,stop_reason=lambda:None if cleanup else budget_reason[0],term_seconds=1,drain_seconds=1,output_limit=2*1024**2);p=f'{len(report["invocations"]):03d}-{name}';(run/(p+'.stdout.log')).write_text(r.stdout);(run/(p+'.stderr.log')).write_text(r.stderr);report['invocations'].append({'command':[str(x) for x in argv],'exitCode':r.returncode,'stdout':p+'.stdout.log','stderr':p+'.stderr.log'})
  if check:assert r.returncode==0,r.stderr[-1500:]
  return r
 def connect(db,user=ACTOR):
  tick();assert sum(not c.closed for c in clients)<5
  c=psycopg.connect(host='127.0.0.1',hostaddr='127.0.0.1',port=pg.port,dbname=db,user=user,sslmode='verify-full',sslrootcert=str(pg.root/'server.crt'),autocommit=True,connect_timeout=5,options=OPTIONS);clients.append(c);report['maximumOpenConnections']=max(report['maximumOpenConnections'],sum(not x.closed for x in clients));return c
 def monitor():
  while not watch_stop.wait(1):
   try:
    r=run_bounded(['du','-sk',str(pg.root)],deadline=min(deadline,time.monotonic()+4),output_limit=4096);disk=int(r.stdout.split()[0])*1024;proof=sum(p.stat().st_size for p in run.rglob('*') if p.is_file());resources.append({'seconds':round(time.monotonic()-started,3),'ownedBytes':disk,'proofBytes':proof});save(run/'resources.json',resources)
    if disk>=1024**3 or proof>=64*1024**2:budget_reason[0]='owned_disk_1GiB' if disk>=1024**3 else 'evidence_64MiB';os.kill(os.getpid(),signal.SIGALRM);return
   except BaseException as e:
    if not watch_stop.is_set():budget_reason[0]='resource_monitor:'+type(e).__name__;os.kill(os.getpid(),signal.SIGALRM)
    return
 def stopped(signum,frame):raise TimeoutError(budget_reason[0] or '300-second global campaign deadline')
 def state(db=DBS[0]):
  c=owners[db]
  with c.transaction():c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY');return local_observe(c,identity_check=lambda row:operator.verify_owned_identity(row,db,json.loads(marker.read_text())))
 def local_observe(c,**kwargs):
  caps={**operator.observer.DEFAULT_ROWS,'journal':5}
  return operator.observe(c,caps,**kwargs)
 def contract(db=DBS[0]):return operator.load_owned_contract(contracts[db],sha(contracts[db]))
 def preflight(db=DBS[0]):return operator.owned_preflight(marker,db,contracts[db],sha(contracts[db]))
 def acceptance(db=DBS[0]):
  p=run/(db+'-acceptance-'+str(time.monotonic_ns())+'.json');save(p,{'kind':'owned_isolated015_acceptance_v1','localOnly':True,'database':db,'operatorSha256':sha(OPERATOR),'contractSha256':sha(contracts[db]),'beforeStateSha256':preflight(db)['stateSha256'],'releaseCommit':'owned_p2_adoption_e2e'});return p
 def apply(db=DBS[0],fault=None):
  a=acceptance(db);return operator.owned_transition(marker,db,contracts[db],sha(contracts[db]),a,sha(a),fault=fault)
 def refuses(fn,code):
  try:fn()
  except operator.Refusal as e:assert e.code in ({code} if isinstance(code,str) else set(code)),(e.code,code);return {'code':e.code}
  raise AssertionError('Expected isolated015 refusal: '+str(code))
 def unchanged(before,after):assert operator.state_hash(before)==operator.state_hash(after)
 def cli(flags,label,check=True):
  env={k:v for k,v in os.environ.items() if not k.startswith('PG')};env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONPATH='/tmp/statarena-publication-test-python');r=command([sys.executable,OPERATOR,*flags],env=env,check=check,name=label);return r
 try:
  for case in CASES:
   if block or (not args.run_local and case not in CASES[:2]):report['cases'].append({'case':case,'status':'unverified','reason':block or 'No owned PG allocation consumed'});continue
   try:
    actual={}
    if case=='implementation_available':
     assert OPERATOR.is_file(),'Isolated015 implementation absent (expected precode RED)';operator=load(OPERATOR,'isolated015_operator');original_owned_connection=operator.owned_connection
     def counted_owned_connection(*a,**k):
      assert sum(not c.closed for c in clients)<5
      c,verify=original_owned_connection(*a,**k);clients.append(c);report['maximumOpenConnections']=max(report['maximumOpenConnections'],sum(not x.closed for x in clients));return c,verify
     operator.owned_connection=counted_owned_connection;actual={'operatorSha256':sha(OPERATOR),'operatorOwnedConnectionsCounted':True}
    elif case=='isolated_scope':
     m=operator.fixed_inputs();assert m['policyId']=='metric-membership-guard-m18da43-rds015-v1' and m['baseline']['stateSha256']=='d237d4d98611829aa4c5ba588629fc943de673eeee1b4640ecef8cd087f9b8b4';assert sha(operator.SQL15)=='3b85fcb4fe9380cc5f96238620ff3f4bedee7485ed52c98fef0bddfac1092bd7';model=json.loads(MODEL.read_text());actual={'modelUnchanged':True,'exact015Candidate':True,'actualAccountedSequenceBaseline':True,'oldPoliciesNotAliased':True}
    elif case=='released_owned_tls_setup':
     assert args.release and args.release.is_absolute() and sha(args.release)==args.release_sha256 and not any(k.startswith('PG') for k in os.environ)
     release=json.loads(args.release.read_text());wanted={'kind':'root_owned_isolated015_campaign_v1','authorizedBy':'ROOT','operatorSha256':sha(OPERATOR),'e2eSha256':sha(Path(__file__)),'pinsSha256':sha(BASE/'PINS.json'),'protocolSha256':sha(BASE/'PROTOCOL.md'),'maximumPgStarts':1,'maximumDatabases':2,'maximumConnections':5,'maximumSeconds':300,'maximumOwnedBytes':1024**3,'maximumProofBytes':64*1024**2};assert all(release.get(k)==v for k,v in wanted.items())
     assert re.fullmatch('[A-Za-z0-9-]+',release['allocationId']);fd=os.open(BASE/(release['allocationId']+'.consumed.json'),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o644)
     with os.fdopen(fd,'w') as f:json.dump({'run':str(run),'releaseSha256':sha(args.release),'executions':1},f);f.write('\n')
     signal.signal(signal.SIGALRM,stopped);signal.setitimer(signal.ITIMER_REAL,max(.1,deadline-time.monotonic()));import psycopg as driver;psycopg=driver
     from harness import LocalPostgres
     from orion_pro_migrate import bootstrap
     from orion_pro_integrity import role_grants_sql
     tempfile.tempdir='/tmp';pg=LocalPostgres(args.pg_bin,run);pg.command=command;command([args.pg_bin/'initdb','-D',pg.data,'--auth=trust','--no-locale','--encoding=UTF8'],name='initdb');command(['openssl','req','-x509','-newkey','rsa:2048','-sha256','-nodes','-days','2','-keyout',pg.root/'server.key','-out',pg.root/'server.crt','-subj','/CN=127.0.0.1','-addext','subjectAltName=IP:127.0.0.1'],name='owned-tls');(pg.root/'server.key').chmod(0o600)
     with (pg.data/'postgresql.conf').open('a') as f:f.write("\nssl=on\nssl_cert_file='"+str(pg.root/'server.crt')+"'\nssl_key_file='"+str(pg.root/'server.key')+"'\nstatement_timeout=8000\nlock_timeout=1000\nlog_error_verbosity=terse\nlog_min_error_statement=panic\nlog_parameter_max_length_on_error=0\ntemp_file_limit=128MB\n")
     report['pgStarts']=1;pg.start();watch=threading.Thread(target=monitor,daemon=True);watch.start();setup=connect('postgres',os.environ.get('USER','postgres'));assert setup.info.server_version==180006;setup.execute('SET default_transaction_read_only=off')
     for role in [ACTOR,'statarena_ingest','statarena_runtime']:setup.execute('CREATE ROLE '+q(role)+' LOGIN NOSUPERUSER '+('CREATEROLE CREATEDB' if role==ACTOR else 'NOCREATEROLE NOCREATEDB')+' NOREPLICATION NOBYPASSRLS')
     for db in DBS:setup.execute('CREATE DATABASE '+q(db)+' OWNER '+q(ACTOR));report['databases']+=1
     epoch=setup.execute('SELECT pg_postmaster_start_time()').fetchone()[0].isoformat();setup.close();marker=pg.root/'p2-owned-marker.json';save(marker,{'kind':'isolated015_owned_pg18_v1','ownedRoot':str(pg.root),'port':pg.port,'serverStartedAt':epoch,'certificatePath':str(pg.root/'server.crt'),'certificateSha256':sha(pg.root/'server.crt')});marker.chmod(0o600)
     for db in DBS:
      c=connect(db);owners[db]=c
      with c.transaction():
       c.execute('SET TRANSACTION READ WRITE');artifacts=[]
       for version,name in [('012','012_orion_pro_domain.sql'),('013','013_orion_pro_integrity.sql')]:
        p=MIG/name;c.execute(p.read_text(),prepare=False);artifacts.append((version,p,p.read_text()));c.execute('INSERT INTO ingest.schema_migrations VALUES(%s,%s,CURRENT_TIMESTAMP,%s)',(version,sha(p),'owned_p2_baseline'))
       bootstrap(c,model,artifacts);c.execute(role_grants_sql(model,'statarena_ingest','statarena_runtime'),prepare=False);c.execute((MIG/'014_orion_pro_membership_nonnull.sql').read_text(),prepare=False);c.execute('INSERT INTO ingest.schema_migrations VALUES(%s,%s,CURRENT_TIMESTAMP,%s)',('014',sha(MIG/'014_orion_pro_membership_nonnull.sql'),'owned_p2_baseline'));c.execute('CREATE SCHEMA statarena;CREATE SCHEMA statarena_app',prepare=False)
      ingest=connect(db,'statarena_ingest')
      with ingest.transaction(force_rollback=True):ingest.execute('SET TRANSACTION READ WRITE');ingest.execute("SELECT nextval('football.players_id_seq') FROM generate_series(1,3)");ingest.execute("SELECT ingest.begin_generation('owned-sequence-gap','owned-gap','owned-gap')")
      ingest.close();save(run/(db+'-baseline-native.json'),state(db))
     actual={'tls':True,'engine':180006,'baseline':'sealed014','localAdminFlags':'NOSUPERUSER CREATEDB CREATEROLE','naturalSequenceGapsCreatedBeforeCapture':True,'setvalCalls':0}
    elif case=='prepare_rollback_templates':
     actual=[]
     for db in DBS:
      before=state(db);p=run/(db+'-contract.json');result=operator.prepare_owned(marker,db,p);contracts[db]=p;after=state(db);unchanged(before,after);c=contract(db);assert c['localOnly'] is True and c['p2DefinitionSha256']==operator.fixed_inputs()['definition']['canonicalP2Sha256'];actual.append({'database':db,'contractSha256':sha(p),'preparation':result,'native67RollbackExact':True})
    elif case=='origin_boundaries':
     wrong_kind=run/'real-kind-is-not-owned.json';wrong_kind.write_bytes((BASE/'P2_POLICY.json').read_bytes());r=cli(['--owned-preflight','--marker',str(marker),'--database',DBS[0],'--contract',str(wrong_kind),'--contract-sha256',sha(wrong_kind)],'real-metadata-as-local',False);assert r.returncode==2 and json.loads(r.stdout)['code']=='ORIGIN';actual={'realMetadataNeverLocalContract':True}
    elif case=='foreign_business_refusal':
     before=state(DBS[1]);c=owners[DBS[1]]
     with c.transaction(force_rollback=True):
      c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ WRITE');c.execute("INSERT INTO ingest.import_runs(id,mode,transform_version,code_commit) OVERRIDING SYSTEM VALUE VALUES(900001,'repair','owned_foreign_refusal','owned')");foreign=local_observe(c,local_write=True);actual=refuses(lambda:operator.verify_state(foreign,contract(DBS[1])),{'BUSINESS'});assert foreign['groups']['nonbootstrap']
     unchanged(before,state(DBS[1]));actual['explicitIdentityDidNotConsumeSequence']=True
    elif case=='lease_and_concurrency_refusals':
     actual=[]
     for key in ["SELECT pg_advisory_xact_lock(20261104,2)","SELECT pg_advisory_xact_lock(20261104,1)","SELECT pg_advisory_xact_lock(97813003::bigint)"]:
      a=acceptance();peer=connect(DBS[0])
      try:
       with peer.transaction():peer.execute(key);actual.append(refuses(lambda:operator.owned_transition(marker,DBS[0],contracts[DBS[0]],sha(contracts[DBS[0]]),a,sha(a)),{'LEASE'}))
      finally:peer.close()
     a=acceptance();peer=connect(DBS[0])
     try:
      with peer.transaction():peer.execute('SELECT 1');actual.append(refuses(lambda:operator.owned_transition(marker,DBS[0],contracts[DBS[0]],sha(contracts[DBS[0]]),a,sha(a)),{'CONCURRENCY'}))
     finally:peer.close()
    elif case=='atomic_failures':
     actual=[]
     for fault in ['after_function','after_journal']:
      before=state();error=refuses(lambda:apply(fault=fault),{'FAULT'});after=state();unchanged(before,after);actual.append({'fault':fault,**error,'beforeSha256':operator.state_hash(before),'afterSha256':operator.state_hash(after),'native67JournalClocksExact':True})
    elif case=='adoption_clock_and_preservation':
     before=state();result=apply();after=state();assert result['status']=='applied' and result['ddlStatements']==result['journalInserts']==1 and operator.verify_state(after,contract())=='P2';assert before['groups']['sequences']==after['groups']['sequences'] and before['groups']['bootstrap']==after['groups']['bootstrap'] and before['groups']['validator']==after['groups']['validator'] and after['groups']['journal'][:-1]==before['groups']['journal'];assert result['newJournalClock']['appliedAt']==result['newJournalClock']['transactionStart'];save(run/'applied-native.json',after);actual=result
    elif case=='lost_ack_independent_readback':
     try:apply(DBS[1],fault='after_commit')
     except operator.OutcomeUnverified:pass
     else:raise AssertionError('Lost acknowledgement must remain unknown before readback')
     fresh=preflight(DBS[1]);observed=state(DBS[1]);assert fresh['policy']=='P2' and fresh['stateSha256']==operator.state_hash(observed) and operator.verify_state(observed,contract(DBS[1]))=='P2';save(run/'companion-committed-native.json',observed);actual={'originallyUnknown':True,'freshIndependentConnectionPolicy':'P2','committedStateSha256':operator.state_hash(observed)}
    elif case=='fresh_cli_noop':
     actual=[]
     for db in DBS:
      a=acceptance(db);before=state(db);r=cli(['--owned-transition','--marker',str(marker),'--database',db,'--contract',str(contracts[db]),'--contract-sha256',sha(contracts[db]),'--acceptance',str(a),'--acceptance-sha256',sha(a)],'cold-noop-'+db);value=json.loads(r.stdout);assert value['status']=='reused' and value['ddlStatements']==value['journalInserts']==0;unchanged(before,state(db));actual.append(value)
    elif case=='native_catalogue_acl_refusals':
     actual=[];c=owners[DBS[0]]
     for statement in ["ALTER VIEW ingest.public_aliases_current SET (security_barrier=true)","REVOKE SELECT ON football.players FROM statarena_runtime"]:
      before=state()
      with c.transaction(force_rollback=True):c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ WRITE');c.execute(statement);actual.append(refuses(lambda:operator.verify_state(local_observe(c,local_write=True),contract()),{'CATALOGUE'}))
      unchanged(before,state())
    elif case=='journal_and_privilege_guards':
     actual=[];owner=owners[DBS[0]]
     for sql in ["UPDATE ingest.schema_migrations SET code_commit='forbidden' WHERE version='015'","DELETE FROM ingest.schema_migrations WHERE version='015'"]:
      try:
       with owner.transaction(force_rollback=True):owner.execute('SET TRANSACTION READ WRITE');owner.execute(sql)
       raise AssertionError('Immutable journal modification accepted')
      except psycopg.Error as e:assert e.sqlstate=='55000';actual.append({'actor':ACTOR,'sqlstate':e.sqlstate,'sql':sql})
     for user in ['statarena_ingest','statarena_runtime']:
      c=connect(DBS[0],user)
      try:
       tests=["INSERT INTO ingest.schema_migrations VALUES('099',repeat('0',64),CURRENT_TIMESTAMP,'forbidden')",operator.SQL15.read_text()]
       if user=='statarena_runtime':tests += ["SELECT ingest.validate_generation(1)","SELECT ingest.begin_generation('denied','test','test')","SELECT ingest.seal_generation(1,repeat('0',64))"]
       for sql in tests:
        try:
         with c.transaction(force_rollback=True):c.execute('SET TRANSACTION READ WRITE');c.execute(sql,prepare=False)
         raise AssertionError('Unprivileged schema/function access accepted')
        except psycopg.Error as e:assert e.sqlstate=='42501';actual.append({'actor':user,'sqlstate':e.sqlstate,'statementSha256':hashlib.sha256(sql.encode()).hexdigest()})
      finally:c.close()
    elif case=='sequence_drift_no_reset':
     before=state();c=connect(DBS[0],'statarena_ingest')
     try:
      with c.transaction():c.execute('SET TRANSACTION READ WRITE');new=c.execute("SELECT nextval('football.players_id_seq')").fetchone()[0]
     finally:c.close()
     actual=refuses(lambda:preflight(),{'SEQUENCE'});after=state();assert before['groups']['sequences']!=after['groups']['sequences'];actual.update(nextValue=new,monotoneGapRetained=True,setvalCalls=0)
    elif case=='bounded_observer':
     c=owners[DBS[1]];caps=dict(contract(DBS[1])['rowCaps']);caps['constraints']=1
     with c.transaction():c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY');actual=refuses(lambda:operator.observe(c,caps),{'BOUND'})
    else:actual={'protectedInputsExact':all(sha(ROOT/p)==h for p,h in report['inputSha256'].items()),'cleanupRequired':True};assert actual['protectedInputsExact']
    report['cases'].append({'case':case,'status':'pass','actual':actual});save(run/'progress.json',report);print('PASS '+case,flush=True)
   except BaseException as e:
    d=getattr(e,'diag',None);report['cases'].append({'case':case,'status':'fail','errorType':type(e).__name__,'error':d.message_primary if d else str(e),'sqlstate':getattr(e,'sqlstate',None),'databaseContext':d.context if d else None,'traceback':traceback.format_exc()});block='First unexpected failure: '+case;save(run/'progress.json',report);print('FAIL '+case,flush=True)
 finally:
  cleanup=True;signal.setitimer(signal.ITIMER_REAL,0);watch_stop.set()
  if watch:watch.join(5)
  cleanup_deadline=time.monotonic()+15
  for c in clients:
   try:c.close()
   except BaseException:pass
  report['connectionsClosed']=all(c.closed for c in clients)
  if pg:
   try:
    if (pg.data/'postmaster.pid').exists():pg.started=True
    pg.stop()
    if block is None:shutil.rmtree(pg.root)
    report['cleanup']={'serverStopped':not(pg.data/'postmaster.pid').exists(),'ownedRoot':str(pg.root),'ownedRootRemoved':not pg.root.exists(),'retainedOnFailure':bool(block)}
   except BaseException as e:report['cleanup']={'serverStopped':False,'ownedRoot':str(pg.root),'errorType':type(e).__name__};block=block or 'Cleanup failed'
  else:report['cleanup']={'serverStarted':False,'ownedRootCreated':False}
  report['resources']=resources;report['elapsedSeconds']=round(time.monotonic()-started,3);report['inputHashesExact']=all(sha(ROOT/p)==h for p,h in report['inputSha256'].items());block=block or (None if report['inputHashesExact'] else 'Input drift');report['counts']={s:sum(x['status']==s for x in report['cases']) for s in ['pass','fail','unverified']};report['status']='fail' if block else 'pass_owned_only' if args.run_local else 'prepared_source_free_only';save(run/'result.json',report);print(json.dumps({'status':report['status'],'counts':report['counts'],'evidence':str(run/'result.json')}),flush=True)
 return 1 if block else 0

if __name__=='__main__':raise SystemExit(main())
