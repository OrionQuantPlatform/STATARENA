#!/usr/bin/env python3
"""Offline RDS policy composition; separately released readonly remote observation only."""
from __future__ import annotations
import argparse, copy, fcntl, hashlib, importlib.util, json, os, re, socket, stat, sys, time
from datetime import datetime, timezone
from pathlib import Path

BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[2];PILOT=ROOT/'docs/verification/orion-pro-pilot-20261104'
MODEL=ROOT/'docs/architecture/orion-plan-20261104/target-schema.proposed.json';MIG=ROOT/'dashboard/backend/migrations'
HOST='statarena-postgres.clcy2iqyajbl.us-east-2.rds.amazonaws.com';DATABASE='statarena_prod';ACTOR='statarena_admin';SCHEMAS=['ingest','football','analytics']
DBS={'rds_policy_empty','rds_policy_populated'};CA=ROOT/'dashboard/backend/certs/rds-us-east-2.pem';POLICY='membership-nonnull-m18da43-rds-bootstrap-v1'
OPTIONS='-c default_transaction_read_only=on -c statement_timeout=8000 -c lock_timeout=1000 -c idle_in_transaction_session_timeout=15000 -c search_path=pg_catalog -c timezone=UTC -c datestyle=ISO,YMD -c extra_float_digits=3'
SQL14=MIG/'014_orion_pro_membership_nonnull.sql';SQL14_SHA='e0810f8670b2cb627ade2c76e3c8eb527ab31fd595d5cf939fd63bfc5cf649d6'
NAMES=['identity','relations','columns','constraints','indexes','guards','journal','bootstrap','nonbootstrap','sequences','security','concurrency','retained','validator']
BYTE_CAPS=dict(zip(NAMES,[16384,262144,524288,1572864,262144,1048576,8192,32768,16384,65536,262144,32768,16384,16384]))
DEFAULT_ROWS=dict(zip(NAMES,[2,208,1710,20001,353,175,4,32,90,68,2,129,3,2]))
MAX_BYTES=4194304;META_MAX=33554432
class Refusal(Exception):
    def __init__(self,code,message):self.code=code;super().__init__(message)
class OutcomeUnverified(Exception):pass
def require(ok,code,message):
    if not ok:raise Refusal(code,message)
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def hashed(value):return hashlib.sha256(canonical(value)).hexdigest()
def save(path,value):Path(path).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')
def q(name):require(bool(re.fullmatch('[a-z_][a-z0-9_]*',name)),'INPUT','Unknown fixed identifier');return '"'+name+'"'
def rel(name):return '.'.join(q(v) for v in name.split('.'))
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def json_file(path,limit=8*1024**2):
    path=Path(path);require(path.is_file() and not path.is_symlink() and path.stat().st_size<=limit,'INPUT','Missing or oversized fixed artifact')
    try:return json.loads(path.read_text())
    except (UnicodeError,ValueError):raise Refusal('INPUT','Malformed fixed artifact') from None
def fixed_inputs():
    pins=json_file(BASE/'INPUTS.json')['files'];require(all((ROOT/p).is_file() and sha(ROOT/p)==h for p,h in pins.items()),'INPUT','Frozen input bytes changed')
    require(sha(SQL14)==SQL14_SHA,'INPUT','Fixed014 bytes changed');return json_file(MODEL,2*1024**2)
def historical():
    p=PILOT/'rds-readbacks/20261104T193830558195Z-rds-schema-bootstrap/result.json';return {q['name']:q['rows'] for q in json_file(p)['queries']}
def metadata_bytes(*objects):
    seen=set();pending=list(objects);size=0
    while pending:
        v=pending.pop()
        if id(v) in seen:continue
        seen.add(id(v));size+=sys.getsizeof(v)
        if isinstance(v,dict):pending.extend(v.keys());pending.extend(v.values())
        elif isinstance(v,(tuple,list)):pending.extend(v)
    size+=sys.getsizeof(seen);require(size<=META_MAX,'BOUND','Retained metadata exceeds32MiB');return size

class Budget:
    def __init__(self):self.select_count=0;self.instruction_count=0;self.reserved=0;self.decoded=0
    def control(self):require(self.instruction_count<20,'BOUND','Instruction limit');self.instruction_count+=1;self.decoded+=32;require(self.decoded<=MAX_BYTES,'BOUND','Decoded metadata limit')
    def reserve(self,cap):
        require(type(cap) is int and cap>0 and self.select_count<16 and self.instruction_count<20 and self.reserved+cap<=MAX_BYTES,'BOUND','SELECT or reserved byte limit')
        self.select_count+=1;self.instruction_count+=1;self.reserved+=cap
    def summary(self):return {'selects':self.select_count,'instructions':self.instruction_count,'reservedBytes':self.reserved,'decodedBytes':self.decoded,'maximumSelects':16,'maximumInstructions':20,'maximumDecodedBytes':MAX_BYTES}

