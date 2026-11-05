#!/usr/bin/env python3
"""Isolated fixed015 adoption. Offline by default; real execution is ROOT released."""
from __future__ import annotations
import argparse,copy,hashlib,importlib.util,json,os,re,signal,socket,stat,sys,time
from datetime import datetime,timezone
from pathlib import Path

sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[3];PARENT=BASE.parent
SQL15=ROOT/'dashboard/backend/migrations/015_orion_pro_metric_membership_guard.sql'
SQL14=ROOT/'dashboard/backend/migrations/014_orion_pro_membership_nonnull.sql'
POLICY_ID='metric-membership-guard-m18da43-rds015-v1'
DBS={'p2_policy_empty','p2_policy_companion'}
RELEASE=BASE/'ROOT_RDS_P2_RELEASE.json';LEDGER=BASE/'RDS_P2_ONESHOT.json'
LIMITS={'connections':2,'observations':3,'selects':47,'explicitExecuteCalls':51,'transactionControls':4,'decodedBytes':12*1024**2,'metadataBytes':32*1024**2,'transientReserveBytes':8*1024**2,'seconds':180,'statementMs':8000,'lockMs':1000}
def load(path,name):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
observer=load(PARENT/'adapter.py','frozen014_native_observer_for_isolated015')
Refusal=observer.Refusal;require=observer.require;sha=observer.sha;save=observer.save;hashed=observer.hashed;stable=observer.stable;state_hash=observer.state_hash
observe=observer.observe
class OutcomeUnverified(RuntimeError):pass


def json_file(path,limit=8*1024**2):return observer.json_file(Path(path),limit)
def raw_body(path):
 text=Path(path).read_text();start=text.index('AS $orion_pro$')+len('AS $orion_pro$');return text[start:text.index('$orion_pro$;',start)]
def validator_definition(state):
 rows=[r for r in state['groups']['guards'] if r['kind']=='function' and r['name']=='ingest.validate_generation' and r['identity']=='g bigint'];require(len(rows)==1,'CATALOGUE','One exact bigint validator required');return rows[0]['definition']
def derived_definition(old):
 previous=raw_body(SQL14);require(old.count(previous)==1,'CATALOGUE','Baseline validator is not exact sealed014');return old.replace(previous,raw_body(SQL15),1)


def fixed_inputs():
 pins=json_file(BASE/'PINS.json');require(pins.get('kind')=='isolated_rds015_inputs_v1','INPUT','Unknown isolated015 pins')
 for path,digest in pins['files'].items():require(sha(ROOT/path)==digest,'INPUT','Protected input differs: '+path)
 m=json_file(BASE/'P2_POLICY.json');require(m.get('kind')=='isolated_rds015_metric_guard_policy_v1' and m.get('policyId')==POLICY_ID and m.get('localOnly') is False and m.get('appliedToRds') is False and m.get('qualifiedImportPairs')==[],'POLICY','Only distinct prepared real015 policy metadata accepted')
 require(sha(SQL15)==m['migration']['sha256']=='3b85fcb4fe9380cc5f96238620ff3f4bedee7485ed52c98fef0bddfac1092bd7','INPUT','015 must remain the exact qualified candidate')
 n=json_file(ROOT/m['baseline']['nativePath']);r=json_file(ROOT/m['baseline']['rollbackReceiptPath'])
 require(sha(ROOT/m['baseline']['nativePath'])==m['baseline']['nativeSha256']=='ed01b0a1c7c25feecdffb3de0a4d3f0a0ac0a39a0348a443f73db1892c4ae60a' and state_hash(n)==m['baseline']['stateSha256']=='d237d4d98611829aa4c5ba588629fc943de673eeee1b4640ecef8cd087f9b8b4','BASELINE','Current accounted-reservation RDS baseline required')
 require(r['status']=='verified_rollback_B0_only_with_exact_sequence_gaps' and r['nativeSha256']==m['baseline']['nativeSha256'] and r['actualStateSha256']==m['baseline']['stateSha256'] and len(r['sequenceDeltas'])==24,'BASELINE','Independent failed-core native baseline receipt differs')
 require(len(n['groups']['sequences'])==67 and [x['version'] for x in n['groups']['journal']]==['012','013','014'],'BASELINE','Exact native67 and012013014 baseline required')
 expected=derived_definition(validator_definition(n));require(expected==(ROOT/m['definition']['path']).read_text() and hashlib.sha256(expected.encode()).hexdigest()==m['definition']['canonicalP2Sha256'],'INPUT','Expected native015 function definition differs')
 proof=json_file(ROOT/m['equivalence']['runtimeReceiptPath']);require(proof['status']=='pass_owned_local_only' and proof['counts']=={'pass':10,'fail':0,'unverified':0} and proof['connectionsClosed'] and proof['inputHashesExact'] and proof['cleanup']['ownedRootRemoved'],'INPUT','Completed dense/compact candidate qualification required')
 observer.fixed_inputs();observer.check_bootstrap(n['groups']);return m


