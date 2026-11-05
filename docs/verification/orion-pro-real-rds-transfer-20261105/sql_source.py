#!/usr/bin/env python3
"""Build and retain one verified owned real typed checkpoint; offline by default."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import stat
import subprocess
import sys
import time

sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
FROZEN = ROOT/'docs/verification/orion-pro-real-native-spatial-20261104'
PILOT = ROOT/'docs/verification/orion-pro-pilot-20261104'
SCRIPTS = ROOT/'dashboard/scripts'
MODEL = ROOT/'docs/architecture/orion-plan-20261104/target-schema.proposed.json'
PG_BIN = Path('/tmp/statarena-cache-test-tools/node_modules/@embedded-postgres/darwin-arm64/native/bin')
RAM = Path('/tmp/orion-real-rds-source-20261105-v3/source.sock')
RELEASE = BASE/'ROOT_SQL_SOURCE_RELEASE_V1.json'
OPTIONS = '-c statement_timeout=8000 -c lock_timeout=1000 -c timezone=UTC -c datestyle=ISO,YMD -c idle_in_transaction_session_timeout=15000'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, default=str)+'\n')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source_marker(path):
    p = Path(path)
    info = p.lstat()
    assert stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid() and stat.S_IMODE(info.st_mode) == 0o600
    m = json.loads(p.read_text())
    root = Path(m['ownedRoot'])
    assert root.name.startswith('orion-pro-e2e-') and root.stat().st_uid == os.getuid() and stat.S_IMODE(root.stat().st_mode) == 0o700
    assert p.parent == root and m['sourceDatabase'] == 'postgres'
    lines = (root/'data/postmaster.pid').read_text().splitlines()
    assert Path(lines[1]) == root/'data' and int(lines[3]) == m['port']
    assert Path(m['certificatePath']).is_relative_to(root) and sha(m['certificatePath']) == m['certificateSha256']
    os.kill(int(lines[0]), 0)
    return m


def connect(m, actor):
    import psycopg
    assert actor in ('orion_pro_owner', 'orion_pro_ingest', 'orion_pro_runtime', os.environ.get('USER', 'postgres'))
    return psycopg.connect(host='127.0.0.1', hostaddr='127.0.0.1', port=m['port'], dbname='postgres', user=actor,
                           password='', passfile='/dev/null', sslmode='verify-full', sslrootcert=m['certificatePath'],
                           autocommit=True, connect_timeout=7, options=OPTIONS)


def worker(args):
    run = args.evidence.resolve()
    assert run.is_relative_to(BASE/'source-runs') and run.is_dir() and not any(k.startswith('PG') for k in os.environ)
    marker = source_marker(args.marker)
    cap = load('real_sql_source_frozen_capture', FROZEN/'capture.py')
    candidate = load('real_sql_source_frozen_candidate', FROZEN/'candidate.py')
    snapshot = cap.fetch_snapshot(RAM)
    label = 'noop' if args.noop else 'initial'
    save(run/(label+'-ram-read.json'), {'socket': str(RAM), 'documentCount': len(snapshot['cache']),
                                       'manifestSha256': snapshot['manifestSha256'], 'captureCodeSha256': snapshot['captureCodeSha256']})
    with connect(marker, 'orion_pro_ingest') as conn:
        settings = conn.execute("SELECT current_database(),current_user,session_user,current_setting('server_version_num'),"
                                "current_setting('statement_timeout'),current_setting('lock_timeout'),"
                                "(SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid())").fetchone()
        assert settings == ('postgres', 'orion_pro_ingest', 'orion_pro_ingest', '180006', '8s', '1s', True)
        result = candidate.import_candidate(conn, run, snapshot)
    save(run/(label+'-candidate.json'), result)
    print(json.dumps({'status': 'pass', 'coreReused': result['core']['reused'],
                      'spatialReused': result['spatial'].get('reused', False), 'sourceCalls': 0}), flush=True)
    return 0


def check_release():
    assert not any(k.startswith('PG') for k in os.environ), 'Inherited libpq settings refused'
    r = json.loads(RELEASE.read_text())
    assert r['kind'] == 'ROOT_REAL_SQL_SOURCE_RELEASE_V1' and r['sourceConstructions'] == 1
    for relative, expected in r['files'].items():
        assert sha(ROOT/relative) == expected, 'Source release dependency changed: '+relative
    assert subprocess.check_output(['git', 'branch', '--show-current'], cwd=ROOT, text=True).strip() == 'main'
    for path in [Path(__file__), RELEASE]:
        blob = subprocess.check_output(['git', 'show', 'HEAD:'+str(path.relative_to(ROOT))], cwd=ROOT)
        assert hashlib.sha256(blob).hexdigest() == sha(path), 'Source launcher/release must already be committed'
    allocation = BASE/'source-allocation-v1.consumed.json'
    assert not allocation.exists(), 'Source allocation already consumed'
    ri = RAM.lstat()
    assert stat.S_ISSOCK(ri.st_mode) and ri.st_uid == os.getuid() and stat.S_IMODE(RAM.parent.stat().st_mode) == 0o700
    captured = json.loads((FROZEN/'capture-v3/capture.json').read_text())
    assert sha(FROZEN/'capture-v3/capture.json') == r['captureReadySha256']
    assert captured['ready'] is True and captured['socket'] == str(RAM)
    os.kill(captured['pid'], 0)
    assert sha(FROZEN/'budget-v3.json') == r['capturedLedgerSha256']
    return r, allocation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--produce', action='store_true')
    parser.add_argument('--worker', action='store_true')
    parser.add_argument('--noop', action='store_true')
    parser.add_argument('--marker', type=Path)
    parser.add_argument('--evidence', type=Path)
    args = parser.parse_args()
    if args.worker:
        try:
            return worker(args)
        except Exception as error:
            print(json.dumps({'status': 'fail', 'errorType': type(error).__name__, 'sqlstate': getattr(error, 'sqlstate', None)}), flush=True)
            return 1
    if not args.produce:
        print(json.dumps({'status': 'offline_plan', 'connections': 0, 'ramReads': 0, 'sourceCalls': 0, 'protocol': str(BASE/'SQL_SOURCE_PROTOCOL.md')}))
        return 0
    def interrupted(signum, frame):
        raise KeyboardInterrupt()
    signal.signal(signal.SIGTERM, interrupted)
    sys.path[:0] = [str(SCRIPTS), str(PILOT), str(ROOT/'tests')]
    from orion_e2e_process import run_bounded
    from harness import LocalPostgres
    from orion_pro_migrate import bootstrap
    from orion_pro_integrity import role_grants_sql
    from orion_pro_bulk_local import oracle, sequences
    release, allocation = check_release()
    assert release['rootLocalPgSlotGranted'] is True
    run = BASE/'source-runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    (run/'inputs').mkdir(parents=True)
    for path in [RELEASE, BASE/'SQL_SOURCE_PROTOCOL.md', *[ROOT/p for p in release['files']]]:
        dest = run/'inputs'/path.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
    fd = os.open(allocation, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(fd, 'w') as stream:
        json.dump({'run': str(run), 'releaseSha256': sha(RELEASE), 'state': 'consumed', 'executions': 1}, stream, indent=2)
        stream.write('\n')
    started = time.monotonic()
    deadline = started + 600
    pg = None
    server = None
    clients = []
    report = {'kind': 'owned_real_typed_sql_checkpoint_v1', 'command': [sys.executable, *sys.argv],
              'releaseSha256': sha(RELEASE), 'expected': str(BASE/'SQL_SOURCE_PROTOCOL.md'), 'sourceCalls': 0,
              'sourceRamReads': 0, 'sourceConstructions': 0, 'rawBodiesPersisted': False, 'rdsWrites': [],
              'fullAcceptance': False, 'cases': [], 'resources': [], 'inputHashes': release['files']}
    last_resource = [0.0]
    def resource_reason():
        now = time.monotonic()
        if now-last_resource[0] < 1 or pg is None or not pg.root.exists():
            return None
        last_resource[0] = now
        disk = int(subprocess.check_output(['du', '-sk', str(pg.root)], text=True, timeout=5).split()[0])*1024
        proof = sum(p.stat().st_size for p in run.rglob('*') if p.is_file())
        report['resources'].append({'elapsedSeconds': round(now-started, 3), 'ownedDiskBytes': disk, 'proofBytes': proof})
        if disk >= 3*1024**3 or proof >= 64*1024**2:
            return 'owned_source_resource_bound'
        return None
    def stage(name, fn):
        if time.monotonic() >= deadline or resource_reason():
            raise ValueError('Source construction wall/resource budget exhausted')
        tick = time.monotonic()
        try:
            value = fn()
        except BaseException as error:
            report['cases'].append({'case': name, 'status': 'fail', 'errorType': type(error).__name__,
                                    'sqlstate': getattr(error, 'sqlstate', None)})
            raise
        report['cases'].append({'case': name, 'status': 'pass', 'elapsedSeconds': round(time.monotonic()-tick, 3), 'actual': value})
        save(run/'progress.json', report)
        return value
    def construction_alarm(signum, frame):
        raise TimeoutError('Source construction600s deadline')
    signal.signal(signal.SIGALRM, construction_alarm)
    signal.setitimer(signal.ITIMER_REAL, max(0.001, deadline-time.monotonic()))
    try:
        pg = LocalPostgres(PG_BIN, run)
        def owned_command(argv, *, env=None, check=True, name='command'):
            command = [str(x) for x in argv]
            cleanup = command[-1] == 'stop'
            r = run_bounded(command, cwd=ROOT, env=env, deadline=time.monotonic()+15 if cleanup else deadline,
                            stop_reason=(lambda: None) if cleanup else resource_reason)
            number = len(pg.commands)+1
            entry = {'argv': command, 'exitCode': r.returncode, 'stdout': f'{number:03d}-{name}.stdout.log', 'stderr': f'{number:03d}-{name}.stderr.log'}
            pg.commands.append(entry)
            (run/entry['stdout']).write_text(r.stdout)
            (run/entry['stderr']).write_text(r.stderr)
            save(run/'commands.json', pg.commands)
            if check and r.returncode:
                raise ValueError('Owned source command failed: '+name)
            return r
        pg.command = owned_command
        def setup():
            pg.command([PG_BIN/'initdb', '-D', pg.data, '--auth=trust', '--no-locale', '--encoding=UTF8'], name='initdb')
            cert, key = pg.data/'server.crt', pg.data/'server.key'
            pg.command(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-sha256', '-nodes', '-days', '2',
                        '-keyout', key, '-out', cert, '-subj', '/CN=127.0.0.1', '-addext', 'subjectAltName=IP:127.0.0.1'], name='owned-tls')
            key.chmod(0o600)
            with (pg.data/'postgresql.conf').open('a') as stream:
                stream.write("\nssl=on\nssl_cert_file='server.crt'\nssl_key_file='server.key'\nstatement_timeout=8000\nlock_timeout=1000\ntemp_file_limit=128MB\nlog_error_verbosity=terse\nlog_min_error_statement=panic\nlog_parameter_max_length_on_error=0\n")
            pg.start()
            marker = {'kind': 'owned_native_transport_pg18_v1', 'ownedRoot': str(pg.root), 'port': pg.port,
                      'sourceDatabase': 'postgres', 'targetDatabase': 'statarena_prod', 'certificatePath': str(cert), 'certificateSha256': sha(cert)}
            with connect(marker, os.environ.get('USER', 'postgres')) as admin:
                assert admin.info.server_version == 180006
                marker['postmasterStartedAt'] = admin.execute('SELECT pg_postmaster_start_time()').fetchone()[0].isoformat()
                for role in ['orion_pro_owner', 'orion_pro_ingest', 'orion_pro_runtime']:
                    admin.execute('CREATE ROLE '+role+' LOGIN NOSUPERUSER NOCREATEROLE NOCREATEDB NOREPLICATION NOBYPASSRLS')
                admin.execute('ALTER DATABASE postgres OWNER TO orion_pro_owner')
            model = json.loads(MODEL.read_text())
            with connect(marker, 'orion_pro_owner') as owner:
                with owner.transaction():
                    artifacts = []
                    for version, filename in [('012', '012_orion_pro_domain.sql'), ('013', '013_orion_pro_integrity.sql')]:
                        path = ROOT/'dashboard/backend/migrations'/filename
                        artifacts.append((version, path, path.read_text()))
                        owner.execute(path.read_text(), prepare=False)
                        owner.execute('INSERT INTO ingest.schema_migrations VALUES(%s,%s,CURRENT_TIMESTAMP,%s)',
                                      (version, sha(path), release['basisCommit']))
                    bootstrap(owner, model, artifacts)
                    owner.execute(role_grants_sql(model, 'orion_pro_ingest', 'orion_pro_runtime'), prepare=False)
            overlay = load('owned_real_source_overlay_oracle', FROZEN/'e2e.py')
            spec = overlay.local_overlay_choice(overlay.OVERLAY_PATH, overlay.OVERLAY_SHA)
            with connect(marker, os.environ.get('USER', 'postgres')) as admin:
                report['validatorOverlay'] = overlay.apply_local_overlay(admin, spec, run)
                assert admin.execute('SELECT version FROM ingest.schema_migrations ORDER BY version').fetchall() == [('012',), ('013',)]
            marker_path = pg.root/'native-marker.json'
            save(marker_path, marker)
            marker_path.chmod(0o600)
            report.update(marker=marker, markerPath=str(marker_path))
            return {'serverVersion': 180006, 'tls': True, 'journal': ['012', '013'], 'syntheticSportsRows': 0}
        stage('owned_tls_native_source', setup)
        marker = report['marker']
        marker_path = Path(report['markerPath'])
        env = {k: v for k, v in os.environ.items() if not k.startswith('PG')}
        env.update(PYTHONDONTWRITEBYTECODE='1', PYTHONPATH='/tmp/statarena-publication-test-python')
        def invoke(noop=False):
            command = [sys.executable, str(Path(__file__)), '--worker', '--marker', str(marker_path), '--evidence', str(run)]
            if noop:
                command.append('--noop')
            r = run_bounded(command, cwd=ROOT, env=env, deadline=deadline, stop_reason=resource_reason)
            label = 'noop' if noop else 'initial'
            (run/(label+'-worker.stdout.log')).write_text(r.stdout)
            (run/(label+'-worker.stderr.log')).write_text(r.stderr)
            report.setdefault('workers', []).append({'command': command, 'exitCode': r.returncode})
            assert r.returncode == 0, 'Genuine source worker failed; no retry'
            value = json.loads(r.stdout)
            assert value['status'] == 'pass' and value['coreReused'] is noop and value['spatialReused'] is noop
            report['sourceRamReads'] += 1
            return value
        stage('real_ordinary_ingest', invoke)
        report['sourceConstructions'] += 1
        cap = load('owned_real_source_readback_capture', FROZEN/'capture.py')
        snapshot = cap.fetch_snapshot(RAM)
        report['sourceRamReads'] += 1
        save(run/'parent-ram-read.json', {'socket': str(RAM), 'documentCount': len(snapshot['cache']),
                                        'manifestSha256': snapshot['manifestSha256'], 'captureCodeSha256': snapshot['captureCodeSha256']})
        checks = load('owned_real_source_independent_oracles', FROZEN/'e2e.py')
        parts = checks.unpack_independent(snapshot)
        with connect(marker, 'orion_pro_runtime') as reader:
            def native31():
                value, ok = checks.native_oracle(reader, parts)
                save(run/'native31-oracle.json', value)
                assert ok and value['typedSlots'] == 478547
                return {'slots': value['typedSlots'], 'sourceSha256': value['sourceSha256'], 'typedSha256': value['typedSha256']}
            stage('independent_native31', native31)
            def spatial():
                value, ok = checks.spatial_oracle(reader, snapshot)
                save(run/'spatial-oracle.json', value)
                assert ok and value['typedCells'] == 1344 and value['typedParents'] == 32
                return {'cells': value['typedCells'], 'parents': value['typedParents'], 'sourceSha256': value['sourceSha256'], 'typedSha256': value['typedSha256']}
            stage('independent_spatial', spatial)
        snapshot.clear()
        del parts
        model = json.loads(MODEL.read_text())
        tables = {t['qualified_name']: t for s in model['schemas'] for t in s['tables'] if t['phase'] != 'models'}
        def native_state():
            with connect(marker, 'orion_pro_runtime') as reader:
                values = oracle(reader, tables)
            with connect(marker, 'orion_pro_owner') as owner:
                seq = sequences(owner)
            return {'tables': values, 'sequences': seq}
        before = stage('independent_native94_before_noop', native_state)
        stage('fresh_process_noop', lambda: invoke(True))
        after = stage('independent_native94_after_noop', native_state)
        assert before == after, 'Fresh process changed native source or sequences'
        save(run/'native94.json', before)
        with connect(marker, 'orion_pro_runtime') as reader:
            phase_rows = reader.execute("SELECT r.checkpoint->>'phase',s.generation,s.id,r.id,s.manifest_sha256 FROM ingest.import_runs r JOIN ingest.dataset_snapshots s ON s.id=(r.checkpoint->>'snapshot_id')::bigint WHERE r.checkpoint->>'kind'='orion_pro_phase_receipt_v2' ORDER BY s.generation").fetchall()
            assert len(phase_rows) == 2 and {r[0] for r in phase_rows} == {'core', 'qualified_real_native_spatial_heatmap'}
            phases = [dict(zip(['phase', 'generation', 'snapshotId', 'runId', 'manifest'], r)) for r in phase_rows]
        with connect(marker, 'orion_pro_owner') as owner:
            owner.execute('ALTER DATABASE postgres SET default_transaction_read_only=on')
        checkpoint = {'kind': 'owned_real_typed_sql_checkpoint_v1', 'ready': True, 'marker': marker,
                      'markerPath': str(marker_path), 'producerSha256': sha(SCRIPTS/'orion_pro_normalize.py'),
                      'producerVersion': 'real_source_core_v2_native31', 'manifestSha256': sha(FROZEN/'MANIFEST.json'),
                      'candidateSha256': sha(FROZEN/'candidate.py'), 'captureCodeSha256': sha(FROZEN/'capture.py'),
                      'sourcePhases': phases, 'native94Sha256': hashlib.sha256(json.dumps(before['tables'], sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest(),
                      'native94Evidence': str(run/'native94.json'), 'sourceRows': sum(v['rows'] for v in before['tables'].values()),
                      'databaseDefaultReadOnly': True, 'fullAcceptance': False, 'rawBodiesPersisted': False,
                      'detailedFamiliesAndFullLeafFidelityAccepted': False}
        save(run/'checkpoint.json', checkpoint)
        report.update(status='ready', constructionSeconds=round(time.monotonic()-started, 3), checkpointSha256=sha(run/'checkpoint.json'))
        assert time.monotonic() < deadline
        signal.setitimer(signal.ITIMER_REAL, 0)
        save(run/'ready.json', report)
        control = pg.root/'control.sock'
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(str(control))
        os.chmod(control, 0o600)
        server.listen(1)
        server.settimeout(1)
        print(json.dumps({'status': 'ready', 'checkpoint': str(run/'checkpoint.json'), 'control': str(control), 'port': pg.port}), flush=True)
        ready_at = time.monotonic()
        while time.monotonic()-ready_at < 3600:
            if resource_reason():
                raise ValueError('Idle source resource budget exceeded')
            try:
                client, _ = server.accept()
            except socket.timeout:
                continue
            with client:
                client.settimeout(2)
                if client.recv(32) == b'STOP\n':
                    report['status'] = 'stopped_cleanly'
                    break
        else:
            raise ValueError('Idle source lifetime exhausted3600s')
        report['idleServiceSeconds'] = round(time.monotonic()-ready_at, 3)
    except (Exception, KeyboardInterrupt) as error:
        report.update(status='fail', errorType=type(error).__name__, sqlstate=getattr(error, 'sqlstate', None),
                      error=str(error) if isinstance(error, (AssertionError, ValueError, TimeoutError)) else None)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        if server is not None:
            server.close()
        for c in clients:
            c.close()
        if pg is not None:
            if (pg.data/'postmaster.pid').exists():
                pg.started = True
            try:
                report['cleanup'] = pg.cleanup()
            except Exception as error:
                report['cleanup'] = {'status': 'fail', 'errorType': type(error).__name__, 'ownedRoot': str(pg.root)}
                report['status'] = 'fail'
        report['elapsedSeconds'] = round(time.monotonic()-started, 3)
        report['sourceRamReads'] = len(list(run.glob('*-ram-read.json')))
        save(run/'result.json', report)
        print(json.dumps({'status': report['status'], 'evidence': str(run/'result.json'), 'cleanup': report.get('cleanup')}), flush=True)
    return 0 if report['status'] == 'stopped_cleanly' else 1


if __name__ == '__main__':
    raise SystemExit(main())