def queries():
    model=fixed_inputs();old=load(PILOT/'rds_catalogue.py','frozen_rds_catalogue_queries').QUERIES
    queries={k:(old[k],(SCHEMAS,)) for k in ['relations','columns','constraints','indexes']}
    queries['relations']=(old['relations'].replace("c.relkind='v'","c.relkind IN ('v','m')").replace("('r','p','v','S')","('r','p','v','m','S')").replace('c.reloptions AS options',"c.reloptions AS options,pg_get_userbyid(c.relowner) AS owner,c.relacl::text AS acl,c.relrowsecurity AS row_security,obj_description(c.oid,'pg_class') AS comment,CASE WHEN c.relkind IN ('v','m') THEN ARRAY(SELECT ROW(a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,a.attgenerated,CASE WHEN a.attcollation=0 THEN NULL ELSE a.attcollation::regcollation::text END)::text FROM pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped ORDER BY a.attnum) ELSE NULL END AS view_columns"),(SCHEMAS,))
    queries['columns']=(old['columns'].replace('a.attgenerated AS generated,',"a.attgenerated AS generated,a.attacl::text AS acl,CASE WHEN a.attcollation=0 THEN NULL ELSE a.attcollation::regcollation::text END AS collation,"),(SCHEMAS,))
    queries['constraints']=(old['constraints'].replace("('p','f','u','c')","('p','f','u','c','n','t')"),(SCHEMAS,))
    queries['identity']=("""SELECT current_database() AS database,current_user AS actor,session_user AS session_actor,current_setting('server_version_num')::integer AS server_version,current_setting('transaction_read_only') AS read_only,current_setting('transaction_isolation') AS isolation,current_setting('statement_timeout') AS statement_timeout,current_setting('lock_timeout') AS lock_timeout,current_setting('search_path') AS search_path,current_setting('TimeZone') AS timezone,pg_postmaster_start_time()::text AS started_at,(SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()) AS ssl,(SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname=current_database()) AS database_owner""",())
    queries['guards']=("""SELECT 'function' AS kind,n.nspname||'.'||p.proname AS name,pg_get_function_identity_arguments(p.oid) AS identity,p.prosecdef AS safe,p.proconfig AS settings,pg_get_functiondef(p.oid) AS definition,pg_get_userbyid(p.proowner) AS owner,p.proacl::text AS acl,p.oid::text AS oid,(to_jsonb(p)-ARRAY['prosrc','oid','pronamespace','proowner','prolang','proargtypes','proallargtypes','prorettype'])::text AS native_properties,l.lanname AS language,pg_get_function_arguments(p.oid) AS arguments,pg_get_function_result(p.oid) AS result,obj_description(p.oid,'pg_proc') AS comment FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace JOIN pg_language l ON l.oid=p.prolang WHERE n.nspname=ANY(%s)
UNION ALL SELECT 'trigger',n.nspname||'.'||c.relname||'.'||t.tgname,'',t.tgenabled='O',NULL::text[],pg_get_triggerdef(t.oid,false),pg_get_userbyid(c.relowner),NULL::text,t.oid::text,(to_jsonb(t)-ARRAY['oid','tgrelid','tgfoid','tgconstrrelid','tgconstrindid','tgconstraint'])::text,NULL::text,NULL::text,NULL::text,obj_description(t.oid,'pg_trigger') FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname=ANY(%s) AND NOT t.tgisinternal ORDER BY 1,2,3""",(SCHEMAS,SCHEMAS))
    queries['journal']=('SELECT version,content_sha256,applied_at::text AS applied_at,code_commit FROM ingest.schema_migrations ORDER BY version',())
    allowed=['ingest.dataset_snapshots','ingest.relation_contracts',*model['seed_data']]
    queries['bootstrap']=("SELECT * FROM ("+' UNION ALL '.join("SELECT '"+n+"'::text AS relation,to_jsonb(t)::text AS row FROM "+rel(n)+' t' for n in allowed)+') x ORDER BY relation,row',())
    tables={t['qualified_name'] for s in model['schemas'] for t in s['tables'] if t['phase']!='models'}
    queries['nonbootstrap']=("SELECT * FROM ("+' UNION ALL '.join("SELECT '"+n+"'::text AS relation WHERE EXISTS(SELECT 1 FROM "+rel(n)+')' for n in sorted(tables-set(allowed)-{'ingest.schema_migrations'}))+') x ORDER BY relation',())
    sequences=sorted(v['relation'] for v in historical()['relations'] if v['relkind']=='S')
    queries['sequences']=('SELECT * FROM ('+' UNION ALL '.join("SELECT '"+n+"'::text AS name,q.last_value::text AS last_value,q.is_called,format_type(s.seqtypid,NULL) AS data_type,s.seqstart::text AS start_value,s.seqincrement::text AS increment,s.seqmax::text AS max_value,s.seqmin::text AS min_value,s.seqcache::text AS cache,s.seqcycle AS cycle FROM "+rel(n)+" q JOIN pg_sequence s ON s.seqrelid='"+n+"'::regclass" for n in sequences)+') x ORDER BY name',())
    actor_set="SELECT oid FROM pg_roles WHERE rolname IN ('statarena_admin','statarena_ingest','statarena_runtime') UNION SELECT nspowner FROM pg_namespace WHERE nspname IN ('ingest','football','analytics') UNION SELECT c.relowner FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname IN ('ingest','football','analytics') UNION SELECT p.proowner FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname IN ('ingest','football','analytics')"
    roles="SELECT rolname,rolsuper,rolinherit,rolcreaterole,rolcreatedb,rolcanlogin,rolreplication,rolconnlimit,rolvaliduntil::text,rolbypassrls,rolconfig FROM pg_roles WHERE oid IN ("+actor_set+") ORDER BY rolname"
    memberships="SELECT p.rolname AS parent,c.rolname AS child,g.rolname AS grantor,m.admin_option,m.inherit_option,m.set_option FROM pg_auth_members m JOIN pg_roles p ON p.oid=m.roleid JOIN pg_roles c ON c.oid=m.member JOIN pg_roles g ON g.oid=m.grantor WHERE m.roleid IN ("+actor_set+") OR m.member IN ("+actor_set+") ORDER BY 1,2,3"
    schemas="SELECT nspname AS name,pg_get_userbyid(nspowner) AS owner,nspacl::text AS acl FROM pg_namespace WHERE nspname IN ('ingest','football','analytics') ORDER BY 1"
    defaults="SELECT r.rolname AS owner,coalesce(n.nspname,'GLOBAL') AS schema,d.defaclobjtype::text AS kind,d.defaclacl::text AS acl FROM pg_default_acl d JOIN pg_roles r ON r.oid=d.defaclrole LEFT JOIN pg_namespace n ON n.oid=d.defaclnamespace WHERE (d.defaclnamespace=0 OR n.nspname IN ('ingest','football','analytics')) AND d.defaclrole IN ("+actor_set+") ORDER BY 1,2,3"
    privileges="""SELECT r.role,'table' AS kind,n.nspname||'.'||c.relname AS name,has_table_privilege(r.role,c.oid,'SELECT') AS readable,has_table_privilege(r.role,c.oid,'INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER') OR has_any_column_privilege(r.role,c.oid,'INSERT,UPDATE,REFERENCES') AS writable FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace CROSS JOIN (VALUES('statarena_ingest'),('statarena_runtime'))r(role) WHERE n.nspname IN ('ingest','football','analytics') AND c.relkind IN ('r','p','v','m')
UNION ALL SELECT r.role,'function',p.oid::regprocedure::text,has_function_privilege(r.role,p.oid,'EXECUTE'),false FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace CROSS JOIN (VALUES('statarena_ingest'),('statarena_runtime'))r(role) WHERE n.nspname IN ('ingest','football','analytics')
UNION ALL SELECT r.role,'sequence',n.nspname||'.'||c.relname,false,has_sequence_privilege(r.role,c.oid,'USAGE,SELECT,UPDATE') FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace CROSS JOIN (VALUES('statarena_ingest'),('statarena_runtime'))r(role) WHERE n.nspname IN ('ingest','football','analytics') AND c.relkind='S'
UNION ALL SELECT r.role,'schema',n.nspname,has_schema_privilege(r.role,n.oid,'USAGE'),has_schema_privilege(r.role,n.oid,'CREATE') FROM pg_namespace n CROSS JOIN (VALUES('statarena_ingest'),('statarena_runtime'))r(role) WHERE n.nspname IN ('ingest','football','analytics') ORDER BY 1,2,3"""
    pieces={k:s for k,s in [('roles',roles),('memberships',memberships),('schemas',schemas),('default_acl',defaults),('privileges',privileges)]}
    queries['security']=('SELECT '+','.join("(SELECT coalesce(json_agg(row_to_json(x)), '[]'::json)::text FROM ("+s+') x) AS '+k for k,s in pieces.items()),())
    queries['concurrency']=("""SELECT 'writer' AS kind,a.usename AS actor,ROW(a.application_name,a.state)::text AS detail FROM pg_stat_activity a WHERE datname=current_database() AND pid<>pg_backend_pid() AND (xact_start IS NOT NULL OR state IS NULL) AND usename NOT IN ('statarena_runtime','rdsadmin')
UNION ALL SELECT 'advisory',a.usename,ROW(l.classid,l.objid,l.objsubid,l.granted)::text FROM pg_locks l LEFT JOIN pg_stat_activity a ON a.pid=l.pid WHERE l.locktype='advisory' AND l.database=(SELECT oid FROM pg_database WHERE datname=current_database()) AND l.pid<>pg_backend_pid()
UNION ALL SELECT 'write_lock',a.usename,ROW(n.nspname,c.relname,l.mode,l.granted)::text FROM pg_locks l JOIN pg_class c ON c.oid=l.relation JOIN pg_namespace n ON n.oid=c.relnamespace LEFT JOIN pg_stat_activity a ON a.pid=l.pid WHERE l.database=(SELECT oid FROM pg_database WHERE datname=current_database()) AND l.pid<>pg_backend_pid() AND n.nspname IN ('ingest','football','analytics') AND l.mode IN ('RowExclusiveLock','ShareRowExclusiveLock','ShareUpdateExclusiveLock','ExclusiveLock','AccessExclusiveLock') ORDER BY 1,2,3""",())
    queries['retained']=("SELECT nspname AS name FROM pg_namespace WHERE nspname IN ('statarena','statarena_app') ORDER BY 1",())
    queries['validator']=("SELECT p.oid::text AS oid,pg_get_userbyid(p.proowner) AS owner,(to_jsonb(p)-ARRAY['prosrc','oid','pronamespace','proowner','prolang','proargtypes','proallargtypes','prorettype'])::text AS properties,l.lanname AS language,pg_get_function_arguments(p.oid) AS arguments,pg_get_function_result(p.oid) AS result,obj_description(p.oid,'pg_proc') AS comment FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace JOIN pg_language l ON l.oid=p.prolang WHERE n.nspname='ingest' AND p.proname='validate_generation' AND p.proargtypes='20'::oidvector",())
    return {k:queries[k] for k in NAMES}

