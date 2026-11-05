#!/usr/bin/env python3
"""Before-code owned 017/018 matched cold COPY and native validation workflow."""
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
import signal
import sys
import tempfile
import threading
import time
import traceback
import types

sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[4]
PILOT=ROOT/'docs/verification/orion-pro-pilot-20261104'
SQLROOT=ROOT/'dashboard/backend/migrations'
SQL=[next(SQLROOT.glob(v+'_orion_pro_*.sql')) for v in ('012','013','014','015','016','017')]
PINS=BASE/'PINS.json'
PINS_SHA='03cf000c7340c6e93d60dc98debff018f627d99089ec2409d6a17651fa61b194'
TARGET=BASE/'TARGET017_PROVENANCE.json'
TARGET_SHA='ec5ebaf93e2875d693d0ff8fd20b341bc689f2b1299a251ebf912fc880971689'
PLAN=BASE/'PROPOSAL.md'
CANDIDATE=BASE/'candidate_018.sql'
LEGACY=BASE.parent/'e2e_v2.py'
LEGACY_SHA='ac030d369b67d327c276cc7dbe9176372d5c3bac29609ffc490c262fa5778204'
MODEL=ROOT/'docs/architecture/orion-native-details-107-20261105/target-schema.approved-107-core.json'
ROLES={'owner':'statarena_admin','writer':'statarena_ingest','reader':'statarena_runtime'}
CLOSED='football_player_match_metric_values_sv_closed_probe_idx'
CLAUSE_START='-- 018 metric history fast path\n'
CLAUSE_END='-- 018 end metric history fast path\n'
CASES=('exact_inputs_and_workflow','candidate_available','separate_allocation','owned_tls_cluster',
       'baseline017_two_aborts_and_native_copy','candidate018_index_build_on_bloat','candidate018_native_copy_and_matched_readback',
       'closed_history_full_native_commit','owned_index_drift_and_exact_errors','cleanup_and_unchanged_inputs')

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

old=load(LEGACY,'frozen_owned_metric_copy_tools')
sha,save,require,q=old.sha,old.save,old.require,old.q
static=load(BASE/'static_e2e.py','closed_guard018_static_shape')

class ExpectedAbort(Exception):
    pass

