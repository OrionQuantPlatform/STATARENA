#!/usr/bin/env python3
"""Bounded real PG/HTTP publisher E2E written before the publisher exists."""
from __future__ import annotations
import argparse
import ast
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import re
import select
import shutil
import signal
import subprocess
import sys
import threading
import time
from urllib.error import HTTPError
from urllib.request import Request,HTTPRedirectHandler,ProxyHandler,build_opener

sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[2]
sys.path[:0]=[str(BASE),str(ROOT/'docs/verification/orion-pro-pilot-20261104'),str(ROOT/'dashboard/scripts')]
from workflow_budget import SharedBudget,OPTIONS,connection_factory,LimitExceeded,digest
from publisher_driver import PublisherDriver,minimal_env
from publisher_oracles import snapshot,active_builds,expected_products,tokens,paths,qs,same_http,metadata_only,bounded_light_list,summary_http,no_begin_generation
from typed_inputs import TypedInputs
from harness import LocalPostgres

MODEL=ROOT/'docs/architecture/orion-plan-20261104/target-schema.proposed.json'
TARGET=ROOT/'dashboard/scripts/orion_pro_publish.py'
PINNED={str(MODEL.relative_to(ROOT)):'18da43f940870b7a3a3cb49323c847dd5e5174e5eea1f8ff0c8a159cf373cb08',
 'dashboard/backend/migrations/012_orion_pro_domain.sql':'f255868599c72d69f40f575a919045325ea1093a00fe4f5a6b96eae9f2c49f65',
 'dashboard/backend/migrations/013_orion_pro_integrity.sql':'85525221cad51b32aff79a777098211b4112f9f00ea7161ac93945654eeb6968'}
SERVICE_NAMES=['orion-pro.js','postgres.js','database-connection.js','metrics.js','cache-policy.js','cache.js','relational-match.js',
 'relational-support.js','relational-catalog.js','cdn.js','relational-core.js','partition-wire.js','catalog-model.json','support-model.json']


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None


class BoundedPostgres(LocalPostgres):
    def __init__(self,*a,budget,**kw):super().__init__(*a,**kw);self.budget=budget
    def command(self,args,*,env=None,check=True,name='command'):
        if name!='postgres-stop':self.budget.check()
        result=subprocess.run([str(x) for x in args],env=minimal_env(),text=True,capture_output=True,timeout=15 if name=='postgres-stop' else 30)
        n=len(self.commands)+1;entry={'argv':[str(x) for x in args],'exit_code':result.returncode,'stdout':f'{n:03d}-{name}.stdout.log','stderr':f'{n:03d}-{name}.stderr.log'}
        self.commands.append(entry);(self.evidence/entry['stdout']).write_text(result.stdout);(self.evidence/entry['stderr']).write_text(result.stderr)
        (self.evidence/'commands.json').write_text(json.dumps(self.commands,indent=2)+'\n')
        if check and result.returncode:raise RuntimeError(name+': '+result.stderr[-1500:])
        return result
    def start(self):
        self.command([self.binaries/'initdb','-D',self.data,'--auth=trust','--no-locale','--encoding=UTF8'],name='initdb')
        options=f"-h 127.0.0.1 -p {self.port} -k {self.socket_dir} -c fsync=on -c max_connections=5 -c superuser_reserved_connections=0 -c max_locks_per_transaction=1024 -c statement_timeout=8000 -c lock_timeout=1000 -c idle_in_transaction_session_timeout=5000 -c log_statement=all -c log_parameter_max_length=0 -c log_parameter_max_length_on_error=0 -c log_line_prefix='[%p] app=%a '"
        self.command([self.binaries/'pg_ctl','-D',self.data,'-l',self.evidence/'postgres.log','-o',options,'-w','start'],name='postgres-start');self.started=True