def envelope(sql):
    return "WITH raw AS MATERIALIZED ("+sql+"),encoded AS MATERIALIZED (SELECT row_to_json(raw)::text AS v,row_number() OVER() AS ordinal FROM raw),measured AS (SELECT count(*) AS n,coalesce(sum(octet_length(v)),0)+greatest(count(*)-1,0)+2 AS bytes FROM encoded) SELECT CASE WHEN n<=%s AND bytes<=%s THEN (SELECT '['||coalesce(string_agg(v,',' ORDER BY ordinal),'')||']' FROM encoded) END,n,bytes FROM measured"
def check_identity(conn,row,local_write=False):
    require(conn.info.server_version==180006 and row['server_version']==180006 and row['actor']==row['session_actor']==ACTOR and row['database_owner']==ACTOR,'ROLE','Named engine/actor/database owner differs')
    require(row['statement_timeout']=='8s' and row['lock_timeout']=='1s' and row['search_path']=='pg_catalog' and row['timezone']=='UTC' and row['isolation']=='repeatable read' and row['ssl'] is True,'IDENTITY','TLS/startup/deadline contract differs')
    require(row['read_only']=='on' or local_write,'IDENTITY','Readonly session required')
def observe(conn,row_caps=None,*,local_write=False,byte_caps=None,budget=None,identity_check=None):
    caps={**BYTE_CAPS,**(byte_caps or {})};require(set(caps)==set(NAMES) and sum(caps.values())<=MAX_BYTES,'BOUND','Unknown or oversized query allocation');rows_caps=row_caps or DEFAULT_ROWS;b=budget or Budget();groups={};log=[]
    for name,(sql,params) in queries().items():
        cap=caps[name];b.reserve(cap);start=time.monotonic();payload,count,size=conn.execute(envelope(sql),(*params,rows_caps[name]-1,cap-128)).fetchone();used=(len(payload.encode()) if payload is not None else 1)+len(str(count))+len(str(size))+16;b.decoded+=used
        log.append({'name':name,'sql':envelope(sql),'params':[*(list(params)),rows_caps[name]-1,cap-128],'rows':count,'serverEncodedBytes':size,'decodedBytes':used,'elapsedMs':round((time.monotonic()-start)*1000,3)})
        require(payload is not None and used<=cap and b.decoded<=MAX_BYTES,'BOUND','Server metadata row/byte envelope refused');groups[name]=json.loads(payload)
        if name=='identity':require(len(groups[name])==1,'IDENTITY','One identity required');check_identity(conn,groups[name][0],local_write);identity_check and identity_check(groups[name][0])
    require(not groups['concurrency'],'CONCURRENCY','Another transaction, lease or write lock is active')
    result={'groups':groups,'queries':log,'budget':b.summary()};result['metadataBytes']=metadata_bytes(result);return result

