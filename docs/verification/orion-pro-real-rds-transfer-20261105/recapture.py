#!/usr/bin/env python3
"""Supervise one frozen source recapture; default is offline validation only."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import selectors
import signal
import stat
import subprocess
import sys
import time

sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
RELEASE = BASE / 'ROOT_CAPTURE_V3_RELEASE.json'
SOURCE = ROOT / 'docs/verification/orion-pro-real-native-spatial-20261104'
LEDGER = SOURCE / 'budget-v3.json'
SOCKET = Path('/tmp/orion-real-rds-source-20261105-v3/source.sock')
EVIDENCE = SOURCE / 'capture-v3'
DEPENDENCIES = {
    'psycopg': '3.3.7', 'psycopg-binary': '3.3.7', 'boto3': '1.43.124',
    'botocore': '1.43.124', 's3transfer': '0.19.3', 'jmespath': '1.1.0',
    'urllib3': '2.8.0', 'python-dateutil': '2.9.0.post0', 'six': '1.17.0',
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git(*args):
    result = subprocess.run(['git', *args], cwd=ROOT, capture_output=True, timeout=10)
    if result.returncode:
        raise ValueError('Git publication check failed')
    return result.stdout


def check(live):
    if any(k.startswith('PG') for k in os.environ):
        raise ValueError('Inherited libpq settings refused before authentication')
    release = json.loads(RELEASE.read_text())
    if release['kind'] != 'ROOT_THIRD_FROZEN_CAPTURE_RELEASE' or release['oneCaptureOnly'] is not True:
        raise ValueError('Capture release identity differs')
    for relative, expected in release['files'].items():
        path = ROOT / relative
        if path.is_symlink() or sha(path) != expected:
            raise ValueError('Capture release file differs: ' + relative)
    for name, expected in DEPENDENCIES.items():
        if importlib.metadata.version(name) != expected:
            raise ValueError('Capture installed dependency differs: ' + name)
    if sha(LEDGER) != release['initialLedgerSha256']:
        raise ValueError('Capture ledger consumed or changed; no replay/reset')
    if SOCKET.parent.exists() or EVIDENCE.exists():
        raise ValueError('Capture socket/evidence namespace already exists')
    command = [sys.executable, str(SOURCE/'capture.py'), '--ledger', str(LEDGER),
               '--expected-selects', '0', '--expected-decoded-bytes', '0']
    verified = subprocess.run([*command, '--check-only'], cwd=ROOT, capture_output=True, timeout=15)
    if verified.returncode or json.loads(verified.stdout)['status'] != 'valid_initial_checkpoint':
        raise ValueError('Frozen capture initial checkpoint refused')
    if live:
        if os.environ.get('STATARENA_SOURCE_FORBIDDEN') == '1':
            raise ValueError('Source access forbidden in this environment')
        if git('branch', '--show-current').strip() != b'main':
            raise ValueError('Capture launcher must be published on main')
        if hashlib.sha256(git('show', 'HEAD:' + str(RELEASE.relative_to(ROOT)))).hexdigest() != sha(RELEASE):
            raise ValueError('Unpublished capture release')
        for relative in release['publishedCode']:
            if hashlib.sha256(git('show', 'HEAD:' + relative)).hexdigest() != release['files'][relative]:
                raise ValueError('Unpublished capture launcher: ' + relative)
    return release, command


def stop_owned(child):
    if child is None or child.poll() is not None:
        return
    os.killpg(child.pid, signal.SIGTERM)
    try:
        child.wait(timeout=3)
    except subprocess.TimeoutExpired:
        os.killpg(child.pid, signal.SIGKILL)
        child.wait(timeout=3)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--check-only', action='store_true')
    mode.add_argument('--capture', action='store_true')
    args = parser.parse_args()
    def interrupted(signum, frame):
        raise KeyboardInterrupt()
    signal.signal(signal.SIGTERM, interrupted)
    report = {'kind': 'root_capture_v3_supervision', 'startedAt': datetime.now(timezone.utc).isoformat(),
              'command': [sys.executable, *sys.argv], 'expected': str(BASE/'RECAPTURE_PROTOCOL.md'),
              'sourceCallsBySupervisor': 0, 'businessWrites': [], 'fullAcceptance': False}
    child = None
    private_path = None
    owned_directory = False
    run = None
    started = time.monotonic()
    try:
        release, command = check(args.capture)
        report.update(releaseSha256=sha(RELEASE), initialLedgerSha256=sha(LEDGER),
                      dependencies=DEPENDENCIES, pythonVersion=sys.version)
        if not args.capture:
            print(json.dumps({**report, 'status': 'offline_check_pass', 'sourceCalls': 0}))
            return 0
        run = BASE/'capture-supervision'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        run.mkdir(parents=True)
        SOCKET.parent.mkdir(mode=0o700)
        owned_directory = True
        import ingest_actor
        with ingest_actor.private_authentication() as private_path:
            environment = {k: v for k, v in os.environ.items() if not k.startswith('PG')}
            environment.update(PGPASSFILE=str(private_path), PYTHONDONTWRITEBYTECODE='1')
            command += ['--source-authorized', '--approved-commit', release['normalizerCommit'],
                        '--socket', str(SOCKET), '--evidence', str(EVIDENCE)]
            child = subprocess.Popen(command, cwd=ROOT, env=environment, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, start_new_session=True)
            report.update(childCommand=command, childPid=child.pid, launcherPid=os.getpid(),
                          launcherCommit=git('rev-parse', 'HEAD').decode().strip())
            selector = selectors.DefaultSelector()
            selector.register(child.stdout, selectors.EVENT_READ)
            output = bytearray()
            deadline = started + 180
            ready = None
            while time.monotonic() < deadline:
                for key, _ in selector.select(min(0.5, max(0, deadline-time.monotonic()))):
                    piece = os.read(key.fileobj.fileno(), 8192)
                    if not piece:
                        raise ValueError('Capture exited before READY')
                    output.extend(piece)
                    if len(output) > 65536:
                        raise ValueError('Capture output exceeded64KiB')
                    if b'\n' in output:
                        ready = json.loads(output.split(b'\n', 1)[0])
                        break
                if ready is not None:
                    break
                if child.poll() is not None:
                    raise ValueError('Capture exited before READY')
            selector.close()
            if ready is None:
                raise ValueError('Capture READY deadline exceeded180s')
            if ready.get('ready') is not True or ready.get('pid') != child.pid or ready.get('socket') != str(SOCKET):
                report['captureResponse'] = ready
                raise ValueError('Frozen capture did not reach READY; no retry')
            report.update(status='ready', capture=ready, readyElapsedSeconds=round(time.monotonic()-started, 3))
        report['privateAuthenticationRemoved'] = not private_path.exists()
        if not report['privateAuthenticationRemoved']:
            raise ValueError('Private authentication was not removed after READY')
        (run/'ready.json').write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps({'status': 'ready', 'pid': child.pid, 'socket': str(SOCKET),
                          'privateAuthenticationRemoved': True, 'evidence': str(run/'ready.json')}), flush=True)
        child.wait()
        if child.returncode != 0:
            raise ValueError('RAM capture child exited abnormally')
        report['status'] = 'stopped_cleanly'
    except (Exception, KeyboardInterrupt) as error:
        report.update(status='fail', errorType=type(error).__name__,
                      error=str(error) if isinstance(error, ValueError) else 'See frozen metadata receipt; no retry')
    finally:
        stop_owned(child)
        if child is not None:
            report.update(childExitCode=child.returncode, childReaped=child.poll() is not None,
                          finalLedgerSha256=sha(LEDGER))
            child.stdout.close()
        report['privateAuthenticationRemoved'] = private_path is None or not private_path.exists()
        if owned_directory:
            if SOCKET.exists() and stat.S_ISSOCK(SOCKET.lstat().st_mode) and SOCKET.lstat().st_uid == os.getuid():
                SOCKET.unlink()
            SOCKET.parent.rmdir()
        report['elapsedSeconds'] = round(time.monotonic()-started, 3)
        if run is not None:
            (run/'result.json').write_text(json.dumps(report, indent=2)+'\n')
        if args.capture or report.get('status') == 'fail':
            print(json.dumps(report), flush=True)
    return 0 if report.get('status') == 'stopped_cleanly' else 1


if __name__ == '__main__':
    raise SystemExit(main())