class Workflow:
    def __init__(self,run,budget,pg,conn,model,psycopg):
        self.run,self.budget,self.pg,self.conn,self.model,self.psycopg=run,budget,pg,conn,model,psycopg
        self.phase='setup';self.api=None;self.api_streams=[];self.http_count=0;self.requests=[];self.setup=[];self.cases={};self.saved={};self.watchdog_errors=[]
        self.inputs=TypedInputs(conn,pg.dsn,run,psycopg);self.driver=PublisherDriver(run,pg.port,budget,self.inputs)
        self.opener=build_opener(ProxyHandler({}),NoRedirect())
    def record(self,id,status,**values):self.cases[id]={'id':id,'status':status,**values}
    def checkpoint(self):
        self.budget.check();state=snapshot(self.conn,self.model)
        connections=self.conn.execute("SELECT count(*) FROM pg_stat_activity WHERE backend_type='client backend'").fetchone()[0]
        assert connections<=5;return state
    def export_api(self):
        dest=self.run/'api-runtime';backend=dest/'dashboard/backend';(backend/'services').mkdir(parents=True)
        for name in SERVICE_NAMES:shutil.copy2(ROOT/'dashboard/backend/services'/name,backend/'services'/name)
        shutil.copy2(ROOT/'dashboard/backend/aws-app.js',backend/'aws-app.js');shutil.copy2(ROOT/'dashboard/package.json',dest/'dashboard/package.json')
        (dest/'dashboard/node_modules').symlink_to(ROOT/'dashboard/node_modules',target_is_directory=True)
        graph='\n'.join((backend/'services'/n).read_text() for n in SERVICE_NAMES if n.endswith('.js'))
        assert not any(v in graph for v in ['@aws-sdk/','./files.js','./data-store.js','./pitchapi.js','./neon.js'])
        return dest,{'files':{str(p.relative_to(dest)):sha(p) for p in [backend/'aws-app.js',dest/'dashboard/package.json',*[backend/'services'/n for n in SERVICE_NAMES]]},
          'environmentFiles':0,'numberedCopies':0,'sourceObjectProviderModules':0,'dependencyReuse':'Existing local node_modules symlink only'}
    def start_api(self,runtime):
        assert self.api is None or self.api.poll() is not None,'At most1 API'
        env=minimal_env();env.update(DATABASE_URL=f'postgresql://statarena_runtime@127.0.0.1:{self.pg.port}/postgres?sslmode=disable',
          STATARENA_DATA_PROVIDER='aws',STATARENA_TEST_DATABASE='1',STATARENA_PRO_API='1',DATABASE_POOL_MAX='1',STATARENA_METRICS_SAMPLE_RATE='0',
          ORION_PUBLISHER_TEST_RUN=str(self.run),ORION_PUBLISHER_API_RUNTIME=str(runtime),PGPASSFILE=os.devnull,PGSERVICEFILE=os.devnull)
        count=len(self.api_streams)//2;out=(self.run/f'api-{count}.stdout.log').open('w');err=(self.run/f'api-{count}.stderr.log').open('w');self.api_streams.extend([out,err])
        self.api=subprocess.Popen(['bun','--no-env-file',str(BASE/'publisher_http_server.mjs')],cwd=runtime/'dashboard',env=env,stdout=subprocess.PIPE,stderr=err,text=True,bufsize=1,start_new_session=True)
        end=time.monotonic()+10
        while time.monotonic()<end:
            self.budget.check();ready,_,_=select.select([self.api.stdout],[],[],.1)
            if not ready:continue
            line=self.api.stdout.readline();out.write(line);out.flush()
            if not line and self.api.poll() is not None:break
            try:info=json.loads(line)
            except ValueError:continue
            if info.get('event')=='ready':
                assert info['identity']==[{'role':'statarena_runtime','readonly':'on','statement_timeout':'8s','lock_timeout':'1s'}],info
                assert len(info['calibration'])==4
                self.origin=f"http://127.0.0.1:{info['port']}";return info
        raise AssertionError('Owned API startup failed')
    def stop_api(self):
        if self.api and self.api.poll() is None:
            os.killpg(self.api.pid,signal.SIGTERM)
            try:self.api.wait(timeout=3)
            except subprocess.TimeoutExpired:os.killpg(self.api.pid,signal.SIGKILL);self.api.wait(timeout=2)
    def http(self,path,method='GET',headers=None):
        self.budget.check();self.http_count+=1;rid=f'h{self.http_count:03d}'
        try:response=self.opener.open(Request(self.origin+path,method=method,headers={'x-e2e-id':rid,**(headers or {})}),timeout=9)
        except HTTPError as error:response=error
        body=response.read().decode();value=json.loads(body) if body else None
        trace=None;end=time.monotonic()+1
        while time.monotonic()<end:
            file=self.run/'api-requests.jsonl'
            for line in file.read_text().splitlines() if file.exists() else []:
                row=json.loads(line)
                if row['id']==rid:trace=row;break
            if trace:break
            time.sleep(.005)
        assert trace,'Missing real request trace'
        row={'id':rid,'path':path,'method':method,'requestHeaders':headers or {},'status':response.status,
          'headers':{k.lower():v for k,v in response.headers.items()},'body':body,'value':value,'sql':trace['sql']}
        self.requests.append(row);return row
    def probe_privileges(self):
        result={}
        for role,actions in [('statarena_ingest',["DELETE FROM ingest.dirty_editions WHERE false","SELECT ingest.validate_aggregation_build(-1)","SELECT nextval('ingest.commit_generation_seq')"]),
                             ('statarena_runtime',["UPDATE football.players SET display_name='forbidden' WHERE false"] )]:
            Factory=connection_factory(self.psycopg,self.budget,self.run/(role+'-privilege.jsonl'),phase=lambda:'operational',owned_port=self.pg.port,role=role)
            with Factory.connect(host='127.0.0.1',port=self.pg.port,dbname='postgres',user=role,options=OPTIONS+' -c application_name=publisher_privilege',autocommit=True) as conn:
                conn.execute('SET default_transaction_read_only=off')
                codes=[]
                for statement in actions:
                    try:conn.execute(statement)
                    except self.psycopg.Error as e:assert e.sqlstate=='42501';codes.append(e.sqlstate)
                    else:raise AssertionError('Unexpected privilege: '+role)
                result[role]=codes
        return result
    def deadline_probes(self):
        self.conn.execute('SELECT pg_advisory_lock(20261105,987)')
        workers=[self.driver.start(probe=True),self.driver.start(probe=True)]
        try:
            row=self.conn.execute("SELECT current_setting('statement_timeout'),current_setting('lock_timeout'),current_setting('idle_in_transaction_session_timeout')").fetchone()
            assert row==('8s','1s','5s')
            start=time.monotonic()
            try:self.conn.execute('SELECT pg_sleep(9)')
            except self.psycopg.Error as e:assert e.sqlstate=='57014';elapsed=time.monotonic()-start
            else:raise AssertionError('Main statement deadline not enforced')
            assert 7.5<=elapsed<9
            for worker in workers:self.driver.finish(worker)
            probes=[json.loads((self.run/(name+'-probe.json')).read_text()) for name in ['worker1','worker2']]
            return {'mainSettings':list(row),'mainStatementCancellationSeconds':round(elapsed,3),'workers':probes}
        finally:self.conn.execute('SELECT pg_advisory_unlock(20261105,987)')
    def helper(self,**kwargs):
        result=self.driver.execute(**kwargs);self.checkpoint();return result
    def assert_unchanged_publish(self,before):
        after=self.checkpoint();assert before==after;return after
    def save_baselines(self):
        manifest=self.http('/api/dashboard/manifest');assert manifest['status']==200
        self.saved['tokens']=tokens(manifest['value']);self.saved['bodies']={p:self.http(p) for k,t in self.saved['tokens'].items() for p in paths(k,t)}
        self.current={'tokens':dict(self.saved['tokens']),'bodies':dict(self.saved['bodies'])}
    def check_current(self,affected):
        manifest=self.http('/api/dashboard/manifest');assert manifest['status']==200
        now=tokens(manifest['value']);bodies={}
        for key,token in now.items():
            assert (token!=self.current['tokens'][key])==(key in affected),(key,affected)
            for path in paths(key,token):
                row=self.http(path);bodies[path]=row
                if key not in affected:same_http(self.current['bodies'][path],row)
            mid={'A':'m_000001','B':'m_000004','C':'m_000005'}[key]
            summary_http(bodies[paths(key,token)[2]],self.inputs,mid)
            if key in ['A','B']:
                shot_response=bodies[paths(key,token)[3]];assert shot_response['status']==200
                shots=[s for p in shot_response['value']['data']['periods'] for s in p['shots']]
                if key=='A':assert shots[0]['expected_goals']==(.67 if self.inputs.markers['A'] else .82)
                shared=[s for s in shots if s['player'] and s['player']['id']=='p_000001']
                assert len(shared)==1
                assert shared[0]['player']['name']==('Shared striker corrected' if self.inputs.markers['shared'] else 'Shared striker v1')
        self.current={'tokens':now,'bodies':bodies}
        return {'changedTokenKeys':affected,'allCurrentDtoOraclesChecked':True,'unchangedBodiesEtagsCursorsExact':True}
    def test_negative_admissions(self):
        for id,kind in [('P02','draft'),('P03','engagement')]:
            with self.inputs.negative_input(kind) as admission:
                before=self.checkpoint();self.helper(admission=admission,rejected=True);self.assert_unchanged_publish(before)
            self.record(id,'pass',evidence='Real committed synthetic negative input rejected without publisher writes; restored by fixture successor')
        import copy
        modifications=[('wrong_source',lambda a:a.update(allowedSourceIds=[self.inputs.ids['other_source']])),
          ('wrong_source_policy',lambda a:a.update(sourcePolicy='unreviewed_policy')),
          ('missing_source_evidence',lambda a:a.pop('sourceEvidence')),
          ('wrong_edition_revision',lambda a:a['editions'][0].update(editionRevision=999999)),
          ('wrong_match_revision',lambda a:a['editions'][0]['intendedMatches'][0].update(matchRevision=999999)),
          ('omitted_intended_match',lambda a:a['editions'][0]['intendedMatches'].pop()),
          ('wrong_type',lambda a:a['declaredTypes'].update(score=['string']))]
        for name,modify in modifications:
            admission=copy.deepcopy(self.inputs.admission());modify(admission);before=self.checkpoint();self.helper(admission=admission,rejected=True);self.assert_unchanged_publish(before)
        self.record('P04','pass',counterexamples=[x[0] for x in modifications],evidence='Business scope rejected despite freshly matching artifact SHA')
        modifications=[('count_mismatch',lambda m:m.update(declaredShotsCount=2)),
          ('stale_coverage_revision',lambda m:m.update(coverageRevision=999999)),
          ('wrong_period',lambda m:m['selectedShotObservations'][0].update(period='second_half')),
          ('wrong_actor',lambda m:m['selectedShotObservations'][0].update(playerId=self.inputs.ids['players'][2]['id']))]
        for name,modify in modifications:
            admission=copy.deepcopy(self.inputs.admission());modify(admission['editions'][0]['intendedMatches'][0])
            before=self.checkpoint();self.helper(admission=admission,rejected=True);self.assert_unchanged_publish(before)
        source_guards=[self.inputs.reject_illegal_typed_collection(kind) for kind in ['duplicate_coverage','wrong_period','wrong_actor']]
        self.record('P05','pass',admissionCounterexamples=[x[0] for x in modifications],existingSourceGuardRejections=source_guards,
          evidence='Invalid metadata cannot be accepted; impossible canonical duplicates/periods/actors are rejected by unchanged012/013 before any publisher input exists')
        before=self.checkpoint();result=self.helper(mode='plan');assert result['status']=='planned';self.assert_unchanged_publish(before)
        self.record('P06','pass',evidence='Plan accepts honestly declared unknown/unavailable capability without materializing an empty collection')
    def bootstrap_faults_and_publish(self):
        before=self.checkpoint();child=self.driver.start(barrier='before_ready_commit');event=self.driver.wait_phase(child,'before_ready_commit');self.driver.kill(child)
        self.assert_unchanged_publish(before);self.record('P22','pass',phase=event,evidence='Uncommitted build/output rolled back with killed writer')
        child=self.driver.start(barrier='after_ready_commit');event=self.driver.wait_phase(child,'after_ready_commit');orphan=self.checkpoint()
        assert orphan['caps']['builds']>0 and not orphan['pointers'];self.driver.kill(child)
        self.record('P21','pass',phase=event,orphanBuildIds=[x[0] for x in orphan['builds']],retryPendingVerification=True)
        a=self.driver.start(keys='AB',barrier='after_plan');self.driver.wait_phase(a,'after_plan')
        c=self.driver.start(keys='C',barrier='after_plan');self.driver.wait_phase(c,'after_plan');self.driver.release(a);self.driver.release(c)
        self.driver.finish(a);self.driver.finish(c);after=self.checkpoint();expected_products(self.conn,self.inputs)
        for old in orphan['builds']:assert old in after['builds'],'Ready orphan must be reused, never edited'
        assert after['caps']['builds']==3 and after['caps']['matchSummaries']==5 and after['caps']['editionSummaries']==3
        self.record('P21','pass',phase=event,orphanBuildIds=[x[0] for x in orphan['builds']],sameIdsReused=True)
        self.record('P25','pass',evidence='Two real disjoint publishers reused ready state and activated coherent scopes')
        self.record('P07','pass',outputs=expected_products(self.conn,self.inputs));self.save_baselines()
    def basic_products_and_http(self,runtime):
        self.record('P08','pass',outputs=expected_products(self.conn,self.inputs));self.record('P09','pass',counterOracle={'A':[3,2,2,1],'B':[1,1,2,2],'C':[1,1,2,1]})
        builds=active_builds(self.conn)
        assert all(v['dg']!=v['cg'] for v in builds.values());self.record('P10','pass',buildMetadata=builds)
        a=self.saved['tokens']['A'];first=self.http('/api/fixtures?'+qs(v=a,league='l_000001',season='2024/2025',limit=2))
        cur=first['value']['pagination']['nextCursor'];second=self.http('/api/fixtures?'+qs(v=a,league='l_000001',season='2024/2025',limit=2,cursor=cur))
        assert [m['id'] for r in [first,second] for m in r['value']['data']['matches']]==['m_000001','m_000002','m_000003']
        bounded_light_list(first,2);bounded_light_list(second,2)
        self.saved['pinnedCursor']=cur;mutable=self.http('/api/fixtures?league=l_000001&season=2024%2F2025&limit=2');self.saved['mutableCursor']=mutable['value']['pagination']['nextCursor']
        self.record('P11','pass',ids=['m_000001','m_000002','m_000003'])
        r=self.http('/api/matches/m_000001/summary?'+qs(v=a));summary_http(r,self.inputs,'m_000001');self.record('P12','pass',bodySha256=digest(r['body']))
        for mid in ['m_000002','m_000003']:
            r=self.http('/api/matches/'+mid+'/summary?'+qs(v=a));summary_http(r,self.inputs,mid)
        r=self.http('/api/pitchapi/matches/m_000001/shots?'+qs(v=a));shot=r['value']['data']['periods'][0]['shots'][0]
        assert shot['event_type']=='' and shot['is_goal'] is True and shot['expected_goals_on_target']==0 and shot['x']==52.5 and shot['y']==34
        r=self.http('/api/pitchapi/matches/m_000004/shots?'+qs(v=self.saved['tokens']['B']));shots=[s for p in r['value']['data']['periods'] for s in p['shots']]
        assert len(shots)==2 and shots[0]['x'] is None and shots[0]['coordinate_state']=='unsupported_frame' and shots[1]['is_goal'] is False
        for mid,key,status,state in [('m_000002','A',200,'empty'),('m_000003','A',404,'unavailable'),('m_000005','C',404,'unknown')]:
            r=self.http(f'/api/pitchapi/matches/{mid}/shots?'+qs(v=self.saved['tokens'][key]));assert r['status']==status
            assert (r['value']['data']['collectionState'] if status==200 else r['value']['error']['state'])==state
        self.record('P13','pass',evidence='Actual V1 native zero/bool/empty/metres/frame and collection states')
        self.stop_api();self.start_api(runtime)
        for path in paths('A',a):
            head=self.http(path,method='HEAD');assert head['status']==200 and head['body']=='';metadata_only(head)
            r=self.http(path,headers={'if-none-match':head['headers']['etag']});assert r['status']==304 and r['body']=='';metadata_only(r)
        self.record('P14','pass',evidence='Fresh API process before each four-route body cache; actual metadata-only HEAD/304')
    def correction_and_same_plan_race(self):
        before=active_builds(self.conn);change=self.inputs.correct_A_data();a=self.driver.start(barrier='after_plan');self.driver.wait_phase(a,'after_plan')
        b=self.driver.start(barrier='after_plan');self.driver.wait_phase(b,'after_plan');self.driver.release(a);self.driver.release(b)
        self.driver.finish(a);self.driver.finish(b);after=active_builds(self.conn);aid=self.inputs.editions['A']['id']
        assert after[aid]!=before[aid]
        for key in ['B','C']:assert after[self.inputs.editions[key]['id']]==before[self.inputs.editions[key]['id']]
        assert self.checkpoint()['caps']['builds']==4
        self.record('P24','pass',evidence='Two same-plan workers produced exactly one additional A build')
        self.record('P15','pass',correction=change,outputs=expected_products(self.conn,self.inputs),http=self.check_current(['A']))
    def shared_correction_and_pointer_crash(self):
        before=active_builds(self.conn);change=self.inputs.correct_shared_catalogue();child=self.driver.start(barrier='after_first_pointer_write')
        event=self.driver.wait_phase(child,'after_first_pointer_write');assert active_builds(self.conn)==before
        self.driver.kill(child);assert active_builds(self.conn)==before
        self.record('P23','pass',phase=event,evidence='Killed open pointer transaction exposes no partial A/B group')
        self.helper();after=active_builds(self.conn)
        for key in ['A','B']:assert after[self.inputs.editions[key]['id']]!=before[self.inputs.editions[key]['id']]
        assert after[self.inputs.editions['C']['id']]==before[self.inputs.editions['C']['id']]
        self.record('P16','pass',correction=change,outputs=expected_products(self.conn,self.inputs),http=self.check_current(['A','B']))
    def independent_dirty_race(self):
        before=active_builds(self.conn);self.inputs.correct_C_data();child=self.driver.start(keys='C',barrier='before_activation_recheck')
        event=self.driver.wait_phase(child,'before_activation_recheck');newer=self.inputs.correct_C_data();queue=self.checkpoint()['dirty']
        self.driver.release(child);result=self.driver.finish(child,rejected=True);assert active_builds(self.conn)==before
        assert self.checkpoint()['dirty']==queue
        self.record('P26','pass',phase=event,result=result,watermarkPreserved=True)
        self.helper();after=active_builds(self.conn)
        for key in ['A','B']:assert after[self.inputs.editions[key]['id']]==before[self.inputs.editions[key]['id']]
        assert after[self.inputs.editions['C']['id']]!=before[self.inputs.editions['C']['id']]
        self.record('P17','pass',correction=newer,outputs=expected_products(self.conn,self.inputs),http=self.check_current(['C']))
    def pins_noops_and_privileges(self):
        for path,old in self.saved['bodies'].items():
            same_http(old,self.http(path))
            if old['status']==200:
                r=self.http(path,headers={'if-none-match':old['headers']['etag']});assert r['status']==304;metadata_only(r)
        self.record('P18','pass',evidence='Old manifest/page/summary/shots bodies and all stable headers unchanged')
        r=self.http('/api/fixtures?'+qs(league='l_000001',season='2024/2025',limit=2,cursor=self.saved['mutableCursor']));assert r['status']==409 and r['headers']['cache-control']=='no-store'
        r=self.http('/api/fixtures?'+qs(v=self.saved['tokens']['A'],league='l_000001',season='2024/2025',limit=2,cursor=self.saved['pinnedCursor']));assert r['status']==200
        self.record('P19','pass',evidence='Mutable stale409; frozen old cursor stays valid')
        for id in ['P20','P27']:
            before=self.checkpoint();offsets={w:len((self.run/(w+'-sql.jsonl')).read_text().splitlines()) if (self.run/(w+'-sql.jsonl')).exists() else 0 for w in ['worker1','worker2']}
            result=self.helper();assert result['status']=='noop';self.assert_unchanged_publish(before)
            for w,n in offsets.items():no_begin_generation(self.run/(w+'-sql.jsonl'),n)
            self.record(id,'pass',sequence=before['sequence'],dirtyHintsRetained=before['dirty'],beginGenerationCalls=0)
        self.record('P28','pass',actualPrivileges=self.probe_privileges(),publisherConnections='Exact writer-bound traced launcher')
    def source_audit(self):
        accesses=[]
        for p in [self.run/'api-source-access.jsonl',self.run/'worker1-access.jsonl',self.run/'worker2-access.jsonl']:
            if p.exists():accesses+=p.read_text().splitlines()
        assert not accesses,accesses;return {'requestSourceAccessCalls':0,'calibrationsSeparate':True}
    def full_future_workflow(self,runtime):
        self.test_negative_admissions();self.bootstrap_faults_and_publish();self.basic_products_and_http(runtime)
        self.correction_and_same_plan_race();self.shared_correction_and_pointer_crash();self.independent_dirty_race()
        self.pins_noops_and_privileges();self.record('P29','pass',sourceAudit=self.source_audit(),budget=self.budget.check())
    def close(self):self.driver.close();self.stop_api();[s.close() for s in self.api_streams if not s.closed]