def stable(state):
    value=copy.deepcopy({k:v for k,v in state['groups'].items() if k not in {'identity','concurrency'}})
    for row in value['relations']:row.pop('bytes',None)
    return value
def state_hash(state):return hashed(stable(state))
def check_bootstrap(groups):
    model=fixed_inputs();old=historical();rows=groups['bootstrap'];native={}
    for r in rows:native.setdefault(r['relation'],[]).append(json.loads(r['row']))
    snap=native.get('ingest.dataset_snapshots',[]);want=old['bootstrap_snapshot'][0]
    require(len(snap)==1 and all(snap[0].get(k)==v for k,v in want.items()) and snap[0]['transform_version']=='bootstrap_v1' and snap[0]['source_priority_version']=='bootstrap_v1' and snap[0]['knowledge_cutoff_at'] is None,'BOOTSTRAP','Exact sealed B0 snapshot required')
    for name in model['seed_data']:
        expected=[r['row'] for r in old['seeds'] if r['relation']==name];require(sorted(native.get(name,[]),key=lambda v:v['code'])==sorted(expected,key=lambda v:v['code']),'BOOTSTRAP','Native bootstrap seed drift')
    require(sorted(native.get('ingest.relation_contracts',[]),key=lambda v:v['relation_name'])==sorted(old['contracts'],key=lambda v:v['relation_name']),'BOOTSTRAP','Native bootstrap contracts differ')
    require(not groups['nonbootstrap'],'BUSINESS','Bootstrap-only target contains business/control data')
