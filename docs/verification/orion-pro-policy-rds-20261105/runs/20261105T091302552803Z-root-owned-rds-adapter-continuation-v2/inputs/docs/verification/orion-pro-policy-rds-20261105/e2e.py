#!/usr/bin/env python3
"""Complete pre-code owned-PG qualification; no remote/source/RAM client."""
from __future__ import annotations
import argparse, ast, copy, fcntl, hashlib, importlib.util, json, os, pwd, re, shutil, stat, subprocess, sys, tempfile, threading, time, _thread
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[2];SCRIPTS=ROOT/'dashboard/scripts';PILOT=ROOT/'docs/verification/orion-pro-pilot-20261104';ADAPTER=BASE/'adapter.py'
DBS=['rds_policy_empty','rds_policy_populated'];ACTOR='statarena_admin'
OPTIONS='-c default_transaction_read_only=on -c statement_timeout=8000 -c lock_timeout=1000 -c idle_in_transaction_session_timeout=15000 -c search_path=pg_catalog -c timezone=UTC -c datestyle=ISO,YMD -c extra_float_digits=3'
CASES=['implementation_available','owned_tls_setup','prepare_composed_contract','offline_and_remote_boundary','owned_cli_and_route_pins','catalogue_and_equivalence','nonzero_roles_exact','native_catalogue_drift','native_acl_drift','journal_and_clocks','bootstrap_and_populated','sequence_state','leases_and_concurrency','atomic_failures','adoption_clock_and_preservation','lost_acknowledgement','fresh_process_noop','old_guards_stay_closed','bounded_queries_and_checkpoints','protected_inputs_and_cleanup']
PARENT_SHA={'campaign':'3d65c2ca695bd261959c4831f0585b77a4050d7111257a923259924e884d3114','result':'520d42f7bccb0446e783e1d9bba40a6cde68d4055ae9ed6fd35a4e0bf966b7c3','manifest':'2a4dd3b91f9638feb19b70b480d9f2fa9e1741ce21366050640cde945b9b0706'}
LOCAL_LIMITS={'maximumPgStarts':1,'databases':2,'seconds':600,'statementTimeoutMs':8000,'lockTimeoutMs':1000,'diskHardBytes':8589934592,'diskSoftBytes':7516192768,'metadataBytes':33554432,'evidenceBytes':67108864,'tempBytesPerBackend':536870912}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):Path(p).write_text(json.dumps(x,indent=2,ensure_ascii=False,default=str)+'\n')
def hashed(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def q(x):assert re.fullmatch('[a-z_][a-z0-9_]*',x);return '"'+x+'"'
def rel(x):return '.'.join(q(v) for v in x.split('.'))
def load(p,name):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def parent_exact():
    return sha(BASE/'campaign.json')==PARENT_SHA['campaign'] and sha(BASE/'runs/20261105T023121117636Z-owned-rds-adapter-compact/result.json')==PARENT_SHA['result'] and sha(BASE/'ATTEMPT_1_HASHES.json')==PARENT_SHA['manifest']
def continuation(args):
    assert parent_exact(),'Original campaign/evidence changed'
    assert args.continuation_release and args.expect_continuation_sha256 and args.ledger,'Separate ROOT continuation release/hash/ledger required'
    release=Path(args.continuation_release);ledger=Path(args.ledger)
    assert stat.S_ISREG(release.lstat().st_mode) and release.resolve()==BASE/'ROOT_LOCAL_CONTINUATION_V2.json'
    assert stat.S_ISREG(ledger.lstat().st_mode) and ledger.resolve()==BASE/'campaign-v2.json'
    assert sha(release)==args.expect_continuation_sha256
    r=json.loads(release.read_text());auth_tree=ast.parse((BASE/'auth_guard_e2e.py').read_text());auth_cases=next(ast.literal_eval(n.value) for n in auth_tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='CASE_NAMES' for t in n.targets))
    expected_code={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),ADAPTER,BASE/'auth_guard_e2e.py']}
    assert r.get('kind')=='rds_policy_owned_continuation_release_v2' and r.get('authorizedBy')=='ROOT' and r.get('scope')=='source_free_owned_only'
    assert r.get('parentSha256')==PARENT_SHA and r.get('codeSha256')==expected_code and r.get('inputsSha256')==sha(BASE/'INPUTS.json')
    assert r.get('expectedCases')==CASES and r.get('expectedAuthCases')==auth_cases and r.get('limits')==LOCAL_LIMITS and r.get('ledgerPath')==str((BASE/'campaign-v2.json').relative_to(ROOT))
    x=json.loads(ledger.read_text());assert x=={'kind':'rds_policy_owned_campaign_v2','state':'unstarted','pgStarts':0,'maximumPgStarts':1,'releaseSha256':args.expect_continuation_sha256,'parentCampaignSha256':PARENT_SHA['campaign'],'limits':LOCAL_LIMITS},'Continuation ledger consumed/mismatched'
    return ledger.resolve()