class Campaign(old.Campaign):
    history=types.FunctionType(old.Campaign.history.__code__,{**old.Campaign.history.__globals__,'ROLES':ROLES})
    def __init__(self,args):
        self.args=args;self.started=time.monotonic();self.deadline=self.started+600;self.stop_reason=None
        self.cleaning=False;self.cleanup_deadline=None;self.clients=[];self.done=threading.Event()
        self.pg=self.driver=self.fixture=self.oracle=self.monitor=None
        self.owners={};self.writers={};self.structure={};self.native={};self.sequence={}
        self.run=BASE/'matched-runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');(self.run/'inputs').mkdir(parents=True)
        self.report={'kind':'owned_017_018_matched_cold_overlap_e2e_v1','command':[sys.executable,*sys.argv],
                     'expected':str(PLAN),'cases':[],'commands':[],'resources':[],'inputSha256':{},
                     'pgStarts':0,'fixtureDatabases':0,'maximumOpenConnections':0,'realSourceCalls':0,'ramGets':0,
                     'rdsCalls':0,'providerCalls':0,'analyzeCommands':0,'manualVacuumCommands':0,'fullAcceptance':False}
        self.env={k:v for k,v in os.environ.items() if k in {'PATH','HOME','USER','TMPDIR','LANG'}}
        self.env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONPATH='/tmp/statarena-publication-test-python')
        self.trials={};self.results={};self.matched_native={}

    def frozen(self):
        require(not sys.flags.optimize and sha(PINS)==PINS_SHA and sha(LEGACY)==LEGACY_SHA and sha(TARGET)==TARGET_SHA,'Exact frozen inputs required')
        self.preserve(Path(__file__));self.preserve(PINS);self.preserve(LEGACY);self.preserve(BASE/'static_e2e.py')
        self.preserve(TARGET);self.target_proof=json.loads(TARGET.read_text())
        binding=json.loads(PINS.read_text())
        for file,expected in binding['files'].items():
            p=ROOT/file;require(sha(p)==expected,'Frozen input changed');self.preserve(p)
        for file,expected in self.target_proof['files'].items():
            p=ROOT/file;require(sha(p)==expected,'Actual target017 proof changed');self.preserve(p)
        require(self.target_proof['originalImmediateUniqueIndexes']==binding['nativeImmediateUniqueIndexes'],
                'Actual 017 supporting indexes differ from the proven P2 definitions')
        legacy=json.loads(old.PINS.read_text());require(sha(old.PINS)==old.PINS_SHA,'Frozen E2E dependencies drifted')
        for file,expected in legacy['files'].items():
            p=ROOT/file;require(sha(p)==expected,'Frozen legacy input changed');self.preserve(p)
        self.model103=json.loads(old.MODEL.read_text())
        model=json.loads(MODEL.read_text());self.tables={t['qualified_name']:t for s in model['schemas'] for t in s['tables'] if t['phase']!='models'}
        require(len(self.tables)==98 and sum(len(t['columns']) for t in self.tables.values())==1829,'Expected exact active98/1829 shape')
        self.settings=json.loads(old.RDS_READBACK.read_text())['plannerSettings'];require(len(self.settings)==14,'Exact measured planner settings required')
        self.predicates=old.exact_predicates()
        self.parent_fn=static.parent_body(SQL[-2].read_text());self.original=''.join(SQL[-2].read_text().splitlines(keepends=True)[1433:1435])
        require(static.START not in SQL[-1].read_text() and self.original in self.parent_fn,'Parent017 drift')
        return {'activeTables':98,'columns':1829,'coldOriginalChecks':[p['sql'] for p in self.predicates]}

    def candidate(self):
        require(CANDIDATE.is_file(),'018 candidate absent (expected precode RED)')
        self.preserve(CANDIDATE);raw=CANDIDATE.read_text();self.candidate_fn=static.parent_body(raw)
        a,tail=self.candidate_fn.split(CLAUSE_START);delta,b=tail.split(CLAUSE_END)
        before,after=delta.split(self.original)
        require(a+self.original+b==self.parent_fn and after.strip()=='END IF;','Any original parent logic changed')
        self.index_sql=raw.split(self.candidate_fn)[0].strip()
        if self.index_sql:
            require(self.index_sql=='CREATE INDEX '+CLOSED+'\n  ON football.player_match_metric_values USING btree (recorded_to_gen)\n  WHERE recorded_to_gen IS NOT NULL;',
                    'Unexpected optional index SQL')
        require(before.strip().startswith('IF CASE WHEN') and before.strip().endswith('END THEN'),'Exact guard envelope required')
        self.guard_sql='SELECT '+before.strip()[3:-5].strip()
        require(self.guard_sql.startswith('SELECT CASE WHEN') and self.guard_sql.endswith('END'),'Invalid diagnostic projection')
        return {'candidateSha256':sha(CANDIDATE),'index':bool(self.index_sql),'originalSqlExact':True}

    def allocate(self):
        args=self.args
        require(args.release and args.release.is_absolute() and args.release.parent==BASE and args.release_sha256 and
                not any(k.startswith('PG') for k in os.environ) and sha(args.release)==args.release_sha256,'Separate exact ROOT release required')
        self.preserve(args.release);actual=json.loads(args.release.read_text())
        exact={'kind':'root_owned_matched_018_overlap_v1','approvedBy':'ROOT','e2eSha256':sha(__file__),'candidateSha256':sha(CANDIDATE),
               'protocolSha256':sha(PLAN),'pinsSha256':PINS_SHA,'actual017ProvenanceSha256':TARGET_SHA,
               'maximumPgStarts':1,'maximumDatabaseConstructions':3,
               'maximumConnections':5,'maximumSeconds':600,'maximumOwnedBytes':3221225472,'maximumProofBytes':100663296,
               'maximumDenseMetricCopyRows':6*478547,'rdsCalls':0,'realSourceCalls':0}
        require(set(actual)==set(exact)|{'allocationId'} and all(actual[k]==v for k,v in exact.items()) and
                re.fullmatch('[A-Za-z0-9-]+',actual['allocationId']),'Unknown ownership/bounds')
        with (BASE/(actual['allocationId']+'.consumed.json')).open('x') as f:
            json.dump({'run':str(self.run),'state':'consumed','releaseSha256':args.release_sha256},f)
        def alarm(signum,frame):raise TimeoutError(self.stop_reason or 'Owned campaign deadline')
        signal.signal(signal.SIGALRM,alarm);signal.setitimer(signal.ITIMER_REAL,max(.001,self.deadline-time.monotonic()))
        return exact

    def setup_cluster(self):
        import psycopg
        from harness import LocalPostgres
        self.driver=psycopg;self.fixture=load(old.FIXTURE,'matched_native_fixture')
        self.oracle=load(old.ORACLE,'matched_independent_native_oracle')
        tempfile.tempdir='/tmp';self.pg=LocalPostgres(old.PG_BIN,self.run);self.pg.command=self.command
        self.command([old.PG_BIN/'initdb','-D',self.pg.data,'--auth=trust','--no-locale','--encoding=UTF8'],name='initdb')
        self.command(['openssl','req','-x509','-newkey','rsa:2048','-sha256','-nodes','-days','2','-keyout',self.pg.data/'server.key',
                      '-out',self.pg.data/'server.crt','-subj','/CN=127.0.0.1','-addext','subjectAltName=IP:127.0.0.1'],name='tls')
        (self.pg.data/'server.key').chmod(0o600)
        with (self.pg.data/'postgresql.conf').open('a') as cfg:
            cfg.write("\nssl=on\nssl_cert_file='server.crt'\nssl_key_file='server.key'\nstatement_timeout=8000\nlock_timeout=1000\n"
                      "autovacuum_naptime='1h'\ntemp_file_limit='256MB'\nlog_error_verbosity=terse\n"
                      "log_min_error_statement=panic\nlog_parameter_max_length_on_error=0\n")
            for k,v in sorted(self.settings.items()):
                require(re.fullmatch('[a-z_]+',k) and re.fullmatch('[0-9.]+|on|off',v['setting']),'Unexpected planner configuration')
                cfg.write(k+'='+v['setting']+'\n')
        self.report['pgStarts']=1;self.pg.start();self.monitor=threading.Thread(target=self.watchdog,daemon=True);self.monitor.start()
        self.admin=self.connect('postgres',os.environ.get('USER','postgres'));require(self.admin.info.server_version==180006,'Exact PG18.6 required')
        for role in ROLES.values():self.admin.execute('CREATE ROLE '+q(role)+' LOGIN NOSUPERUSER NOCREATEROLE NOCREATEDB NOREPLICATION NOBYPASSRLS')
        return {'onePrivateCluster':True,'roles':ROLES}

    def install(self,db):
        from orion_pro_migrate import bootstrap
        from orion_pro_integrity import role_grants_sql
        from orion_pro_bulk_local import sequences
        self.admin.execute('CREATE DATABASE '+q(db)+' OWNER '+q(ROLES['owner']))
        self.report['fixtureDatabases']+=1
        owner=self.owners[db]=self.connect(db,ROLES['owner'])
        with owner.transaction():
            artifacts=[]
            for i,path in enumerate(SQL):
                text=path.read_text();owner.execute(text,prepare=False)
                owner.execute('INSERT INTO ingest.schema_migrations VALUES(%s,%s,CURRENT_TIMESTAMP,%s)',
                              (str(12+i).zfill(3),sha(path),'matched_owned_018'))
                if i<2:artifacts.append((str(12+i).zfill(3),path,text))
                if i==1:
                    bootstrap(owner,self.model103,artifacts)
                    owner.execute(role_grants_sql(self.model103,ROLES['writer'],ROLES['reader']),prepare=False)
        writer=self.writers[db]=self.connect(db,ROLES['writer'])
        got={n:{'setting':s,'unit':u} for n,s,u in writer.execute('SELECT name,setting,unit FROM pg_settings WHERE name=ANY(%s)',(list(self.settings),))}
        require(got==self.settings,'Planner settings differ')
        identity=writer.execute("SELECT current_user,session_user,(SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()),"
                                "current_setting('statement_timeout'),current_setting('lock_timeout'),rolsuper,rolcreaterole,"
                                "rolcreatedb,rolreplication,rolbypassrls FROM pg_roles WHERE rolname=current_user").fetchone()
        require(identity==(ROLES['writer'],ROLES['writer'],True,'8s','1s',False,False,False,False,False),'Wrong ordinary TLS writer')
        self.native[db]=self.oracle.oracle(owner,self.tables,self.report);self.sequence[db]=sequences(owner)
        self.structure[db]=self.oracle.function_properties(owner)
        definition=owner.execute("SELECT pg_get_functiondef('ingest.validate_generation(bigint)'::regprocedure)").fetchone()[0]
        require(hashlib.sha256(definition.encode()).hexdigest()==self.target_proof['canonicalParentDefinitionSha256'],
                'Local017 parent differs from the independently observed actual body')
        require(len(self.native[db])==98 and len(self.sequence[db])==67,'Owned installed native shape differs')
        return owner,writer

    def adopt_candidate(self,db):
        from orion_pro_bulk_local import sequences
        c=self.owners[db];before=self.oracle.oracle(c,self.tables,self.report);seq=sequences(c);props=self.oracle.function_properties(c)
        before_shape=self.oracle.structure(c);timings={}
        with c.transaction():
            if self.index_sql:
                now=time.monotonic();c.execute(self.index_sql,prepare=False);timings['indexMs']=(time.monotonic()-now)*1000
                require(timings['indexMs']<8000,'Closed index build exceeded8s on aborted-load B0')
            now=time.monotonic();c.execute(self.candidate_fn,prepare=False);timings['functionMs']=(time.monotonic()-now)*1000
            c.execute('INSERT INTO ingest.schema_migrations VALUES(%s,%s,CURRENT_TIMESTAMP,%s)',
                      ('018',sha(CANDIDATE),'matched_owned_018'))
        after=self.oracle.oracle(c,self.tables,self.report)
        require({k:v for k,v in after.items() if k!='ingest.schema_migrations'}=={k:v for k,v in before.items() if k!='ingest.schema_migrations'} and
                sequences(c)==seq and self.oracle.function_properties(c)==props,'018 changed business/native state, sequences or function identity')
        shape=self.oracle.structure(c);adds=[row for row in shape if row not in before_shape]
        require(all(row in shape for row in before_shape) and
                [row[0] for row in adds]==(['football.'+CLOSED] if self.index_sql else []),'Unexpected catalogue delta')
        reader=self.connect(db,ROLES['reader'])
        try:
            actual=reader.execute("SELECT pg_get_functiondef('ingest.validate_generation(bigint)'::regprocedure)").fetchone()[0]
            require(CLAUSE_START in actual and CLAUSE_END in actual and self.original in actual,
                    'Independent native candidate function body differs')
        finally:reader.close()
        save(self.run/(db+'-adoption.json'),{'timings':timings,'nativeBefore':before,'nativeAfter':after,'sequence67':seq,'indexDelta':adds})
        return timings

    def explain(self,c,sql,params=None):
        estimated=c.execute('EXPLAIN (SETTINGS,FORMAT JSON) '+sql,params,prepare=False).fetchone()[0]
        now=time.monotonic();observed=c.execute('EXPLAIN (ANALYZE,BUFFERS,SETTINGS,FORMAT JSON) '+sql,params,prepare=False).fetchone()[0]
        return {'sql':sql,'estimated':estimated,'observed':observed,'elapsedMs':round((time.monotonic()-now)*1000,3)}

    def fixture_attempt(self,db,label,*,abort=False,compact=False,candidate=False):
        outer=self;c=self.writers[db];result={'label':label,'abortBeforeSeal':abort,'seals':[],'commits':[],'candidate':candidate}
        class Proxy:
            def __init__(self):self.batches=[]
            def __getattr__(self,name):return getattr(c,name)
            def execute(self,sql,params=None):
                outer.tick();projection=old.metric_projection(sql)
                if projection:
                    names,select=projection;self.batches.append((','.join(map(q,names)),select,params));return None
                if sql==old.SHAPE:
                    result['copy']=outer.copy_batches(c,self.batches);result['cold']=outer.cold(c)
                    require(result['copy']['rows']==(1240 if compact else 478547),'Expected closed COPY count')
                    if abort:
                        if label=='prior_abort_2':
                            result['noIndexProbeBeforeRollback']=outer.explain(c,'SELECT recorded_to_gen FROM '+old.TABLE+
                                ' WHERE recorded_to_gen IS NOT NULL ORDER BY recorded_to_gen LIMIT 1')
                        raise ExpectedAbort()
                    if candidate:
                        requires_original=c.execute(outer.guard_sql,prepare=False).fetchone()[0]
                        require(requires_original is False,'Open-only fresh draft did not skip exact original pair')
                    else:
                        result['withoutIndexEstimate']=c.execute('EXPLAIN (SETTINGS,FORMAT JSON) SELECT recorded_to_gen FROM '+old.TABLE+
                                ' WHERE recorded_to_gen IS NOT NULL ORDER BY recorded_to_gen LIMIT 1',prepare=False).fetchone()[0]
                if sql.startswith('SELECT ingest.seal_generation'):
                    t=time.monotonic()
                    try:return c.execute(sql,params,prepare=False)
                    finally:result['seals'].append(round((time.monotonic()-t)*1000,3))
                return c.execute(sql,params)
            def commit(self):
                t=time.monotonic()
                try:c.commit()
                finally:result['commits'].append(round((time.monotonic()-t)*1000,3))
        data=self.run/(db+'-'+label);data.mkdir()
        fixture=self.fixture.fixture
        if compact:fixture=types.FunctionType(fixture.__code__,{**fixture.__globals__,'APPEARANCES':40,'SCALARS':1240,'MATCHES':4,'PLAYERS':40})
        try:
            result['phases']=fixture(Proxy(),self.model103,'a'*64,data)
            require(not abort and len(result['seals'])==len(result['commits'])==2 and
                    max(result['seals']+result['commits'])<8000,'Both actual owned seals and commits required')
            result['status']='committed'
        except ExpectedAbort:
            require(abort and c.execute('SELECT count(*) FROM '+old.TABLE).fetchone()[0]==0,'Aborted load left visible facts')
            result.update(status='deliberately_rolled_back_before_seal',afterRollbackCold=self.cold(c))
        except self.driver.Error as error:
            ctx=error.diag.context or ''
            result.update(status='native_failure',sqlstate=error.sqlstate,context=ctx)
            require(not abort and not compact and not candidate and error.sqlstate=='57014' and
                    len(result['seals'])==1 and 'player_match_metric_values' in ctx and 'recorded_to_gen' in ctx and
                    any(p['sql'][7:] in ctx for p in self.predicates),'Unexpected native SQL failure')
            result['status']='expected_original_overlap_timeout'
        finally:save(data/'result.json',result)
        return result

    def bloat(self,db):
        for n in (1,2):
            self.trials.setdefault(db,[]).append(self.fixture_attempt(db,'prior_abort_'+str(n),abort=True))
            require(self.oracle.oracle(self.owners[db],self.tables,self.report)==self.native[db],
                    'An aborted local COPY left visible facts or changed the B0 journal')
        return {'twoDeliberateAborts':True,'after':self.trials[db][-1]['afterRollbackCold']}

    def matched_state(self,owner,db):
        from orion_pro_bulk_local import native_rows
        with owner.transaction():
            clocks=list(owner.execute('SELECT generation,status,created_at,sealed_at FROM ingest.dataset_snapshots ORDER BY generation'))
            require(len(clocks)==3 and all(status=='sealed' and created==sealed and created.tzinfo is not None
                                          for _,status,created,sealed in clocks),'Exact native owned transaction clocks required')
            replacements={created.isoformat():index for index,(_,_,created,_) in enumerate(clocks)}
            require(len(replacements)==3,'Distinct fixture transaction clocks required')
            substitutions={}
            for name,table in self.tables.items():
                for col,spec in table['columns'].items():
                    if spec['type']!='timestamptz' or (spec.get('default_sql')!='CURRENT_TIMESTAMP' and not
                        (name=='ingest.dataset_snapshots' and col in {'created_at','sealed_at'})):continue
                    branches=' '.join("WHEN TIMESTAMPTZ '"+clock+"' THEN TIMESTAMPTZ '2040-01-01 00:00:00+00' + INTERVAL '"+
                                      str(index)+" seconds'" for clock,index in replacements.items())
                    substitutions.setdefault(name,{})[col]='CASE '+q(col)+' '+branches+' ELSE '+q(col)+' END'
            digest={name:native_rows(owner,name,self.tables,substitutions.get(name))
                    for name in sorted(set(self.tables)-{'ingest.schema_migrations'})}
        save(self.run/(db+'-matched-native.json'),{'rows':digest,'actualFixtureTransactionClocks':clocks,
                                                 'onlyClockSubstitutions':substitutions,'journalObservedSeparately':True})
        return digest

    def baseline(self):
        db='matched_baseline';owner,c=self.install(db);self.bloat(db)
        result=self.results[db]=self.fixture_attempt(db,'actual_default')
        if result['status']=='committed':
            g=result['phases'][0]['generation']
            self.native[db]=self.oracle.oracle(owner,self.tables,self.report)
            self.matched_native[db]=self.matched_state(owner,db)
            plans=[self.explain(c,re.sub(r'\bg\b','%(g)s::bigint',p['sql']),{'g':g}) for p in self.predicates]
            plans.append(self.explain(c,'SELECT recorded_to_gen FROM '+old.TABLE+' WHERE recorded_to_gen IS NOT NULL ORDER BY recorded_to_gen LIMIT 1'))
            save(self.run/'baseline-observed-postcommit-plans.json',plans)
        save(self.run/'baseline-native94plus4.json',self.native[db])
        c.close();owner.close();self.admin.execute('DROP DATABASE '+q(db))
        return result

    def prepare_candidate(self):
        db='matched_candidate';self.install(db);bloat=self.bloat(db)
        return {**bloat,'adoption':self.adopt_candidate(db)}

    def compare(self):
        db='matched_candidate';owner,c=self.owners[db],self.writers[db]
        result=self.results[db]=self.fixture_attempt(db,'actual_guarded',candidate=True)
        a=self.trials['matched_baseline']+[self.results['matched_baseline']];b=self.trials[db]+[result]
        require([t['copy']['wireSha256'] for t in a]==[t['copy']['wireSha256'] for t in b],
                'Corresponding COPY payload bytes differ')
        actual=self.oracle.oracle(owner,self.tables,self.report);save(self.run/'candidate-native98.json',actual)
        if a[-1]['status']=='committed':
            old_rows=self.native['matched_baseline'];counts={n:v['rows'] for n,v in actual.items()}
            require(actual[old.TABLE]==old_rows[old.TABLE] and
                    all(counts[n]==v['rows'] for n,v in old_rows.items() if n!='ingest.schema_migrations'),
                    'Matched native metric state or active relation counts differ')
            require(self.matched_state(owner,db)==self.matched_native['matched_baseline'],
                    'Matched native active rows differ after exact documented owned transaction clock projection')
        plan=self.explain(c,self.guard_sql)
        def scan(node):return [node]+[n for x in node.get('Plans',[]) for n in scan(x)]
        nodes=scan(plan['observed'][0]['Plan']);indexes=[n for n in nodes if n.get('Index Name')==CLOSED]
        if self.index_sql:
            require(indexes and any(n.get('Actual Loops',0)>0 for n in indexes) and
                    not any(n.get('Node Type') in {'Seq Scan','Bitmap Heap Scan'} and n.get('Relation Name')=='player_match_metric_values' and
                            n.get('Actual Loops',0)>0 for n in nodes),'Fast branch did not use the bounded closed index')
        save(self.run/'candidate-observed-postcommit-plan.json',plan)
        return {'matchedCopyPayloads':True,'baselineStatus':a[-1]['status'],'candidateSeals':result['seals'],
                'candidateDeferredCommits':result['commits'],'observedClosedProbeIndex':bool(indexes)}

    def historical(self):
        # Exact already qualified ordinary-ingest correction workflow, no planner setting.
        return self.history('matched_candidate',('default',))

    def drift(self):
        db='matched_compact';owner,c=self.install(db);self.adopt_candidate(db)
        self.fixture_attempt(db,'compact_native',compact=True,candidate=True)
        checks=[]
        for variant in ('variant','canonical'):
            name='football_player_match_metric_values_sv_'+variant+'_current_idx'
            definition=owner.execute('SELECT pg_get_indexdef(%s::regclass)',('football.'+name,)).fetchone()[0]
            owner.execute('DROP INDEX football.'+q(name))
            require(c.execute(self.guard_sql,prepare=False).fetchone()[0] is True,'Missing immediate unique index did not force original pair')
            c.execute('BEGIN')
            try:
                g=c.execute('SELECT ingest.begin_generation(%s,%s,%s)',('owned-index-drift:'+variant,'owned_drift','owned_drift')).fetchone()[0]
                cols=[k for k,v in self.tables[old.TABLE]['columns'].items() if not v.get('identity')]
                overrides={'recorded_from_gen':'%s::bigint'}
                if variant=='variant':overrides['is_canonical']='false'
                else:overrides['variant_key']="'owned:alternate'"
                c.execute('INSERT INTO '+old.TABLE+' ('+','.join(map(q,cols))+') SELECT '+
                          ','.join(overrides.get(x,'t.'+q(x)) for x in cols)+' FROM '+old.TABLE+' t WHERE t.metric_code=%s ORDER BY revision_id LIMIT 1',
                          (g,'m05'))
                c.execute('SELECT ingest.seal_generation(%s,%s)',(g,old.hashed(variant)),prepare=False)
                raise AssertionError('Original overlap incorrectly skipped in owned index-drift case')
            except self.driver.Error as error:
                require(error.sqlstate=='23514' and error.diag.message_primary==
                        'Historical interval overlap: football.player_match_metric_values / '+name,'Wrong original overlap refusal')
                checks.append({'variant':variant,'sqlstate':error.sqlstate,'message':error.diag.message_primary})
            finally:c.rollback()
            owner.execute(definition,prepare=False)
            require(c.execute(self.guard_sql,prepare=False).fetchone()[0] is False,'Exact unique restore did not recover open-only proof')
        if self.index_sql:
            owner.execute('DROP INDEX football.'+q(CLOSED));require(c.execute(self.guard_sql,prepare=False).fetchone()[0] is True,'Missing probe index did not fall back')
            owner.execute(self.index_sql,prepare=False)
        save(self.run/'owned-index-drift-results.json',checks)
        return checks