def check_historical(state):
    old=historical();g=state['groups'];check_bootstrap(g)
    for name,oldname in [('relations','relations'),('columns','columns'),('constraints','constraints'),('indexes','indexes'),('guards','functions_triggers')]:
        wanted=old[oldname];keys=set(wanted[0]);keys.discard('bytes');actual=[{k:r[k] for k in keys} for r in g[name] if name!='constraints' or r['kind'] not in {'n','t'}];expected=[{k:r[k] for k in keys} for r in wanted]
        require(sorted(map(canonical,actual))==sorted(map(canonical,expected)),'CATALOGUE','Attested B0 structure differs')
    require([{k:r[k] for k in ['version','content_sha256','code_commit']} for r in g['journal']]==old['journal'],'JOURNAL','Attested B0 journal differs')
    require(all(r['applied_at'] is not None for r in g['journal']),'JOURNAL','Native journal clocks absent')
    grants=json.loads(g['security'][0]['privileges']);runtime=[{k:r[k] for k in ['kind','name','readable','writable']} for r in grants if r['role']=='statarena_runtime' and r['kind']!='schema']
    require(sorted(map(canonical,runtime))==sorted(map(canonical,old['runtime_effective_privileges'])),'CATALOGUE','Attested runtime grants differ')
    schemas=[{'schema':r['name'],'usable':r['readable'],'creatable':r['writable']} for r in grants if r['role']=='statarena_runtime' and r['kind']=='schema']
    require(sorted(map(canonical,schemas))==sorted(map(canonical,old['runtime_schema_access'])),'CATALOGUE','Attested schema access differs')
    require(g['retained']==[{'name':'statarena'},{'name':'statarena_app'}],'CATALOGUE','Existing source namespaces absent')
def verify_state(state,contract):
    groups=state['groups'];check_bootstrap(groups);base=contract['baseline'];journal=groups['journal'];expected=base['journal'];versions=[r['version'] for r in journal]
    require(versions in [['012','013'],['012','013','014']],'JOURNAL','Unknown migration chain');require(journal[:2]==expected,'JOURNAL','Existing native journal rows changed');current='P1' if len(journal)==3 else 'P0'
    if current=='P1':
        tail=journal[2];require(tail['content_sha256']==SQL14_SHA and tail['code_commit']==contract['releaseCommit'] and tail['applied_at'] is not None,'JOURNAL','014 binding/clock differs')
        try:clock=datetime.fromisoformat(tail['applied_at']);require(clock.tzinfo is not None,'JOURNAL','014 clock must be aware')
        except (ValueError,TypeError):raise Refusal('JOURNAL','014 clock malformed') from None
    wanted=copy.deepcopy(base)
    if current=='P1':
        for row in wanted['guards']:
            if row['kind']=='function' and row['name']=='ingest.validate_generation' and row['identity']=='g bigint':row['definition']=contract['p1Definition']
    actual=stable(state);actual.pop('journal');wanted.pop('journal')
    for name in wanted:
        code='BOOTSTRAP' if name=='bootstrap' else 'SEQUENCE' if name=='sequences' else 'CATALOGUE'
        require(actual[name]==wanted[name],code,'Exact native policy metadata differs')
    return current

def no_pg_environment():require(not any(k.startswith('PG') for k in os.environ),'ROUTE','Inherited libpq options/routing are forbidden')
def validated_rds_passfile(environ=None):
    env=os.environ if environ is None else environ
    require(not any(k.startswith('PG') for k in env),'ROUTE','Inherited libpq options/routing are forbidden')
    raw=env.get('ORION_RDS_PASSFILE')
    require(isinstance(raw,str) and bool(raw),'AUTH','Dedicated private authentication file required')
    path=Path(raw)
    require(path.is_absolute() and '..' not in path.parts,'AUTH','Dedicated private authentication file required')
    try:
        leaf=path.lstat();parent=path.parent.lstat()
    except (OSError,ValueError):raise Refusal('AUTH','Private authentication metadata unavailable') from None
    require(stat.S_ISREG(leaf.st_mode) and leaf.st_uid==os.getuid() and stat.S_IMODE(leaf.st_mode)==0o600 and
            stat.S_ISDIR(parent.st_mode) and parent.st_uid==os.getuid() and stat.S_IMODE(parent.st_mode)==0o700,
            'AUTH','Private authentication metadata differs')
    return str(path)
def _rds_connection_kwargs(passfile,address):
    return dict(host=HOST,hostaddr=address,port=5432,dbname=DATABASE,user=ACTOR,sslmode='verify-full',
                sslrootcert=str(CA),passfile=passfile,autocommit=True,connect_timeout=7,options=OPTIONS,
                application_name='orion-rds-policy-readonly-complement')
def owned_marker(path):
    path=Path(path)
    try:raw=path.lstat()
    except OSError:raise Refusal('LOCAL','Owned marker required') from None
    require(stat.S_ISREG(raw.st_mode),'LOCAL','Owned marker must be a regular raw file')
    path=path.resolve();m=json_file(path,16384);root=Path(m.get('ownedRoot','')).resolve();require(m.get('kind')=='orion_rds_policy_owned_pg18_v1' and root.name.startswith('orion-pro-e2e-') and root.is_dir() and path.parent==root and path.stat().st_uid==os.getuid() and stat.S_IMODE(path.stat().st_mode)==0o600,'LOCAL','Owned marker required')
    require((root/'data/postmaster.pid').is_file(),'LOCAL','Owned postmaster absent');lines=(root/'data/postmaster.pid').read_text().splitlines();require(len(lines)>3 and Path(lines[1]).resolve()==root/'data' and int(lines[3])==m['port'],'LOCAL','Owned data/port differs')
    cert=Path(m['certificatePath']).resolve();require(cert.parent==root and sha(cert)==m['certificateSha256'],'LOCAL','Owned TLS certificate differs');started=datetime.fromisoformat(m['serverStartedAt']);require(started.tzinfo is not None,'LOCAL','Aware owned start time required');return m