def verify_state(state,contract):
 g=state['groups'];observer.check_bootstrap(g);base=contract['baseline'];journal=g['journal'];require([r['version'] for r in base['journal']]==['012','013','014'],'JOURNAL','Contract baseline must be exact012013014')
 versions=[r['version'] for r in journal];require(versions in [['012','013','014'],['012','013','014','015']] and journal[:3]==base['journal'],'JOURNAL','Existing journal, hashes or original clocks differ')
 current='P2' if len(journal)==4 else 'P1'
 if current=='P2':
  tail=journal[-1];require(set(tail)=={'version','content_sha256','applied_at','code_commit'} and tail['content_sha256']==sha(SQL15) and tail['code_commit']==contract['releaseCommit'],'JOURNAL','015 journal metadata differs')
  try:require(datetime.fromisoformat(tail['applied_at']).tzinfo is not None,'JOURNAL','Aware native015 clock required')
  except (TypeError,ValueError):raise Refusal('JOURNAL','Malformed native015 clock') from None
 wanted=copy.deepcopy(base)
 if current=='P2':
  rows=[row for row in wanted['guards'] if row['kind']=='function' and row['name']=='ingest.validate_generation' and row['identity']=='g bigint'];require(len(rows)==1,'CATALOGUE','One baseline validator required');rows[0]['definition']=contract['p2Definition']
 actual=stable(state);actual.pop('journal');wanted.pop('journal')
 require(set(actual)==set(wanted),'CATALOGUE','Unknown native metadata group')
 for name in wanted:require(actual[name]==wanted[name],'SEQUENCE' if name=='sequences' else 'BOOTSTRAP' if name=='bootstrap' else 'CATALOGUE','Exact isolated015 native group differs: '+name)
 return current


def caps_for(state):
 caps={name:len(rows)+1 for name,rows in state['groups'].items()};caps.update(journal=5,bootstrap=32,nonbootstrap=90,concurrency=129);return caps
def owned_marker(path):
 path=Path(path);require(path.is_absolute() and stat.S_ISREG(path.lstat().st_mode) and not path.is_symlink(),'LOCAL','Regular absolute owned marker required');m=json_file(path,16384);root=Path(m.get('ownedRoot','')).resolve()
 require(m.get('kind')=='isolated015_owned_pg18_v1' and root.name.startswith('orion-pro-e2e-') and root.is_dir() and path.resolve().parent==root and path.stat().st_uid==os.getuid() and stat.S_IMODE(path.stat().st_mode)==0o600,'LOCAL','Isolated owned marker differs')
 pid=(root/'data/postmaster.pid').read_text().splitlines();require(len(pid)>3 and Path(pid[1]).resolve()==root/'data' and int(pid[3])==m['port'],'LOCAL','Owned postmaster/data/port differs')
 cert=Path(m['certificatePath']);require(cert.resolve().parent==root and sha(cert)==m['certificateSha256'],'LOCAL','Owned TLS certificate differs');require(datetime.fromisoformat(m['serverStartedAt']).tzinfo is not None,'LOCAL','Aware owned epoch required');return m
def verify_owned_identity(row,database,marker):
 require(row['database']==database and database in DBS and datetime.fromisoformat(row['started_at'])==datetime.fromisoformat(marker['serverStartedAt']),'LOCAL','Owned database/postmaster epoch differs')
