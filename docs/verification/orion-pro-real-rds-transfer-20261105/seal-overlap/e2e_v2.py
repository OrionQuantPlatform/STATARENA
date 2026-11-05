#!/usr/bin/env python3
"""Precode campaign for scoped planner tuning on fresh owned P2 metric COPY."""
from __future__ import annotations
import argparse
import ast
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

sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[3]
TRANSFER = BASE.parent
PINS = BASE / 'PINS.json'
PINS_SHA = 'd24416c4932aad289fe255126144f4353e03eb0fdf02c45e1186a764ac37c0b8'
SCOPE = BASE / 'planner_scope.py'
PROTOCOL = BASE / 'PROTOCOL.md'
MIGRATIONS = ROOT / 'dashboard/backend/migrations'
SQL = [MIGRATIONS / p for p in ('012_orion_pro_domain.sql', '013_orion_pro_integrity.sql',
                                '014_orion_pro_membership_nonnull.sql', '015_orion_pro_metric_membership_guard.sql')]
MODEL = ROOT / 'docs/architecture/orion-plan-20261104/target-schema.proposed.json'
FIXTURE = ROOT / 'tests/orion_pro_bulk_stream_local.py'
PILOT = ROOT / 'docs/verification/orion-pro-pilot-20261104'
ORACLE = ROOT / 'docs/verification/orion-validator-membership-20261105/e2e.py'
FAILED = TRANSFER / 'real-core-operation-v4-p2/apply.result.json'
RDS_READBACK = TRANSFER / 'failed-core-p2-readbacks/20261105T171021459489Z/result.json'
PG_BIN = Path('/tmp/statarena-cache-test-tools/node_modules/@embedded-postgres/darwin-arm64/native/bin')
TABLE = 'football.player_match_metric_values'
SHAPE = 'SELECT count(*),count(DISTINCT(match_id,player_id,period_code,family_code,metric_code)),bool_and(is_canonical),count(DISTINCT variant_key) FROM ' + TABLE
ROLES = {'owner': 'orion_pro_owner', 'writer': 'orion_pro_ingest', 'reader': 'orion_pro_runtime'}
CASES = ('immutable_inputs', 'candidate_available', 'separate_root_allocation', 'owned_exact_p2_tls_settings',
         'compact_default_full_seal_and_commit', 'dense_fresh_and_bloated_copy_plans', 'dense_tuned_full_seal_and_commit',
         'adjacent_history_and_exact_rejections', 'interval_truth_under_both_plans', 'native_catalogue_acl_and_cleanup')


