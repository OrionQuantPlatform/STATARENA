"""Closed local E2E launcher; RAM capture and remote services are never managed."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import shlex
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
SOURCE = ROOT / 'docs/verification/orion-pro-real-native-spatial-20261104'
HELPER = SOURCE / 'e2e.py'
PG_BIN = Path('/tmp/statarena-cache-test-tools/node_modules/@embedded-postgres/darwin-arm64/native/bin')
SOCKET = Path('/tmp/orion-real-native-spatial-20261105-v2/source.sock')
RAM_PID = 54737
REAL_LABEL = 'real-native-spatial-overlay-e0810f-v2'
RELEASE_PATH = BASE / 'ROOT_REAL_RELEASE_V2.json'
REAL_LEDGER = BASE / 'real_execution_ledger_v2.json'
SQL_PATH = 'docs/verification/orion-validator-membership-20261105/candidate.sql'
SQL_SHA = 'e0810f8670b2cb627ade2c76e3c8eb527ab31fd595d5cf939fd63bfc5cf649d6'
CASES = ['empty_local_bootstrap', 'worker_dsn_preconnect_boundary', 'local_validator_overlay_contract',
         'local_writer_deadlines', 'source_startup_contract', 'future_captured_ledger_guard',
         'capture_checkpoint_cli', 'global_budget_guards', 'profile_metadata_admission',
         'private_origin_configuration', 'resource_error_null_contract', 'real_core_import',
         'independent_native31', 'real_spatial_import_and_oracle', 'fresh_process_noop']
LEDGERS = ['docs/verification/orion-pro-pilot-20261104/real-source-budget.json',
           'docs/verification/orion-pro-real-native-spatial-20261104/budget.json',
           'docs/verification/orion-pro-real-native-spatial-20261104/budget-v2.json']
PIN_PATHS = [str(Path(__file__).resolve().relative_to(ROOT)),
             'docs/verification/orion-pro-real-native-spatial-20261104/e2e.py',
             'docs/verification/orion-pro-real-native-spatial-20261104/candidate.py',
             'docs/verification/orion-pro-real-native-spatial-20261104/capture.py',
             'docs/verification/orion-pro-real-native-spatial-20261104/MANIFEST.json',
             'docs/verification/orion-pro-real-native-spatial-20261104/FIELDS.json',
             'docs/verification/orion-pro-real-native-spatial-20261104/capture-v2/ready-snapshot.json',
             'docs/verification/orion-pro-real-native-spatial-20261104/neon-error-metadata/result.json',
             'dashboard/scripts/orion_pro_normalize.py',
             'docs/architecture/orion-plan-20261104/target-schema.proposed.json',
             'dashboard/backend/migrations/012_orion_pro_domain.sql',
             'dashboard/backend/migrations/013_orion_pro_integrity.sql', SQL_PATH, *LEDGERS,
             'docs/verification/orion-real-spatial-digest-20261105/spatial_native.py',
             'docs/verification/orion-real-supervision-20261105/real_execution_ledger.json']
COUNTERS = {'selects': 4, 'decodedBytes': 9682314, 'objectHttpRequests': 3, 'physicalHttpBytes': 3961}
BOUNDS = {'wallSeconds': 1800, 'interruptSeconds': 1770, 'diskBytes': 4 * 1024**3,
          'softDiskBytes': 7 * 1024**3 // 2, 'heartbeatSeconds': 15, 'sampleSeconds': 1,
          'cleanupSeconds': 30, 'statementTimeoutMs': 8000, 'lockTimeoutMs': 1000}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def release_valid(path, supplied_sha):
    if path is None or supplied_sha is None:
        return False
    if path.resolve() != RELEASE_PATH or path.is_symlink():
        return False
    try:
        if sha(path) != supplied_sha:
            return False
        release = json.loads(path.read_text())
        expected = {'kind', 'atUtc', 'rootDecision', 'mode', 'oneRunOnly', 'label', 'sourceSocket', 'capturePid',
                    'sourceCounters', 'bounds', 'pinnedFiles', 'sourceFreeGateReceipt', 'sourceFreeGateSha256',
                    'suggestedCommit', 'attempt'}
        if set(release) != expected:
            return False
        if release['kind'] != 'ROOT_ONE_LOCAL_RAM_RECONCILIATION_RELEASE_V2' or release['rootDecision'] != 'reviewed_exact_one_run' or release['attempt'] != 'v2':
            return False
        if (release['mode'], release['oneRunOnly'], release['label'], release['sourceSocket'], release['capturePid']) != ('real', True, REAL_LABEL, str(SOCKET), RAM_PID):
            return False
        if release['bounds'] != BOUNDS or release['sourceCounters'] != COUNTERS:
            return False
        if set(release['pinnedFiles']) != set(PIN_PATHS):
            return False
        if any(sha(ROOT / name) != value for name, value in release['pinnedFiles'].items()):
            return False
        gate = ROOT / release['sourceFreeGateReceipt']
        if not gate.resolve().is_relative_to(BASE / 'gate-runs') or sha(gate) != release['sourceFreeGateSha256']:
            return False
        if json.loads(gate.read_text())['counts'] != {'pass': 6, 'fail': 0, 'unverified': 0}:
            return False
        os.kill(RAM_PID, 0)
        if not stat.S_ISSOCK(SOCKET.lstat().st_mode) or SOCKET.lstat().st_uid != os.getuid():
            return False
        ready = json.loads((SOURCE / 'capture-v2/capture.json').read_text())
        budget = json.loads((SOURCE / 'budget-v2.json').read_text())
        return ready['ready'] is True and ready['pid'] == RAM_PID and all(budget[k] == v for k, v in COUNTERS.items())
    except (OSError, ValueError, KeyError, TypeError):
        return False


def allocated(paths):
    total = 0
    for root in paths:
        if not root.exists():
            continue
        for current, dirs, files in os.walk(root, followlinks=False):
            dirs[:] = [d for d in dirs if not (Path(current) / d).is_symlink()]
            for p in [Path(current), *(Path(current) / f for f in files)]:
                try:
                    total += p.lstat().st_blocks * 512
                except FileNotFoundError:
                    pass
    return total


def register_roots(private_tmp, roots, launch_epoch):
    # The parent owns this namespace before Popen. A killed initdb need not
    # finish or write commands.json before its directory can be accounted for.
    for root in private_tmp.iterdir():
        if not root.name.startswith('orion-pro-e2e-'):
            continue
        data = root / 'data'
        if root in roots:
            continue
        if root.is_symlink() or data.is_symlink() or not root.is_dir() or root.resolve().parent != private_tmp.resolve():
            raise RuntimeError('Unowned database directory refused')
        info = root.stat()
        if info.st_uid != os.getuid() or info.st_ctime < launch_epoch - 2:
            raise RuntimeError('Existing or foreign database root refused')
        roots[root] = {'root': str(root), 'data': str(data), 'registeredFrom': 'parent-owned-private-TMPDIR',
                       'ownerUid': info.st_uid}


def discover_runs(before_dirs, label, private_tmp):
    found = set()
    for run in set((SOURCE / 'runs').iterdir()) - before_dirs:
        if not run.is_dir() or run.is_symlink():
            continue
        if run.name.endswith('-' + label):
            found.add(run)
            continue
        if not any(run.name.endswith('-' + v) for v in ['local-overlay-probe-default', 'local-overlay-probe-allowed']):
            continue
        try:
            entries = json.loads((run / 'commands.json').read_text())
        except (OSError, ValueError):
            continue
        for entry in entries:
            argv = entry.get('argv', [])
            if argv and argv[0] == str(PG_BIN / 'initdb') and '-D' in argv:
                data = Path(argv[argv.index('-D') + 1])
                if data.name == 'data' and data.parent.parent.resolve() == private_tmp.resolve():
                    found.add(run)
    return found


def fallback_cleanup(roots, deadline):
    results = []
    for root, meta in roots.items():
        item = {'root': str(root), 'alreadyRemovedByChild': not root.exists()}
        if not root.exists():
            results.append(item)
            continue
        if time.monotonic() >= deadline:
            results.append({**item, 'removed': False, 'errorType': 'CleanupDeadline'})
            continue
        data = Path(meta['data'])
        try:
            if root.is_symlink() or data.is_symlink() or root.stat().st_uid != os.getuid():
                raise RuntimeError('Cleanup ownership changed')
            pidfile = data / 'postmaster.pid'
            if pidfile.exists():
                pid = int(pidfile.read_text().splitlines()[0])
                inspect = subprocess.run(['ps', '-p', str(pid), '-o', 'uid=,command='], capture_output=True, text=True, timeout=min(3, max(0.1, deadline - time.monotonic())))
                if inspect.returncode == 0 and inspect.stdout.strip():
                    uid, command = inspect.stdout.strip().split(None, 1)
                    parts = shlex.split(command)
                    if int(uid) != os.getuid() or not parts or Path(parts[0]).name != 'postgres' or '-D' not in parts:
                        raise RuntimeError('Postmaster identity not owned')
                    if Path(parts[parts.index('-D') + 1]).resolve() != data.resolve():
                        raise RuntimeError('Postmaster data directory not owned')
                    remaining = deadline - time.monotonic()
                    if remaining <= 1:
                        raise RuntimeError('CleanupDeadline')
                    stop_seconds = max(1, min(15, int(remaining) - 1))
                    stopped = subprocess.run([str(PG_BIN / 'pg_ctl'), '-D', str(data), '-m', 'fast', '-t', str(stop_seconds), '-w', 'stop'], capture_output=True, timeout=min(18, remaining))
                    if stopped.returncode != 0:
                        raise RuntimeError('Owned postmaster stop failed')
                    item['fallbackStoppedOwnedPostmaster'] = True
            shutil.rmtree(root)
            item['removed'] = not root.exists()
        except Exception as error:
            item['errorType'] = type(error).__name__
            item['removed'] = False
        results.append(item)
    return results


def verify_inner(run_dir, mode):
    result = json.loads((run_dir / 'result.json').read_text())
    wanted = ['local_overlay_probe'] if mode == 'smoke' else CASES
    if result['counts'] != {'pass': len(wanted), 'fail': 0, 'unverified': 0}:
        raise RuntimeError('Child did not pass every required case')
    if [c['case'] for c in result['cases']] != wanted or any(c['status'] != 'pass' for c in result['cases']):
        raise RuntimeError('Child case membership incomplete')
    if result['sourceCallsByTest'] != 0 or result['fullAcceptance'] is not False:
        raise RuntimeError('Unexpected source or acceptance scope')
    if result['validatorPolicy']['policy'] != 'local_candidate_membership_e0810f':
        raise RuntimeError('Wrong local validator policy')
    if result['validatorPolicy']['fileSha256'] != SQL_SHA:
        raise RuntimeError('Wrong local validator artifact')
    if result['cleanup']['server_stopped'] is not True or result['cleanup']['owned_directory_removed'] is not True:
        raise RuntimeError('Child cleanup incomplete')
    if mode == 'smoke':
        if result['realNativeStatesCompared'] != 0 or result['realTripletsCompared'] != 0:
            raise RuntimeError('Smoke unexpectedly compared source facts')
    else:
        if result['realNativeStatesCompared'] != 478547 or result['realTripletsCompared'] != 1344:
            raise RuntimeError('Real corpus membership incomplete')
        case = {c['case']: c['actual'] for c in result['cases']}
        for name in ['independent_native31', 'real_spatial_import_and_oracle']:
            if case[name]['sourceSha256'] != case[name]['typedSha256'] or case[name]['errors']:
                raise RuntimeError('Independent native source SQL mismatch')
        fresh = case['fresh_process_noop']
        if fresh['before'] != fresh['after'] or fresh['unchanged'] is not True:
            raise RuntimeError('Fresh process changed native state')
        if len(fresh['before']['tables']) != 94 or len(fresh['before']['sequences']) != 67:
            raise RuntimeError('Fresh process fingerprint coverage incomplete')
        if not fresh['worker']['coreReused'] or not fresh['worker']['spatialReused']:
            raise RuntimeError('Fresh process did not reuse phase receipts')
        if any(result['sourceCaptureBudget'][k] != v for k, v in COUNTERS.items()):
            raise RuntimeError('Captured source budget differs')
    return result


def execute(mode, release_sha):
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    label = REAL_LABEL if mode == 'real' else 'root-supervision-smoke-' + stamp
    expected = CASES if mode == 'real' else ['local_overlay_probe']
    if mode == 'real' and any(p.name.endswith('-' + label) for p in (SOURCE / 'runs').iterdir()):
        raise RuntimeError('Real label already consumed')
    before_ledgers = {p: sha(ROOT / p) for p in LEDGERS}
    before_dirs = set((SOURCE / 'runs').iterdir())
    evidence = BASE / 'runs' / (stamp + '-' + mode)
    evidence.mkdir(parents=True)
    if mode == 'real':
        with REAL_LEDGER.open('x') as stream:
            json.dump({'state': 'started', 'releaseSha256': release_sha, 'label': label, 'evidence': str(evidence), 'atUtc': stamp}, stream, indent=2)
            stream.write('\n')
    # Keep nested PG Unix socket paths within macOS sockaddr_un bounds.
    private_tmp = Path(tempfile.mkdtemp(prefix='orion-owned-', dir='/tmp'))
    private_tmp.chmod(0o700)
    private_identity = (private_tmp.stat().st_uid, private_tmp.stat().st_ino)
    command = [sys.executable, str(HELPER), '--label', label, '--local-validator-overlay', SQL_PATH,
               '--local-validator-overlay-sha256', SQL_SHA]
    command += ['--source-socket', str(SOCKET)] if mode == 'real' else ['--prepare-only', '--overlay-probe-only']
    env = {k: os.environ[k] for k in ['PATH', 'HOME', 'TMPDIR', 'USER', 'LANG', 'LC_ALL', 'LC_CTYPE'] if k in os.environ}
    env.update(TMPDIR=str(private_tmp), PYTHONPATH='/tmp/statarena-publication-test-python',
               PYTHONDONTWRITEBYTECODE='1', AWS_EC2_METADATA_DISABLED='true', STATARENA_SOURCE_FORBIDDEN='1')
    start, launch_epoch = time.monotonic(), time.time()
    report = {'kind': 'ROOT_OWNED_LOCAL_RECONCILIATION_SUPERVISION', 'mode': mode, 'attempt': 'v2', 'command': command,
              'releaseSha256': release_sha, 'pinnedFiles': {p: sha(ROOT / p) for p in PIN_PATHS},
              'sourceLedgersBefore': before_ledgers, 'bounds': BOUNDS, 'sourceBodiesReadBySupervisor': 0,
              'remoteActions': [], 'fullAcceptance': False, 'expectedCases': expected,
              'privateTemporaryRoot': str(private_tmp), 'privateTemporaryUidInode': list(private_identity),
              'privateTemporaryMode': '0700', 'sourceForbiddenEnvironment': True,
              'suggestedCommit': 'test: supervise the real native source reconciliation within fixed bounds'}
    save(evidence / 'setup.json', report)
    events = (evidence / 'events.jsonl').open('w')
    proc = None
    roots, run_dirs, completed = {}, set(), []
    stream_stats = {n: {'bytes': 0, 'hash': hashlib.sha256()} for n in ['stdout', 'stderr']}
    buffer = b''
    selector = selectors.DefaultSelector()
    stopped_reason, critical, cleanup_deadline, parent_exited_at = None, None, None, None
    peak, next_sample, next_heartbeat = 0, 0.0, 0.0
    soft_wall, hard_wall = (1770, 1800) if mode == 'real' else (55, 60)

    def event(value):
        value = {'elapsedSeconds': round(time.monotonic() - start, 3), **value}
        events.write(json.dumps(value) + '\n'); events.flush()
        print(json.dumps(value), flush=True)

    try:
        proc = subprocess.Popen(command, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                start_new_session=True, bufsize=0)
        if proc.pid == RAM_PID:
            raise RuntimeError('Reserved RAM process must not be supervised')
        report['childPid'] = proc.pid
        for name, pipe in [('stdout', proc.stdout), ('stderr', proc.stderr)]:
            selector.register(pipe, selectors.EVENT_READ, name)
        event({'event': 'child_started', 'mode': mode, 'pid': proc.pid})
        while proc.poll() is None or selector.get_map():
            elapsed = time.monotonic() - start
            if proc.poll() is not None and selector.get_map():
                parent_exited_at = parent_exited_at or time.monotonic()
                if time.monotonic() - parent_exited_at >= 2:
                    critical = 'PipeDrainDeadline'
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    for key in list(selector.get_map().values()):
                        selector.unregister(key.fileobj); key.fileobj.close()
                    event({'event': 'pipe_drain_stopped', 'reason': critical})
                    break
            if elapsed >= next_sample:
                run_dirs.update(discover_runs(before_dirs, label, private_tmp))
                register_roots(private_tmp, roots, launch_epoch)
                disk = allocated([private_tmp, *run_dirs, evidence]); peak = max(peak, disk)
                if proc.poll() is None and stopped_reason is None and (elapsed >= soft_wall or disk >= BOUNDS['softDiskBytes']):
                    stopped_reason = 'wall_soft_stop' if elapsed >= soft_wall else 'disk_soft_stop'
                    os.killpg(proc.pid, signal.SIGINT)
                    event({'event': 'interrupt', 'reason': stopped_reason})
                if proc.poll() is None and (elapsed >= hard_wall or disk >= BOUNDS['diskBytes']):
                    stopped_reason = stopped_reason or 'hard_budget_stop'
                    os.killpg(proc.pid, signal.SIGKILL)
                    event({'event': 'force_stop', 'reason': stopped_reason})
                if elapsed >= next_heartbeat:
                    active = next((x for x in expected if x not in completed), None)
                    event({'event': 'heartbeat', 'ownedAllocatedBytes': disk, 'registeredPostgresRoots': len(roots),
                           'completedCases': len(completed), 'activeCaseInferred': active})
                    next_heartbeat = elapsed + BOUNDS['heartbeatSeconds']
                next_sample = elapsed + BOUNDS['sampleSeconds']
            for key, _ in selector.select(0.2):
                chunk = os.read(key.fileobj.fileno(), 65536)
                if not chunk:
                    selector.unregister(key.fileobj); key.fileobj.close(); continue
                name = key.data
                stream_stats[name]['bytes'] += len(chunk); stream_stats[name]['hash'].update(chunk)
                if name != 'stdout':
                    continue
                buffer += chunk
                while b'\n' in buffer:
                    line, buffer = buffer.split(b'\n', 1)
                    if len(line) > 256:
                        continue
                    parsed = re.fullmatch(rb'(PASS|FAIL) ([a-z0-9_]+)(?:: [A-Za-z]+)?', line)
                    if parsed:
                        case = parsed[2].decode()
                        if case in expected:
                            completed.append(case)
                            event({'event': 'case_boundary', 'case': case, 'status': parsed[1].decode().lower()})
                if len(buffer) > 4096:
                    buffer = b''
            if proc.poll() is not None and not selector.get_map():
                break
        report['childExitCode'] = proc.wait(timeout=3)
        if critical or stopped_reason is not None or report['childExitCode'] != 0:
            raise RuntimeError('Child interrupted or unsuccessful')
        run_dirs.update(discover_runs(before_dirs, label, private_tmp))
        primary = [p for p in run_dirs if p.name.endswith('-' + label)]
        if len(primary) != 1:
            raise RuntimeError('Unique child evidence directory not observed')
        inner = verify_inner(primary[0], mode)
        report.update(innerReceipt=str(primary[0] / 'result.json'), innerReceiptSha256=sha(primary[0] / 'result.json'),
                      innerCounts=inner['counts'], realNativeStatesCompared=inner['realNativeStatesCompared'],
                      realTripletsCompared=inner['realTripletsCompared'])
    except BaseException as error:
        critical = type(error).__name__
        cleanup_deadline = time.monotonic() + BOUNDS['cleanupSeconds']
        if proc is not None and proc.poll() is None:
            os.killpg(proc.pid, signal.SIGINT)
            try:
                proc.wait(timeout=20)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL); proc.wait(timeout=3)
    finally:
        cleanup_deadline = cleanup_deadline or time.monotonic() + BOUNDS['cleanupSeconds']
        selector.close()
        # A short child can finish between samples: final registration must still
        # cover its retained commands, even when normal child cleanup removed PG.
        run_dirs.update(discover_runs(before_dirs, label, private_tmp))
        try:
            register_roots(private_tmp, roots, launch_epoch)
        except Exception as error:
            critical = critical or type(error).__name__
        cleanup = fallback_cleanup(roots, cleanup_deadline)
        after_ledgers = {p: sha(ROOT / p) for p in LEDGERS}
        unchanged = before_ledgers == after_ledgers
        roots_removed = all(not Path(v['root']).exists() for v in cleanup)
        private_removed = False
        if roots_removed and time.monotonic() < cleanup_deadline:
            try:
                if private_tmp.is_symlink() or (private_tmp.stat().st_uid, private_tmp.stat().st_ino) != private_identity:
                    raise RuntimeError('Private temporary ownership changed')
                if any(private_tmp.rglob('postmaster.pid')):
                    raise RuntimeError('Unverified postmaster remains in private namespace')
                shutil.rmtree(private_tmp)
                private_removed = not private_tmp.exists()
            except Exception as error:
                critical = critical or type(error).__name__
        cleanup_ok = roots_removed and private_removed
        pins_ok = all(sha(ROOT / p) == value for p, value in report['pinnedFiles'].items())
        report.update(status='pass' if not critical and unchanged and cleanup_ok and pins_ok else 'fail',
                      errorType=critical, budgetStop=stopped_reason, elapsedSeconds=round(time.monotonic() - start, 3),
                      observedPeakAllocatedBytes=peak, sourceLedgersAfter=after_ledgers, sourceLedgersUnchanged=unchanged,
                      cleanup=cleanup, cleanupVerified=cleanup_ok, pinnedFilesUnchanged=pins_ok,
                      privateTemporaryRootRemoved=private_removed,
                      observedCaseBoundaries=completed, unverifiedCases=[x for x in expected if x not in completed],
                      streams={n: {'bytes': v['bytes'], 'sha256': v['hash'].hexdigest()} for n, v in stream_stats.items()},
                      unexercisedBranches=['Budget interrupt/force-stop and fallback postmaster cleanup are not exercised by a normally completing smoke.'])
        if mode == 'real':
            ledger = json.loads(REAL_LEDGER.read_text())
            ledger.update(state=report['status'], elapsedSeconds=report['elapsedSeconds'])
            save(REAL_LEDGER, ledger)
        save(evidence / 'result.json', report)
        events.close()
    print(json.dumps({'status': report['status'], 'mode': mode, 'innerCounts': report.get('innerCounts'),
                      'cleanupVerified': report['cleanupVerified'], 'sourceLedgersUnchanged': unchanged,
                      'evidence': str(evidence)}), flush=True)
    return report['status'] != 'pass'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--mode', choices=['real', 'smoke'], default='real')
    parser.add_argument('--attempt', choices=['v2'], default='v2')
    parser.add_argument('--release', type=Path)
    parser.add_argument('--release-sha256')
    args = parser.parse_args()
    if not args.run:
        print(json.dumps({'status': 'offline_plan', 'mode': args.mode, 'attempt': args.attempt, 'childStarted': False,
                          'bounds': BOUNDS, 'sourceBodiesRead': 0, 'remoteActions': []}))
        return 0
    if args.mode == 'real' and not release_valid(args.release, args.release_sha256):
        print(json.dumps({'status': 'real_release_refused', 'childStarted': False}))
        return 2
    try:
        return execute(args.mode, args.release_sha256)
    except Exception as error:
        print(json.dumps({'status': 'launcher_refused', 'errorType': type(error).__name__, 'childStarted': False}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