def owned_connection(marker,database):
 fixed_inputs();observer.no_pg_environment();require(database in DBS,'LOCAL','Unknown isolated owned database');m=owned_marker(marker)
 import psycopg
 c=psycopg.connect(host='127.0.0.1',hostaddr='127.0.0.1',port=m['port'],dbname=database,user=observer.ACTOR,sslmode='verify-full',sslrootcert=m['certificatePath'],autocommit=True,connect_timeout=5,options=observer.OPTIONS,application_name='isolated015-owned-adoption')
 return c,lambda row:verify_owned_identity(row,database,m)
def artifact(path):
 path=Path(path);require(path.is_absolute() and not path.is_symlink() and path.is_file() and path.resolve().is_relative_to(BASE/'owned-runs'),'LOCAL','Owned qualification artifact required');return path.resolve()
def load_owned_contract(path,digest):
 path=artifact(path);require(sha(path)==digest,'INPUT','Owned contract hash differs');c=json_file(path)
 require(c.get('kind')=='owned_isolated015_contract_v1' and c.get('localOnly') is True and c.get('policyId')==POLICY_ID,'ORIGIN','Only distinct owned015 contract accepted')
 fixed_inputs();require(c['operatorSha256']==sha(Path(__file__)) and c['pinsSha256']==sha(BASE/'PINS.json') and c['querySha256']==hashed(observer.queries()) and c['migrationSha256']==sha(SQL15),'INPUT','Owned code/query/migration pins differ');return c
def prepare_owned(marker,database,path):
 fixed_inputs();path=Path(path).resolve();require(path.is_relative_to(BASE/'owned-runs') and not path.exists(),'LOCAL','Fresh owned contract path required');c,verify=owned_connection(marker,database)
 try:
  with c.transaction():c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY');before=observe(c,identity_check=verify);require([r['version'] for r in before['groups']['journal']]==['012','013','014'],'JOURNAL','Owned baseline must already contain sealed014');observer.check_bootstrap(before['groups']);expected=derived_definition(validator_definition(before));rowcaps=caps_for(before)
  with c.transaction(force_rollback=True):
   c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ WRITE');c.execute(SQL15.read_text(),prepare=False);after=observe(c,rowcaps,local_write=True,identity_check=verify);a=stable(before);b=stable(after);require([name for name in a if a[name]!=b[name]]==['guards'],'CATALOGUE','Owned015 overlay changes more than function metadata');delta=[(x,y) for x,y in zip(a['guards'],b['guards']) if x!=y];require(len(delta)==1 and {k:v for k,v in delta[0][0].items() if k!='definition'}=={k:v for k,v in delta[0][1].items() if k!='definition'} and delta[0][1]['definition']==expected,'CATALOGUE','Owned native015 normalization/OID/properties differ')
  with c.transaction():c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY');restored=observe(c,rowcaps,identity_check=verify);require(state_hash(restored)==state_hash(before),'CATALOGUE','Owned prepare rollback did not restore exact native state')
  require(hashlib.sha256(expected.encode()).hexdigest()==fixed_inputs()['definition']['canonicalP2Sha256'],'CATALOGUE','Owned normalized definition differs from exact RDS-derived015 template')
  contract={'kind':'owned_isolated015_contract_v1','localOnly':True,'policyId':POLICY_ID,'database':database,'operatorSha256':sha(Path(__file__)),'pinsSha256':sha(BASE/'PINS.json'),'querySha256':hashed(observer.queries()),'migrationSha256':sha(SQL15),'baseline':stable(before),'rowCaps':rowcaps,'p2Definition':expected,'p2DefinitionSha256':hashlib.sha256(expected.encode()).hexdigest(),'releaseCommit':'owned_p2_adoption_e2e'};observer.metadata_bytes(contract,before,after,restored);save(path,contract)
  return {'status':'prepared_owned_rollback_only','contractSha256':sha(path),'p2DefinitionSha256':contract['p2DefinitionSha256'],'nativeStateRestored':True,'localOnly':True}
 finally:c.close()


def summarize(state,current):
 return {'policy':current,'stateSha256':state_hash(state),'nativeGroups':14,'sequenceCount':len(state['groups']['sequences']),'budget':state['budget'],'fullAcceptance':False}