def owned_connection(marker,database):
    fixed_inputs();no_pg_environment();require(database in DBS,'LOCAL','Unknown owned database');m=owned_marker(marker)
    import psycopg
    c=psycopg.connect(host='127.0.0.1',hostaddr='127.0.0.1',port=m['port'],dbname=database,user=ACTOR,sslmode='verify-full',sslrootcert=m['certificatePath'],autocommit=True,connect_timeout=5,options=OPTIONS,application_name='orion-rds-policy-owned')
    require(c.info.host=='127.0.0.1' and c.info.port==m['port'],'LOCAL','Owned route differs')
    def verify(r):require(r['database']==database and datetime.fromisoformat(r['started_at'])==datetime.fromisoformat(m['serverStartedAt']),'LOCAL','Owned database/start time differs')
    return c,verify
def artifact_path(path):
    path=Path(path)
    try:raw=path.lstat()
    except OSError:raise Refusal('INPUT','Artifact must be a regular qualification file') from None
    require(stat.S_ISREG(raw.st_mode),'INPUT','Artifact must be a regular raw qualification file')
    path=path.resolve();require(path.is_relative_to(BASE/'runs') and path.is_file(),'INPUT','Artifact must be a regular qualification file');return path
def load_contract(path,digest):
    path=artifact_path(path);require(sha(path)==digest,'INPUT','Contract hash differs');c=json_file(path);require(c.get('kind')=='owned_rds_composed_policy_contract_v1' and c['adapterSha256']==sha(Path(__file__)) and c['inputsSha256']==sha(BASE/'INPUTS.json') and c['policy']==POLICY,'INPUT','Exact local contract/code binding differs');require(c['querySha256']==hashed(queries()),'INPUT','Query templates differ');return c
def summarize(state,policy):
    g=state['groups'];counts={'tables':sum(r['relkind'] in {'r','p'} for r in g['relations']),'columns':len(g['columns']),'foreignKeys':sum(r['kind']=='f' for r in g['constraints']),'nativeConstraints':len(g['constraints']),'views':sum(r['relkind'] in {'v','m'} for r in g['relations']),'sequences':len(g['sequences'])}
    i=g['identity'][0];return {'policy':policy,'stateSha256':state_hash(state),'counts':counts,'roleFlags':json.loads(g['security'][0]['roles']),'settings':{'host':'127.0.0.1' if i['database'] in DBS else HOST,'statementTimeout':i['statement_timeout'],'lockTimeout':i['lock_timeout'],'ssl':i['ssl']},'budget':state['budget'],'metadataBytes':state['metadataBytes'],'fullAcceptance':False}
def prepare_owned(marker,database,path):
    path=Path(path).resolve();require(path.is_relative_to(BASE/'runs') and not path.exists(),'INPUT','New owned contract path required');conn,verify=owned_connection(marker,database)
    try:
        with conn.transaction():
            conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY');before=observe(conn,identity_check=verify);check_historical(before)
        rowcaps={name:len(rows)+1 for name,rows in before['groups'].items()};rowcaps.update(journal=4,nonbootstrap=90,bootstrap=32,concurrency=129)
        with conn.transaction(force_rollback=True):
            conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ WRITE');conn.execute(SQL14.read_text(),prepare=False);after=observe(conn,rowcaps,local_write=True,identity_check=verify)
            a=stable(before);b=stable(after);delta=[name for name in a if a[name]!=b[name]];require(delta==['guards'],'CATALOGUE','Overlay changes more than function metadata')
            changed=[(x,y) for x,y in zip(a['guards'],b['guards']) if x!=y];require(len(changed)==1 and changed[0][0]['name']=='ingest.validate_generation' and {k:v for k,v in changed[0][0].items() if k!='definition'}=={k:v for k,v in changed[0][1].items() if k!='definition'},'CATALOGUE','Only exact validator definition may change');p1=changed[0][1]['definition']
        contract={'kind':'owned_rds_composed_policy_contract_v1','policy':POLICY,'localOnly':True,'database':database,'adapterSha256':sha(Path(__file__)),'inputsSha256':sha(BASE/'INPUTS.json'),'querySha256':hashed(queries()),'rowCaps':rowcaps,'byteCaps':BYTE_CAPS,'baseline':stable(before),'p1Definition':p1,'p1DefinitionSha256':hashlib.sha256(p1.encode()).hexdigest(),'releaseCommit':'local_rds_policy_e2e','RdsNativeComplement':'not_observed_not_approved'};metadata_bytes(contract,before,after);save(path,contract);return {'path':str(path),'sha256':sha(path),'constraintRows':len(before['groups']['constraints']),'rowCaps':rowcaps}
    finally:conn.close()