def require(ok, message):
    if not ok:
        raise AssertionError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def hashed(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()


def save(path, data):
    Path(path).write_text(json.dumps(data, indent=2, default=str) + '\n')


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def q(value):
    require(re.fullmatch('[a-z_][a-z0-9_]*', value), 'Unsafe SQL identifier')
    return '"' + value + '"'


def metric_projection(sql):
    if not sql.startswith('INSERT INTO ' + TABLE + '('):
        return None
    matched = re.fullmatch(r'INSERT INTO football\.player_match_metric_values\(([a-z_0-9,\s]+)\)\s+(SELECT .*)', sql, re.S)
    require(matched is not None, 'Frozen metric INSERT SELECT syntax differs')
    names = tuple(col.strip() for col in matched[1].split(','))
    require(len(set(names)) == len(names), 'Frozen COPY columns are not unique')
    return names, matched[2]


def fixture_emission(model, expected_sql, evidence):
    """Run the frozen fixture to its metric-shape SELECT, executing no SQL."""
    module = load(FIXTURE, 'frozen_metric_emission_offline')
    class StopAtShape(Exception):
        pass
    class Recorder:
        def __init__(self):
            self.calls = []
            self.rolled_back = False
        def execute(self, sql, params=None):
            projection = metric_projection(sql)
            if projection:
                require(sql == expected_sql and len(params) == sql.count('%s') == 9 and
                        params[:7] == (module.VERSION, module.ESCAPED, 2, module.VERSION, module.VERSION,
                                       'a'*64, len(self.calls)*1000) and params[8] == 2,
                        'Metric fixture did not emit the exact SQL/bound arguments')
                self.calls.append(params)
                return None
            if sql == SHAPE:
                raise StopAtShape()
            if sql.startswith('SELECT ingest.begin_generation('):
                return types.SimpleNamespace(fetchone=lambda: (2,))
            if sql.endswith('RETURNING *'):
                cols = sql.split(' (',1)[1].split(')',1)[0].replace('"','').split(',')
                require(len(cols) == len(params), 'Unexpected frozen fixture INSERT metadata')
                vals = tuple(params)
                if 'revision_id' not in cols:
                    cols.append('revision_id'); vals += (1,)
                return types.SimpleNamespace(description=[types.SimpleNamespace(name=k) for k in cols],
                                             fetchone=lambda: vals)
            return None
        def rollback(self):
            self.rolled_back = True
    compact = types.FunctionType(module.fixture.__code__,{**module.fixture.__globals__,
                                'APPEARANCES':40,'SCALARS':1240,'MATCHES':4,'PLAYERS':40})
    results = []
    for label, rows, fn in [('compact',1240,compact),('dense',478547,module.fixture)]:
        recorder = Recorder()
        try:
            fn(recorder,model,'a'*64,evidence)
        except StopAtShape:
            pass
        else:
            raise AssertionError('Frozen emission did not reach the metric shape gate')
        require(recorder.rolled_back and len(recorder.calls)==(rows+999)//1000 and
                all(values[7]==min(values[6]+999,rows-1) for values in recorder.calls),
                'Frozen fixture metric windows do not cover exact shape')
        results.append({'shape':label,'calls':len(recorder.calls),'rows':rows,
                        'allBoundArgumentsSha256':hashed(recorder.calls),'databaseCalls':0})
    return results


def exact_predicates():
    lines = SQL[-1].read_text().splitlines()
    require(sum('RAISE EXCEPTION' in row for row in lines) == 264, 'Original validator assertion count differs')
    result = []
    for no, variant in ((155, 'variant'), (156, 'canonical')):
        body, message = lines[no - 1].split(" THEN RAISE EXCEPTION USING ERRCODE='23514', MESSAGE=", 1)
        require(body.startswith('IF EXISTS (SELECT 1 FROM "football"."player_match_metric_values" a JOIN ') and
                ('_sv_' + variant + '_current_idx') in message, 'Exact native overlap lines differ')
        result.append({'name': variant, 'line': no, 'sql': 'SELECT ' + body[3:]})
    context = json.loads(FAILED.read_text())['child']['postCopyNativeTimeout']
    require(hashlib.sha256(context['context'].encode()).hexdigest() == context['sha256'] and
            context['context'].splitlines()[0] == 'PL/pgSQL expression "' + result[0]['sql'][7:] + '"' and
            'line 153 at IF' in context['context'], 'Captured real failing clause differs')
    return result


class Campaign:
    def __init__(self, args):
        self.args = args
        self.started = time.monotonic()
        self.deadline = self.started + 600
        self.stop_reason = None
        self.cleaning = False
        self.cleanup_deadline = None
        self.clients = []
        self.pg = self.driver = self.fixture = self.oracle = self.scope = self.monitor = None
        self.done = threading.Event()
        self.owners, self.writers, self.structure, self.native, self.sequence = {}, {}, {}, {}, {}
        self.run = BASE / 'runs' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        (self.run / 'inputs').mkdir(parents=True)
        self.report = {'kind': 'owned_fresh_copy_p2_overlap_e2e_v2', 'command': [sys.executable, *sys.argv],
                       'expected': str(PROTOCOL), 'cases': [], 'inputSha256': {}, 'commands': [], 'resources': [],
                       'pgStarts': 0, 'fixtureDatabases': 0, 'fixtureConstructions': 0, 'maximumOpenConnections': 0,
                       'analyzeCommands': 0, 'manualVacuumCommands': 0, 'sourceReads': 0, 'ramGets': 0,
                       'rdsCalls': 0, 'providerCalls': 0, 'fullAcceptance': False}
        self.env = {k: v for k, v in os.environ.items() if k in {'PATH','HOME','USER','TMPDIR','LANG'}}
        self.env.update(PYTHONDONTWRITEBYTECODE='1', PYTHONPATH='/tmp/statarena-publication-test-python')

    def tick(self):
        require(self.cleaning or (self.stop_reason is None and time.monotonic() < self.deadline),
                self.stop_reason or '600-second campaign deadline')

    def preserve(self, path):
        path = Path(path).resolve()
        dst = self.run / 'inputs' / path.relative_to(ROOT)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dst)
        self.report['inputSha256'][str(path.relative_to(ROOT))] = sha(path)

    def command(self, argv, *, env=None, check=True, name='command'):
        self.tick()
        from orion_e2e_process import run_bounded
        cmd = [str(v) for v in argv]
        result = run_bounded(cmd, cwd=ROOT, env=self.env if env is None else env,
                             deadline=self.cleanup_deadline if self.cleaning else self.deadline,
                             stop_reason=lambda: None if self.cleaning else self.stop_reason, output_limit=2 * 1024 ** 2)
        label = f'{len(self.report["commands"]):03d}-{name}'
        (self.run / (label + '.stdout.log')).write_text(result.stdout)
        (self.run / (label + '.stderr.log')).write_text(result.stderr)
        self.report['commands'].append({'command': cmd, 'exitCode': result.returncode, 'stdout': label + '.stdout.log',
                                        'stderr': label + '.stderr.log'})
        require(not check or result.returncode == 0, name + ': ' + result.stderr[-900:])
        return result

    def watchdog(self):
        from orion_e2e_process import run_bounded
        while not self.done.wait(1):
            try:
                result = run_bounded(['du','-sk',str(self.pg.root)], deadline=min(self.deadline,time.monotonic()+4),
                                     output_limit=4096)
                disk = int(result.stdout.split()[0])*1024
                proof = sum(p.stat().st_size for p in self.run.rglob('*') if p.is_file())
                self.report['resources'].append({'seconds': round(time.monotonic()-self.started,3),
                                                 'ownedBytes': disk, 'proofBytes': proof})
                if disk >= 3*1024**3 or proof >= 96*1024**2:
                    self.stop_reason = 'Owned disk or proof size cap'
                    os.kill(os.getpid(),signal.SIGALRM)
                    return
            except BaseException as error:
                if not self.done.is_set():
                    self.stop_reason = 'Resource monitor ' + type(error).__name__
                    os.kill(os.getpid(),signal.SIGALRM)
                return

    def frozen(self):
        self.preserve(Path(__file__))
        self.preserve(PINS)
        require(sha(PINS) == PINS_SHA and not sys.flags.optimize, 'Exact pins and enabled checks required')
        self.pins = json.loads(PINS.read_text())
        require(self.pins['kind'] == 'owned_metric_overlap_planner_runtime_pins_v1', 'Unknown pin contract')
        for rel, digest in self.pins['files'].items():
            path = ROOT / rel
            require(sha(path) == digest, 'Frozen input drift: ' + rel)
            self.preserve(path)
        self.predicates = exact_predicates()
        self.model = json.loads(MODEL.read_text())
        self.tables = {t['qualified_name']: t for s in self.model['schemas'] for t in s['tables'] if t['phase'] != 'models'}
        statements = [n.value for n in ast.walk(ast.parse(FIXTURE.read_text())) if isinstance(n, ast.Constant) and
                      isinstance(n.value, str) and n.value.startswith('INSERT INTO ' + TABLE + '(')]
        require(len(statements) == 1, 'Expected one frozen metric batch SQL template')
        self.fixture_metric_template = statements[0]
        names, _ = metric_projection(self.fixture_metric_template)
        require('transform_code_sha256' in names and set(names) <= set(self.tables[TABLE]['columns']),
                'Metric fixture columns differ from the frozen typed schema')
        self.settings = json.loads(RDS_READBACK.read_text())['plannerSettings']
        require(len(self.tables) == 94 and len(self.settings) == 14, 'Closed active model or planner settings differ')
        emission = fixture_emission(self.model,self.fixture_metric_template,self.run)
        return {'nativeChecksUnchanged': 264, 'capturedClause': self.predicates[0], 'realPlannerSettings': self.settings,
                'pinsSha256': PINS_SHA, 'fixtureMetricColumnCount': len(names),
                'fixtureMetricSqlSha256': hashlib.sha256(self.fixture_metric_template.encode()).hexdigest(),
                'exactFixtureEmission':emission}

    def candidate(self):
        require(SCOPE.is_file(), 'Scoped planner candidate absent (expected precode RED)')
        self.preserve(SCOPE)
        self.scope = load(SCOPE, 'owned_overlap_planner_scope')
        require(self.scope.CHANGE == 'SET LOCAL enable_nestloop=off', 'Only one reviewed local planner setting allowed')
        return {'candidateSha256': sha(SCOPE), 'setting': self.scope.CHANGE}

    def allocate(self):
        args = self.args
        require(not any(k.startswith('PG') for k in os.environ), 'Inherited libpq settings refused')
        require(args.release and args.release.is_absolute() and args.release.parent == BASE and
                sha(args.release) == args.release_sha256, 'Exact absolute separate ROOT release required')
        self.preserve(args.release)
        release = json.loads(args.release.read_text())
        expected = {'kind': 'root_owned_fresh_p2_overlap_planner_v2', 'approvedBy': 'ROOT', 'e2eSha256': sha(__file__),
                    'candidateSha256': sha(SCOPE), 'protocolSha256': sha(PROTOCOL), 'pinsSha256': PINS_SHA,
                    'maximumPgStarts': 1, 'maximumDatabaseConstructions': 2, 'maximumConnections': 5,
                    'maximumSeconds': 600, 'maximumOwnedBytes': 3*1024**3, 'maximumProofBytes': 96*1024**2,
                    'maximumDenseMetricCopyRows': 2*478547, 'sourceCalls': 0, 'rdsCalls': 0}
        require(set(release) == set(expected) | {'allocationId'} and all(release[k] == v for k,v in expected.items()) and
                re.fullmatch('[A-Za-z0-9-]+', release['allocationId']), 'Exact allocation scope or code differs')
        ledger = BASE / (release['allocationId'] + '.consumed.json')
        with ledger.open('x') as file:
            json.dump({'run': str(self.run), 'releaseSha256': args.release_sha256, 'state': 'consumed'}, file, indent=2)
            file.write('\n')
        def alarm(signum, frame):
            raise TimeoutError(self.stop_reason or 'Owned local active deadline')
        signal.signal(signal.SIGALRM, alarm)
        signal.setitimer(signal.ITIMER_REAL, max(.001,self.deadline-time.monotonic()))
        return expected

    def connect(self, db, role):
        self.tick()
        require(sum(not c.closed for c in self.clients) < 5, 'Five-client cap')
        conn = self.driver.connect(host='127.0.0.1',hostaddr='127.0.0.1',port=self.pg.port,dbname=db,user=role,
                                   password='',passfile='/dev/null',sslmode='verify-full',sslrootcert=str(self.pg.data/'server.crt'),
                                   autocommit=True,connect_timeout=5,
                                   options='-c statement_timeout=8000 -c lock_timeout=1000 -c timezone=UTC '
                                           '-c datestyle=ISO,YMD -c extra_float_digits=3 -c search_path=pg_catalog')
        self.clients.append(conn)
        self.report['maximumOpenConnections'] = max(self.report['maximumOpenConnections'], sum(not c.closed for c in self.clients))
        return conn

    def setup(self):
        import psycopg
        from harness import LocalPostgres
        from orion_pro_migrate import bootstrap
        from orion_pro_integrity import role_grants_sql
        from orion_pro_bulk_local import sequences
        self.driver = psycopg
        self.fixture = load(FIXTURE, 'frozen_dense_overlap_fixture')
        self.oracle = load(ORACLE, 'frozen_overlap_independent_oracle')
        tempfile.tempdir = '/tmp'
        self.pg = LocalPostgres(PG_BIN, self.run)
        self.pg.command = self.command
        self.command([PG_BIN/'initdb','-D',self.pg.data,'--auth=trust','--no-locale','--encoding=UTF8'],name='initdb')
        self.command(['openssl','req','-x509','-newkey','rsa:2048','-sha256','-nodes','-days','2',
                      '-keyout',self.pg.data/'server.key','-out',self.pg.data/'server.crt',
                      '-subj','/CN=127.0.0.1','-addext','subjectAltName=IP:127.0.0.1'],name='tls')
        (self.pg.data/'server.key').chmod(0o600)
        with (self.pg.data/'postgresql.conf').open('a') as cfg:
            cfg.write("\nssl=on\nssl_cert_file='server.crt'\nssl_key_file='server.key'\nstatement_timeout=8000\n"
                      "lock_timeout=1000\nautovacuum_naptime='1h'\ntemp_file_limit='256MB'\n"
                      "log_error_verbosity=terse\nlog_min_error_statement=panic\nlog_parameter_max_length_on_error=0\n")
            for name, value in sorted(self.settings.items()):
                require(re.fullmatch('[a-z_]+',name) and re.fullmatch('[0-9.]+|on|off',value['setting']), 'Unrecognized planning config')
                cfg.write(name + '=' + value['setting'] + '\n')
        self.report['pgStarts'] = 1
        self.pg.start()
        self.monitor = threading.Thread(target=self.watchdog, daemon=True)
        self.monitor.start()
        admin = self.connect('postgres',os.environ.get('USER','postgres'))
        require(admin.info.server_version == 180006, 'Exact PG18.6 required')
        for role in ROLES.values():
            admin.execute('CREATE ROLE '+q(role)+' LOGIN NOSUPERUSER NOCREATEROLE NOCREATEDB NOREPLICATION NOBYPASSRLS')
        for db in ('overlap_compact','overlap_dense'):
            admin.execute('CREATE DATABASE '+q(db)+' OWNER '+q(ROLES['owner']))
            self.report['fixtureDatabases'] += 1
            owner = self.owners[db] = self.connect(db,ROLES['owner'])
            with owner.transaction():
                artifacts = []
                for version, path in zip(('012','013'),SQL[:2]):
                    text = path.read_text()
                    owner.execute(text, prepare=False)
                    artifacts.append((version,path,text))
                    owner.execute('INSERT INTO ingest.schema_migrations VALUES(%s,%s,CURRENT_TIMESTAMP,%s)',
                                  (version,sha(path),'owned_overlap_setup'))
                bootstrap(owner,self.model,artifacts)
                owner.execute(role_grants_sql(self.model,ROLES['writer'],ROLES['reader']),prepare=False)
                for version,path in zip(('014','015'),SQL[2:]):
                    owner.execute(path.read_text(),prepare=False)
                    owner.execute('INSERT INTO ingest.schema_migrations VALUES(%s,%s,CURRENT_TIMESTAMP,%s)',
                                  (version,sha(path),'owned_overlap_setup'))
            self.structure[db] = self.protected(owner)
            self.sequence[db] = sequences(owner)
            self.native[db] = self.oracle.oracle(owner,self.tables,self.report)
            require(len(self.sequence[db]) == 67 and len(self.native[db]) == 94,'Native bootstrap shape differs')
            writer = self.writers[db] = self.connect(db,ROLES['writer'])
            ids = writer.execute("SELECT current_user,(SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()),"
                                 "current_setting('statement_timeout'),current_setting('lock_timeout'),rolsuper,rolcreaterole,"
                                 "rolcreatedb,rolreplication,rolbypassrls FROM pg_roles WHERE rolname=current_user").fetchone()
            require(ids == (ROLES['writer'],True,'8s','1s',False,False,False,False,False), 'Ordinary TLS actor differs')
            got = {n:{'setting':s,'unit':u} for n,s,u in writer.execute('SELECT name,setting,unit FROM pg_settings WHERE name=ANY(%s)',(list(self.settings),))}
            require(got == self.settings,'Owned planner settings differ from actual RDS readback')
        admin.close()
        save(self.run/'owned-initial-protected.json',self.structure)
        return {'databases': 2, 'pg': 180006, 'settingsExact': True, 'nativeTables': 94, 'sequenceRows': 67}

    def protected(self, conn):
        definition = conn.execute("SELECT pg_get_functiondef('ingest.validate_generation(bigint)'::regprocedure)").fetchone()[0]
        require(hashlib.sha256(definition.encode()).hexdigest() == 'b5ad69e06b59adba7476eb96fbf834caa13492820dce8e3cb99d482bf386613e',
                'Owned schema must retain exact 015 validator')
        rows = list(conn.execute('SELECT version,content_sha256,applied_at::text,code_commit FROM ingest.schema_migrations ORDER BY version'))
        require([r[:2] for r in rows] == [(v,sha(p)) for v,p in zip(('012','013','014','015'),SQL)],
                'Exact 012..015 journal required')
        deferred = conn.execute("SELECT tgenabled,tgdeferrable,tginitdeferred FROM pg_trigger WHERE tgrelid="
                                "'ingest.dataset_snapshots'::regclass AND tgname='pro_generation_commit'").fetchone()
        require(deferred == ('O',True,True), 'Actual deferred constraint trigger must remain enabled')
        return {'validatorSha256': hashlib.sha256(definition.encode()).hexdigest(),
                'properties': self.oracle.function_properties(conn), 'structure': self.oracle.structure(conn),
                'journal': rows, 'deferred': deferred}

    def copy_batches(self, conn, batches):
        require(conn.execute("SELECT current_setting('enable_nestloop')").fetchone()[0]=='on',
                'Regular COPY inherited a native admission setting')
        count = peak = wire_bytes = 0
        digest = hashlib.sha256()
        for columns, select, params in batches:
            self.tick()
            payload = bytearray()
            with conn.cursor().copy('COPY ('+select+') TO STDOUT',params) as stream:
                for piece in stream:
                    require(len(payload)+len(piece) <= 1024**2,'Native metric COPY block exceeds1MiB')
                    payload.extend(piece)
            rows = payload.count(b'\n')
            require(0 < rows <= 1000, 'Exact bounded COPY row window')
            digest.update(str(len(payload)).encode()+b':')
            digest.update(payload)
            digest.update(b'\n')
            with conn.cursor().copy('COPY '+TABLE+' ('+columns+') FROM STDIN') as stream:
                stream.write(payload)
            count += rows
            wire_bytes += len(payload)
            peak = max(peak,len(payload))
        return {'rows':count,'commands':len(batches),'wireBytes':wire_bytes,'wireSha256':digest.hexdigest(),
                'largestBlockBytes':peak}

    def cold(self, conn):
        result = conn.execute("SELECT c.relpages,c.reltuples,s.analyze_count,s.autoanalyze_count,s.vacuum_count,s.autovacuum_count,"
                              "pg_relation_size(c.oid),pg_indexes_size(c.oid),pg_total_relation_size(c.oid) "
                              "FROM pg_class c JOIN pg_stat_all_tables s ON s.relid=c.oid WHERE c.oid=%s::regclass",(TABLE,)).fetchone()
        require(result[2:6] == (0,0,0,0) and result[1] <= 0,'Fresh uncommitted COPY acquired catalogue statistics')
        return dict(zip(('relpages','reltuples','analyzeCount','autoAnalyzeCount','vacuumCount','autoVacuumCount',
                         'heapBytes','indexesBytes','totalBytes'),result))

    def plans(self, conn, label, g):
        plans = []
        for mode in ('default','no_nestloop'):
            for pred in self.predicates:
                self.tick()
                sql = re.sub(r'\bg\b','%(g)s::bigint',pred['sql'])
                conn.execute('SAVEPOINT overlap_explain')
                try:
                    if mode == 'no_nestloop':
                        self.scope.activate(conn)
                    params = {'g':g}
                    estimate_sql = 'EXPLAIN (SETTINGS,FORMAT JSON) '+sql
                    observed_sql = 'EXPLAIN (ANALYZE,BUFFERS,SETTINGS,FORMAT JSON) '+sql
                    entry = {'shape':label,'mode':mode,'variant':pred['name'],'generation':g,'estimateSql':estimate_sql,
                             'observedSql':observed_sql,'estimate':conn.execute(estimate_sql,params,prepare=False).fetchone()[0]}
                    start = time.monotonic()
                    try:
                        entry['observed'] = conn.execute(observed_sql,params,prepare=False).fetchone()[0]
                        entry['status'] = 'observed'
                    except self.driver.Error as error:
                        entry.update(status='timeout',sqlstate=error.sqlstate)
                        require(error.sqlstate == '57014', 'Unexpected SQLSTATE in exact overlap diagnostic')
                    finally:
                        entry['elapsedMs'] = round((time.monotonic()-start)*1000,3)
                        plans.append(entry)
                        save(self.run/('plans-'+label+'.json'),plans)
                    require(mode != 'no_nestloop' or entry['status']=='observed','Tuned exact overlap diagnostic exceeded8s')
                finally:
                    conn.execute('ROLLBACK TO SAVEPOINT overlap_explain')
                    conn.execute('RELEASE SAVEPOINT overlap_explain')
                require(conn.execute("SELECT current_setting('enable_nestloop')").fetchone()[0]=='on',
                        'Planner scope escaped diagnostic savepoint')
        return plans

    def build_fixture(self, db, dense):
        conn = self.writers[db]
        outer = self
        class Probe:
            def __init__(self):
                self.batches, self.seals, self.commits = [], [], []
                self.copy_trials = []
            def __getattr__(self,name):
                return getattr(conn,name)
            def execute(self,sql,params=None,**kwargs):
                outer.tick()
                projection = metric_projection(sql)
                if projection:
                    require(sql == outer.fixture_metric_template, 'Unexpected metric INSERT template')
                    columns=','.join(map(q,projection[0]))
                    self.batches.append((columns,projection[1],params))
                    return None
                if sql == SHAPE:
                    require(self.batches and not self.copy_trials,'Frozen metric fixture batching changed')
                    if dense:
                        g=conn.execute("SELECT generation FROM ingest.dataset_snapshots WHERE status='draft'").fetchone()[0]
                        conn.execute('SAVEPOINT prior_aborted_copy')
                        try:
                            first=outer.copy_batches(conn,self.batches)
                            first.update(shape='fresh',catalogue=outer.cold(conn))
                            require(first['rows']==478547,'First dense metric copy incomplete')
                            self.copy_trials.append(first)
                            save(outer.run/'dense-copy-trials.json',self.copy_trials)
                            outer.plans(conn,'fresh',g)
                        finally:
                            conn.execute('ROLLBACK TO SAVEPOINT prior_aborted_copy')
                            conn.execute('RELEASE SAVEPOINT prior_aborted_copy')
                        require(conn.execute('SELECT count(*) FROM '+TABLE).fetchone()[0]==0,'Aborted trial left visible metric rows')
                        first['afterRollbackCatalogue']=outer.cold(conn)
                    final=outer.copy_batches(conn,self.batches)
                    final.update(shape='prior_aborted_copy' if dense else 'compact',catalogue=outer.cold(conn))
                    if dense:
                        require(final['rows']==478547 and self.copy_trials[0]['wireSha256']==final['wireSha256'],
                                'Repeated fresh COPY payload differs')
                        final['physicalBytesAddedVsFirstTrial']=final['catalogue']['totalBytes']-first['catalogue']['totalBytes']
                    else:require(final['rows']==1240,'Compact metric copy count differs')
                    self.copy_trials.append(final)
                    save(outer.run/(db+'-copy-trials.json'),self.copy_trials)
                    if dense:outer.plans(conn,'prior_aborted_copy',g)
                if sql.startswith('SELECT ingest.seal_generation'):
                    require(conn.execute("SELECT current_setting('enable_nestloop')").fetchone()[0]=='on','Before-seal scope drift')
                    if dense:outer.scope.activate(conn)
                    start=time.monotonic()
                    result=conn.execute(sql,params,prepare=False)
                    ms=round((time.monotonic()-start)*1000,3)
                    require(ms<8000,'Actual full validator seal exceeded8s')
                    self.seals.append({'generation':params[0],'elapsedMs':ms})
                    return result
                return conn.execute(sql,params,**kwargs)
            def commit(self):
                expected='off' if dense else 'on'
                require(conn.execute("SELECT current_setting('enable_nestloop')").fetchone()[0]==expected,'Deferred commit planner scope differs')
                start=time.monotonic()
                conn.commit()
                ms=round((time.monotonic()-start)*1000,3)
                require(ms<8000 and conn.execute("SELECT current_setting('enable_nestloop')").fetchone()[0]=='on',
                        'Actual deferred commit exceeded8s or leaked planner setting')
                self.commits.append({'elapsedMs':ms})
        probe=Probe()
        output=self.run/db;output.mkdir()
        fixture=self.fixture.fixture
        if not dense:
            fixture=types.FunctionType(fixture.__code__,{**fixture.__globals__,'APPEARANCES':40,'SCALARS':1240,'MATCHES':4,'PLAYERS':40})
        phases=fixture(probe,self.model,hashed({'fixture':sha(FIXTURE),'campaign':sha(__file__)}),output)
        self.report['fixtureConstructions'] += 1
        require(len(phases)==len(probe.seals)==len(probe.commits)==2,'Actual core/family native seals and deferred commits required')
        facts=conn.execute('SELECT (SELECT count(*) FROM '+TABLE+'),(SELECT count(*) FROM football.match_players),'
                           '(SELECT count(*) FROM football.matches)').fetchone()
        require(facts==((478547,15437,612) if dense else (1240,40,4)),'Exact fixture native shape differs')
        result={'copyTrials':probe.copy_trials,'seal':probe.seals,'deferredCommit':probe.commits,'phases':phases,
                'metricRows':facts[0],'appearances':facts[1],'matches':facts[2]}
        save(self.run/(db+'-initial-native.json'),result)
        return result

    def history(self, db, modes):
        self.writers[db].close()
        out = []
        for mode in modes:
            c = self.connect(db,ROLES['writer'])
            for case in ('noop_successor','unselected_parent','valid_adjacent_correction'):
                self.tick()
                c.execute('BEGIN')
                start = None
                try:
                    g = c.execute('SELECT ingest.begin_generation(%s,%s,%s)',(f'overlap-e2e:{db}:{mode}:{case}',
                                  'owned_overlap_e2e','owned_overlap_e2e')).fetchone()[0]
                    old = c.execute('SELECT revision_id,match_player_revision_id,numeric_value FROM '+TABLE+
                                    " WHERE metric_code='m05' AND recorded_to_gen IS NULL ORDER BY revision_id LIMIT 1").fetchone()
                    require(old is not None,'Fixture correction witness missing')
                    if case == 'unselected_parent':
                        require(c.execute('UPDATE football.match_players SET recorded_to_gen=%s WHERE revision_id=%s',(g,old[1])).rowcount==1,
                                'Exact parent closure missing')
                    else:
                        require(c.execute('UPDATE '+TABLE+' SET recorded_to_gen=%s WHERE revision_id=%s',(g,old[0])).rowcount==1,
                                'Exact metric predecessor closure missing')
                        cols=[k for k,v in self.tables[TABLE]['columns'].items() if not v.get('identity')]
                        substitutions={'recorded_from_gen':'%s::bigint','recorded_to_gen':'NULL::bigint'}
                        if case=='valid_adjacent_correction':substitutions['numeric_value']='old.numeric_value+1'
                        new=c.execute('INSERT INTO '+TABLE+' ('+','.join(map(q,cols))+') SELECT '+
                                      ','.join(substitutions.get(k,'old.'+q(k)) for k in cols)+' FROM '+TABLE+
                                      ' old WHERE old.revision_id=%s RETURNING revision_id,numeric_value',(g,old[0])).fetchone()
                    if mode=='no_nestloop':self.scope.activate(c)
                    start=time.monotonic()
                    c.execute('SELECT ingest.seal_generation(%s,%s)',(g,hashed([db,mode,case])),prepare=False)
                    seal=round((time.monotonic()-start)*1000,3)
                    require(case=='valid_adjacent_correction','A deliberately invalid native scenario was sealed')
                    t=time.monotonic();c.commit();commit=round((time.monotonic()-t)*1000,3)
                    require(max(seal,commit)<8000,'Historical seal/deferred commit exceeded8s')
                    observed=list(c.execute('SELECT revision_id,numeric_value,recorded_from_gen,recorded_to_gen FROM '+TABLE+
                                            ' WHERE revision_id=ANY(%s) ORDER BY revision_id',([old[0],new[0]],)))
                    require(len(observed)==2 and observed[0][0:2]==(old[0],old[2]) and observed[0][3]==g and
                            observed[1]==(new[0],old[2]+1,g,None),'Historical adjacency/native values differ')
                    out.append({'mode':mode,'case':case,'status':'committed','sealMs':seal,'deferredCommitMs':commit})
                except self.driver.Error as error:
                    c.rollback()
                    message=error.diag.message_primary
                    expected='Identical typed reimport must reuse the retained version: football.player_match_metric_values' \
                        if case=='noop_successor' else 'Selected parent membership differs'
                    require(case!='valid_adjacent_correction' and error.sqlstate=='23514' and expected.lower() in message.lower(),
                            'Unexpected native history SQLSTATE/reason: '+str(error.sqlstate)+' '+str(message))
                    require(c.execute('SELECT count(*) FROM ingest.dataset_snapshots WHERE generation=%s',(g,)).fetchone()[0]==0,
                            'Rejected native snapshot persisted')
                    out.append({'mode':mode,'case':case,'status':'rolled_back','sqlstate':error.sqlstate,'message':message,
                                'sealMs':round((time.monotonic()-start)*1000,3) if start else None})
                except BaseException:
                    c.rollback()
                    raise
                require(c.execute("SELECT current_setting('enable_nestloop')").fetchone()[0]=='on','Historical scope leaked')
                save(self.run/(db+'-history.json'),out)
            c.close()
        if len(modes)==2:
            def signatures(items):return [(r['case'],r['status'],r.get('sqlstate'),r.get('message')) for r in items]
            require(signatures(out[:3])==signatures(out[3:]),'Default and candidate native outcomes differ')
        return out

    def interval_truth(self):
        c=self.connect('overlap_compact',ROLES['writer'])
        witnesses={
            'open_separate_variants': ([(1,5,None,'a',True),(2,5,None,'b',False)],(False,False)),
            'adjacent_half_open': ([(1,1,5,'a',True),(2,5,None,'a',True)],(False,False)),
            'closed_overlap': ([(1,1,7,'a',True),(2,5,None,'a',True)],(True,True)),
            'untouched_overlap': ([(1,1,7,'a',True),(2,2,8,'a',True)],(False,False)),
            'cross_variant_canonical': ([(1,1,7,'a',True),(2,5,None,'b',True)],(False,True)),
            'same_variant_noncanonical': ([(1,1,7,'a',False),(2,5,None,'a',True)],(True,False)),
        }
        out=[]
        for mode in ('default','no_nestloop'):
            with c.transaction():
                if mode=='no_nestloop':self.scope.activate(c)
                for label,(rows,expected) in witnesses.items():
                    base="WITH t(revision_id,recorded_from_gen,recorded_to_gen,variant_key,is_canonical,match_id,player_id,period_code,family_code,metric_code,numeric_value) AS (VALUES "
                    fmt="(%s::bigint,%s::bigint,%s::bigint,%s::text,%s::boolean,1::bigint,2::bigint,'full_match','standard','m05',NULL::numeric)"
                    base+=','.join(fmt for _ in rows)+') '
                    sql=[base+re.sub(r'\bg\b','5::bigint',p['sql']).replace('"football"."player_match_metric_values"','t') for p in self.predicates]
                    params=[v for row in rows for v in row]
                    actual=tuple(c.execute(stmt,params,prepare=False).fetchone()[0] for stmt in sql)
                    require(actual==expected,'Literal historical truth differs: '+label)
                    out.append({'mode':mode,'case':label,'expected':expected,'actual':actual,'queries':sql,'technicalParams':params})
        c.close()
        save(self.run/'interval-truth.json',out)
        return {'witnesses':len(out),'matchedExactOverlapQueries':True}

    def final_native(self):
        from orion_pro_bulk_local import sequences
        for db, c in self.owners.items():
            require(self.protected(c)==self.structure[db],'Native catalogue/validator/ACL or original journal drift')
            actual=self.oracle.oracle(c,self.tables,self.report)
            seq=sequences(c)
            require(len(actual)==94 and len(seq)==67,'Final native shape differs')
            require(actual['ingest.schema_migrations']==self.native[db]['ingest.schema_migrations'],'Native journal changed')
            save(self.run/(db+'-native94.json'),actual)
            save(self.run/(db+'-sequence67.json'),{'before':self.sequence[db],'after':seq})
        runtime=self.connect('overlap_dense',ROLES['reader'])
        errors=[]
        for sql in ("SELECT ingest.begin_generation('denied','x','x')","SELECT ingest.seal_generation(1,repeat('0',64))",
                    "SELECT ingest.validate_generation(1)","SELECT nextval('ingest.commit_generation_seq')",
                    "SELECT last_value FROM football.player_match_metric_values_revision_id_seq"):
            try:
                runtime.execute(sql)
            except self.driver.Error as error:
                require(error.sqlstate=='42501','Runtime denied for wrong reason')
                errors.append({'sql':sql,'sqlstate':error.sqlstate})
            else:raise AssertionError('Runtime unexpectedly allowed protected operation')
        runtime.close()
        return {'nativeTables':94,'sequences':67,'ordinaryRuntimeDenials':errors,'functionAndSchemaExact':True}

    def cleanup(self, failed):
        self.cleaning = True
        self.cleanup_deadline = time.monotonic()+15
        signal.setitimer(signal.ITIMER_REAL,0)
        self.done.set()
        if self.monitor:self.monitor.join(5)
        for c in self.clients:c.close()
        self.report['clientsClosed']=all(c.closed for c in self.clients)
        if self.pg:
            if (self.pg.data/'postmaster.pid').exists():self.pg.started=True
            self.pg.stop()
            if not failed:shutil.rmtree(self.pg.root)
            self.report['cleanup']={'serverStopped':not(self.pg.data/'postmaster.pid').exists(),
                                    'ownedRoot':str(self.pg.root),'ownedRootRemoved':not self.pg.root.exists(),
                                    'retainedForFailureInspection':failed,'realCorpusTouched':False}
        else:self.report['cleanup']={'serverStarted':False,'ownedRootCreated':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__,allow_abbrev=False)
    modes=parser.add_mutually_exclusive_group();modes.add_argument('--check-only',action='store_true');modes.add_argument('--run-local',action='store_true')
    parser.add_argument('--release',type=Path);parser.add_argument('--release-sha256')
    args=parser.parse_args()
    sys.path[:0]=[str(ROOT/'tests'),str(PILOT),str(ROOT/'dashboard/scripts'),'/tmp/statarena-publication-test-python']
    c=Campaign(args)
    blocked=None;dense=None
    steps=(c.frozen,c.candidate,c.allocate,c.setup,lambda:c.build_fixture('overlap_compact',False),
           lambda:c.build_fixture('overlap_dense',True),lambda:{k:dense[k] for k in ('seal','deferredCommit','metricRows')},
           lambda:{'compact':c.history('overlap_compact',('default','no_nestloop')),
                   'dense':c.history('overlap_dense',('no_nestloop',))},c.interval_truth,c.final_native)
    try:
        for i,(name,step) in enumerate(zip(CASES,steps)):
            if blocked or (not args.run_local and i>1):
                c.report['cases'].append({'case':name,'status':'unverified','reason':blocked or 'Owned run not released'})
                continue
            try:
                actual=step()
                if i==5:dense=actual
                c.report['cases'].append({'case':name,'status':'pass','actual':actual})
                print('PASS '+name,flush=True)
            except BaseException as error:
                blocked=name;diag=getattr(error,'diag',None)
                c.report['cases'].append({'case':name,'status':'fail','errorType':type(error).__name__,
                    'error':diag.message_primary if diag else str(error),'sqlstate':getattr(error,'sqlstate',None),
                    'nativeContext':diag.context if diag else None,'traceback':traceback.format_exc()})
                print('FAIL '+name,flush=True)
            save(c.run/'progress.json',c.report)
    finally:
        try:c.cleanup(blocked is not None)
        except BaseException as error:
            blocked=blocked or 'cleanup';c.report['cleanup']={'errorType':type(error).__name__,'error':str(error)}
        c.report['inputHashesExact']=all(sha(ROOT/p)==h for p,h in c.report['inputSha256'].items())
        blocked=blocked or (None if c.report['inputHashesExact'] else 'input drift')
        c.report['elapsedSeconds']=round(time.monotonic()-c.started,3)
        c.report['counts']={s:sum(x['status']==s for x in c.report['cases']) for s in ('pass','fail','unverified')}
        c.report['status']='fail' if blocked else 'pass_owned_local_only' if args.run_local else 'source_free_preflight_only'
        save(c.run/'result.json',c.report)
        print(json.dumps({'status':c.report['status'],'counts':c.report['counts'],'evidence':str(c.run/'result.json')}))
    return 1 if blocked else 0


if __name__=='__main__':
    raise SystemExit(main())
