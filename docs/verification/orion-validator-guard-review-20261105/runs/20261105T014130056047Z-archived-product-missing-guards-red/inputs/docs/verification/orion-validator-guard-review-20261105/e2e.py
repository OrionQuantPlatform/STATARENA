#!/usr/bin/env python3
"""Pre-fix CLI/native PG E2E for local route and catalogue guards only."""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import hashlib
import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import _thread
import time
import traceback

sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[2]
SCRIPTS=ROOT/'dashboard/scripts'
OLD=ROOT/'docs/verification/orion-validator-adoption-20261105'
MODEL=ROOT/'docs/architecture/orion-plan-20261104/target-schema.proposed.json'
SQL=[ROOT/'dashboard/backend/migrations'/n for n in ['012_orion_pro_domain.sql','013_orion_pro_integrity.sql']]
NEW_SQL=ROOT/'dashboard/backend/migrations/014_orion_pro_membership_nonnull.sql'
MODULES=[SCRIPTS/'orion_pro_policy.py',SCRIPTS/'orion_pro_upgrade.py']
ARCHIVE='85033e90631b82d1257298ce54c72071fd091a61'
OLD_MANIFEST_SHA='d4e98446837e3ee01c8b081e1883867e6b80241acda157dac69d1e72e95601a3'
OLD_CODE=['288139f30d6ba003f5befbb4d7a1a71ef6b0a9d2ada8b42641a1158c9ce32d63','1b1eade5be41dadb361267fff457b72083caab8d2e7f21543f1ef9e2c541fd14']
CASES=['archive_checkpoint_bound','owned_setup_ordinary','policy_oracle_bound','offline_cli_poisoned_hostaddr',
       'cli_explicit_route_pin','complete_native_catalogue','view_definition_drift','schema_create_drift',
       'schema_default_acl_drift','global_default_acl_drift','runtime_role_flag_drift','runtime_membership_drift',
       'positive_apply_noop_compensation','archive_and_cleanup']