def owned_preflight(marker,database,path,digest):
    c=load_contract(path,digest);require(c['database']==database,'LOCAL','Contract database differs');conn,verify=owned_connection(marker,database);budget=Budget()
    try:
        budget.control();budget.control()
        with conn.transaction():conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY');s=observe(conn,c['rowCaps'],budget=budget,identity_check=verify);current=verify_state(s,c)
        budget.control();s['budget']=budget.summary();return {'status':'ready_owned_only',**summarize(s,current)}
    finally:conn.close()
def _transition_core(conn,c,a,verify,*,fault=None):
    """Fixed function/journal transition; caller supplies its separately qualified connection."""
    result=None
    with conn.transaction():
        conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ WRITE')
        for sql in ['SELECT pg_try_advisory_xact_lock(20261104,2)','SELECT pg_try_advisory_xact_lock(20261104,1)','SELECT pg_try_advisory_xact_lock(97813003::bigint)']:require(conn.execute(sql).fetchone()[0],'LEASE','Existing lease held')
        before=observe(conn,c['rowCaps'],local_write=True,identity_check=verify);current=verify_state(before,c);require(state_hash(before)==a['beforeStateSha256'],'ACCEPTANCE','Accepted before-state changed')
        if current=='P1':return {'status':'reused',**summarize(before,'P1')}
        transaction_start=conn.execute('SELECT transaction_timestamp()::text').fetchone()[0];conn.execute(SQL14.read_text(),prepare=False)
        if fault=='after_function':raise Refusal('FAULT','Owned injected after-function failure')
        conn.execute('INSERT INTO ingest.schema_migrations(version,content_sha256,applied_at,code_commit) VALUES(%s,%s,CURRENT_TIMESTAMP,%s)',('014',SQL14_SHA,c['releaseCommit']))
        if fault=='after_journal':raise Refusal('FAULT','Owned injected after-journal failure')
        clock=conn.execute("SELECT applied_at::text,transaction_timestamp()::text,clock_timestamp()::text FROM ingest.schema_migrations WHERE version='014'").fetchone();require(clock[0]==clock[1]==transaction_start and datetime.fromisoformat(clock[0])<=datetime.fromisoformat(clock[2]),'JOURNAL','New native transaction clock differs')
        after=observe(conn,c['rowCaps'],local_write=True,identity_check=verify);require(verify_state(after,c)=='P1','CATALOGUE','P1 postcondition failed');require(before['groups']['validator']==after['groups']['validator'],'CATALOGUE','Native function properties changed');result={'status':'applied',**summarize(after,'P1'),'newJournalClock':dict(zip(['appliedAt','transactionStart','observedAfterInsert'],clock)),'protectedPropertiesPreserved':True}
    if fault=='after_commit':raise OutcomeUnverified('Owned commit acknowledgement lost; independent readback required')
    return result

def owned_transition(marker,database,path,digest,acceptance_path,acceptance_sha,*,fault=None):
    c=load_contract(path,digest);require(c['database']==database,'LOCAL','Contract database differs');acceptance_path=artifact_path(acceptance_path);a=json_file(acceptance_path,65536);require(sha(acceptance_path)==acceptance_sha and a=={**a,'kind':'owned_rds_policy_acceptance_v1','database':database,'contractSha256':digest,'adapterSha256':sha(Path(__file__)),'releaseCommit':c['releaseCommit'],'localOnly':True} and set(a)=={'kind','database','contractSha256','adapterSha256','beforeStateSha256','releaseCommit','localOnly'},'ACCEPTANCE','Exact owned acceptance required');require(fault in {None,'after_function','after_journal','after_commit'},'LOCAL','Unknown owned fault');conn,verify=owned_connection(marker,database);result=None
    try:return _transition_core(conn,c,a,verify,fault=fault)
    finally:conn.close()

def validate_release(path,digest):
    path=Path(path).resolve();require(path==BASE/'ROOT_RDS_READONLY_RELEASE.json' and path.is_file() and sha(path)==digest,'RELEASE','Separate fixed ROOT readonly release required');r=json_file(path,65536)
    target={'host':HOST,'port':5432,'database':DATABASE,'actor':ACTOR,'engine':180006,'sslmode':'verify-full','caSha256':sha(CA)}
    require(r.get('kind')=='orion_rds_policy_ro_release_v1' and r.get('authorizedBy')=='ROOT' and r.get('adapterSha256')==sha(Path(__file__)) and r.get('inputsSha256')==sha(BASE/'INPUTS.json') and r.get('target')==target and r.get('proEnabled') is False and r.get('collectorsEnabled') is False,'RELEASE','ROOT release target/code/scope differs')
    proof=artifact_path(r['localReceiptPath']);require(sha(proof)==r['localReceiptSha256'],'RELEASE','Local proof hash differs');p=json_file(proof);require(p.get('status')=='pass' and p.get('counts')=={'pass':20,'fail':0,'unverified':0} and p.get('protectedAfterExact') is True and p.get('cleanup',{}).get('server_stopped') is True and p.get('cleanup',{}).get('owned_directory_removed') is True,'RELEASE','Completed local qualification required')
    require(p['cases'][0]['actual']['adapterSha256']==sha(Path(__file__)) and p['cases'][2]['actual']['contractSha256']==r['preparedContractSha256'],'RELEASE','Prepared contract/code not bound by completed E2E')
    prepared=load_contract(r['preparedContractPath'],r['preparedContractSha256']);require(r.get('ledgerPath')==str(BASE/'remote-budget-v1.json'),'RELEASE','New fixed remote ledger required');return r,prepared
