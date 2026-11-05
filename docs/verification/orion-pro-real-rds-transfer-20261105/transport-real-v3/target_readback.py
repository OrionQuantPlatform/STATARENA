#!/usr/bin/env python3
"""Independent readonly target015 descriptor. ROOT supplies the connection."""
from datetime import datetime,timezone
import hashlib,importlib.util,ipaddress,json,os,sys,time,traceback
from pathlib import Path
sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[3]
def load(path,name):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
boundary=load(BASE/'target_policy.py','native_target_p2_policy_boundary')
def save(path,value):Path(path).write_text(json.dumps(value,indent=2,default=str)+'\n')
def read_target(conn,output_dir,*,root_command=None):
 started=time.monotonic();deadline=started+90;out=Path(output_dir).resolve();assert out.is_relative_to(BASE/'target-readbacks');out.mkdir(parents=True,exist_ok=False)
 result={'kind':'real_rds_p2_015_target_descriptor_readback_v1','status':'running','command':root_command or [sys.executable,*sys.argv],'expected':str(BASE/'TARGET_READBACK_PROTOCOL.md'),'sourceCalls':0,'ramGets':0,'cloudCalls':0,'rdsWrites':[],'connectionsOpenedByHelper':0,'callerOwnsConnection':True,'selects':0,'queries':[],'targetPolicySha256':boundary.SHA,'helperSha256':boundary.digest(Path(__file__)),'fullAcceptance':False,'productionActivation':False}
 begun=False;error=None
 def count(name,sql):
  assert result['selects']<8 and time.monotonic()<deadline,'Bounded target descriptor read limit';result['selects']+=1;result['queries'].append({'name':name,'sql':sql});save(out/'progress.json',result)
 def query(name,sql):count(name,sql);return conn.execute(sql).fetchall()
 try:
  m=boundary.load_target_policy();assert not any(k.startswith('PG') for k in os.environ),'Inherited libpq routing refused';assert conn.autocommit is True and conn.info.transaction_status.name=='IDLE','ROOT connection must be idle autocommit'
  target=m['target'];params=conn.info.get_parameters();ca=Path(params.get('sslrootcert',''));assert conn.info.host==target['host'] and conn.info.port==5432 and conn.info.dbname==target['database'] and conn.info.user==target['actor'] and params.get('sslmode')=='verify-full' and ca.resolve()==ROOT/'dashboard/backend/certs/rds-us-east-2.pem' and boundary.digest(ca)==target['caSha256'],'Fixed client TLS host/CA/actor/route required'
  client_addr=str(ipaddress.ip_address(conn.info.hostaddr));conn.execute('BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY');begun=True
  rows=query('identity',"SELECT current_database(),current_user,session_user,pg_postmaster_start_time(),host(inet_server_addr()),inet_server_port(),current_setting('transaction_read_only'),current_setting('transaction_isolation'),current_setting('statement_timeout'),current_setting('lock_timeout'),current_setting('idle_in_transaction_session_timeout'),current_setting('TimeZone'),current_setting('DateStyle'),(SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()),rolsuper,rolcreaterole,rolcreatedb,rolreplication,rolbypassrls,(SELECT count(*) FROM pg_roles WHERE rolname<>current_user AND pg_has_role(current_user,oid,'MEMBER')),(SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname IN ('ingest','football','analytics') AND c.relowner=current_user::regrole),has_table_privilege(current_user,'football.players','INSERT'),has_table_privilege(current_user,'ingest.schema_migrations','INSERT,UPDATE,DELETE') OR has_any_column_privilege(current_user,'ingest.schema_migrations','INSERT,UPDATE') FROM pg_roles WHERE rolname=current_user")
  assert len(rows)==1;row=rows[0];assert row[:4]==(target['database'],target['actor'],target['actor'],datetime.fromisoformat(target['postmasterStartedAt'])) and row[5:14]==(5432,'on','repeatable read','8s','1s','15s','UTC','ISO, YMD',True) and all(v is False for v in row[14:19]) and row[19:]==(0,0,True,False) and conn.info.server_version==180006,'Exact actual target actor/TLS/epoch/readonly/deadline/privileges differ'
  server_addr=str(ipaddress.ip_address(row[4]));result['identity']={'host':target['host'],'clientHostaddr':client_addr,'serverInetAddr':server_addr,'serverPort':row[5],'database':row[0],'actor':row[1],'engine':180006,'postmasterStartedAt':row[3].isoformat(),'tls':True,'readOnly':True,'isolation':'repeatable read','statementTimeout':'8s','lockTimeout':'1s'}
  sys.path.insert(0,str(ROOT/'dashboard/scripts'));old=load(ROOT/'dashboard/scripts/orion_pro_native_transport_real_v2.py','frozen_v2_native_target_projection')
  count('catalogue','Frozen real_v2.catalogue(conn, False): native catalogue SQL with exact target roles');catalogue=old.catalogue(conn,False)
  count('validator_properties','Frozen orion_pro_policy.function_properties(conn)');properties=old.policy.function_properties(conn)
  definition=query('validator_definition',"SELECT pg_get_functiondef('ingest.validate_generation(bigint)'::regprocedure)");assert len(definition)==1 and hashlib.sha256(definition[0][0].encode()).hexdigest()==m['canonicalDefinitionSha256'],'Actual canonical015 definition differs'
  journal=[list(v) for v in query('journal','SELECT version,content_sha256,applied_at::text,code_commit FROM ingest.schema_migrations ORDER BY version LIMIT 5')];assert journal==m['targetJournal']
  count('journal_native','Frozen real_v2.journal_native(conn), exact four-row RR snapshot');journal_sha=old.journal_native(conn)
  b0=query('bootstrap_native',"SELECT ROW(s.*)::text FROM ingest.dataset_snapshots s WHERE transform_version='bootstrap_v1' ORDER BY id LIMIT 2");assert len(b0)==1
  seq=query('sequence_metadata_and_privileges',"SELECT s.schemaname||'.'||s.sequencename,s.increment_by,s.cycle,s.cache_size,has_sequence_privilege(current_user,c.oid,'USAGE'),has_sequence_privilege(current_user,c.oid,'SELECT') FROM pg_sequences s JOIN pg_namespace n ON n.nspname=s.schemaname JOIN pg_class c ON c.relnamespace=n.oid AND c.relname=s.sequencename WHERE s.schemaname IN ('ingest','football','analytics') ORDER BY 1 LIMIT 68")
  assert len(seq)==67 and all(x[1:4]==(1,False,1) and x[5] is False and x[4]==(x[0]!='ingest.commit_generation_seq') for x in seq),'Exact ordinary ingest sequence metadata/privileges differ'
  descriptor={'kind':m['targetKind'],'origin':m['targetOrigin'],'roles':old.TARGET_ROLES.copy(),'endpoint':{'database':row[0],'actor':row[1],'serverVersion':180006,'postmasterStartedAt':row[3].isoformat(),'tls':True},'catalogueSha256':catalogue['sha256'],'nativeCatalogueCounts':catalogue['counts'],'functionProperties':properties,'journal':journal,'journalNativeSha256':journal_sha,'bootstrapNativeText':b0[0][0],'rdsP2StateSha256':m['actualAfterStateSha256'],'rdsP2NativeReceiptSha256':m['actualAfterNativeSha256'],'rdsP2AdoptionReceiptSha256':m['actualAdoptionReceiptSha256']}
  boundary.validate_target_descriptor(descriptor,m);p=out/'target-descriptor.json';save(p,descriptor);result.update(status='verified_actual_p2_target_descriptor',targetDescriptorPath=str(p.relative_to(ROOT)),targetDescriptorSha256=boundary.digest(p),catalogueRetainedBytes=catalogue['bytes'],canonicalDefinitionSha256=m['canonicalDefinitionSha256'],sequenceMetadataRows=67,sequenceValueSelects=0,sequenceUsage=66,actualAdoptionNativeSha256=m['actualAfterNativeSha256'],actualAdoptionStateSha256=m['actualAfterStateSha256'])
 except BaseException as e:error=e;result.update(status='fail',errorType=type(e).__name__,error=str(e),sqlstate=getattr(e,'sqlstate',None),traceback=traceback.format_exc())
 finally:
  if begun:
   try:conn.rollback();result['readTransactionRolledBack']=True
   except BaseException as e:error=error or e;result.update(status='fail',readTransactionRolledBack=False,rollbackErrorType=type(e).__name__)
  result['elapsedSeconds']=round(time.monotonic()-started,3);save(out/'result.json',result)
 if error:raise RuntimeError('Readonly target descriptor refused; see '+str(out/'result.json')) from error
 return result

if __name__=='__main__':
 assert sys.argv[1:] in [[],['--check-plan']],'ROOT connection API only; default CLI is offline'
 if len(sys.argv)==1:print(json.dumps({'status':'offline_plan','connections':0,'realTargetObserved':False}))
 else:
  m=boundary.load_target_policy();print(json.dumps({'status':'prepared_actual_adoption_inputs_only','connections':0,'realTargetObserved':False,'targetPolicySha256':boundary.SHA,'adoptedNativeStateSha256':m['actualAfterStateSha256'],'expectedJournalNativeSha256':m['targetJournalNativeSha256']}))