def owned_preflight(marker,database,path,digest):
 contract=load_owned_contract(path,digest);require(contract['database']==database,'LOCAL','Owned contract database differs');c,verify=owned_connection(marker,database)
 try:
  with c.transaction():c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY');s=observe(c,contract['rowCaps'],identity_check=verify);current=verify_state(s,contract)
  return {'status':'ready_owned_only',**summarize(s,current),'connectionsClosed':True}
 finally:c.close()
def transition_core(conn,contract,acceptance,verify,*,fault=None,observation=observe):
 local=contract.get('localOnly') is True
 require((local and contract.get('kind')=='owned_isolated015_contract_v1' and conn.info.dbname in DBS and conn.info.host=='127.0.0.1') or (not local and contract.get('kind')=='actual_rds015_contract_v1' and conn.info.dbname==observer.DATABASE and conn.info.host==observer.HOST),'ORIGIN','Owned and real connection/contract origins cannot mix')
 require(fault is None or local,'MODE','Faults are owned-only');result=None
 with conn.transaction():
  conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ WRITE')
  for statement in ['SELECT pg_try_advisory_xact_lock(20261104,2)','SELECT pg_try_advisory_xact_lock(20261104,1)','SELECT pg_try_advisory_xact_lock(97813003::bigint)']:require(conn.execute(statement).fetchone()[0],'LEASE','Existing native lease held')
  before=observation(conn,contract['rowCaps'],local_write=True,identity_check=verify);current=verify_state(before,contract);require(state_hash(before)==acceptance['beforeStateSha256'],'ACCEPTANCE','Accepted native before state differs')
  if current=='P2':return {'status':'reused',**summarize(before,'P2'),'ddlStatements':0,'journalInserts':0,'localOnly':local}
  clock0=conn.execute('SELECT transaction_timestamp()::text').fetchone()[0];conn.execute(SQL15.read_text(),prepare=False)
  if fault=='after_function':raise Refusal('FAULT','Owned after-function injection')
  conn.execute('INSERT INTO ingest.schema_migrations(version,content_sha256,applied_at,code_commit) VALUES(%s,%s,CURRENT_TIMESTAMP,%s)',('015',sha(SQL15),contract['releaseCommit']))
  if fault=='after_journal':raise Refusal('FAULT','Owned after-journal injection')
  clock=conn.execute("SELECT applied_at::text,transaction_timestamp()::text,clock_timestamp()::text FROM ingest.schema_migrations WHERE version='015'").fetchone();require(clock[0]==clock[1]==clock0 and datetime.fromisoformat(clock[0])<=datetime.fromisoformat(clock[2]),'JOURNAL','Native015 transaction clock differs')
  after=observation(conn,contract['rowCaps'],local_write=True,identity_check=verify);require(verify_state(after,contract)=='P2' and before['groups']['validator']==after['groups']['validator'],'CATALOGUE','Native015 protected properties/postcondition differ')
  result={'status':'applied',**summarize(after,'P2'),'ddlStatements':1,'journalInserts':1,'localOnly':local,'newJournalClock':dict(zip(['appliedAt','transactionStart','observedAfterInsert'],clock)),'protectedPropertiesPreserved':True}
 if fault=='after_commit':raise OutcomeUnverified('Commit acknowledgement unknown; fresh readonly classification required')
 return result
def owned_transition(marker,database,path,digest,acceptance_path,acceptance_sha,*,fault=None):
 contract=load_owned_contract(path,digest);require(contract['database']==database,'LOCAL','Owned contract database differs');acceptance_path=artifact(acceptance_path);require(sha(acceptance_path)==acceptance_sha,'ACCEPTANCE','Acceptance hash differs');a=json_file(acceptance_path,65536)
 require(set(a)=={'kind','localOnly','database','operatorSha256','contractSha256','beforeStateSha256','releaseCommit'} and a['kind']=='owned_isolated015_acceptance_v1' and a['localOnly'] is True and a['database']==database and a['operatorSha256']==sha(Path(__file__)) and a['contractSha256']==digest and a['releaseCommit']==contract['releaseCommit'],'ORIGIN','Exact distinct owned acceptance required');require(fault in [None,'after_function','after_journal','after_commit'],'MODE','Unknown owned fault')
 c,verify=owned_connection(marker,database)
 try:return transition_core(c,contract,a,verify,fault=fault)
 finally:c.close()