def remote_preflight(args):
    fixed_inputs();require(args.expected_selects==0 and args.expected_decoded_bytes==0 and args.expected_instructions==0,'CHECKPOINT','Explicit zero checkpoint required');r,c=validate_release(args.release,args.expect_release_sha256);passfile=validated_rds_passfile();ledger_path=BASE/'remote-budget-v1.json'
    with ledger_path.open('r+') as f:
        fcntl.flock(f,fcntl.LOCK_EX);ledger=json.load(f);require(ledger=={'kind':'rds_policy_one_shot_ro_budget_v1','state':'unstarted','selects':0,'decodedBytes':0,'instructions':0,'releaseSha256':args.expect_release_sha256},'CHECKPOINT','Remote ledger missing/consumed or mismatched');ledger['state']='claimed';f.seek(0);json.dump(ledger,f,indent=2);f.truncate()
    report={'kind':'rds_native_complement_readonly_v1','status':'failed','remoteWrites':[],'fullAcceptance':False,'releaseSha256':args.expect_release_sha256};conn=None;budget=Budget();out=BASE/'rds-readbacks'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True)
    try:
        addresses=sorted({item[4][0] for item in socket.getaddrinfo(HOST,5432,type=socket.SOCK_STREAM)});require(bool(addresses),'ROUTE','Fixed endpoint resolution failed')
        import psycopg
        conn=psycopg.connect(**_rds_connection_kwargs(passfile,addresses[0]))
        require(conn.info.host==HOST and conn.info.port==5432,'ROUTE','Fixed RDS route differs');budget.control();budget.control()
        with conn.transaction():conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY');state=observe(conn,c['rowCaps'],budget=budget);require(state['groups']['identity'][0]['database']==DATABASE,'IDENTITY','RDS database differs');check_historical(state)
        budget.control();report.update(status='observed_bootstrap_needs_ROOT_review',nativeComplement=state,preparedP1DefinitionSha256=c['p1DefinitionSha256'],localFixtureSecurityNotTransplanted=True)
    except Exception as error:report['error']={'type':type(error).__name__,'code':getattr(error,'code',None),'sqlstate':getattr(error,'sqlstate',None)}
    finally:
        if conn is not None:conn.close()
        report['budget']=budget.summary();report['connectionClosed']=conn is None or conn.closed
        raw=canonical(report)
        if len(raw)>MAX_BYTES:report={'status':'failed','reason':'receipt_byte_limit','budget':budget.summary(),'remoteWrites':[],'fullAcceptance':False}
        (out/'result.json').write_bytes(canonical(report)+b'\n');ledger.update(state='consumed',selects=budget.select_count,decodedBytes=budget.decoded,instructions=budget.instruction_count,result=str(out/'result.json'));save(ledger_path,ledger)
    return {'status':report['status'],'evidence':str(out/'result.json'),'fullAcceptance':False}
def main():
    p=argparse.ArgumentParser(description=__doc__);m=p.add_mutually_exclusive_group();m.add_argument('--owned-preflight',action='store_true');m.add_argument('--owned-transition',action='store_true');m.add_argument('--preflight-rds',action='store_true')
    p.add_argument('--marker',type=Path);p.add_argument('--database',choices=sorted(DBS));p.add_argument('--contract',type=Path);p.add_argument('--expect-contract-sha256');p.add_argument('--acceptance',type=Path);p.add_argument('--expect-acceptance-sha256');p.add_argument('--release',type=Path);p.add_argument('--expect-release-sha256');p.add_argument('--expected-selects',type=int);p.add_argument('--expected-decoded-bytes',type=int);p.add_argument('--expected-instructions',type=int);a=p.parse_args()
    try:
        fixed_inputs()
        if a.preflight_rds:out=remote_preflight(a)
        elif a.owned_preflight or a.owned_transition:
            require(all([a.marker,a.database,a.contract,a.expect_contract_sha256]),'LOCAL','Explicit owned marker/database/contract required');out=owned_transition(a.marker,a.database,a.contract,a.expect_contract_sha256,a.acceptance,a.expect_acceptance_sha256) if a.owned_transition else owned_preflight(a.marker,a.database,a.contract,a.expect_contract_sha256)
        else:out={'status':'offline_plan','policy':POLICY,'connections':0,'remoteApplyAvailable':False,'queryCount':14,'reservedBytes':sum(BYTE_CAPS.values()),'unknownRdsNativeFieldsRequireROOTReview':True,'fullAcceptance':False}
        print(json.dumps(out));return 0 if out['status']!='failed' else 1
    except Exception as e:
        print(json.dumps({'status':'refused','code':getattr(e,'code','INPUT'),'errorType':type(e).__name__,'sqlstate':getattr(e,'sqlstate',None),'fullAcceptance':False}));return 2
if __name__=='__main__':raise SystemExit(main())
