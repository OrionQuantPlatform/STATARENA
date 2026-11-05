#!/usr/bin/env python3
"""ROOT execution of the fixed qualified015 release with ephemeral private auth."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[3]
RESULT = BASE / 'ROOT015_EXECUTION_V1.json'


def aws(*args):
    child = subprocess.run(['aws', *args, '--profile', 'statarena', '--region', 'us-east-2', '--output', 'json'],
                           capture_output=True, text=True, timeout=40)
    if child.returncode:
        raise RuntimeError('Fixed AWS authentication operation failed')
    return json.loads(child.stdout)


def main():
    assert len(sys.argv) == 1 and not RESULT.exists(), 'Fixed one-shot ROOT wrapper only'
    started = time.monotonic()
    report = {'kind': 'root_fixed015_private_auth_execution_v1',
              'startedAtUtc': datetime.now(timezone.utc).isoformat(),
              'wrapperSha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'command': [sys.executable, str(Path(__file__))], 'status': 'unverified',
              'credentialBodyArchived': False, 'sourceCalls': 0, 'productionActivation': False}
    private_path = None
    try:
        spec = importlib.util.spec_from_file_location('root_fixed015_operator', BASE / 'adopt_p2.py')
        operator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(operator)
        release, policy = operator.release_structure()
        operator.validate_local_proof(release)
        report['releaseSha256'] = operator.sha(operator.RELEASE)
        identity = aws('sts', 'get-caller-identity')
        assert identity['Account'] == '361769570630'
        assert identity['Arn'] == 'arn:aws:iam::361769570630:user/hugo.lemonnier'
        secret = aws('ssm', 'get-parameter', '--name', '/statarena/app/rds-admin', '--with-decryption')
        body = json.loads(secret['Parameter']['Value'])
        actor = body.get('username') or body.get('user')
        password = body.get('password')
        target = policy['target']
        assert actor == target['actor'] == 'statarena_admin'
        assert isinstance(password, str) and password and not any(c in password for c in '\r\n\x00')
        for name in ['host', 'hostname']:
            if name in body:
                assert body[name] == operator.observer.HOST
        def escape(value):
            return str(value).replace('\\', '\\\\').replace(':', '\\:')
        with tempfile.TemporaryDirectory(prefix='orion-root015-private-', dir='/tmp') as private:
            private_path = Path(private)
            private_path.chmod(0o700)
            passfile = private_path / 'auth.pgpass'
            descriptor = os.open(passfile, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, 'w') as stream:
                stream.write(':'.join(escape(v) for v in [operator.observer.HOST, 5432,
                             'statarena_prod', actor, password]) + '\n')
            env = {k: v for k, v in os.environ.items() if not k.startswith('PG')}
            env.update(PYTHONPATH='/tmp/statarena-publication-test-python', PYTHONDONTWRITEBYTECODE='1')
            command = [sys.executable, str(BASE / 'adopt_p2.py'), '--execute-released-rds',
                       '--target-passfile', str(passfile), '--release-sha256', report['releaseSha256']]
            child = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, timeout=205)
            assert password not in child.stdout and password not in child.stderr
            result = json.loads(child.stdout)
            report.update(operatorResult=result, operatorExitCode=child.returncode,
                          operatorStderrBytes=len(child.stderr.encode()),
                          operatorStderrSha256=hashlib.sha256(child.stderr.encode()).hexdigest(), parameterReads=1)
            report['status'] = result['status']
            assert child.returncode == 0 and result['connectionsClosed']
            assert result['status'] in ['applied_and_independently_verified', 'commit_outcome_verified_P2']
    except BaseException as error:
        report.update(wrapperFailureType=type(error).__name__)
        if report['status'] == 'unverified':
            report['status'] = 'failed_or_unverified'
    finally:
        report['privateAuthenticationRemoved'] = private_path is None or not private_path.exists()
        report['elapsedSeconds'] = round(time.monotonic() - started, 3)
        report['finishedAtUtc'] = datetime.now(timezone.utc).isoformat()
        with RESULT.open('x') as stream:
            json.dump(report, stream, indent=2)
            stream.write('\n')
        print(json.dumps({'status': report['status'], 'privateAuthenticationRemoved': report['privateAuthenticationRemoved'],
                          'evidence': str(RESULT)}))
    return 0 if 'wrapperFailureType' not in report and report['privateAuthenticationRemoved'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