def release_structure():
 if LEDGER.exists():raise Refusal('CHECKPOINT','Real isolated015 allocation already claimed/consumed; no reset or retry')
 require(RELEASE.is_file() and not RELEASE.is_symlink(),'RELEASE','Separate fixed ROOT015 release required');r=json_file(RELEASE,65536);m=fixed_inputs()
 require(r.get('kind')=='root_isolated_rds015_adoption_release_v1' and r.get('authorizedBy')=='ROOT' and r.get('scope')=='fixed015_one_function_one_journal_only','RELEASE','Explicit fixed015 ROOT release required')
 require(r.get('target')==m['target'] and r.get('operatorSha256')==sha(Path(__file__)) and r.get('pinsSha256')==sha(BASE/'PINS.json') and r.get('policySha256')==sha(BASE/'P2_POLICY.json') and r.get('migrationSha256')==sha(SQL15) and re.fullmatch('[a-f0-9]{40}',r.get('codeCommit','')),'RELEASE','Exact ROOT target/code/migration binding differs')
 require(r.get('beforeStateSha256')==m['baseline']['stateSha256'] and r.get('nativeBaselineSha256')==m['baseline']['nativeSha256'],'BASELINE','Latest real accounted-sequence baseline required')
 require(r.get('policyId')==POLICY_ID,'POLICY','Old/local policy alias refused');require(r.get('origin')==m['origin'],'ORIGIN','Owned/local acceptance cannot authorize actual RDS')
 require(r.get('productionActivation') is False and r.get('collectorsEnabled') is False and r.get('fullAcceptance') is False,'RELEASE','Activation and collector scope must stay closed');return r,m
def validate_local_proof(r):
 path=Path(r.get('localReceiptPath',''));require(path.is_absolute() and path.is_relative_to(BASE/'owned-runs') and path.is_file() and not path.is_symlink() and sha(path)==r.get('localReceiptSha256'),'RELEASE','Completed owned operational proof required');p=json_file(path)
 require(p['status']=='pass_owned_only' and p['counts']=={'pass':16,'fail':0,'unverified':0} and p['connectionsClosed'] and p['inputHashesExact'] and p['cleanup']['serverStopped'] and p['cleanup']['ownedRootRemoved'] and p['inputSha256'].get(str(Path(__file__).relative_to(ROOT)))==sha(Path(__file__)),'RELEASE','Exact complete operational proof/code/cleanup required')
 require(p['pgStarts']==1 and p['databases']==2 and p['remoteCalls']==p['sourceCalls']==p['sourceRamReads']==p['setvalCalls']==0 and all((ROOT/name).is_file() and sha(ROOT/name)==digest for name,digest in p['inputSha256'].items()),'RELEASE','Operational proof inputs, owned scope or metadata changed')
 required=[BASE/'PINS.json',BASE/'P2_POLICY.json',BASE/'PROTOCOL.md',BASE/'local_e2e.py',SQL15]
 require(all(p['inputSha256'].get(str(path.relative_to(ROOT)))==sha(path) for path in required),'RELEASE','Exact operational protocol/test/policy/migration proof binding required')
def actual_contract(r,m):
 n=json_file(ROOT/m['baseline']['nativePath']);return {'kind':'actual_rds015_contract_v1','localOnly':False,'policyId':POLICY_ID,'database':observer.DATABASE,'baseline':stable(n),'rowCaps':caps_for(n),'p2Definition':(ROOT/m['definition']['path']).read_text(),'p2DefinitionSha256':m['definition']['canonicalP2Sha256'],'releaseCommit':r['codeCommit']}