KNOWN_RED=set(CASES[4:12])
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False,default=str)+'\n')
def hashed(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()

AUDIT_SQL="""SELECT kind,key,value FROM (
 SELECT 'schema' kind,nspname key,ROW(pg_get_userbyid(nspowner),nspacl::text)::text value FROM pg_namespace WHERE nspname IN ('ingest','football','analytics')
 UNION ALL SELECT 'view',n.nspname||'.'||c.relname,ROW(pg_get_viewdef(c.oid),pg_get_userbyid(c.relowner),c.relacl::text,c.reloptions)::text FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname IN ('ingest','football','analytics') AND c.relkind IN ('v','m')
 UNION ALL SELECT 'role',rolname,ROW(rolsuper,rolinherit,rolcreaterole,rolcreatedb,rolcanlogin,rolreplication,rolconnlimit,rolvaliduntil,rolbypassrls,rolconfig)::text FROM pg_roles WHERE rolname IN ('policy_owner','policy_ingest','policy_runtime')
 UNION ALL SELECT 'membership',r.rolname||'->'||m.rolname,ROW(g.rolname,a.admin_option,a.inherit_option,a.set_option)::text FROM pg_auth_members a JOIN pg_roles r ON r.oid=a.roleid JOIN pg_roles m ON m.oid=a.member JOIN pg_roles g ON g.oid=a.grantor WHERE r.rolname IN ('policy_owner','policy_ingest','policy_runtime') OR m.rolname IN ('policy_owner','policy_ingest','policy_runtime')
 UNION ALL SELECT 'default_acl',r.rolname||'.'||coalesce(n.nspname,'GLOBAL')||'.'||d.defaclobjtype,d.defaclacl::text FROM pg_default_acl d JOIN pg_roles r ON r.oid=d.defaclrole LEFT JOIN pg_namespace n ON n.oid=d.defaclnamespace WHERE (d.defaclnamespace=0 OR n.nspname IN ('ingest','football','analytics')) AND r.rolname IN ('policy_owner','policy_ingest','policy_runtime')
) audit ORDER BY kind,key"""

def archive_check():
    p=OLD/'final-hashes.json';assert sha(p)==OLD_MANIFEST_SHA
    data=json.loads(p.read_text());assert data['artifactCount']==253
    checked=[]
    for rel,item in data['files'].items():
        got=subprocess.run(['git','cat-file','blob',ARCHIVE+':'+rel],cwd=ROOT,capture_output=True,timeout=15)
        assert got.returncode==0 and hashlib.sha256(got.stdout).hexdigest()==item['sha256'],'Archived checkpoint blob differs: '+rel
        checked.append({'path':rel,'sha256':item['sha256']})
    for rel,item in data['files'].items():
        if rel.startswith(str(OLD.relative_to(ROOT))+'/'):assert sha(ROOT/rel)==item['sha256'],'Frozen proof bytes differ'
    assert all(sha(ROOT/rel)==h for rel,h in data['protectedInputs'].items())
    return {'archiveCommit':ARCHIVE,'oldManifestSha256':OLD_MANIFEST_SHA,'archivedEntries':len(checked),'entries':checked}

class Budget:
    def __init__(self,pg,run,red):
        self.pg,self.run=pg,run;self.start=time.monotonic();self.stop=threading.Event();self.samples=[];self.reason=None
        self.path=BASE/'campaign.json';self.ledger=json.loads(self.path.read_text()) if self.path.exists() else {'maximumPgStarts':2,'runs':[]}
        assert len(self.ledger['runs'])<2,'Review RED+green PG budget exhausted'
        assert (len(self.ledger['runs'])==0 and red) or (len(self.ledger['runs'])==1 and not red and self.ledger['runs'][0]['status']=='expected_guard_red'),'RED must precede green; unexpected stop needs ROOT'
        self.entry={'mode':'expected-red' if red else 'green','startedAt':datetime.now(timezone.utc).isoformat()};self.ledger['runs'].append(self.entry);save(self.path,self.ledger)
        self.thread=threading.Thread(target=self.watch,daemon=True);self.thread.start()
    def watch(self):
        while not self.stop.wait(1):
            disk=int(subprocess.check_output(['du','-sk',str(self.pg.root)],text=True).split()[0])*1024;proof=sum(p.stat().st_size for p in BASE.rglob('*') if p.is_file());elapsed=time.monotonic()-self.start
            self.samples.append({'seconds':round(elapsed,3),'ownedBytes':disk,'proofBytes':proof})
            if disk>=7*1024**3 or proof>=64*1024**2 or elapsed>=600:self.reason='resource_limit';_thread.interrupt_main();return
    def close(self,status):
        self.stop.set();self.thread.join(3);self.entry.update(status=status,elapsedSeconds=round(time.monotonic()-self.start,3),budgetStop=self.reason);save(self.path,self.ledger);save(self.run/'resources.json',self.samples);return self.entry

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--label',default='guard-review');ap.add_argument('--expect-red',action='store_true');ap.add_argument('--archive-gate-only',action='store_true');ap.add_argument('--pg-bin',type=Path,default=Path('/tmp/statarena-cache-test-tools/node_modules/@embedded-postgres/darwin-arm64/native/bin'));args=ap.parse_args()
    assert all(c.isalnum() or c=='-' for c in args.label)
    # Test-process isolation only: no inherited libpq route/secret is used by setup.
    for key in tuple(os.environ):
        if key.startswith('PG'):os.environ.pop(key)
    os.environ['PGHOSTADDR']='127.0.0.1'
    sys.path[:0]=[str(SCRIPTS),str(ROOT/'docs/verification/orion-pro-pilot-20261104'),'/tmp/statarena-publication-test-python']
    run=BASE/'runs'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-'+args.label);(run/'inputs').mkdir(parents=True)
    report={'kind':'local_validator_guard_review_e2e','startedAt':datetime.now(timezone.utc).isoformat(),'command':['python3',str(Path(__file__).relative_to(ROOT)),*sys.argv[1:]],'expectRed':args.expect_red,'expected':'PROTOCOL.md','cases':[],'remoteActions':[],'sourceReads':0,'denseRuns':0,'fullAcceptance':False,'archiveCommit':ARCHIVE,'sourceSha256':{}}
    paths=[Path(__file__),BASE/'PROTOCOL.md',BASE/'DRIVER_TRIPWIRE.py',*MODULES,MODEL,*SQL,NEW_SQL,OLD/'final-hashes.json',OLD/'ROOT_ARCHIVE_REVIEW.json',SCRIPTS/'orion_pro_migrate.py',SCRIPTS/'orion_pro_integrity.py',SCRIPTS/'orion_pro_schema.py']
    for p in paths:
        destination=run/'inputs'/p.relative_to(ROOT);destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,destination);report['sourceSha256'][str(p.relative_to(ROOT))]=sha(p)
    pg=budget=admin=target=other=None;blocker=None;policy=upgrade=None;marker=None
    def audit():return [list(row) for row in target.execute(AUDIT_SQL)]
    def acceptance(pid):
        loaded=policy.load_policy(pid);state=upgrade.run_local(marker,'policy_empty','policy_owner','preflight',pid,loaded['manifestSha256']);path=run/('acceptance-'+str(len(list(run.glob('acceptance-*.json'))))+'.json')
        body={'kind':'orion_pro_policy_local_acceptance_v1','scope':loaded['manifest']['scope'],'policyId':pid,'manifestSha256':loaded['manifestSha256'],'helperSha256':sha(MODULES[0]),'runnerSha256':sha(MODULES[1]),'database':'policy_empty','beforeStateSha256':state['stateSha256'],'releaseCommit':'local-guard-review-e2e','localOnly':True};save(path,body);return loaded,path,sha(path)
    def preflight():
        loaded=policy.load_policy(policy.P1);return upgrade.run_local(marker,'policy_empty','policy_owner','preflight',policy.P1,loaded['manifestSha256'])
    def cli(local=False):
        trip=run/'tripwire';trip.mkdir(exist_ok=True);shutil.copy2(BASE/'DRIVER_TRIPWIRE.py',trip/'sitecustomize.py');receipt=run/('driver-route-local.json' if local else 'driver-route-offline.json')
        env={k:v for k,v in os.environ.items() if k in ['PATH','HOME','USER','TMPDIR','LANG']};env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(trip)+':/tmp/statarena-publication-test-python',PGHOSTADDR='203.0.113.77',ORION_ROUTE_TRIPWIRE_RESULT=str(receipt))
        cmd=['python3',str(MODULES[1])]
        if local:
            loaded=policy.load_policy(policy.P1);cmd+=['--preflight-local','--marker',str(marker),'--database','policy_empty','--expect-manifest-sha256',loaded['manifestSha256']]
        got=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True,timeout=30);data=json.loads(got.stdout);trace=json.loads(receipt.read_text()) if receipt.exists() else None
        save(run/('cli-local.json' if local else 'cli-offline.json'),{'command':cmd,'exitCode':got.returncode,'stdout':data,'tripwire':trace});return got.returncode,data,trace
    def drift(change,restore,conn):
        before=audit();conn.execute(change,prepare=False);observed=None
        try:
            try:preflight()
            except policy.Refusal as e:assert e.code=='CATALOGUE',e.code;observed={'refused':True,'code':e.code}
            else:observed={'refused':False}
        finally:conn.execute(restore,prepare=False)
        assert audit()==before,'Native security/view restoration differs'
        assert observed['refused'],'MISSING_GUARD_ACCEPTED_DRIFT'
        return {'outcome':observed,'baselineAuditSha256':hashed(before),'restoredAuditSha256':hashed(audit())}
    def install(conn):
        from orion_pro_migrate import bootstrap
        from orion_pro_integrity import role_grants_sql
        model=json.loads(MODEL.read_text())
        with conn.transaction():
            artifacts=[(v,p,p.read_text()) for v,p in zip(['012','013'],SQL)]
            for v,p,body in artifacts:conn.execute(body,prepare=False);conn.execute('INSERT INTO ingest.schema_migrations(version,content_sha256,applied_at,code_commit) VALUES(%s,%s,CURRENT_TIMESTAMP,%s)',(v,sha(p),'local-guard-review-fixture'))
            bootstrap(conn,model,artifacts);conn.execute(role_grants_sql(model,'policy_ingest','policy_runtime'),prepare=False)
    try:
        for name in CASES:
            if blocker or (args.archive_gate_only and name!='archive_checkpoint_bound'):
                report['cases'].append({'case':name,'status':'unverified','reason':blocker or 'Archive-only, no PG'});continue
            started=time.monotonic()
            try:
                actual={}
                if name=='archive_checkpoint_bound':
                    auth=json.loads((BASE/'archive-authorization.json').read_text());assert auth['archiveCommit']==ARCHIVE and auth['oldManifestSha256']==OLD_MANIFEST_SHA
                    actual=archive_check();save(run/'archive-checked.json',actual)
                    if args.expect_red:assert [sha(p) for p in MODULES]==OLD_CODE,'Functional RED must use unchanged archived product'
                elif name=='owned_setup_ordinary':
                    import psycopg
                    from harness import LocalPostgres
                    policy=importlib.import_module('orion_pro_policy');upgrade=importlib.import_module('orion_pro_upgrade');pg=LocalPostgres(args.pg_bin,run);budget=Budget(pg,run,args.expect_red)
                    pg.command([pg.binaries/'initdb','-D',pg.data,'--auth=trust','--no-locale','--encoding=UTF8'],name='initdb')
                    with (pg.data/'postgresql.conf').open('a') as f:f.write('\nstatement_timeout=8000\nlock_timeout=1000\ntemp_file_limit=512MB\nlog_error_verbosity=terse\nlog_min_error_statement=panic\nlog_parameter_max_length_on_error=0\n')
                    pg.start();owner=os.environ.get('USER','postgres');admin=psycopg.connect(host='127.0.0.1',hostaddr='127.0.0.1',port=pg.port,dbname='postgres',user=owner,autocommit=True)
                    assert admin.info.server_version==180006
                    for role in ['policy_owner','policy_ingest','policy_runtime']:admin.execute('CREATE ROLE '+role+' LOGIN NOSUPERUSER NOCREATEROLE NOCREATEDB NOREPLICATION NOBYPASSRLS')
                    for database in ['policy_empty','policy_facts']:admin.execute('CREATE DATABASE '+database+' OWNER policy_owner')
                    target=psycopg.connect(host='127.0.0.1',hostaddr='127.0.0.1',port=pg.port,dbname='policy_empty',user='policy_owner',autocommit=True);other=psycopg.connect(host='127.0.0.1',hostaddr='127.0.0.1',port=pg.port,dbname='policy_facts',user='policy_owner',autocommit=True)
                    install(target);install(other);marker=pg.root/'policy-marker.json';save(marker,{'kind':'orion_owned_policy_pg18_v1','ownedRoot':str(pg.root),'port':pg.port,'serverStartedAt':admin.execute('SELECT pg_postmaster_start_time()::text').fetchone()[0]});marker.chmod(0o600)
                    actual={'serverVersion':admin.info.server_version,'ordinaryRoles':list(admin.execute("SELECT rolname,rolsuper,rolcreaterole,rolcreatedb,rolreplication,rolbypassrls FROM pg_roles WHERE rolname IN ('policy_owner','policy_ingest','policy_runtime') ORDER BY 1"))};assert not any(any(x[1:]) for x in actual['ordinaryRoles'])
                elif name=='policy_oracle_bound':
                    if not args.expect_red:
                        p0=policy.catalogue(target)
                        try:
                            with target.transaction():target.execute(NEW_SQL.read_text(),prepare=False);p1=policy.catalogue(target);raise RuntimeError('rollback_oracle_only')
                        except RuntimeError as e:assert str(e)=='rollback_oracle_only'
                        artifacts=policy.build_artifacts(p0,p1)
                        for p,body in artifacts.items():
                            assert p.is_relative_to(ROOT/'dashboard/backend/schema-policies/orion-pro/guard-review-v2') or p.is_relative_to(BASE/'local-compensation'),'Old policy path must remain immutable'
                            p.parent.mkdir(parents=True,exist_ok=True);p.write_text(body);copy=run/'prepared-artifacts'/p.relative_to(ROOT);copy.parent.mkdir(parents=True,exist_ok=True);copy.write_text(body)
                        actual['preparedArtifacts']={str(p.relative_to(ROOT)):sha(p) for p in artifacts}
                    loaded=policy.load_policy(policy.P1);assert preflight()['currentPolicy']==policy.P0
                    assert upgrade.run_local(marker,'policy_facts','policy_owner','preflight',policy.P1,loaded['manifestSha256'])['currentPolicy']==policy.P0
                    baseline=audit();save(run/'baseline-native-security-views.json',baseline);actual.update(manifestSha256=loaded['manifestSha256'],baselineAuditSha256=hashed(baseline),nativeViewCount=sum(x[0]=='view' for x in baseline));assert actual['nativeViewCount']==46
                elif name=='offline_cli_poisoned_hostaddr':
                    code,data,trace=cli();assert code==0 and data['status']=='planned' and data['connections']==0 and trace is None;actual={'offlinePlan':data,'driverCalls':0}
                elif name=='cli_explicit_route_pin':
                    code,data,trace=cli(True);save(run/'route-proof.json',{'exitCode':code,'stdout':data,'tripwire':trace});assert trace is not None and trace['actualNonlocalConnections']==0
                    assert code==0 and trace['explicitHostaddr']=='127.0.0.1' and trace['effectiveHostaddr']=='127.0.0.1' and not trace['nonlocalPrevented'],'MISSING_EXPLICIT_HOSTADDR_PIN'
                    actual={'tripwire':trace,'currentPolicy':data['currentPolicy']}
                elif name=='complete_native_catalogue':
                    cat=policy.catalogue(target);counts={k:sum(x[0]==k for x in cat['rows']) for k in ['schema','view','role','membership','default_acl']}
                    assert counts['schema']==3 and counts['view']==46 and counts['role']==3,'MISSING_NATIVE_CATALOGUE_CATEGORIES';actual={'categories':counts,'catalogueSha256':cat['sha256']}
                elif name=='view_definition_drift':
                    definition=target.execute("SELECT pg_get_viewdef('football.matches_current'::regclass)").fetchone()[0].strip().removesuffix(';');actual=drift('CREATE OR REPLACE VIEW football.matches_current AS SELECT * FROM ('+definition+') x WHERE false','CREATE OR REPLACE VIEW football.matches_current AS '+definition,target)
                elif name=='schema_create_drift':actual=drift('GRANT CREATE ON SCHEMA football TO policy_runtime','REVOKE CREATE ON SCHEMA football FROM policy_runtime',target)
                elif name=='schema_default_acl_drift':actual=drift('ALTER DEFAULT PRIVILEGES FOR ROLE policy_owner IN SCHEMA football GRANT INSERT ON TABLES TO policy_runtime','ALTER DEFAULT PRIVILEGES FOR ROLE policy_owner IN SCHEMA football REVOKE INSERT ON TABLES FROM policy_runtime',target)
                elif name=='global_default_acl_drift':actual=drift('ALTER DEFAULT PRIVILEGES FOR ROLE policy_owner GRANT EXECUTE ON FUNCTIONS TO policy_runtime','ALTER DEFAULT PRIVILEGES FOR ROLE policy_owner REVOKE EXECUTE ON FUNCTIONS FROM policy_runtime',target)
                elif name=='runtime_role_flag_drift':actual=drift('ALTER ROLE policy_runtime BYPASSRLS','ALTER ROLE policy_runtime NOBYPASSRLS',admin)
                elif name=='runtime_membership_drift':actual=drift('GRANT policy_ingest TO policy_runtime','REVOKE policy_ingest FROM policy_runtime',admin)
                elif name=='positive_apply_noop_compensation':
                    native=policy.native_state(target);security=audit();props=policy.function_properties(target);oldjournal=list(target.execute('SELECT version,content_sha256,applied_at::text,code_commit FROM ingest.schema_migrations ORDER BY version'))
                    loaded,path,h=acceptance(policy.P1);result=upgrade.run_local(marker,'policy_empty','policy_owner','apply',policy.P1,loaded['manifestSha256'],path,h);assert result['status']=='applied'
                    newjournal=list(target.execute('SELECT version,content_sha256,applied_at::text,code_commit FROM ingest.schema_migrations ORDER BY version'));assert oldjournal==newjournal[:-1] and newjournal[-1][2] is not None
                    assert security==audit() and native==policy.native_state(target) and props==policy.function_properties(target)
                    loaded,path,h=acceptance(policy.P1);noop=upgrade.run_local(marker,'policy_empty','policy_owner','apply',policy.P1,loaded['manifestSha256'],path,h);assert noop['status']=='reused' and newjournal==list(target.execute('SELECT version,content_sha256,applied_at::text,code_commit FROM ingest.schema_migrations ORDER BY version'))
                    loaded,path,h=acceptance(policy.P2);restore=upgrade.run_local(marker,'policy_empty','policy_owner','apply',policy.P2,loaded['manifestSha256'],path,h);assert restore['status']=='applied' and security==audit() and native==policy.native_state(target)
                    final=list(target.execute('SELECT version,content_sha256,applied_at::text,code_commit FROM ingest.schema_migrations ORDER BY version'));assert final[:-1]==newjournal and final[-1][0]=='099' and final[-1][2] is not None
                    actual={'apply':result,'noop':noop,'localCompensation':restore,'viewSecurityUnchanged':True,'allOldJournalRowsExact':True}
                elif name=='archive_and_cleanup':
                    actual=archive_check();assert all(sha(ROOT/p)==h for p,h in report['sourceSha256'].items());assert sha(NEW_SQL)=='e0810f8670b2cb627ade2c76e3c8eb527ab31fd595d5cf939fd63bfc5cf649d6';actual['currentProductSha256']={str(p.relative_to(ROOT)):sha(p) for p in MODULES}
                report['cases'].append({'case':name,'status':'pass','elapsedMs':round((time.monotonic()-started)*1000,3),'actual':actual})
            except BaseException as e:
                expected=args.expect_red and name in KNOWN_RED and isinstance(e,AssertionError) and str(e) in {'MISSING_EXPLICIT_HOSTADDR_PIN','MISSING_NATIVE_CATALOGUE_CATEGORIES','MISSING_GUARD_ACCEPTED_DRIFT'}
                report['cases'].append({'case':name,'status':'fail','expectedPreFixGap':expected,'error':{'type':type(e).__name__,'sqlstate':getattr(e,'sqlstate',None),'message':str(e) if isinstance(e,AssertionError) else 'Unexpected owned-local failure; inspect traceback'}})
                (run/('trace-'+name+'.txt')).write_text(traceback.format_exc())
                if not expected:blocker=name
    finally:
        for conn in [other,target,admin]:
            if conn is not None:conn.close()
        expected_red=args.expect_red and not blocker and all(any(c['case']==n and c['status']=='fail' and c.get('expectedPreFixGap') for c in report['cases']) for n in KNOWN_RED)
        status='expected_guard_red' if expected_red else 'pass' if not blocker and not args.expect_red and not args.archive_gate_only and all(c['status']=='pass' for c in report['cases']) else 'stopped_for_ROOT_brief'
        if budget:report['resourceBudget']=budget.close(status)
        report['cleanup']=pg.cleanup() if pg else {'server_stopped':True,'owned_directory_removed':True,'pgStarted':False};report['status']=status;report['finishedAt']=datetime.now(timezone.utc).isoformat();report['counts']={s:sum(c['status']==s for c in report['cases']) for s in ['pass','fail','unverified']};save(run/'result.json',report)
        print(json.dumps({'status':status,'counts':report['counts'],'receipt':str((run/'result.json').relative_to(ROOT)),'sha256':sha(run/'result.json'),'remoteActions':[]}))
    return 0 if status=='pass' else 1

if __name__=='__main__':raise SystemExit(main())
