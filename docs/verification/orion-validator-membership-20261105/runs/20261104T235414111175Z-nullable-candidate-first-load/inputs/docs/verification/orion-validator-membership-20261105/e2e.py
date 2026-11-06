#!/usr/bin/env python3
"""Pre-code native validator equivalence/capacity E2E. No source/cloud client."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
import _thread
import time
import traceback
import types

sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
PILOT = ROOT / 'docs/verification/orion-pro-pilot-20261104'
SCRIPTS = ROOT / 'dashboard/scripts'
MODEL = ROOT / 'docs/architecture/orion-plan-20261104/target-schema.proposed.json'
ORIGINAL = ROOT / 'dashboard/backend/migrations/013_orion_pro_integrity.sql'
DOMAIN = ROOT / 'dashboard/backend/migrations/012_orion_pro_domain.sql'
CANDIDATE = BASE / 'candidate.py'
FIXTURE = ROOT / 'tests/orion_pro_bulk_stream_local.py'
MODEL_SHA = '18da43f940870b7a3a3cb49323c847dd5e5174e5eea1f8ff0c8a159cf373cb08'
CASES = ['candidate_available', 'pure_equivalence_scope', 'owned_catalogue_and_acl',
         'compact_original_semantics', 'dense_candidate_plans_seal_commit',
         'dense_candidate_semantics', 'native_values_and_state_unchanged',
         'runtime_and_objects_unchanged', 'protected_inputs_and_cleanup']


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path, value): path.write_text(json.dumps(value, indent=2, default=str) + '\n')
def digest(value): return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()
def metadata_budget(*roots):
    seen = set(); pending = list(roots); total = 0
    while pending:
        value = pending.pop()
        if id(value) in seen: continue
        seen.add(id(value)); total += sys.getsizeof(value)
        if isinstance(value, dict): pending.extend(value.keys()); pending.extend(value.values())
        elif isinstance(value, (list, tuple, set)): pending.extend(value)
    total += sys.getsizeof(seen) + sys.getsizeof(pending)
    assert total <= 32 * 1024**2, 'Retained validator metadata bound'
    return total
def q(value):
    assert re.fullmatch('[a-z_][a-z0-9_]*', value)
    return '"' + value + '"'
def rel(name): return '.'.join(q(p) for p in name.split('.'))


class Budget:
    def __init__(self, owned, evidence, label):
        self.owned, self.evidence = owned, evidence
        self.start = time.monotonic(); self.stop = threading.Event(); self.samples = []; self.reason = None
        self.path = BASE / 'campaign.json'
        self.ledger = json.loads(self.path.read_text()) if self.path.exists() else {'maximumFullStarts': 2, 'maximumCampaignSeconds': 2400, 'runs': []}
        assert len(self.ledger['runs']) < 2 and not self.ledger.get('stopForROOTBrief'), 'Fresh ROOT brief required before another full load'
        assert sum(r.get('elapsedSeconds', 0) for r in self.ledger['runs']) < 2400
        self.entry = {'label': label, 'startedAt': datetime.now(timezone.utc).isoformat()}
        self.ledger['runs'].append(self.entry); save(self.path, self.ledger)
        self.thread = threading.Thread(target=self.watch, daemon=True); self.thread.start()

    def watch(self):
        while not self.stop.wait(2):
            try:
                size = int(subprocess.check_output(['du', '-sk', str(self.owned)], text=True).split()[0]) * 1024
                elapsed = time.monotonic() - self.start
                self.samples.append({'elapsedSeconds': round(elapsed, 3), 'ownedDiskBytes': size}); save(self.evidence / 'resources.json', self.samples)
                if size >= 7 * 1024**3 or elapsed >= 1200:
                    self.reason = '7GiB_soft_stop' if size >= 7 * 1024**3 else '20minute_wall_stop'
                    _thread.interrupt_main(); return
            except (OSError, subprocess.CalledProcessError):
                if not self.stop.is_set(): self.reason = 'resource_monitor_failure'; _thread.interrupt_main()
                return

    def close(self, success):
        self.stop.set(); self.thread.join(4)
        if self.owned.exists(): self.samples.append({'elapsedSeconds': round(time.monotonic() - self.start, 3), 'ownedDiskBytes': int(subprocess.check_output(['du', '-sk', str(self.owned)], text=True).split()[0]) * 1024})
        self.entry.update(status='pass' if success else 'stopped_for_ROOT_brief', elapsedSeconds=round(time.monotonic() - self.start, 3),
                          peakObservedDiskBytes=max((r['ownedDiskBytes'] for r in self.samples), default=0), budgetStop=self.reason)
        if not success: self.ledger['stopForROOTBrief'] = 'First-load failure/limit; no implicit second run'
        save(self.path, self.ledger); save(self.evidence / 'resources.json', self.samples)
        return self.entry


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path); module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


def function_ddl(text):
    start = text.index('CREATE OR REPLACE FUNCTION "ingest"."validate_generation"(')
    end = text.index('$orion_pro$;', start) + len('$orion_pro$;')
    return text[start:end]


def protected():
    output = {}
    for folder, count in [('orion-pro-bulk-20261104', 529), ('orion-pro-bulk-stream-20261105', 98)]:
        p = ROOT / 'docs/verification' / folder; manifest = json.loads((p / 'final-hashes.json').read_text())
        assert len(manifest['artifacts']) == count
        changed = [name for name, value in manifest['artifacts'].items() if sha(p / name) != value['sha256']]
        assert not changed, (folder, changed)
        output[folder] = {'artifacts': count, 'changed': changed, 'manifestSha256': sha(p / 'final-hashes.json')}
    return output


def structure(conn):
    return list(conn.execute("""SELECT n.nspname||'.'||c.relname,c.relkind,pg_get_userbyid(c.relowner),c.relacl::text,
        (SELECT count(*) FROM pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)
        FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname IN ('ingest','football','analytics') AND c.relkind IN ('r','p','i','S') ORDER BY 1"""))


def function_properties(conn):
    return conn.execute("SELECT oid::text,pg_get_userbyid(proowner),prosecdef,proconfig,proacl::text,pg_get_function_identity_arguments(oid) FROM pg_proc WHERE oid='ingest.validate_generation(bigint)'::regprocedure").fetchone()


def oracle(conn, tables, metrics):
    output = {}
    with conn.transaction():
        for name, table in sorted(tables.items()):
            columns = ','.join('t.' + q(c) for c in table['columns']); order = ','.join('t.' + q(c) for c in table['primary_key']['columns'])
            h = hashlib.sha256(); count = 0
            with conn.cursor(name='independent_' + str(time.monotonic_ns())) as cursor:
                cursor.execute(f'SELECT ROW({columns})::text FROM {rel(name)} t ORDER BY {order}')
                for rows in iter(lambda: cursor.fetchmany(250), []):
                    retained = sys.getsizeof(rows) + sum(sys.getsizeof(row) + sys.getsizeof(row[0]) for row in rows)
                    wire = sum(len(row[0].encode()) for row in rows); budget = retained + 3 * wire + 1024 * 1024
                    assert budget <= 16 * 1024**2, 'Native oracle buffer bound'
                    metrics['nativeOracleBufferPeakBytes'] = max(metrics.get('nativeOracleBufferPeakBytes', 0), budget)
                    for row in rows:
                        raw = row[0].encode(); h.update(str(len(raw)).encode() + b':' + raw + b'\n'); count += 1
            output[name] = {'rows': count, 'sha256': h.hexdigest()}
    return output


def query_at(query, generation, focus=None):
    assert query.count('ingest.selected_at(g,') == 2
    sql = query.replace('ingest.selected_at(g,', 'ingest.selected_at(%s::bigint,').rstrip(';')
    params = [generation, generation]
    if focus is not None:
        sql += ' AND child.match_id=%s AND child.player_id=%s'
        params += list(focus)
    return sql, params


def temp_stats(conn):
    return conn.execute('SELECT temp_files,temp_bytes FROM pg_stat_database WHERE datname=current_database()').fetchone()


class Probe:
    def __init__(self, conn, compiled, tables, report, evidence):
        self.conn, self.compiled, self.tables, self.report, self.evidence = conn, compiled, tables, report, evidence
        self.hooked = False; self.seals = []; self.commits = []; self.statement_counts = {}

    def __getattr__(self, name): return getattr(self.conn, name)

    def execute(self, sql, params=None, **kwargs):
        start = time.monotonic()
        kind = sql.strip().split()[0].upper(); self.statement_counts[kind] = self.statement_counts.get(kind, 0) + 1
        if sql.startswith('SELECT ingest.seal_generation'):
            try:
                result = self.conn.execute(sql, params, **kwargs)
                self.seals.append({'generation': params[0], 'elapsedMs': round((time.monotonic() - start) * 1000, 3), 'status': 'pass'})
                return result
            except Exception as exc:
                self.seals.append({'generation': params[0], 'elapsedMs': round((time.monotonic() - start) * 1000, 3), 'status': 'fail', 'sqlstate': getattr(exc, 'sqlstate', None)}); raise
        result = self.conn.execute(sql, params, **kwargs)
        # Frozen fixture's count is evaluated before its before-seal timestamp.
        if sql == 'SELECT count(*) FROM football.player_match_metric_values' and not self.hooked:
            self.hooked = True; self.diagnostic()
        return result

    def commit(self):
        start = time.monotonic()
        try:
            self.conn.commit(); self.commits.append({'elapsedMs': round((time.monotonic() - start) * 1000, 3), 'status': 'pass'})
        except Exception as exc:
            self.commits.append({'elapsedMs': round((time.monotonic() - start) * 1000, 3), 'status': 'fail', 'sqlstate': getattr(exc, 'sqlstate', None)}); raise

    def diagnostic(self):
        generation = self.conn.execute("SELECT generation FROM ingest.dataset_snapshots WHERE status='draft'").fetchone()[0]
        before = oracle(self.conn, self.tables, self.report)
        source_stats = temp_stats(self.conn)
        original, params = query_at(self.compiled['original_query'], generation)
        start = time.monotonic()
        estimated = self.conn.execute('EXPLAIN (VERBOSE, SETTINGS, FORMAT JSON) ' + original, params).fetchone()[0]
        save(self.evidence / 'original-estimated-plan.json', {'kind': 'non_analyze_no_actual_timing', 'generation': generation,
             'elapsedMs': round((time.monotonic() - start) * 1000, 3), 'plan': estimated})
        candidate, params = query_at(self.compiled['candidate_query'], generation)
        start = time.monotonic()
        try:
            with self.conn.transaction():
                analyzed = self.conn.execute('EXPLAIN (ANALYZE, BUFFERS, VERBOSE, SETTINGS, FORMAT JSON) ' + candidate, params).fetchone()[0]
        except Exception as exc:
            save(self.evidence / 'candidate-query-failed.json', {'elapsedMs': round((time.monotonic() - start) * 1000, 3), 'sqlstate': getattr(exc, 'sqlstate', None)})
            raise
        elapsed = round((time.monotonic() - start) * 1000, 3)
        assert elapsed < 8000 and analyzed[0]['Plan']['Actual Rows'] == 0, 'Candidate SELECT gate failed'
        save(self.evidence / 'candidate-analyzed-plan.json', {'generation': generation, 'elapsedMs': elapsed, 'plan': analyzed,
             'tempCountersBefore': source_stats, 'tempCountersAfter': temp_stats(self.conn), 'counterTiming': 'pg_stat_database samples may lag; EXPLAIN buffers are query-local'})
        after = oracle(self.conn, self.tables, self.report); assert after == before, 'Diagnostic SELECT changed native rows'
        self.report['preSealOracle'] = before; self.report['diagnosticGeneration'] = generation; self.report['candidateQueryMs'] = elapsed
        self.report['metadataPeakBytes'] = max(self.report.get('metadataPeakBytes', 0), metadata_budget(self.tables, self.compiled, self.report))


def negative_workflows(conn, compiled, tables, phases, psycopg):
    focus_row = conn.execute("SELECT match_id,player_id,team_id,revision_id,match_team_revision_id FROM football.match_players WHERE is_canonical AND NOT is_deleted ORDER BY revision_id LIMIT 1").fetchone()
    match, player, team, revision, _ = focus_row; focus = (match, player); pinned = phases[0]['generation']
    fk = next(f['name'] for f in tables['football.player_match_metric_values']['foreign_keys'] if f['references']['table'] == 'football.match_players')
    observations = []

    def truth(query, g):
        sql, params = query_at(query, g, focus); return bool(conn.execute(sql, params).fetchone())

    assert not truth(compiled['original_query'], pinned) and not truth(compiled['candidate_query'], pinned)
    for mode in ['closed', 'wrong_team', 'nonnull_position', 'noncanonical', 'deleted']:
        try:
            with conn.transaction():
                g = conn.execute('SELECT ingest.begin_generation(%s,%s,%s)', ('negative:' + mode + ':' + str(time.monotonic_ns()), 'validator_e2e', 'validator_e2e')).fetchone()[0]
                conn.execute('UPDATE football.match_players SET recorded_to_gen=%s WHERE revision_id=%s', (g, revision))
                if mode != 'closed':
                    columns = [c for c, spec in tables['football.match_players']['columns'].items() if not spec.get('identity')]
                    expressions = {c: 'old.' + q(c) for c in columns}
                    expressions.update(recorded_from_gen=str(g), recorded_to_gen='NULL::bigint')
                    if mode == 'wrong_team':
                        other = conn.execute('SELECT team_id,revision_id FROM football.match_teams WHERE match_id=%s AND team_id<>%s AND recorded_to_gen IS NULL', (match, team)).fetchone()
                        expressions.update(team_id=str(other[0]), match_team_revision_id=str(other[1]))
                    elif mode == 'nonnull_position':
                        # Explicit native mapping, not an invented default for an unobserved source value.
                        conn.execute("""INSERT INTO football.position_mappings(source_id,raw_position_code,mapping_version,position_code,position_definition_version,status,
                            recorded_from_gen,variant_key,is_canonical,contract_version,transform_version,transform_code_sha256,source_record_id,provenance_kind)
                            SELECT 2,'FWD',%s,'FWD','bootstrap_v1','validated',%s,'stream:primary',true,contract_version,transform_version,transform_code_sha256,source_record_id,'provider'
                            FROM football.match_players WHERE revision_id=%s""", ('validator_position', g, revision))
                        expressions.update(position_code="'FWD'", position_definition_version="'bootstrap_v1'", raw_position_code="'FWD'", raw_position_code_state="'string'", position_mapping_version="'validator_position'")
                    elif mode == 'noncanonical': expressions['is_canonical'] = 'false'
                    elif mode == 'deleted': expressions['is_deleted'] = 'true'
                    conn.execute(f"INSERT INTO football.match_players ({','.join(q(c) for c in columns)}) SELECT {','.join(expressions[c] for c in columns)} FROM football.match_players old WHERE revision_id=%s", (revision,))
                old_result, new_result = truth(compiled['original_query'], g), truth(compiled['candidate_query'], g)
                assert old_result is True and new_result is True, (mode, old_result, new_result)
                assert not truth(compiled['original_query'], pinned) and not truth(compiled['candidate_query'], pinned), 'Historical generation changed'
                conn.execute('SELECT ingest.seal_generation(%s,%s)', (g, digest(mode)))
                raise AssertionError('Invalid membership was accepted: ' + mode)
        except psycopg.Error as exc:
            assert exc.sqlstate == '23514' and fk in exc.diag.message_primary, (mode, exc.sqlstate, exc.diag.message_primary)
            observations.append({'mode': mode, 'sqlstate': exc.sqlstate, 'membershipRule': fk, 'historicalStillValid': True})
    for mode in ['wrong_physical_anchor', 'wrong_provider']:
        try:
            with conn.transaction():
                g = conn.execute('SELECT ingest.begin_generation(%s,%s,%s)', ('negative:' + mode + ':' + str(time.monotonic_ns()), 'validator_e2e', 'validator_e2e')).fetchone()[0]
                table = tables['football.player_match_metric_values']; columns = [c for c, spec in table['columns'].items() if not spec.get('identity')]
                expr = {c: 'old.' + q(c) for c in columns}; expr.update(recorded_from_gen=str(g), recorded_to_gen='NULL::bigint', is_canonical='false', variant_key="'validator:negative'")
                if mode == 'wrong_physical_anchor':
                    bad = conn.execute('SELECT revision_id FROM football.match_players WHERE revision_id<>%s ORDER BY revision_id LIMIT 1', (revision,)).fetchone()[0]
                    expr['match_player_revision_id'] = str(bad)
                else: expr['source_id'] = '10'
                conn.execute(f"INSERT INTO football.player_match_metric_values ({','.join(q(c) for c in columns)}) SELECT {','.join(expr[c] for c in columns)} FROM football.player_match_metric_values old WHERE match_id=%s AND player_id=%s ORDER BY revision_id LIMIT 1", focus)
                raise AssertionError('Invalid exact FK was accepted')
        except psycopg.Error as exc:
            assert exc.sqlstate == '23503', (mode, exc.sqlstate)
            observations.append({'mode': mode, 'sqlstate': exc.sqlstate, 'constraint': exc.diag.constraint_name, 'separateFromMembershipTest': True})
    return observations


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--label', default='validator-e2e'); parser.add_argument('--static-only', action='store_true')
    parser.add_argument('--pg-bin', type=Path, default=Path('/tmp/statarena-cache-test-tools/node_modules/@embedded-postgres/darwin-arm64/native/bin'))
    args = parser.parse_args(); assert re.fullmatch('[A-Za-z0-9][A-Za-z0-9-]{0,70}', args.label)
    sys.path[:0] = [str(ROOT / 'tests'), str(PILOT), str(SCRIPTS), '/tmp/statarena-publication-test-python']
    import psycopg
    from psycopg.conninfo import make_conninfo
    from harness import LocalPostgres
    from orion_pro_migrate import bootstrap
    from orion_pro_integrity import role_grants_sql, integrity_sql
    fixture_module = load(FIXTURE, 'frozen_stream_fixture')
    run = BASE / 'runs' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-' + args.label); inputs = run / 'inputs'; inputs.mkdir(parents=True)
    paths = [Path(__file__), CANDIDATE, BASE / 'PROTOCOL.md', MODEL, ORIGINAL, DOMAIN, FIXTURE, ROOT / 'tests/orion_pro_bulk_local.py',
             SCRIPTS / 'orion_pro_bulk.py', SCRIPTS / 'orion_pro_migrate.py', SCRIPTS / 'orion_pro_integrity.py', SCRIPTS / 'orion_pro_schema.py', PILOT / 'harness.py']
    report = {'kind': 'local_nullable_membership_validator_e2e', 'startedAt': datetime.now(timezone.utc).isoformat(),
              'command': ['python3', str(Path(__file__).relative_to(ROOT)), *sys.argv[1:]], 'cases': [], 'sourceSha256': {},
              'fullAcceptance': False, 'remoteActions': [], 'scope': 'Validator-only local candidate; no streamer or014/RDS claim',
              'versions': {'python': sys.version, 'psycopg': psycopg.__version__}, 'statementTimeoutMs': 8000, 'lockTimeoutMs': 1000}
    for p in paths:
        if p.exists():
            destination = inputs / p.relative_to(ROOT); destination.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(p, destination)
            report['sourceSha256'][str(p.relative_to(ROOT))] = sha(p)
    model = json.loads(MODEL.read_text()); tables = {t['qualified_name']: t for s in model['schemas'] for t in s['tables'] if t['phase'] != 'models'}
    pg = budget = admin = dense = compact = dense_writer = compact_writer = probe = None; blocker = None; compiled = None

    def install(conn):
        conn.execute("SET TimeZone='UTC'"); conn.execute("SET DateStyle='ISO, YMD'"); conn.execute('SET extra_float_digits=3')
        with conn.transaction():
            artifacts = [(v, p, p.read_text()) for v, p in [('012', DOMAIN), ('013', ORIGINAL)]]
            for version, p, sql in artifacts:
                conn.execute(sql, prepare=False); conn.execute('INSERT INTO ingest.schema_migrations(version,content_sha256,code_commit) VALUES(%s,%s,%s)', (version, sha(p), 'local_validator_fixture'))
            bootstrap(conn, model, artifacts)
            conn.execute(role_grants_sql(model, ingest_role='bulk_ingest', runtime_role='bulk_runtime'), prepare=False)
        conn.execute("SET statement_timeout='8s'"); conn.execute("SET lock_timeout='1s'")

    try:
        for case in CASES:
            if blocker:
                report['cases'].append({'case': case, 'status': 'unverified', 'reason': blocker}); continue
            if args.static_only and case not in CASES[:2]:
                report['cases'].append({'case': case, 'status': 'unverified', 'reason': 'Static-only mode; no database started'}); continue
            try:
                actual = {}
                if case == 'candidate_available':
                    assert CANDIDATE.is_file(), 'Local candidate generator is absent'
                    module = load(CANDIDATE, 'membership_candidate'); compiled = module.compile_candidate(MODEL, ORIGINAL)
                    actual = {'candidateSha256': sha(CANDIDATE)}
                elif case == 'pure_equivalence_scope':
                    assert sha(MODEL) == MODEL_SHA and integrity_sql(model, tables) == ORIGINAL.read_text()
                    original = function_ddl(ORIGINAL.read_text()); candidate = compiled['sql'].strip(); pattern = r'(selected_parent\."(?P<c>[a-z_]+)") = (anchor\."(?P=c)")'
                    normalized, changes = re.subn(pattern, lambda m: m[1] + ' IS NOT DISTINCT FROM ' + m[3], candidate)
                    assert normalized == original and changes == 139
                    clauses = [line for line in candidate.splitlines() if 'FROM ' in line and ' selected_parent ' in line]
                    assert len(clauses) == 81; eq = nullable = 0
                    for line in clauses:
                        parent = re.search(r'FROM "([a-z_]+)"\."([a-z_]+)" selected_parent', line); parent = tables[parent[1] + '.' + parent[2]]
                        for match in re.finditer(r'selected_parent\."([a-z_]+)" (IS NOT DISTINCT FROM|=) anchor\."\1"', line):
                            expected = 'IS NOT DISTINCT FROM' if parent['columns'][match[1]]['nullable'] else '='
                            assert match[2] == expected; eq += expected == '='; nullable += expected != '='
                    assert (eq, nullable) == (139, 46)
                    report['protectedBefore'] = protected(); actual = {'clauses': 81, 'equalities': eq, 'nullableRetained': nullable, 'normalizedExactlyOriginal': True}
                    report['metadataPeakBytes'] = metadata_budget(model, compiled, report)
                    (run / 'candidate.sql').write_text(compiled['sql'] + '\n'); save(run / 'candidate-metadata.json', {k: v for k, v in compiled.items() if k != 'sql'})
                elif case == 'owned_catalogue_and_acl':
                    pg = LocalPostgres(args.pg_bin, run); assert shutil.disk_usage(pg.root).free >= 16 * 1024**3
                    pg.command([pg.binaries / 'initdb', '-D', pg.data, '--auth=trust', '--no-locale', '--encoding=UTF8'], name='initdb')
                    with (pg.data / 'postgresql.conf').open('a') as f: f.write('\nlog_error_verbosity=terse\nlog_min_error_statement=panic\nlog_parameter_max_length_on_error=0\ntemp_file_limit=512MB\n')
                    pg.start(); budget = Budget(pg.root, run, args.label); admin = psycopg.connect(pg.dsn, autocommit=True); assert admin.info.server_version == 180006
                    report['versions']['postgres'] = admin.info.server_version
                    for role in ['bulk_ingest', 'bulk_runtime']: admin.execute(f'CREATE ROLE {role} LOGIN NOSUPERUSER NOCREATEROLE NOCREATEDB NOREPLICATION NOBYPASSRLS')
                    for name in ['validator_dense', 'validator_original']: admin.execute('CREATE DATABASE ' + q(name))
                    dense = psycopg.connect(make_conninfo(pg.dsn, dbname='validator_dense'), autocommit=True); install(dense)
                    compact = psycopg.connect(make_conninfo(pg.dsn, dbname='validator_original'), autocommit=True); install(compact)
                    actual_null = {(r[0], r[1]): r[2] for r in dense.execute("SELECT n.nspname||'.'||c.relname,a.attname,a.attnotnull FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname IN ('ingest','football','analytics') AND c.relkind IN ('r','p') AND a.attnum>0 AND NOT a.attisdropped")}
                    expected_null = {(n, c): not spec['nullable'] for n, t in tables.items() for c, spec in t['columns'].items()}; assert actual_null == expected_null
                    before = function_properties(dense); report['structureBefore'] = structure(dense)
                    dense.execute(compiled['sql'], prepare=False); assert function_properties(dense) == before and structure(dense) == report['structureBefore']
                    report['functionProperties'] = before; report['dbNullability'] = [{'table': n, 'column': c, 'notNull': v} for (n, c), v in sorted(actual_null.items())]
                    dense_writer = psycopg.connect(make_conninfo(pg.dsn, dbname='validator_dense', user='bulk_ingest'), autocommit=True)
                    compact_writer = psycopg.connect(make_conninfo(pg.dsn, dbname='validator_original', user='bulk_ingest'), autocommit=True)
                    for conn in [dense_writer, compact_writer]:
                        conn.execute("SET statement_timeout='8s'"); conn.execute("SET lock_timeout='1s'"); conn.execute("SET TimeZone='UTC'")
                        assert not any(conn.execute('SELECT rolsuper,rolcreaterole,rolcreatedb,rolreplication,rolbypassrls FROM pg_roles WHERE rolname=current_user').fetchone())
                    report['settings'] = {n: {'setting': s, 'unit': u} for n, s, u in dense_writer.execute("SELECT name,setting,unit FROM pg_settings WHERE name IN ('work_mem','hash_mem_multiplier','temp_file_limit')")}
                    actual = {'actualColumnNullabilityVerified': len(actual_null), 'sameAclOwnerSecurityPath': True, 'sameSchemaIndexes': True}
                elif case == 'compact_original_semantics':
                    small_globals = {**fixture_module.fixture.__globals__, 'APPEARANCES': 40, 'SCALARS': 1240, 'MATCHES': 4, 'PLAYERS': 40}
                    small = types.FunctionType(fixture_module.fixture.__code__, small_globals, name='compact_original_fixture')
                    evidence = run / 'compact'; evidence.mkdir()
                    producer = digest({'fixture': sha(FIXTURE), 'runner': sha(Path(__file__)), 'shape': [40, 31]})
                    phases = small(compact_writer, model, producer, evidence)
                    before = oracle(compact, tables, report); report['compactNegative'] = negative_workflows(compact_writer, compiled, tables, phases, psycopg)
                    assert oracle(compact, tables, report) == before; report['compactPositiveOracle'] = before
                    actual = {'scalarRows': 1240, 'negativeCases': report['compactNegative'], 'original013Validator': True}
                elif case == 'dense_candidate_plans_seal_commit':
                    probe = Probe(dense_writer, compiled, tables, report, run)
                    producer = digest({'fixture': sha(FIXTURE), 'runner': sha(Path(__file__)), 'candidate': sha(CANDIDATE), 'shape': [15437, 31]})
                    phases = fixture_module.fixture(probe, model, producer, run); report['densePhases'] = phases
                    assert probe.hooked and len(probe.seals) == len(probe.commits) == 2
                    assert all(v['status'] == 'pass' and v['elapsedMs'] < 8000 for v in probe.seals + probe.commits)
                    actual = {'canonicalScalarRows': 478547, 'plansBeforePureSeal': True, 'seals': probe.seals, 'commits': probe.commits, 'statementCounts': probe.statement_counts}
                elif case == 'dense_candidate_semantics':
                    before = oracle(dense, tables, report); report['densePositiveOracle'] = before
                    report['denseNegative'] = negative_workflows(dense_writer, compiled, tables, report['densePhases'], psycopg)
                    assert [(v['mode'], v['sqlstate']) for v in report['denseNegative']] == [(v['mode'], v['sqlstate']) for v in report['compactNegative']]
                    assert oracle(dense, tables, report) == before
                    actual = {'sameOriginalAndCandidateRejections': True, 'negativeCases': report['denseNegative']}
                elif case == 'native_values_and_state_unchanged':
                    assert report['densePositiveOracle']['football.player_match_metric_values']['rows'] == 478547
                    assert dense.execute('SELECT count(DISTINCT(match_id,player_id,period_code,family_code,metric_code)),bool_and(is_canonical),count(DISTINCT variant_key) FROM football.player_match_metric_values').fetchone() == (478547, True, 1)
                    assert dense.execute("SELECT parameters->>'large',parameters->>'fraction',(parameters->'null')::text,parameters->'missing' IS NULL,jsonb_typeof(parameters->'array'),jsonb_typeof(parameters->'text'),parameters->>'empty' FROM ingest.document_lineage").fetchone() == ('12345678901234567890123456789', '0.123456789012345678901234567890123456789', 'null', True, 'array', 'string', '')
                    actual = {'nativeOracleRelations': 94, 'noValueTransformation': True, 'exactTypedTechnicalStates': True}
                elif case == 'runtime_and_objects_unchanged':
                    assert function_properties(dense) == report['functionProperties'] and structure(dense) == report['structureBefore']
                    runtime = psycopg.connect(make_conninfo(pg.dsn, dbname='validator_dense', user='bulk_runtime'), autocommit=True); denials = []
                    try:
                        for sql in ["SELECT ingest.validate_generation(1)", "SELECT ingest.begin_generation('denied','test','test')", "SELECT ingest.seal_generation(1,repeat('0',64))", "SELECT nextval('ingest.commit_generation_seq')", "INSERT INTO ingest.quality_issues(rule_code,severity) VALUES('denied','info')"]:
                            try:
                                with runtime.transaction(): runtime.execute(sql); raise AssertionError('Runtime unexpectedly authorized')
                            except psycopg.Error as exc: assert exc.sqlstate == '42501'; denials.append(exc.sqlstate)
                    finally: runtime.close()
                    actual = {'denials': denials, 'sameFunctionPrivilegesAndObjects': True}
                elif case == 'protected_inputs_and_cleanup':
                    assert protected() == report['protectedBefore']; assert sha(MODEL) == MODEL_SHA and integrity_sql(model, tables) == ORIGINAL.read_text()
                    actual = {'frozenArtifactsUnchanged': 627, 'default013StillExact': True}
                report['cases'].append({'case': case, 'status': 'pass', 'actual': actual}); print('PASS ' + case, flush=True)
            except Exception as exc:
                value = {'case': case, 'status': 'fail', 'errorType': type(exc).__name__, 'sqlstate': getattr(exc, 'sqlstate', None),
                         'error': exc.diag.message_primary if getattr(exc, 'diag', None) else str(exc), 'traceback': traceback.format_exc()}
                if getattr(exc, 'diag', None): value['databaseContext'] = exc.diag.context
                report['cases'].append(value); blocker = 'Required gate failed: ' + case; print('FAIL ' + case + ': ' + value['error'][:300], flush=True)
    except KeyboardInterrupt: report['interrupted'] = budget.reason if budget else 'interrupted'
    finally:
        if probe: report['pureSealTimings'] = probe.seals; report['pureCommitTimings'] = probe.commits
        for conn in [dense_writer, compact_writer, dense, compact, admin]:
            if conn:
                try: conn.close()
                except Exception: pass
        if budget: report['resourceBudget'] = budget.close(not blocker and 'interrupted' not in report)
        report['cleanup'] = pg.cleanup() if pg else {'serverStopped': True, 'ownedDirectoryRemoved': True, 'serverStarted': False}
        report['finishedAt'] = datetime.now(timezone.utc).isoformat(); report['counts'] = {s: sum(c['status'] == s for c in report['cases']) for s in ['pass', 'fail', 'unverified']}
        report['currentInputsUnchanged'] = all(sha(ROOT / n) == v for n, v in report['sourceSha256'].items())
        report['status'] = 'static_preflight' if args.static_only and report['counts']['fail'] == 0 else 'pass' if report['counts']['pass'] == len(CASES) and 'interrupted' not in report else 'fail'
        save(run / 'result.json', report); print(json.dumps({'status': report['status'], 'counts': report['counts'], 'evidence': str(run)}), flush=True)
    return 0 if report['status'] in {'pass', 'static_preflight'} else 1


if __name__ == '__main__': raise SystemExit(main())