def main():
    p=argparse.ArgumentParser();p.add_argument('--label',default='owned-pg-precode-red');p.add_argument('--pg-bin',type=Path,default=Path('/tmp/statarena-cache-test-tools/node_modules/@embedded-postgres/darwin-arm64/native/bin'));args=p.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]{0,70}',args.label):p.error('Simple label required')
    import psycopg
    clean_environment=minimal_env();os.environ.clear();os.environ.update(clean_environment)
    from orion_pro_migrate import bootstrap
    from orion_pro_integrity import role_grants_sql
    run=BASE/'runs'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-'+args.label);(run/'inputs').mkdir(parents=True)
    budget=SharedBudget(run/'budget.json',create=True);pg=BoundedPostgres(args.pg_bin,run,budget=budget);db=None;workflow=None
    source_files=[MODEL,ROOT/'dashboard/backend/migrations/012_orion_pro_domain.sql',ROOT/'dashboard/backend/migrations/013_orion_pro_integrity.sql',
      ROOT/'dashboard/backend/aws-app.js',ROOT/'dashboard/package.json',*[ROOT/'dashboard/backend/services'/n for n in SERVICE_NAMES],
      ROOT/'docs/verification/orion-pro-readers-20261104/fixture.py',ROOT/'docs/verification/orion-pro-pilot-20261104/fixtures.py',ROOT/'docs/verification/orion-pro-pilot-20261104/harness.py',
      *[ROOT/'dashboard/scripts'/n for n in ['orion_pro_migrate.py','orion_pro_integrity.py','orion_pro_schema.py']],
      *[BASE/n for n in ['E2E_WORKFLOW_PROTOCOL.md','FAILURE_MATRIX.json','publisher_workflow.py','workflow_budget.py','typed_inputs.py','publisher_driver.py','publisher_worker.py','publisher_oracles.py','publisher_http_server.mjs']]]
    if TARGET.exists():source_files.append(TARGET)
    sources={str(f.relative_to(ROOT)):sha(f) for f in source_files}
    for file in source_files:
        dest=run/'inputs'/file.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file,dest)
    report={'kind':'PRECODE_OWNED_PG18_REAL_HTTP_PUBLISHER_WORKFLOW','command':['python3',str(Path(__file__).relative_to(ROOT)),*sys.argv[1:]],
      'requiredEnvironment':'PYTHONPATH=/tmp/statarena-publication-test-python','expected':'E2E_WORKFLOW_PROTOCOL.md and frozen30-case matrix',
      'sourceSha256':sources,'remoteActions':[],'publisherImplemented':TARGET.exists(),'model107Used':False,'setupChecks':[],'workflowCases':[]}
    assert all(sources[path]==value for path,value in PINNED.items()),'Model/012/013 differ from the approved local setup'
    phase=['setup'];watchdog_stop=threading.Event()
    hard_deadline=time.monotonic()+600
    def watchdog():
        while not watchdog_stop.wait(.1):
            try:
                if time.monotonic()>hard_deadline:raise LimitExceeded('Monotonic hard deadline reached')
                budget.check()
            except Exception:
                if workflow:
                    workflow.watchdog_errors.append('Hard deadline reached')
                    for child in workflow.driver.children:
                        if child['process'].poll() is None:os.killpg(child['process'].pid,signal.SIGKILL)
                    if workflow.api and workflow.api.poll() is None:os.killpg(workflow.api.pid,signal.SIGKILL)
                if db is not None:
                    try:db.cancel_safe(timeout=1)
                    except Exception:pass
                return
    watcher=threading.Thread(target=watchdog,daemon=True);watcher.start()
    try:
        pg.start();model=json.loads(MODEL.read_text())
        Factory=connection_factory(psycopg,budget,run/'main-sql.jsonl',phase=lambda:phase[0],owned_port=pg.port,role=os.environ.get('USER','postgres'))
        db=Factory.connect(host='127.0.0.1',port=pg.port,dbname='postgres',user=os.environ.get('USER','postgres'),options=OPTIONS+' -c application_name=publisher_fixture_setup',autocommit=True)
        assert db.info.server_version==180006
        artifacts=[(v,ROOT/'dashboard/backend/migrations'/name,(ROOT/'dashboard/backend/migrations'/name).read_text()) for v,name in [('012','012_orion_pro_domain.sql'),('013','013_orion_pro_integrity.sql')]]
        with db.transaction():
            for version,file,sql in artifacts:
                db.execute(sql,prepare=False);db.execute('INSERT INTO ingest.schema_migrations(version,content_sha256,applied_at,code_commit) VALUES(%s,%s,CURRENT_TIMESTAMP,%s)',(version,sha(file),'publisher-owned-precode'))
            report['bootstrap']=bootstrap(db,model,artifacts)
            for role in ['statarena_ingest','statarena_runtime']:db.execute(f'CREATE ROLE {role} LOGIN NOSUPERUSER NOCREATEROLE NOCREATEDB NOREPLICATION NOBYPASSRLS')
            db.execute(role_grants_sql(model,ingest_role='statarena_ingest',runtime_role='statarena_runtime'),prepare=False)
        report['schemaIdentity']={'serverVersion':db.info.server_version,'journal':[list(r) for r in db.execute('SELECT version,content_sha256 FROM ingest.schema_migrations ORDER BY version').fetchall()]}
        assert report['schemaIdentity']['journal']==[[version,PINNED[str(path.relative_to(ROOT))]] for version,path,_ in artifacts]
        workflow=Workflow(run,budget,pg,db,model,psycopg);report['inputOracle']=workflow.inputs.prepare_inputs()
        phase[0]='operational';workflow.phase='operational';db.execute("SET application_name='publisher_harness_main'")
        state=workflow.checkpoint();assert len(state['counts'])==94 and not state['builds'] and not state['pointers']
        workflow.record('P01','pass',schemaTables=94,inputSetupSha256=digest(report['inputOracle']),noAnalyticalOutputs=True)
        report['admission']=workflow.inputs.admission();(run/'initial-admission.json').write_text(json.dumps(report['admission'],indent=2)+'\n')
        report['setupChecks'].append({'case':'independent_typed_inputs','status':'pass','actual':state['caps']})
        runtime,export=workflow.export_api();report['apiSourceExport']=export;report['apiIdentity']=workflow.start_api(runtime)
        report['setupChecks'].append({'case':'api_identity_source_fences','status':'pass','actual':report['apiIdentity']})
        for path in ['/api/dashboard/manifest','/api/fixtures?league=l_000001&season=2024%2F2025','/api/matches/m_000001/summary','/api/pitchapi/matches/m_000001/shots']:
            r=workflow.http(path);assert r['status']==503 and r['headers']['cache-control']=='no-store';metadata_only(r)
        r=workflow.http('/api/dashboard/manifest',method='HEAD');assert r['status']==503 and r['body']=='';metadata_only(r)
        report['setupChecks'].append({'case':'real_http_unpublished_four_paths','status':'pass','actual':{'requests':5,'status':503,'noStore':True}})
        report['deadlineProbes']=workflow.deadline_probes();report['setupChecks'].append({'case':'main_and_two_worker_deadlines','status':'pass','actual':report['deadlineProbes']})
        report['privilegeProbes']=workflow.probe_privileges();report['setupChecks'].append({'case':'actual_writer_runtime_acl','status':'pass','actual':report['privilegeProbes']})
        before=workflow.checkpoint()
        command=[sys.executable,'-I',str(TARGET),'--help'];child=subprocess.run(command,cwd=BASE,env=minimal_env(),text=True,capture_output=True,timeout=5)
        (run/'publisher-help.stdout.log').write_text(child.stdout);(run/'publisher-help.stderr.log').write_text(child.stderr)
        if not TARGET.exists():
            assert child.returncode==2 and 'No such file or directory' in child.stderr
            workflow.assert_unchanged_publish(before);workflow.record('P00','fail',expected={'exitCode':0,'usableCLI':True},actual={'exitCode':child.returncode,'targetExists':False},expectedPreCodeRed=True,command=command)
            report['prerequisiteFailure']={'id':'publisher-cli-absent','case':'P00','dependentCases':'P02–P29','detail':'One actual CLI error; no repeated calls or substitute publication'}
        else:
            assert child.returncode==0 and 'admission' in child.stdout and 'local' in child.stdout
            workflow.record('P00','pass',actual={'targetExists':True,'exitCode':child.returncode},command=command);workflow.full_future_workflow(runtime)
        report['sourceAudit']=workflow.source_audit();report['finalState']=workflow.checkpoint()
    except Exception as error:
        report['error']={'type':type(error).__name__,'message':str(error)[:4000]}
    finally:
        watchdog_stop.set();watcher.join(timeout=1)
        if workflow:workflow.close()
        if db is not None:db.close()
        report['cleanup']=pg.cleanup()
        report['cleanup'].update(apiStopped=workflow is None or workflow.api is None or workflow.api.poll() is not None,
          workersStopped=workflow is None or all(x['process'].poll() is not None for x in workflow.driver.children))
        cases=workflow.cases if workflow else {}
        for i in range(30):
            id=f'P{i:02d}'
            report['workflowCases'].append(cases.get(id,{'id':id,'status':'unverified','blockedBy':'publisher-cli-absent' if 'prerequisiteFailure' in report else 'setup-or-prior-workflow-failure'}))
        report['httpRequests']=workflow.requests if workflow else [];report['publisherInvocations']=workflow.driver.invocations if workflow else []
        report['budget']=budget.read();report['sourceChangesDuringRun']=[str(f.relative_to(ROOT)) for f in source_files if sha(f)!=sources[str(f.relative_to(ROOT))]]
        pg_statements={}
        for line in (run/'postgres.log').read_text().splitlines() if (run/'postgres.log').exists() else []:
            found=re.match(r'\[\d+\] app=(\S+) (?:LOG:  )(?:statement:|execute [^:]*:)',line)
            if found:pg_statements[found[1]]=pg_statements.get(found[1],0)+1
        actual_operational=sum(n for app,n in pg_statements.items() if app!='publisher_fixture_setup')
        report['sqlAccounting']={'reservedOperationalCalls':report['budget']['counts']['sql'],'serverLoggedOperationalStatements':actual_operational,
          'serverLoggedClientCommandsByApplication':pg_statements,'internalTransactionCommandsReserved':True}
        if actual_operational>report['budget']['counts']['sql'] or actual_operational>1500:
            report['error']={'type':'SQLAccountingError','message':'Server observed an unreserved or over-budget operational statement'}
        if workflow and workflow.watchdog_errors:report['error']={'type':'LimitExceeded','message':'; '.join(workflow.watchdog_errors)}
        report['counts']={s:sum(c['status']==s for c in report['workflowCases']) for s in ['pass','fail','unverified']}
        report['setupPassCount']=sum(c['status']=='pass' for c in report['setupChecks'])
        report['status']='pass' if report['counts']=={'pass':30,'fail':0,'unverified':0} and 'error' not in report and not report['sourceChangesDuringRun'] else 'fail'
        report['finishedAt']=datetime.now(timezone.utc).isoformat();(run/'result.json').write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps({'status':report['status'],'counts':report['counts'],'setupPassCount':report['setupPassCount'],'error':report.get('error'),'receipt':str((run/'result.json').relative_to(ROOT))}))
    return report['status']!='pass'


if __name__=='__main__':raise SystemExit(main())