def main():
    parser=argparse.ArgumentParser(description=__doc__,allow_abbrev=False);mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--check-only',action='store_true');mode.add_argument('--run-local',action='store_true')
    parser.add_argument('--release',type=Path);parser.add_argument('--release-sha256');args=parser.parse_args()
    sys.path[:0]=[str(ROOT/'tests'),str(PILOT),str(ROOT/'dashboard/scripts'),'/tmp/statarena-publication-test-python']
    c=Campaign(args);block=None
    actions=(c.frozen,c.candidate,c.allocate,c.setup_cluster,c.baseline,c.prepare_candidate,c.compare,c.historical,c.drift,
             lambda:{'inputFiles':len(c.report['inputSha256']),'allOwnedConnectionsClosedInFinally':True})
    try:
        for i,(name,fn) in enumerate(zip(CASES,actions)):
            if block or not args.run_local and i>1:
                c.report['cases'].append({'case':name,'status':'unverified','reason':block or 'Owned campaign not released'});continue
            try:c.report['cases'].append({'case':name,'status':'pass','actual':fn()})
            except BaseException as e:
                block=name;diag=getattr(e,'diag',None)
                c.report['cases'].append({'case':name,'status':'fail','error':diag.message_primary if diag else str(e),
                                          'sqlstate':getattr(e,'sqlstate',None),'traceback':traceback.format_exc()})
            save(c.run/'progress.json',c.report)
    finally:
        try:c.cleanup(block is not None)
        except BaseException as e:block=block or 'cleanup';c.report['cleanup']={'status':'fail','errorType':type(e).__name__}
        c.report['inputHashesExact']=all(sha(ROOT/p)==h for p,h in c.report['inputSha256'].items())
        block=block or (None if c.report['inputHashesExact'] else 'Input drift')
        c.report['elapsedSeconds']=round(time.monotonic()-c.started,3);c.report['status']='fail' if block else 'pass_owned_only' if args.run_local else 'pass_preflight_only'
        c.report['counts']={s:sum(x['status']==s for x in c.report['cases']) for s in ('pass','fail','unverified')}
        save(c.run/'result.json',c.report);print(json.dumps({'status':c.report['status'],'counts':c.report['counts'],'evidence':str(c.run/'result.json')}))
    return 1 if block else 0

if __name__=='__main__':raise SystemExit(main())
