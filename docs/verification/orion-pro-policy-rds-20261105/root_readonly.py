#!/usr/bin/env python3
"""One released read-only RDS observation; never print or archive credential bodies."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]

def aws(*args):
    result = subprocess.run(['aws', *args, '--profile', 'statarena', '--region', 'us-east-2', '--output', 'json'],
                            capture_output=True, text=True, timeout=40)
    if result.returncode:
        raise RuntimeError('AWS operation failed; no secret-bearing diagnostic archived')
    return json.loads(result.stdout)

def main():
    report = {'kind': 'root_rds_readonly_execution_v1', 'startedAt': datetime.now(timezone.utc).isoformat(),
              'command': [sys.executable, str(Path(__file__))], 'remoteWrites': [], 'fullAcceptance': False}
    private_path = None
    try:
        identity = aws('sts', 'get-caller-identity')
        assert identity['Account'] == '361769570630' and identity['Arn'] == 'arn:aws:iam::361769570630:user/hugo.lemonnier'
        report['identity'] = {k: identity[k] for k in ['Account', 'Arn']}
        release_path = BASE / 'ROOT_RDS_READONLY_RELEASE.json'
        release = json.loads(release_path.read_text())
        ledger = json.loads((BASE / 'remote-budget-v1.json').read_text())
        assert ledger['state'] == 'unstarted'
        raw = aws('ssm', 'get-parameter', '--name', '/statarena/app/rds-admin', '--with-decryption')
        data = json.loads(raw['Parameter']['Value'])
        username = data.get('username') or data.get('user')
        password = data.get('password')
        assert username == release['target']['actor'] and isinstance(password, str) and password and not any(c in password for c in '\r\n\x00')
        def escaped(value):
            return value.replace('\\', '\\\\').replace(':', '\\:')
        with tempfile.TemporaryDirectory(prefix='orion-rds-private-', dir='/tmp') as private:
            private_path = Path(private)
            private_path.chmod(0o700)
            passfile = private_path / 'auth.pgpass'
            descriptor = os.open(passfile, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, 'w') as stream:
                stream.write(':'.join(escaped(str(v)) for v in [release['target']['host'], 5432, 'statarena_prod', username, password]) + '\n')
            env = {k: v for k, v in os.environ.items() if not k.startswith('PG')}
            env.update(ORION_RDS_PASSFILE=str(passfile), PYTHONPATH='/tmp/statarena-publication-test-python', PYTHONDONTWRITEBYTECODE='1')
            command = [sys.executable, str(BASE / 'adapter.py'), '--preflight-rds', '--release', str(release_path),
                       '--expect-release-sha256', hashlib.sha256(release_path.read_bytes()).hexdigest(),
                       '--expected-selects', '0', '--expected-decoded-bytes', '0', '--expected-instructions', '0']
            child = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, timeout=180)
            assert password not in child.stdout and password not in child.stderr
            report.update(adapterCommand=command, adapterExitCode=child.returncode, adapterResult=json.loads(child.stdout),
                          parameterReads=1, credentialBodyArchived=False)
        report['status'] = report['adapterResult']['status']
    except Exception as error:
        report.update(status='failed', errorType=type(error).__name__)
    finally:
        report['privateAuthenticationRemoved'] = private_path is None or not private_path.exists()
        report['finishedAt'] = datetime.now(timezone.utc).isoformat()
        out = BASE / 'ROOT_READONLY_EXECUTION.json'
        assert not out.exists(), 'Do not overwrite an earlier execution receipt'
        out.write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps({'status': report['status'], 'privateAuthenticationRemoved': report['privateAuthenticationRemoved'], 'evidence': str(out)}))
    return 0 if report['status'] == 'observed_bootstrap_needs_ROOT_review' and report['privateAuthenticationRemoved'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