def ledger_update(path,fn):
    assert path==BASE/'campaign-v2.json' and parent_exact()
    with path.open('r+') as f:
        fcntl.flock(f,fcntl.LOCK_EX);x=json.load(f);fn(x);f.seek(0);json.dump(x,f,indent=2);f.write('\n');f.truncate();return x

class Watch:
    def __init__(self,pg):
        self.pg=pg;self.start=time.monotonic();self.stop=threading.Event();self.reason=None;self.samples=[];self.t=threading.Thread(target=self.run,daemon=True);self.t.start()
    def run(self):
        while not self.stop.wait(1):
            try:
                disk=int(subprocess.check_output(['du','-sk',str(self.pg.root)],text=True).split()[0])*1024
                proof=sum(p.stat().st_size for p in BASE.rglob('*') if p.is_file() and not p.is_symlink());elapsed=time.monotonic()-self.start
                self.samples.append({'seconds':round(elapsed,3),'ownedBytes':disk,'evidenceBytes':proof})
                if disk>=7*1024**3 or proof>=64*1024**2 or elapsed>=600:self.reason='resource_limit';_thread.interrupt_main();return
            except OSError:self.reason='monitor_failure';_thread.interrupt_main();return
    def close(self):self.stop.set();self.t.join(2)

@contextmanager
def snapshot(conn):
    if conn.info.transaction_status==0:
        with conn.transaction():conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY');yield
    else:yield

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);parser.add_argument('--pg-bin',type=Path,default=Path('/tmp/statarena-cache-test-tools/node_modules/@embedded-postgres/darwin-arm64/native/bin'));parser.add_argument('--continuation-release',type=Path);parser.add_argument('--expect-continuation-sha256');parser.add_argument('--ledger',type=Path);args=parser.parse_args();assert re.fullmatch('[A-Za-z0-9][A-Za-z0-9-]{0,70}',args.label)
    try:ledger_path=continuation(args)
    except Exception as error:print(json.dumps({'status':'refused','reason':'ROOT continuation inputs missing/mismatched/consumed','errorType':type(error).__name__,'postgresStarts':0}));return 2
    sys.path[:0]=[str(SCRIPTS),str(PILOT),'/tmp/statarena-publication-test-python']
    run=BASE/'runs'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-'+args.label);(run/'inputs').mkdir(parents=True)
    pins=json.loads((BASE/'INPUTS.json').read_text())['files'];assert all(sha(ROOT/p)==h for p,h in pins.items())
    for path in [Path(__file__),BASE/'ADAPTER_PROTOCOL.md',BASE/'PREPARATION_V2_PROTOCOL.md',BASE/'AUTH_GUARD_PROTOCOL.md',BASE/'auth_guard_e2e.py',BASE/'INPUTS.json',Path(args.continuation_release),ADAPTER,*[ROOT/p for p in pins]]:
        if path.is_file():
            dest=run/'inputs'/path.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
    report={'kind':'source_free_rds_policy_adapter_e2e_v1','command':[sys.executable,str(Path(__file__)),*sys.argv[1:]],'startedAt':datetime.now(timezone.utc).isoformat(),'expected':str(BASE/'ADAPTER_PROTOCOL.md'),'cases':[],'protectedBefore':pins,'remoteCalls':0,'sourceOrRamReads':0,'fullAcceptance':False}
    pg=watch=setup=owner=second=lock=None;private=None;blocker=None;adp=None;contracts={};accepts={};marker=None;cert=None
    model=json.loads((ROOT/'docs/architecture/orion-plan-20261104/target-schema.proposed.json').read_text());tables={t['qualified_name']:t for s in model['schemas'] for t in s['tables'] if t['phase']!='models'}
    def connect(db,actor=ACTOR):
        return psycopg.connect(host='127.0.0.1',hostaddr='127.0.0.1',port=pg.port,dbname=db,user=actor,sslmode='verify-full',sslrootcert=str(cert),autocommit=True,connect_timeout=5,options=OPTIONS,application_name='rds-policy-owned-e2e')
    def verify_os_super(c):
        r=c.execute("SELECT current_database(),current_user,rolsuper,current_setting('data_directory'),current_setting('statement_timeout'),current_setting('lock_timeout'),(SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()),current_setting('transaction_read_only') FROM pg_roles WHERE rolname=current_user").fetchone()
        assert c.info.server_version==180006 and c.info.host=='127.0.0.1' and c.info.port==pg.port and r[1:3]==(pwd.getpwuid(os.getuid()).pw_name,True) and Path(r[3]).resolve()==pg.data.resolve() and r[4:]==('8s','1s',True,'on')
    def super_sql(statement):
        c=connect(DBS[0],pwd.getpwuid(os.getuid()).pw_name)
        try:
            verify_os_super(c)
            with c.transaction():c.execute('SET TRANSACTION READ WRITE');c.execute(statement)
        finally:c.close()
    def audit(conn):
        out={'native':{},'journal':None,'sequences':None,'catalogue':None}
        with snapshot(conn):
            for name,t in sorted(tables.items()):
                if name=='ingest.schema_migrations':continue
                h=hashlib.sha256();count=0
                for (value,) in conn.execute('SELECT ROW(t.*)::text FROM '+rel(name)+' t ORDER BY '+','.join('t.'+q(c) for c in t['primary_key']['columns'])):
                    b=value.encode();h.update(len(b).to_bytes(8,'big'));h.update(b);count+=1
                out['native'][name]={'count':count,'sha256':h.hexdigest()}
            out['journal']=[list(r) for r in conn.execute('SELECT version,content_sha256,applied_at::text,code_commit FROM ingest.schema_migrations ORDER BY version')]
            seq=[]
            for schema,name in conn.execute("SELECT schemaname,sequencename FROM pg_sequences WHERE schemaname IN ('ingest','football','analytics') ORDER BY 1,2"):
                value=conn.execute('SELECT last_value,is_called FROM '+rel(schema+'.'+name)).fetchone();seq.append([schema,name,*value])
            out['sequences']=seq
            sql=policy.CATALOGUE_SQL.replace('policy_owner',ACTOR).replace('policy_ingest','statarena_ingest').replace('policy_runtime','statarena_runtime')
            out['catalogue']={kind+':'+key:hashlib.sha256(value.encode()).hexdigest() for kind,key,value in conn.execute(sql)}
        return out
    def cpath(db):return contracts[db]['path']
    def contract(db=DBS[0]):return adp.load_contract(cpath(db),sha(cpath(db)))
    def preflight(db=DBS[0]):return adp.owned_preflight(marker,db,cpath(db),sha(cpath(db)))
    def accept(db=DBS[0]):
        current=preflight(db);p=run/('acceptance-'+db+'-'+str(len(accepts))+'.json');value={'kind':'owned_rds_policy_acceptance_v1','database':db,'contractSha256':sha(cpath(db)),'adapterSha256':sha(ADAPTER),'beforeStateSha256':current['stateSha256'],'releaseCommit':'local_rds_policy_e2e','localOnly':True};save(p,value);accepts[str(p)]=value;return p
    def apply(db=DBS[0],fault=None):
        p=accept(db);return adp.owned_transition(marker,db,cpath(db),sha(cpath(db)),p,sha(p),fault=fault)
    def refuses(fn,codes):
        try:fn()
        except adp.Refusal as error:
            assert error.code in ({codes} if isinstance(codes,str) else codes),(error.code,codes);return {'code':error.code}
        raise AssertionError('Expected reviewed refusal')
    def mutate(sql,expected_codes):
        before=audit(owner)
        with owner.transaction(force_rollback=True):
            owner.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ WRITE');owner.execute(sql,prepare=False)
            result=refuses(lambda:adp.verify_state(adp.observe(owner,contract()['rowCaps'],local_write=True),contract()),expected_codes)
        assert before==audit(owner);return result
    def cli(flags,name,tripwire=False,env_add=None):
        folder=run/'cli'/name;folder.mkdir(parents=True);env={k:v for k,v in os.environ.items() if not k.startswith('PG')};env['PYTHONPATH']='/tmp/statarena-publication-test-python';env['PYTHONDONTWRITEBYTECODE']='1'
        if tripwire:
            site=folder/'sitecustomize.py';site.write_text("import os,socket\nfrom pathlib import Path\nimport psycopg\ndef blocked(*a,**k):\n Path(os.environ['CONNECT_TRIPWIRE']).write_text('attempted')\n raise RuntimeError('network_forbidden')\npsycopg.connect=blocked\nsocket.getaddrinfo=blocked\n");env['PYTHONPATH']=str(folder)+':'+env['PYTHONPATH'];env['CONNECT_TRIPWIRE']=str(folder/'attempted')
        if env_add:env.update(env_add)
        command=[sys.executable,str(ADAPTER),*flags];result=subprocess.run(command,text=True,capture_output=True,env=env,timeout=40);(folder/'stdout.log').write_text(result.stdout);(folder/'stderr.log').write_text(result.stderr);save(folder/'command.json',command)
        if tripwire:assert not (folder/'attempted').exists()
        return result
    try:
        for name in CASES:
            if blocker:report['cases'].append({'case':name,'status':'unverified','reason':blocker});continue
            start=time.monotonic();actual={}
            try:
                if name=='implementation_available':
                    if not ADAPTER.is_file():
                        raise AssertionError('Adapter missing under reviewed continuation')
                    adp=load(ADAPTER,'new_rds_policy_adapter');adp.fixed_inputs();import orion_pro_policy as policy;import psycopg
                    actual={'adapterSha256':sha(ADAPTER),'testSha256':sha(Path(__file__)),'policySha256':sha(SCRIPTS/'orion_pro_policy.py')}
                elif name=='owned_tls_setup':
                    def claim(x):assert x['kind']=='rds_policy_owned_campaign_v2' and x['pgStarts']==0 and x['state']=='unstarted';x['pgStarts']=1;x['state']='running';x['startedAt']=datetime.now(timezone.utc).isoformat();x['testSha256']=sha(Path(__file__));x['adapterSha256']=sha(ADAPTER)
                    ledger_update(ledger_path,claim)
                    from harness import LocalPostgres
                    private=Path(tempfile.mkdtemp(prefix='orion-rds-policy-',dir='/tmp'));os.chmod(private,0o700);tempfile.tempdir=str(private)
                    pg=LocalPostgres(args.pg_bin,run);watch=Watch(pg);pg.command([pg.binaries/'initdb','-D',pg.data,'--auth=trust','--no-locale','--encoding=UTF8'],name='initdb')
                    ssl_config=pg.root/'ssl.cnf';ssl_config.write_text('[req]\ndistinguished_name=dn\nx509_extensions=ext\nprompt=no\n[dn]\nCN=127.0.0.1\n[ext]\nsubjectAltName=IP:127.0.0.1,DNS:localhost\nbasicConstraints=critical,CA:TRUE\n');cert=pg.root/'server.crt';key=pg.root/'server.key'
                    pg.command(['/usr/bin/openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','2','-config',ssl_config,'-keyout',key,'-out',cert],name='owned-tls-cert');os.chmod(key,0o600);shutil.copy2(cert,run/'inputs/owned-server.crt');shutil.copy2(ssl_config,run/'inputs/owned-ssl.cnf')
                    with (pg.data/'postgresql.conf').open('a') as f:f.write("\nlog_error_verbosity=terse\nlog_min_error_statement=panic\nlog_parameter_max_length_on_error=0\nstatement_timeout=8000\nlock_timeout=1000\ntemp_file_limit=512MB\nssl=on\nssl_cert_file='"+str(cert)+"'\nssl_key_file='"+str(key)+"'\n")
                    pg.start();setup=connect('postgres',os.environ.get('USER','postgres'));assert setup.info.server_version==180006
                    verify_os_super(setup);setup.execute('SET default_transaction_read_only=off') # Verified owned OS-superuser setup only; CREATE DATABASE needs autocommit.
                    for role in [ACTOR,'statarena_ingest','statarena_runtime']:setup.execute('CREATE ROLE '+q(role)+' LOGIN NOSUPERUSER '+('CREATEROLE CREATEDB' if role==ACTOR else 'NOCREATEROLE NOCREATEDB')+' NOREPLICATION NOBYPASSRLS')
                    for db in DBS:setup.execute('CREATE DATABASE '+q(db)+' OWNER '+q(ACTOR))
                    started=setup.execute('SELECT pg_postmaster_start_time()').fetchone()[0];setup.close();setup=None
                    marker=pg.root/'rds-policy-marker.json';save(marker,{'kind':'orion_rds_policy_owned_pg18_v1','ownedRoot':str(pg.root),'port':pg.port,'serverStartedAt':started.isoformat(),'certificatePath':str(cert),'certificateSha256':sha(cert)});os.chmod(marker,0o600)
                    from orion_pro_migrate import bootstrap
                    from orion_pro_integrity import role_grants_sql
                    for db in DBS:
                        c=connect(db)
                        with c.transaction():
                            c.execute('SET TRANSACTION READ WRITE');artifacts=[]
                            for version,filename in [('012','012_orion_pro_domain.sql'),('013','013_orion_pro_integrity.sql')]:
                                p=ROOT/'dashboard/backend/migrations'/filename;body=p.read_text();artifacts.append((version,p,body));c.execute(body,prepare=False);c.execute('INSERT INTO ingest.schema_migrations(version,content_sha256,applied_at,code_commit) VALUES(%s,%s,CURRENT_TIMESTAMP,%s)',(version,sha(p),'c66e03652184c19fcaf9ccd055ea293d9adc4bbb'))
                            bootstrap(c,model,artifacts);c.execute(role_grants_sql(model,'statarena_ingest','statarena_runtime'),prepare=False);c.execute('CREATE SCHEMA statarena;CREATE SCHEMA statarena_app',prepare=False)
                        c.close()
                    owner=connect(DBS[0]);second=connect(DBS[1]);actual={'settings':owner.execute("SELECT current_setting('statement_timeout'),current_setting('lock_timeout'),(SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid())").fetchone(),'serverVersion':owner.info.server_version,'databases':2};assert actual['settings']==('8s','1s',True)
                    logs=dict(owner.execute("SELECT name,setting FROM pg_settings WHERE name IN ('log_error_verbosity','log_min_error_statement','log_parameter_max_length_on_error')"));assert logs=={'log_error_verbosity':'terse','log_min_error_statement':'panic','log_parameter_max_length_on_error':'0'};actual['logging']=logs
                elif name=='prepare_composed_contract':
                    before=audit(owner)
                    for db in DBS:
                        p=run/('contract-'+db+'.json');contracts[db]={'path':p};adp.prepare_owned(marker,db,p)
                    assert before==audit(owner);c=contract();actual={'rowCaps':c['rowCaps'],'contractSha256':sha(cpath(DBS[0])),'rolledBackOverlay':True};count=owner.execute("SELECT count(*) FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname IN ('ingest','football','analytics')").fetchone()[0];assert c['rowCaps']['constraints']==count+1;actual['actualNnInclusiveConstraints']=count
                elif name=='offline_and_remote_boundary':
                    positive=cli([],name,True,{'PGHOSTADDR':'192.0.2.1','PGOPTIONS':'-c statement_timeout=0','ORION_PILOT_DATABASE_URL':'postgresql://synthetic@external.invalid/none'});assert positive.returncode==0 and json.loads(positive.stdout)['connections']==0
                    checks=[]
                    for label,flags in [('remote-no-release',['--preflight-rds']),('remote-apply',['--apply-rds']),('arbitrary-host',['--host','external.invalid']),('unknown-policy',['--policy','latest']),('missing-checkpoint',['--preflight-rds','--release',str(run/'missing.json'),'--expect-release-sha256','0'*64])]:
                        r=cli(flags,label,True);assert r.returncode==2;checks.append(label)
                    actual={'offlineNoConnections':True,'refused':checks}
                    auth=load(BASE/'auth_guard_e2e.py','same_precode_auth_guard_cases');actual['authGuard']=auth.run_cases(adp,run/'auth-guard');assert actual['authGuard']['status'] in {'pass','pass_with_uid_unisolated'}
                elif name=='owned_cli_and_route_pins':
                    flags=['--owned-preflight','--marker',str(marker),'--database',DBS[0],'--contract',str(cpath(DBS[0])),'--expect-contract-sha256',sha(cpath(DBS[0]))];r=cli(flags,name);assert r.returncode==0;actual=json.loads(r.stdout);assert actual['settings']['statementTimeout']=='8s' and actual['settings']['lockTimeout']=='1s' and actual['settings']['ssl'] is True
                    poisoned=cli(flags,'owned-poison-route',True,{'PGHOSTADDR':'192.0.2.1'});assert poisoned.returncode==2
                    alias=run/'contract-symlink.json';alias.symlink_to(cpath(DBS[0]));bad=list(flags);bad[bad.index('--contract')+1]=str(alias);r=cli(bad,'owned-contract-symlink',True);assert r.returncode==2 and json.loads(r.stdout)['code']=='INPUT'
                    marker_alias=pg.root/'marker-symlink.json';marker_alias.symlink_to(marker);bad=list(flags);bad[bad.index('--marker')+1]=str(marker_alias);r=cli(bad,'owned-marker-symlink',True);assert r.returncode==2 and json.loads(r.stdout)['code']=='LOCAL';actual['rawSymlinkRefusals']=['contract','marker']
                elif name=='catalogue_and_equivalence':
                    p=preflight();actual=p['counts'];assert actual['tables']==94 and actual['columns']==1709 and actual['foreignKeys']==431 and actual['views']==46 and actual['sequences']==67;assert policy.equivalence()=={'clauses':81,'changed':139,'retained':46,'exactReversal':True,'modelSha256':policy.MODEL_SHA}
                elif name=='nonzero_roles_exact':
                    p=preflight();flags=next(v for v in p['roleFlags'] if v['rolname']==ACTOR);assert flags['rolcreaterole'] and flags['rolcreatedb'] and not flags['rolsuper'];before=audit(owner);actual={'nativeRoleFlags':flags}
                    try:super_sql('ALTER ROLE statarena_admin NOCREATEDB');actual['oneNativeFlag']=refuses(lambda:preflight(),{'CATALOGUE','ROLE'})
                    finally:super_sql('ALTER ROLE statarena_admin CREATEDB')
                    assert before==audit(owner)
                    try:super_sql('GRANT statarena_runtime TO statarena_ingest');actual['nativeMembership']=refuses(lambda:preflight(),{'CATALOGUE','ROLE'})
                    finally:super_sql('REVOKE statarena_runtime FROM statarena_ingest')
                    assert before==audit(owner)
                elif name=='native_catalogue_drift':
                    actual={'view':mutate('ALTER VIEW ingest.public_aliases_current SET (security_barrier=true)',{'CATALOGUE'}),'constraint':mutate("ALTER TABLE football.players ADD CONSTRAINT synthetic_rds_policy_check CHECK(display_name IS DISTINCT FROM 'synthetic_reserved')",{'CATALOGUE','BOUND'}),'proc':mutate('ALTER FUNCTION ingest.validate_generation(bigint) STABLE',{'CATALOGUE'})}
                    idx=next(x for x in contract()['baseline']['indexes'] if x['method']=='btree');actual['index']=mutate('ALTER INDEX '+rel(idx['relation'].split('.')[0]+'.'+idx['name'])+' SET (fillfactor=80)',{'CATALOGUE'})
                    trig=next(x for x in contract()['baseline']['guards'] if x['kind']=='trigger');schema,table,trigger=trig['name'].split('.');actual['trigger']=mutate('ALTER TABLE '+rel(schema+'.'+table)+' DISABLE TRIGGER '+q(trigger),{'CATALOGUE'})
                elif name=='native_acl_drift':
                    actual={'schema':mutate('GRANT CREATE ON SCHEMA football TO statarena_runtime',{'CATALOGUE'}),'function':mutate('GRANT EXECUTE ON FUNCTION ingest.validate_generation(bigint) TO PUBLIC',{'CATALOGUE'}),'default':mutate('ALTER DEFAULT PRIVILEGES IN SCHEMA football GRANT SELECT ON TABLES TO PUBLIC',{'CATALOGUE'})}
                elif name=='journal_and_clocks':
                    actual={'clock':mutate("UPDATE ingest.schema_migrations SET applied_at=applied_at+interval '1 microsecond' WHERE version='012'",{'JOURNAL'}),'digest':mutate("UPDATE ingest.schema_migrations SET content_sha256=repeat('0',64) WHERE version='013'",{'JOURNAL'})}
                    actual['nullOldClock']=mutate("UPDATE ingest.schema_migrations SET applied_at=NULL WHERE version='012'",{'JOURNAL'})
                    for version in ['777','099']:
                        actual['chain'+version]=mutate("INSERT INTO ingest.schema_migrations(version,content_sha256,applied_at,code_commit) VALUES('"+version+"',repeat('0',64),CURRENT_TIMESTAMP,'synthetic_unknown')",{'JOURNAL'})
                    insert014="INSERT INTO ingest.schema_migrations(version,content_sha256,applied_at,code_commit) VALUES('014','"+adp.SQL14_SHA+"',CURRENT_TIMESTAMP,'local_rds_policy_e2e')"
                    actual['p0BodyP1Journal']=mutate(insert014,{'CATALOGUE'})
                    actual['p1BodyP0Journal']=mutate(adp.SQL14.read_text(),{'CATALOGUE'})
                    actual['nullNewClock']=mutate(adp.SQL14.read_text()+"\n"+insert014.replace('CURRENT_TIMESTAMP','NULL'),{'JOURNAL'})
                    rows=owner.execute('SELECT applied_at FROM ingest.schema_migrations ORDER BY version').fetchall();assert all(v[0] is not None and v[0].tzinfo is not None for v in rows)
                elif name=='bootstrap_and_populated':
                    actual={'seed':mutate("ALTER TABLE football.periods DISABLE TRIGGER USER;UPDATE football.periods SET label='synthetic_drift' WHERE code='full_match';ALTER TABLE football.periods ENABLE TRIGGER USER",{'BOOTSTRAP'})}
                    before=audit(second)
                    with second.transaction(force_rollback=True):
                        second.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ WRITE');second.execute("INSERT INTO football.players(display_name) VALUES('synthetic_rds_policy_unrelated')");foreign=audit(second);c=contract(DBS[1]);actual['populated']=refuses(lambda:adp.verify_state(adp.observe(second,c['rowCaps'],local_write=True),c),{'BUSINESS'});assert foreign==audit(second)
                    # Rollback removes the deliberately uncommitted fixture; sequence allocation is restored explicitly.
                    with second.transaction():
                        second.execute('SET TRANSACTION READ WRITE')
                        for schema,n,last,called in before['sequences']:second.execute('SELECT setval(%s::regclass,%s,%s)',(schema+'.'+n,last,called))
                    assert before==audit(second);actual['foreignUnchangedDuringRefusal']=True
                elif name=='sequence_state':
                    before=audit(owner);name='football.players_id_seq';value=owner.execute('SELECT last_value,is_called FROM football.players_id_seq').fetchone()
                    try:
                        with owner.transaction():owner.execute('SET TRANSACTION READ WRITE');owner.execute('SELECT setval(%s::regclass,%s,true)',(name,value[0]+1))
                        actual=refuses(lambda:preflight(),{'CATALOGUE','SEQUENCE'})
                    finally:
                        with owner.transaction():owner.execute('SET TRANSACTION READ WRITE');owner.execute('SELECT setval(%s::regclass,%s,%s)',(name,*value))
                    assert before==audit(owner)
                elif name=='leases_and_concurrency':
                    actual={}
                    for label,statement in [('migration','SELECT pg_advisory_xact_lock(20261104,2)'),('generation','SELECT pg_advisory_xact_lock(20261104,1)'),('serving','SELECT pg_advisory_xact_lock(97813003::bigint)')]:
                        pending=accept()
                        lock=connect(DBS[0])
                        with lock.transaction():lock.execute(statement);actual[label]=refuses(lambda:adp.owned_transition(marker,DBS[0],cpath(DBS[0]),sha(cpath(DBS[0])),pending,sha(pending)),{'LEASE'})
                        lock.close();lock=None
                    pending=accept()
                    lock=connect(DBS[0])
                    with lock.transaction():lock.execute('SET TRANSACTION READ WRITE');lock.execute('SELECT 1');actual['writer']=refuses(lambda:adp.owned_transition(marker,DBS[0],cpath(DBS[0]),sha(cpath(DBS[0])),pending,sha(pending)),{'CONCURRENCY'})
                    lock.close();lock=None
                elif name=='atomic_failures':
                    actual={}
                    for fault in ['after_function','after_journal']:
                        before=audit(owner);actual[fault]=refuses(lambda:apply(fault=fault),{'FAULT'});assert before==audit(owner)
                elif name=='adoption_clock_and_preservation':
                    before=audit(owner);result=apply();after=audit(owner);assert result['status']=='applied' and len(after['journal'])==3 and after['journal'][:-1]==before['journal'];assert after['native']==before['native'] and after['sequences']==before['sequences']
                    delta=[k for k in before['catalogue'] if before['catalogue'][k]!=after['catalogue'][k]];assert delta==['function:ingest.validate_generation(g bigint)'];assert result['newJournalClock']['appliedAt']==result['newJournalClock']['transactionStart'];assert result['protectedPropertiesPreserved'];actual={'result':result,'catalogueDelta':delta,'nativeRelationsPreserved':len(after['native']),'sequencesPreserved':len(after['sequences'])}
                elif name=='lost_acknowledgement':
                    try:apply(DBS[1],fault='after_commit')
                    except adp.OutcomeUnverified:pass
                    else:raise AssertionError('Lost acknowledgement must not claim rollback')
                    p=preflight(DBS[1]);assert p['policy']=='P1';before=audit(second);retry=apply(DBS[1]);assert retry['status']=='reused' and before==audit(second);actual={'freshPolicy':'P1','retry':retry,'outcomeOriginallyUnverified':True}
                elif name=='fresh_process_noop':
                    p=accept();before=audit(owner);flags=['--owned-transition','--marker',str(marker),'--database',DBS[0],'--contract',str(cpath(DBS[0])),'--expect-contract-sha256',sha(cpath(DBS[0])),'--acceptance',str(p),'--expect-acceptance-sha256',sha(p)];r=cli(flags,name);assert r.returncode==0;actual=json.loads(r.stdout);assert actual['status']=='reused' and before==audit(owner);actual['independent94RelationsAnd67SequencesUnchanged']=True
                elif name=='old_guards_stay_closed':
                    r=subprocess.run([sys.executable,str(SCRIPTS/'orion_pro_upgrade.py'),'--preflight-local','--database',DBS[0],'--marker',str(marker)],text=True,capture_output=True,timeout=30);assert r.returncode==2;(run/'old-local-guard.stdout.log').write_text(r.stdout);(run/'old-local-guard.stderr.log').write_text(r.stderr)
                    bulk=load(SCRIPTS/'orion_pro_bulk.py','frozen_old_bulk_rds_guard');b=bulk.Candidate(None,None,{},{});before=audit(owner)
                    try:
                        with snapshot(owner):b.baseline(owner,source=True)
                    except bulk.Refusal as e:assert e.code=='BASELINE'
                    else:raise AssertionError('Old bulk baseline accepted014')
                    assert before==audit(owner);actual={'oldLocalRefused':True,'oldBulkBaselineRefused':True}
                elif name=='bounded_queries_and_checkpoints':
                    c=contract();caps=dict(c['rowCaps']);caps['constraints']=1
                    with snapshot(owner):row=refuses(lambda:adp.observe(owner,caps),{'BOUND'})
                    budget=adp.Budget();budget.instruction_count=20;counter=refuses(lambda:budget.control(),{'BOUND'});budget=adp.Budget();budget.select_count=16;selects=refuses(lambda:budget.reserve(100),{'BOUND'});budget=adp.Budget();budget.reserved=4194304;size=refuses(lambda:budget.reserve(1),{'BOUND'})
                    with snapshot(owner):byte_limit=refuses(lambda:adp.observe(owner,c['rowCaps'],byte_caps={'constraints':128}),{'BOUND'})
                    actual={'nativeOverflow':row,'instructionOverflow':counter,'selectOverflow':selects,'globalByteOverflow':size,'serverByteOverflow':byte_limit,'lastSuccessfulInspection':preflight()['budget']}
                elif name=='protected_inputs_and_cleanup':
                    assert all(sha(ROOT/p)==h for p,h in pins.items());actual={'protectedInputCount':len(pins),'unchanged':True,'cleanupPendingFinally':True}
                report['cases'].append({'case':name,'status':'pass','elapsedSeconds':round(time.monotonic()-start,3),'actual':actual});print('PASS '+name,flush=True)
            except BaseException as error:
                report['cases'].append({'case':name,'status':'fail','elapsedSeconds':round(time.monotonic()-start,3),'errorType':type(error).__name__,'sqlstate':getattr(error,'sqlstate',None),'reason':str(error) if isinstance(error,AssertionError) else None});blocker='First unexpected failure: '+name;print('FAIL '+name+' '+type(error).__name__,flush=True)
    finally:
        for c in [lock,owner,second,setup]:
            if c is not None:
                try:c.close()
                except Exception:pass
        if watch:watch.close();save(run/'resources.json',watch.samples)
        try:report['cleanup']=pg.cleanup() if pg else {'pgStarted':False,'server_stopped':True,'owned_directory_removed':True}
        except Exception as e:report['cleanup']={'failed':True,'errorType':type(e).__name__}
        cleanup_proved=report['cleanup'].get('server_stopped') is True and report['cleanup'].get('owned_directory_removed') is True
        report['privateRootRemoved']=private is None or not private.exists()
        if private and private.exists() and cleanup_proved:
            try:shutil.rmtree(private);report['privateRootRemoved']=not private.exists()
            except Exception as error:report['privateCleanupErrorType']=type(error).__name__
        elif private and private.exists():report['privateRootRetainedForROOT']=str(private)
        report['originalCampaignEvidenceUnchanged']=parent_exact();report['protectedAfterExact']=all(sha(ROOT/p)==h for p,h in pins.items());report['counts']={s:sum(c['status']==s for c in report['cases']) for s in ['pass','fail','unverified']};report['status']='pass' if report['counts']=={'pass':20,'fail':0,'unverified':0} and report['protectedAfterExact'] and report['originalCampaignEvidenceUnchanged'] and report['privateRootRemoved'] and cleanup_proved and (not watch or watch.reason is None) else 'fail';report['finishedAt']=datetime.now(timezone.utc).isoformat()
        if pg:
            def finish(x):x.update(state='pass' if report['status']=='pass' else 'stop_for_ROOT',result=str(run/'result.json'),budgetStop=watch.reason if watch else None,elapsedSeconds=round(time.monotonic()-watch.start,3) if watch else None)
            ledger_update(ledger_path,finish)
        save(run/'result.json',report);print(json.dumps({'status':report['status'],'counts':report['counts'],'evidence':str(run/'result.json')}),flush=True)
    return 0 if report['status']=='pass' else 1
if __name__=='__main__':raise SystemExit(main())