def real_execution(args,r,m,passfile):
 started=time.monotonic();out=BASE/'rds-adoption'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);report={'kind':'actual_isolated015_adoption_v1','command':[sys.executable,str(Path(__file__)),*sys.argv[1:]],'releaseSha256':sha(RELEASE),'policyId':POLICY_ID,'status':'unverified','limits':LIMITS,'connections':0,'explicitExecuteCalls':0,'selects':0,'decodedBytes':0,'maxRetainedMetadataBytes':0,'observations':[],'remoteBusinessWrites':[],'sourceCalls':0,'fullAcceptance':False,'productionActivation':False};connections=[];states=[];contract=actual_contract(r,m)
 def wall():require(time.monotonic()-started<LIMITS['seconds'],'BOUND','180-second real operation deadline')
 class Counted:
  def __init__(self,c):self.connection=c
  def __getattr__(self,k):return getattr(self.connection,k)
  def execute(self,sql,*a,**k):
   wall();report['explicitExecuteCalls']+=1;report['selects']+=int(sql.lstrip().upper().startswith(('SELECT','WITH')));require(report['explicitExecuteCalls']<=51 and report['selects']<=47,'BOUND','Real execute/SELECT allocation exceeded');return self.connection.execute(sql,*a,**k)
 def observed(*a,**k):
  s=observe(*a,**k);states.append(s);report['decodedBytes']+=s['budget']['decodedBytes'];retained=observer.metadata_bytes(contract,states,report);report['maxRetainedMetadataBytes']=max(report['maxRetainedMetadataBytes'],retained);require(len(report['observations'])+len(states)<=3 and report['decodedBytes']<=12*1024**2 and retained+8*1024**2<=32*1024**2,'BOUND','Real native metadata allocation exceeded');return s
 def store():
  for s in states:
   path=out/('native-'+str(len(report['observations']))+'.json');save(path,s);report['observations'].append({'path':str(path.relative_to(ROOT)),'sha256':sha(path),'stateSha256':state_hash(s),'budget':s['budget']})
  states.clear()
 try:
  addresses=sorted({x[4][0] for x in socket.getaddrinfo(observer.HOST,5432,type=socket.SOCK_STREAM)});require(addresses,'ROUTE','Fixed RDS DNS resolution required');import psycopg
  def connect():
   wall();require(report['connections']<2,'BOUND','Two real connections maximum');c=psycopg.connect(**observer._rds_connection_kwargs(passfile,addresses[0]));connections.append(c);report['connections']+=1;require(c.info.host==observer.HOST and c.info.dbname==observer.DATABASE and c.info.user==observer.ACTOR,'ROUTE','Exact real connection route/actor differs');return Counted(c)
  def verify(row):require(row['database']==observer.DATABASE and row['started_at']==m['target']['postmasterStartedAt'],'IDENTITY','Actual RDS endpoint/epoch differs')
  writer=connect()
  try:report['transition']=transition_core(writer,contract,{'beforeStateSha256':r['beforeStateSha256']},verify,observation=observed)
  except BaseException as e:report['transitionError']={'type':type(e).__name__,'code':getattr(e,'code',None),'sqlstate':getattr(e,'sqlstate',None)}
  finally:writer.close()
  expected_after=state_hash(states[-1]) if states and [x['version'] for x in states[-1]['groups']['journal']]==['012','013','014','015'] else None;store();reader=connect()
  try:
   with reader.transaction():
    reader.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY');final=observed(reader,contract['rowCaps'],identity_check=verify);classification=verify_state(final,contract);require(final['groups']['identity'][0]['read_only']=='on','IDENTITY','Fresh readback must be readonly')
    if classification=='P2' and expected_after is not None:require(state_hash(final)==expected_after,'CATALOGUE','Independent committed state differs from exact precommit postcondition')
   report['independentPolicy']=classification;report['status']='applied_and_independently_verified' if classification=='P2' and 'transitionError' not in report else 'commit_outcome_verified_P2' if classification=='P2' else 'not_applied_P1_verified'
  finally:reader.close()
  store()
 except BaseException as e:report['error']={'type':type(e).__name__,'code':getattr(e,'code',None),'sqlstate':getattr(e,'sqlstate',None)}
 finally:
  for c in connections:c.close()
  store();report['connectionsClosed']=all(c.closed for c in connections);report['elapsedSeconds']=round(time.monotonic()-started,3);report['credentialBodyArchived']=False;report['privatePassfileOwnedByRoot']=True;save(out/'result.json',report);save(LEDGER,{'kind':'isolated_rds015_oneshot_v1','state':'consumed','executions':1,'releaseSha256':sha(RELEASE),'outcome':report['status'],'result':str((out/'result.json').relative_to(ROOT))})
 return report,out/'result.json'


