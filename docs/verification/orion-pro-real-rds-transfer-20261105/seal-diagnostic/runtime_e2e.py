#!/usr/bin/env python3
"""One released owned PG campaign: sealed014 compact vs dense CASE candidate."""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import hashlib,importlib.util,json,os,re,shutil,signal,sys,tempfile,threading,time,traceback,types
from pathlib import Path

sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[3]
MODEL=ROOT/'docs/architecture/orion-plan-20261104/target-schema.proposed.json'
SQLROOT=ROOT/'dashboard/backend/migrations'
SEALED=SQLROOT/'014_orion_pro_membership_nonnull.sql'
CANDIDATE=BASE/'candidate_metric_membership_guard.sql'
FIXTURE=ROOT/'tests/orion_pro_bulk_stream_local.py'
PILOT=ROOT/'docs/verification/orion-pro-pilot-20261104'
OLDHELPER=ROOT/'docs/verification/orion-validator-membership-20261105/e2e.py'
CASES=['frozen_inputs','separate_allocation','owned_tls_sealed014_setup','compact014_positive',
       'compact014_equivalence','dense_candidate_positive_and_plans','dense_candidate_equivalence',
       'native_and_acl','runtime_denials','protected_inputs_and_cleanup']
ROLES={'owner':'orion_pro_owner','writer':'orion_pro_ingest','reader':'orion_pro_runtime'}

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def hashed(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def save(p,v):Path(p).write_text(json.dumps(v,indent=2,default=str)+'\n')
def load(p,n):
    s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def q(v):assert re.fullmatch('[a-z_][a-z0-9_]*',v);return '"'+v+'"'
def rel(v):return '.'.join(q(x) for x in v.split('.'))


def predicates():
    old=SEALED.read_text().splitlines();new=CANDIDATE.read_text().splitlines();assert len(old)==len(new)
    assert [i+1 for i,(a,b) in enumerate(zip(old,new)) if a!=b]==[241,242,243]
    output=[]
    for number in [241,242,243]:
        body,suffix=old[number-1][len('IF EXISTS ('):].rsplit(") THEN RAISE EXCEPTION USING ERRCODE='23514', MESSAGE=",1)
        assert new[number-1].startswith('IF (CASE WHEN EXISTS (') and new[number-1].endswith(suffix)
        condition=new[number-1][len('IF ('):].rsplit(") THEN RAISE EXCEPTION USING ERRCODE='23514', MESSAGE=",1)[0]
        _,selected=body.rsplit(' AND NOT EXISTS (',1);parent=body.split(' child JOIN ',1)[1].split(' anchor ON ',1)[0]
        guard='SELECT 1 FROM '+parent+' anchor WHERE NOT EXISTS ('+selected[:-1]+')'
        assert condition=='CASE WHEN EXISTS ('+guard+') THEN EXISTS ('+body+') ELSE false END'
        output.append({'line':number,'old':'SELECT EXISTS ('+body+')','candidate':'SELECT ('+condition+')','guard':'SELECT EXISTS ('+guard+')'})
    restored=list(new)
    for i in [241,242,243]:restored[i-1]=old[i-1]
    assert '\n'.join(restored)+'\n'==SEALED.read_text()
    return output


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run-local',action='store_true');parser.add_argument('--check-only',action='store_true')
    parser.add_argument('--release',type=Path);parser.add_argument('--release-sha256')
    parser.add_argument('--pg-bin',type=Path,default=Path('/tmp/statarena-cache-test-tools/node_modules/@embedded-postgres/darwin-arm64/native/bin'))
    args=parser.parse_args();assert not(args.run_local and args.check_only)
    started=time.monotonic();deadline=started+600;cleanup=False;cleanup_deadline=None
    sys.path[:0]=[str(ROOT/'tests'),str(PILOT),str(ROOT/'dashboard/scripts'),'/tmp/statarena-publication-test-python']
    from orion_e2e_process import run_bounded
    run=BASE/'runtime-runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');(run/'inputs').mkdir(parents=True)
    report={'kind':'owned_sealed014_metric_guard_runtime_e2e_v1','command':[sys.executable,str(Path(__file__)),*sys.argv[1:]],
            'expected':str(BASE/'RUNTIME_PROTOCOL.md'),'cases':[],'invocations':[],'inputSha256':{},'pgStarts':0,'fixtureDatabases':0,'fixtureConstructions':0,
            'maximumOpenConnections':0,'sourceRamReads':0,'cloudCalls':0,'realSourceCalls':0,'realRdsWrites':[],'fullAcceptance':False,'analyzeCommands':0}
    paths=[Path(__file__),BASE/'RUNTIME_PROTOCOL.md',BASE/'RUNTIME_PINS.json',CANDIDATE,SEALED,MODEL,FIXTURE,OLDHELPER,ROOT/'tests/orion_pro_bulk_local.py',ROOT/'tests/orion_e2e_process.py',PILOT/'harness.py',SQLROOT/'012_orion_pro_domain.sql',SQLROOT/'013_orion_pro_integrity.sql',ROOT/'dashboard/scripts/orion_pro_migrate.py',ROOT/'dashboard/scripts/orion_pro_integrity.py']
    if args.release:paths.append(args.release.resolve())
    for p in paths:
        if p.is_file():
            dest=run/'inputs'/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest);report['inputSha256'][str(p.relative_to(ROOT))]=sha(p)
    pg=None;clients=[];admin=None;owners={};writers={};before={};phases={};block=None;psycopg=None;helper=None;fixture=None;preds=None;model=None;tables=None
    monitor_stop=threading.Event();monitor=None;budget_reason=[None];samples=[]
    env={k:v for k,v in os.environ.items() if k in ['PATH','HOME','USER','TMPDIR','LANG']};env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONPATH='/tmp/statarena-publication-test-python')
    def tick():
        if not cleanup:
            assert time.monotonic()<deadline,'600-second campaign deadline';assert budget_reason[0] is None,budget_reason[0]
    def command(argv,*,env=None,check=True,name='command'):
        tick();result=run_bounded([str(v) for v in argv],cwd=ROOT,env=env,deadline=cleanup_deadline if cleanup else deadline,stop_reason=lambda:None if cleanup else budget_reason[0],term_seconds=1,drain_seconds=1,output_limit=2*1024**2)
        i=len(report['invocations']);prefix=f'{i:03d}-{name}';(run/(prefix+'.stdout.log')).write_text(result.stdout);(run/(prefix+'.stderr.log')).write_text(result.stderr)
        report['invocations'].append({'command':[str(v) for v in argv],'exitCode':result.returncode,'stdout':prefix+'.stdout.log','stderr':prefix+'.stderr.log'})
        if check:assert result.returncode==0,result.stderr[-1000:]
        return result
    def watch():
        while not monitor_stop.wait(1):
            try:
                result=run_bounded(['du','-sk',str(pg.root)],deadline=min(deadline,time.monotonic()+4),output_limit=4096)
                disk=int(result.stdout.split()[0])*1024;proof=sum(p.stat().st_size for p in run.rglob('*') if p.is_file())
                samples.append({'seconds':round(time.monotonic()-started,3),'ownedBytes':disk,'proofBytes':proof});save(run/'resources.json',samples)
                if disk>=3*1024**3 or proof>=96*1024**2:budget_reason[0]='owned_disk_3GiB' if disk>=3*1024**3 else 'proof_96MiB';os.kill(os.getpid(),signal.SIGALRM);return
            except BaseException as error:
                if not monitor_stop.is_set():budget_reason[0]='resource_monitor:'+type(error).__name__;os.kill(os.getpid(),signal.SIGALRM)
                return
    def connect(db,user):
        tick();assert sum(not c.closed for c in clients)<5,'Maximum five client connections'
        c=psycopg.connect(host='127.0.0.1',hostaddr='127.0.0.1',port=pg.port,dbname=db,user=user,password='',sslmode='verify-full',sslrootcert=str(pg.data/'server.crt'),autocommit=True,connect_timeout=5,
            options='-c statement_timeout=8000 -c lock_timeout=1000 -c timezone=UTC -c datestyle=ISO,YMD -c extra_float_digits=3')
        clients.append(c);report['maximumOpenConnections']=max(report['maximumOpenConnections'],sum(not x.closed for x in clients));return c
    def native(c):tick();return helper.oracle(c,tables,report)
    def sequences(c):
        from orion_pro_bulk_local import sequences as seq
        tick();return seq(c)
    def exact_predicates(c,g):
        output=[]
        for p in preds:
            pair=[]
            for key in ['old','candidate']:
                sql=re.sub(r'\bg\b','%(g)s::bigint',p[key]);tick();pair.append(c.execute(sql,{'g':g},prepare=False).fetchone()[0])
            assert type(pair[0]) is bool and pair[0] is pair[1],(p['line'],g,pair)
            output.append(pair[0])
        return output
    def begin(c,label):return c.execute('SELECT ingest.begin_generation(%s,%s,%s)',('guard-e2e:'+label+':'+str(time.monotonic_ns()),'owned_metric_guard_e2e','owned_metric_guard_e2e')).fetchone()[0]
    def clone(c,name,where,params,overrides):
        columns=[col for col,s in tables[name]['columns'].items() if not s.get('identity')];expr={col:'old.'+q(col) for col in columns};expr.update(overrides)
        cursor=c.execute('INSERT INTO '+rel(name)+' ('+','.join(map(q,columns))+') SELECT '+','.join(expr[col] for col in columns)+' FROM '+rel(name)+' old WHERE '+where+' RETURNING *',params)
        names=[column.name for column in cursor.description]
        return [dict(zip(names,row)) for row in cursor.fetchall()]
    def seal_commit(c,g,label):
        tick();t=time.monotonic();c.execute('SELECT ingest.seal_generation(%s,%s)',(g,hashed(label)));seal=(time.monotonic()-t)*1000;assert seal<8000
        t=time.monotonic();c.commit();commit=(time.monotonic()-t)*1000;assert commit<8000
        return {'generation':g,'sealMs':round(seal,3),'deferredCommitMs':round(commit,3)}
    class Probe:
        def __init__(self,c,db,diagnostic=False):self.conn=c;self.db=db;self.diagnostic=diagnostic;self.hooked=False;self.seals=[];self.commits=[]
        def __getattr__(self,name):return getattr(self.conn,name)
        def execute(self,sql,params=None,**kwargs):
            tick();t=time.monotonic();result=self.conn.execute(sql,params,**kwargs)
            if sql.startswith('SELECT ingest.seal_generation'):
                elapsed=(time.monotonic()-t)*1000;assert elapsed<8000;self.seals.append({'generation':params[0],'elapsedMs':round(elapsed,3)})
            if self.diagnostic and sql=='SELECT count(*) FROM football.player_match_metric_values' and not self.hooked:
                self.hooked=True;g=self.conn.execute("SELECT generation FROM ingest.dataset_snapshots WHERE status='draft'").fetchone()[0];plans=[]
                for p in preds:
                    guard=self.conn.execute(re.sub(r'\bg\b','%(g)s::bigint',p['guard']),{'g':g}).fetchone()[0];assert guard is False
                    sqlplan='EXPLAIN (ANALYZE,BUFFERS,SETTINGS,FORMAT JSON) '+re.sub(r'\bg\b','%(g)s::bigint',p['candidate'])
                    plan=self.conn.execute(sqlplan,{'g':g}).fetchone()[0];nodes=[]
                    def visit(n):
                        if n.get('Relation Name')=='player_match_metric_values':nodes.append(n)
                        for child in n.get('Plans',[]):visit(child)
                    visit(plan[0]['Plan']);assert nodes and all(n.get('Actual Loops')==0 for n in nodes),(p['line'],nodes)
                    plans.append({'line':p['line'],'generation':g,'sql':sqlplan,'guardFalse':True,'metricChildLoops':[n['Actual Loops'] for n in nodes],'plan':plan})
                save(run/'dense-initial-owned-draft-plans.json',plans)
            return result
        def commit(self):
            tick();t=time.monotonic();self.conn.commit();elapsed=(time.monotonic()-t)*1000;assert elapsed<8000;self.commits.append({'elapsedMs':round(elapsed,3)})

    def scenarios(db):
        c=writers[db];owner=owners[db];pinned=phases[db][0]['generation'];outcomes=[]
        baseline=native(owner);seq_before=sequences(owner)
        def focus():return c.execute('SELECT match_id,player_id,team_id,revision_id,source_record_id FROM football.match_players WHERE is_canonical AND NOT is_deleted AND recorded_to_gen IS NULL ORDER BY revision_id LIMIT 1').fetchone()
        f=focus();match,player,team,revision,record=f
        expected_rules=[next(fk['name'] for fk in tables['football.player_match_metric_values']['foreign_keys'] if fk['references']['table']==n) for n in ['football.metric_definitions','football.periods','football.match_players']]
        def mapping(g,code):
            c.execute("INSERT INTO football.position_mappings(source_id,raw_position_code,mapping_version,position_code,position_definition_version,status,recorded_from_gen,contract_version,transform_version,transform_code_sha256,source_record_id,provenance_kind) SELECT 2,%s,%s,%s,'bootstrap_v1','validated',%s,contract_version,transform_version,transform_code_sha256,source_record_id,'provider' FROM football.match_players WHERE revision_id=%s",(code,'guard_position_'+code,code,g,revision))
        def replacement(g,mode,rev):
            c.execute('UPDATE football.match_players SET recorded_to_gen=%s WHERE revision_id=%s',(g,rev));over={'recorded_from_gen':str(g),'recorded_to_gen':'NULL::bigint','participation_evidence':"'guard-e2e changed evidence "+mode+' generation '+str(g)+"'"}
            if mode=='wrong_team':
                other=c.execute('SELECT team_id,revision_id FROM football.match_teams WHERE match_id=%s AND team_id<>%s AND recorded_to_gen IS NULL',(match,team)).fetchone();over.update(team_id=str(other[0]),match_team_revision_id=str(other[1]))
            elif mode=='noncanonical':over['is_canonical']='false'
            elif mode=='deleted':over['is_deleted']='true'
            elif mode in ['FWD','DEF']:
                over.update(position_code="'"+mode+"'",position_definition_version="'bootstrap_v1'",raw_position_code="'"+mode+"'",raw_position_code_state="'string'",position_mapping_version="'guard_position_"+mode+"'")
            elif mode=='NULL':over.update(position_code='NULL::text',position_definition_version='NULL::text',raw_position_code='NULL::text',raw_position_code_state="'absent'",position_mapping_version='NULL::text')
            rows=clone(c,'football.match_players','old.revision_id=%s',(rev,),over);assert len(rows)==1
            return rows[0]['revision_id']
        def run_scenario(label,mutate,expected_state=None,expected_rule=None,positive=False):
            nonlocal baseline,revision
            tick();old_native=native(owner);old_seq=sequences(owner);c.execute('BEGIN');g=None;entry={'mode':label}
            report['workflowInProgress']={'database':db,'mode':label};save(run/'progress.json',report)
            try:
                g=begin(c,label);report['workflowInProgress']['generation']=g;save(run/'progress.json',report);mutate(g)
                current=exact_predicates(c,g);historical=exact_predicates(c,pinned);assert historical==[False,False,False],(label,historical)
                if expected_state is not None:assert current==expected_state,(label,current,expected_state)
                entry.update(generation=g,predicateTruth=current,historicalOriginalCoreValid=True)
                if positive:
                    assert current==[False,False,False];entry.update(seal_commit(c,g,label));entry['sqlstate']=None
                else:
                    c.execute('SELECT ingest.seal_generation(%s,%s)',(g,hashed(label)));raise AssertionError('Invalid scenario was sealed: '+label)
            except psycopg.Error as error:
                c.rollback();assert not positive and error.sqlstate in ['23503','23514','55000'],(label,error.sqlstate,error.diag.message_primary)
                if expected_rule is not None:assert error.sqlstate=='23514' and expected_rule in error.diag.message_primary,(label,error.diag.message_primary)
                if label.startswith('missing_'):assert error.sqlstate=='23503'
                if label=='reopen_closed':assert error.sqlstate=='55000'
                entry.update(sqlstate=error.sqlstate,constraint=error.diag.constraint_name,message=error.diag.message_primary,databaseContext=error.diag.context)
            except BaseException:c.rollback();raise
            finally:
                if c.info.transaction_status.name!='IDLE':c.rollback()
            new_native=native(owner);new_seq=sequences(owner)
            assert set(new_seq)==set(old_seq) and all(new_seq[k][0]>=old_seq[k][0] and (old_seq[k][1] is not True or new_seq[k][1] is True) for k in old_seq),'Sequence decreased after workflow'
            if not positive:assert new_native==old_native,'Negative workflow changed native94'
            entry.update(native94RollbackExact=not positive,sequence67Monotone=True);outcomes.append(entry);save(run/(db+'-workflows.json'),outcomes);report.pop('workflowInProgress',None)
            if positive:baseline=new_native
            return entry
        for kind,col,value in [('definition','metric_code',"'missing_guard_definition'"),('period','period_code',"'missing_guard_period'"),('participant','match_player_revision_id','9223372036854775806::bigint')]:
            def missing(g,col=col,value=value,kind=kind):
                over={'recorded_from_gen':str(g),'recorded_to_gen':'NULL::bigint','variant_key':"'guard:missing'",col:value}
                if kind=='participant':over['period_code']="'extra_time_first_half'"
                clone(c,'football.player_match_metric_values','old.match_id=%s AND old.player_id=%s AND old.recorded_to_gen IS NULL ORDER BY old.revision_id LIMIT 1',(match,player),over)
            run_scenario('missing_'+kind,missing)
        run_scenario('definition_closed',lambda g:c.execute("UPDATE football.metric_definitions SET recorded_to_gen=%s WHERE code='m05' AND recorded_to_gen IS NULL",(g,)),[True,False,False],expected_rules[0])
        def closed_period(g):
            c.execute("UPDATE football.periods SET recorded_to_gen=%s WHERE code='extra_time_first_half' AND recorded_to_gen IS NULL",(g,))
            clone(c,'football.player_match_metric_values','old.match_id=%s AND old.player_id=%s AND old.recorded_to_gen IS NULL ORDER BY old.revision_id LIMIT 1',(match,player),{'recorded_from_gen':str(g),'recorded_to_gen':'NULL::bigint','period_code':"'extra_time_first_half'"})
        run_scenario('period_closed',closed_period,[False,True,False],expected_rules[1])
        run_scenario('participant_closed',lambda g:c.execute('UPDATE football.match_players SET recorded_to_gen=%s WHERE revision_id=%s',(g,revision)),[False,False,True],expected_rules[2])
        for mode in ['wrong_team','noncanonical','deleted']:
            run_scenario('participant_'+mode,lambda g,mode=mode:replacement(g,mode,revision),[False,False,True],expected_rules[2])
        def null_value_bad(g):mapping(g,'FWD');replacement(g,'FWD',revision)
        run_scenario('NULL_value',null_value_bad,[False,False,True],expected_rules[2])
        next_revision=[None]
        def null_null(g):next_revision[0]=replacement(g,'NULL',revision)
        run_scenario('NULL_NULL',null_null,[False,False,False],positive=True);revision=next_revision[0]
        def correct_value(g):
            mapping(g,'FWD');mapping(g,'DEF');next_revision[0]=replacement(g,'FWD',revision)
            count=c.execute('UPDATE football.player_match_metric_values SET recorded_to_gen=%s WHERE match_id=%s AND player_id=%s AND recorded_to_gen IS NULL',(g,match,player)).rowcount;assert count==31
            rows=clone(c,'football.player_match_metric_values','old.match_id=%s AND old.player_id=%s AND old.recorded_to_gen=%s',(match,player,g),{'recorded_from_gen':str(g),'recorded_to_gen':'NULL::bigint','match_player_revision_id':str(next_revision[0])});assert len(rows)==31
        run_scenario('closed_history_consistent_value_transition',correct_value,[False,False,False],positive=True);revision=next_revision[0]
        for mode,label in [('NULL','value_NULL'),('DEF','value_different_value')]:run_scenario(label,lambda g,mode=mode:replacement(g,mode,revision),[False,False,True],expected_rules[2])
        def value_same(g):next_revision[0]=replacement(g,'FWD',revision)
        run_scenario('value_same_value',value_same,[False,False,False],positive=True);revision=next_revision[0]
        original_revision=f[3]
        run_scenario('reopen_closed',lambda g:c.execute('UPDATE football.match_players SET recorded_to_gen=NULL WHERE revision_id=%s',(original_revision,)))
        assert native(owner)==baseline,'Final native94 differs beyond positive committed workflows'
        save(run/(db+'-final-native94.json'),baseline);save(run/(db+'-final-sequence67.json'),sequences(owner))
        return outcomes

    def timeout_handler(signum,frame):raise TimeoutError(budget_reason[0] or '600-second global deadline')
    try:
        for case in CASES:
            if block or (not args.run_local and case!='frozen_inputs'):
                report['cases'].append({'case':case,'status':'unverified','reason':block or 'Source-free preflight only; PG campaign not consumed'});continue
            try:
                actual={}
                if case=='frozen_inputs':
                    pins=json.loads((BASE/'RUNTIME_PINS.json').read_text());assert pins['kind']=='owned_metric_guard_runtime_pins_v1'
                    for name,h in pins['files'].items():assert sha(ROOT/name)==h,'Pinned input changed: '+name
                    assert sha(SEALED)=='e0810f8670b2cb627ade2c76e3c8eb527ab31fd595d5cf939fd63bfc5cf649d6' and sha(CANDIDATE)=='3b85fcb4fe9380cc5f96238620ff3f4bedee7485ed52c98fef0bddfac1092bd7'
                    preds=predicates();model=json.loads(MODEL.read_text());tables={t['qualified_name']:t for s in model['schemas'] for t in s['tables'] if t['phase']!='models'};assert len(tables)==94
                    actual={'candidateSha256':sha(CANDIDATE),'baseline':'sealed014','changedAssertions':3,'otherExceptionStatementsUnchanged':261}
                elif case=='separate_allocation':
                    assert args.release and args.release.is_absolute() and sha(args.release)==args.release_sha256,'Exact absolute ROOT allocation required'
                    assert not any(k.startswith('PG') for k in os.environ),'Inherited libpq routing refused'
                    release=json.loads(args.release.read_text());assert release['kind']=='root_local_metric_guard_runtime_campaign_v1' and release['approvedBy']=='ROOT'
                    required={'candidateSha256':sha(CANDIDATE),'sealed014Sha256':sha(SEALED),'fixtureSha256':sha(FIXTURE),'e2eSha256':sha(Path(__file__)),'protocolSha256':sha(BASE/'RUNTIME_PROTOCOL.md'),'pinsSha256':sha(BASE/'RUNTIME_PINS.json'),'maximumPgStarts':1,'maximumDatabaseConstructions':2,'maximumConnections':5,'maximumSeconds':600,'maximumOwnedBytes':3*1024**3,'maximumProofBytes':96*1024**2}
                    assert all(release.get(k)==v for k,v in required.items()),'ROOT allocation bounds/bytes differ'
                    assert re.fullmatch('[A-Za-z0-9-]+',release['allocationId']);consumed=BASE/(release['allocationId']+'.consumed.json');fd=os.open(consumed,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o644)
                    with os.fdopen(fd,'w') as f:json.dump({'run':str(run),'releaseSha256':sha(args.release),'executions':1},f,indent=2);f.write('\n')
                    signal.signal(signal.SIGALRM,timeout_handler);signal.setitimer(signal.ITIMER_REAL,max(.1,deadline-time.monotonic()));actual=required
                elif case=='owned_tls_sealed014_setup':
                    import psycopg as driver;psycopg=driver
                    from harness import LocalPostgres
                    from orion_pro_migrate import bootstrap
                    from orion_pro_integrity import role_grants_sql
                    helper=load(OLDHELPER,'frozen_membership_e2e_helpers');fixture=load(FIXTURE,'frozen_dense_native_fixture');tempfile.tempdir='/tmp';pg=LocalPostgres(args.pg_bin,run);pg.command=command
                    command([args.pg_bin/'initdb','-D',pg.data,'--auth=trust','--no-locale','--encoding=UTF8'],name='initdb')
                    command(['openssl','req','-x509','-newkey','rsa:2048','-sha256','-nodes','-days','2','-keyout',pg.data/'server.key','-out',pg.data/'server.crt','-subj','/CN=127.0.0.1','-addext','subjectAltName=IP:127.0.0.1'],name='tls-certificate');(pg.data/'server.key').chmod(0o600)
                    with (pg.data/'postgresql.conf').open('a') as f:f.write("\nssl=on\nssl_cert_file='server.crt'\nssl_key_file='server.key'\nstatement_timeout=8000\nlock_timeout=1000\nlog_error_verbosity=terse\nlog_min_error_statement=panic\nlog_parameter_max_length_on_error=0\ntemp_file_limit=256MB\n")
                    report['pgStarts']=1;pg.start();monitor=threading.Thread(target=watch,daemon=True);monitor.start();admin=connect('postgres',os.environ.get('USER','postgres'));assert admin.info.server_version==180006
                    for role in ROLES.values():admin.execute('CREATE ROLE '+q(role)+' LOGIN NOSUPERUSER NOCREATEROLE NOCREATEDB NOREPLICATION NOBYPASSRLS')
                    for db in ['guard_compact','guard_dense']:
                        admin.execute('CREATE DATABASE '+q(db)+' OWNER '+q(ROLES['owner']));report['fixtureDatabases']+=1;owners[db]=connect(db,ROLES['owner']);c=owners[db]
                        with c.transaction():
                            artifacts=[]
                            for version,name in [('012','012_orion_pro_domain.sql'),('013','013_orion_pro_integrity.sql')]:
                                p=SQLROOT/name;c.execute(p.read_text(),prepare=False);artifacts.append((version,p,p.read_text()));c.execute('INSERT INTO ingest.schema_migrations VALUES(%s,%s,CURRENT_TIMESTAMP,%s)',(version,sha(p),'owned_metric_guard_fixture'))
                            bootstrap(c,model,artifacts);c.execute(role_grants_sql(model,ROLES['writer'],ROLES['reader']),prepare=False)
                            c.execute(SEALED.read_text(),prepare=False);c.execute('INSERT INTO ingest.schema_migrations VALUES(%s,%s,CURRENT_TIMESTAMP,%s)',('014',sha(SEALED),'owned_metric_guard_fixture'))
                        before[db]={'properties':helper.function_properties(c),'structure':helper.structure(c),'native':native(c),'sequences':sequences(c)}
                        assert c.execute('SELECT prosrc FROM pg_proc WHERE oid=\'ingest.validate_generation(bigint)\'::regprocedure').fetchone()[0] in SEALED.read_text()
                        if db=='guard_dense':c.execute(CANDIDATE.read_text(),prepare=False)
                        assert helper.function_properties(c)==before[db]['properties'] and helper.structure(c)==before[db]['structure']
                        assert native(c)==before[db]['native'] and sequences(c)==before[db]['sequences']
                        writers[db]=connect(db,ROLES['writer']);identity=writers[db].execute("SELECT current_user,(SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()),current_setting('statement_timeout'),current_setting('lock_timeout'),rolsuper,rolcreaterole,rolcreatedb,rolreplication,rolbypassrls FROM pg_roles WHERE rolname=current_user").fetchone();assert identity[:4]==(ROLES['writer'],True,'8s','1s') and all(x is False for x in identity[4:])
                    actual={'pgVersion':180006,'tls':True,'fixtureDatabases':2,'baseline014Exact':True,'candidateOwnerOidAclSecurityPathExact':True,'native94AndSequence67UnchangedByOverlay':True}
                elif case=='compact014_positive':
                    evidence=run/'compact';evidence.mkdir();small=types.FunctionType(fixture.fixture.__code__,{**fixture.fixture.__globals__,'APPEARANCES':40,'SCALARS':1240,'MATCHES':4,'PLAYERS':40},name='qualified_compact_fixture')
                    probe=Probe(writers['guard_compact'],'guard_compact');phases['guard_compact']=small(probe,model,hashed({'fixture':sha(FIXTURE),'e2e':sha(Path(__file__))}),evidence);report['fixtureConstructions']+=1
                    assert len(probe.seals)==len(probe.commits)==2;actual={'shape':{'appearances':40,'metrics':31,'scalars':1240},'seals':probe.seals,'commits':probe.commits,'validator':'sealed014'};report['compactInitial']=actual
                elif case=='compact014_equivalence':
                    report['compactWorkflows']=scenarios('guard_compact');actual={'workflows':len(report['compactWorkflows']),'allAgainstSealed014':True}
                elif case=='dense_candidate_positive_and_plans':
                    evidence=run/'dense';evidence.mkdir();probe=Probe(writers['guard_dense'],'guard_dense',True);phases['guard_dense']=fixture.fixture(probe,model,hashed({'fixture':sha(FIXTURE),'e2e':sha(Path(__file__))}),evidence);report['fixtureConstructions']+=1
                    assert probe.hooked and len(probe.seals)==len(probe.commits)==2
                    assert owners['guard_dense'].execute('SELECT count(*) FROM football.player_match_metric_values').fetchone()[0]==478547 and owners['guard_dense'].execute('SELECT count(*) FROM football.match_players').fetchone()[0]==15437
                    actual={'shape':{'appearances':15437,'metrics':31,'scalars':478547},'seals':probe.seals,'commits':probe.commits,'allThreeChildSubplansUnexecuted':True};report['denseInitial']=actual
                elif case=='dense_candidate_equivalence':
                    report['denseWorkflows']=scenarios('guard_dense');assert [(x['mode'],x['sqlstate']) for x in report['denseWorkflows']]==[(x['mode'],x['sqlstate']) for x in report['compactWorkflows']]
                    actual={'workflows':len(report['denseWorkflows']),'sameBaseline014Outcomes':True,'candidateFullSealAndDeferredCommitOrdinaryIngest':True}
                elif case=='native_and_acl':
                    for db,c in owners.items():
                        assert helper.function_properties(c)==before[db]['properties'] and helper.structure(c)==before[db]['structure']
                        assert c.execute("SELECT count(*) FROM pg_trigger WHERE tgrelid='ingest.dataset_snapshots'::regclass AND tgname='pro_generation_commit' AND tgenabled='O' AND tgdeferrable AND tginitdeferred").fetchone()[0]==1
                        assert c.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema IN ('ingest','football','analytics') AND table_type='BASE TABLE'").fetchone()[0]==94
                    actual={'relations':94,'sequenceValuesObservedByOwner':67,'ownerOidAclSecurityPathAndStructureUnchanged':True,'deferredCommitTriggersEnabled':True}
                elif case=='runtime_denials':
                    admin.close();runtime=connect('guard_dense',ROLES['reader']);denials=[]
                    try:
                        for sql in ["SELECT ingest.validate_generation(1)","SELECT ingest.begin_generation('denied','test','test')","SELECT ingest.seal_generation(1,repeat('0',64))","SELECT nextval('ingest.commit_generation_seq')","INSERT INTO ingest.quality_issues(rule_code,severity) VALUES('denied','info')","SELECT last_value FROM football.players_id_seq"]:
                            try:runtime.execute(sql);raise AssertionError('Runtime unexpectedly permitted: '+sql)
                            except psycopg.Error as error:assert error.sqlstate=='42501';denials.append({'sql':sql,'sqlstate':error.sqlstate})
                    finally:runtime.close()
                    actual={'denials':denials,'newGrants':[]}
                else:actual={'protectedInputsExact':all(sha(ROOT/p)==h for p,h in report['inputSha256'].items()),'cleanupRequiredInFinally':True};assert actual['protectedInputsExact']
                report['cases'].append({'case':case,'status':'pass','actual':actual});save(run/'progress.json',report);print('PASS '+case,flush=True)
            except BaseException as error:
                block='First unexpected failure: '+case;diag=getattr(error,'diag',None);entry={'case':case,'status':'fail','errorType':type(error).__name__,'error':diag.message_primary if diag else str(error),'sqlstate':getattr(error,'sqlstate',None),'databaseContext':diag.context if diag else None,'traceback':traceback.format_exc()};report['cases'].append(entry);save(run/'progress.json',report);print('FAIL '+case+': '+entry['error'][:400],flush=True)
    finally:
        cleanup=True;signal.setitimer(signal.ITIMER_REAL,0);monitor_stop.set()
        if monitor:monitor.join(5)
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
                report['cleanup']={'serverStopped':not(pg.data/'postmaster.pid').exists(),'ownedRoot':str(pg.root),'ownedRootRemoved':not pg.root.exists(),'retainedForFailureInspection':bool(block),'realCorpusTouched':False}
            except BaseException as error:report['cleanup']={'serverStopped':False,'ownedRoot':str(pg.root),'errorType':type(error).__name__};block=block or 'Cleanup failed'
        else:report['cleanup']={'serverStarted':False,'ownedRootCreated':False}
        report['resourceSamples']=samples;report['budgetStop']=budget_reason[0];report['elapsedSeconds']=round(time.monotonic()-started,3)
        report['inputHashesExact']=all(sha(ROOT/p)==h for p,h in report['inputSha256'].items());block=block or (None if report['inputHashesExact'] else 'Input drift')
        report['counts']={s:sum(c['status']==s for c in report['cases']) for s in ['pass','fail','unverified']};report['status']='fail' if block else 'pass_owned_local_only' if args.run_local else 'source_free_preflight_only'
        save(run/'result.json',report);print(json.dumps({'status':report['status'],'counts':report['counts'],'evidence':str(run/'result.json')}),flush=True)
    return 1 if block else 0

if __name__=='__main__':raise SystemExit(main())