def main():
 ap=argparse.ArgumentParser(description=__doc__);modes=ap.add_mutually_exclusive_group();modes.add_argument('--check-plan',action='store_true');modes.add_argument('--prepare-owned',action='store_true');modes.add_argument('--owned-preflight',action='store_true');modes.add_argument('--owned-transition',action='store_true');modes.add_argument('--execute-released-rds',action='store_true');ap.add_argument('--marker',type=Path);ap.add_argument('--database',choices=sorted(DBS));ap.add_argument('--contract',type=Path);ap.add_argument('--contract-sha256');ap.add_argument('--output',type=Path);ap.add_argument('--acceptance',type=Path);ap.add_argument('--acceptance-sha256');ap.add_argument('--fault',choices=['after_function','after_journal','after_commit']);ap.add_argument('--target-passfile',type=Path);ap.add_argument('--release-sha256');args=ap.parse_args()
 try:
  if not any([args.check_plan,args.prepare_owned,args.owned_preflight,args.owned_transition,args.execute_released_rds]):print(json.dumps({'status':'offline_plan','connections':0,'businessWrites':[],'policyId':POLICY_ID,'fullAcceptance':False}));return 0
  if args.check_plan:
   m=fixed_inputs();print(json.dumps({'status':'prepared_not_applied','connections':0,'policyId':POLICY_ID,'migrationSha256':sha(SQL15),'beforeStateSha256':m['baseline']['stateSha256'],'canonicalP2Sha256':m['definition']['canonicalP2Sha256'],'realStateObserved':False,'fullAcceptance':False}));return 0
  observer.no_pg_environment()
  if args.execute_released_rds:
   require(args.fault is None,'MODE','Real fault injection forbidden');r,m=release_structure();require(args.target_passfile is not None,'AUTH','ROOT private passfile required');passfile=observer.validated_rds_passfile({'ORION_RDS_PASSFILE':str(args.target_passfile)});require(args.release_sha256==sha(RELEASE),'RELEASE','Out-of-band exact ROOT release hash required');validate_local_proof(r)
   fd=os.open(LEDGER,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o644)
   with os.fdopen(fd,'w') as f:json.dump({'kind':'isolated_rds015_oneshot_v1','state':'claimed','executions':1,'releaseSha256':sha(RELEASE),'atUtc':datetime.now(timezone.utc).isoformat()},f,indent=2);f.write('\n')
   def stopped(signum,frame):raise Refusal('BOUND','Real015 global operation deadline or supervision stop')
   signal.signal(signal.SIGALRM,stopped);signal.signal(signal.SIGTERM,stopped);signal.setitimer(signal.ITIMER_REAL,LIMITS['seconds'])
   try:result,path=real_execution(args,r,m,passfile)
   finally:signal.setitimer(signal.ITIMER_REAL,0)
   print(json.dumps({'status':result['status'],'evidence':str(path),'connectionsClosed':result['connectionsClosed'],'fullAcceptance':False}));return 0 if result['status'] in ['applied_and_independently_verified','commit_outcome_verified_P2'] and result['connectionsClosed'] else 1
  require(args.marker and args.database,'LOCAL','Explicit owned marker/database required')
  if args.prepare_owned:require(args.output is not None,'LOCAL','Fresh owned output path required');result=prepare_owned(args.marker,args.database,args.output)
  else:
   require(args.contract and args.contract_sha256,'LOCAL','Owned contract/hash required')
   if args.owned_preflight:result=owned_preflight(args.marker,args.database,args.contract,args.contract_sha256)
   else:require(args.acceptance and args.acceptance_sha256,'ACCEPTANCE','Owned acceptance/hash required');result=owned_transition(args.marker,args.database,args.contract,args.contract_sha256,args.acceptance,args.acceptance_sha256,fault=args.fault)
  print(json.dumps(result));return 0
 except OutcomeUnverified as e:print(json.dumps({'status':'outcome_unknown','errorType':type(e).__name__,'fullAcceptance':False}));return 3
 except BaseException as e:print(json.dumps({'status':'refused','code':getattr(e,'code','INPUT'),'errorType':type(e).__name__,'fullAcceptance':False}));return 2

if __name__=='__main__':raise SystemExit(main())
