#!/usr/bin/env python3
"""Pre-code whole-CLI boundaries for the new released RDS operator; zero PG/cloud."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
OPERATOR = BASE / 'root_adopt.py'
CASES = ['implementation_available', 'offline', 'missing_release', 'wrong_target',
         'wrong_code', 'consumed_ledger', 'pg_route_poison', 'unknown_host_option']

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    run = BASE / 'adoption-boundary' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    (run / 'inputs').mkdir(parents=True)
    for path in [Path(__file__), BASE / 'ROOT_ADOPTION_PROTOCOL.md', OPERATOR]:
        if path.exists():
            shutil.copy2(path, run / 'inputs' / path.name)
    report = {'kind': 'native_rds_adoption_cli_boundary_e2e', 'command': [sys.executable, str(Path(__file__))],
              'expected': 'ROOT_ADOPTION_PROTOCOL.md', 'cases': [], 'postgresStarts': 0, 'cloudCalls': 0, 'fullAcceptance': False}
    private = None
    blocker = None
    try:
        for name in CASES:
            if blocker:
                report['cases'].append({'case': name, 'status': 'unverified', 'reason': blocker})
                continue
            try:
                actual = {}
                if name == 'implementation_available':
                    assert OPERATOR.is_file(), 'New released RDS operator absent'
                    private = Path(tempfile.mkdtemp(prefix='orion-rds-operator-boundary-', dir='/tmp'))
                    mirror = private / 'repo'
                    paths = [OPERATOR, BASE / 'adapter.py', BASE / 'root_readonly.py', BASE / 'INPUTS.json', BASE / 'ROOT_RDS_NATIVE_BASELINE_REVIEW.json', BASE / 'ROOT_LIVE_CONTROLS.json']
                    native = json.loads((BASE / 'ROOT_RDS_NATIVE_BASELINE_REVIEW.json').read_text())
                    paths += [ROOT / p for p in json.loads((BASE / 'INPUTS.json').read_text())['files']]
                    paths += [ROOT / native['readonlyReceiptPath'], ROOT / native['preparedP1ContractPath']]
                    for path in set(paths):
                        dest = mirror / path.relative_to(ROOT)
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(path, dest)
                    copied = mirror / OPERATOR.relative_to(ROOT)
                    mb = copied.parent
                    release = mb / 'ROOT_RDS_TRANSITION_RELEASE.json'
                    ledger = mb / 'rds-adoption-budget-v1.json'
                    fixture = {
                        'kind': 'root_rds_one_function_adoption_release_v1', 'authorizedBy': 'ROOT',
                        'scope': 'fixed014_and_one_journal_row_only', 'codeCommit': 'a' * 40,
                        'operatorSha256': sha(OPERATOR), 'adapterSha256': sha(BASE / 'adapter.py'),
                        'nativeReviewSha256': sha(BASE / 'ROOT_RDS_NATIVE_BASELINE_REVIEW.json'),
                        'controlsSha256': sha(BASE / 'ROOT_LIVE_CONTROLS.json'),
                        'target': {'host': 'statarena-postgres.clcy2iqyajbl.us-east-2.rds.amazonaws.com', 'port': 5432,
                                   'database': 'statarena_prod', 'actor': 'statarena_admin', 'engine': 180006,
                                   'sslmode': 'verify-full', 'caSha256': sha(ROOT / 'dashboard/backend/certs/rds-us-east-2.pem')},
                        'proEnabled': False, 'collectorsEnabled': False,
                    }
                    env = {k: v for k, v in os.environ.items() if not k.startswith('PG')}
                    env.update(PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(private) + ':/tmp/statarena-publication-test-python', TRIPWIRE_FILE=str(private / 'forbidden'))
                    (private / 'sitecustomize.py').write_text("import os,socket,subprocess\nfrom pathlib import Path\nimport psycopg\ndef blocked(*a,**k):\n Path(os.environ['TRIPWIRE_FILE']).touch()\n raise RuntimeError('forbidden_side_effect')\nsocket.getaddrinfo=blocked\npsycopg.connect=blocked\nsubprocess.run=blocked\n")
                else:
                    if release.exists():
                        release.unlink()
                    if ledger.exists():
                        ledger.unlink()
                    body = json.loads(json.dumps(fixture))
                    args = [] if name == 'offline' else ['--execute-released-rds']
                    expected_code = None
                    child_env = dict(env)
                    if name == 'wrong_target':
                        body['target']['database'] = 'statarena'
                        expected_code = 'RELEASE'
                    elif name == 'wrong_code':
                        body['operatorSha256'] = '0' * 64
                        expected_code = 'RELEASE'
                    elif name == 'consumed_ledger':
                        expected_code = 'CHECKPOINT'
                    elif name == 'pg_route_poison':
                        child_env['PGHOSTADDR'] = '192.0.2.7'
                        expected_code = 'ROUTE'
                    elif name == 'unknown_host_option':
                        args += ['--host', 'external.invalid']
                    if name in ['wrong_target', 'wrong_code', 'consumed_ledger']:
                        release.write_text(json.dumps(body))
                        ledger.write_text(json.dumps({'kind': 'rds_native_adoption_one_shot_v1', 'state': 'consumed' if name == 'consumed_ledger' else 'unstarted', 'executions': 0, 'releaseSha256': sha(release)}))
                    command = [sys.executable, str(copied), *args]
                    result = subprocess.run(command, env=child_env, capture_output=True, text=True, timeout=20)
                    (run / (name + '.stdout.log')).write_text(result.stdout)
                    (run / (name + '.stderr.log')).write_text(result.stderr)
                    assert not (private / 'forbidden').exists(), 'Unreleased operator attempted AWS/DNS/driver'
                    if name == 'offline':
                        value = json.loads(result.stdout)
                        assert result.returncode == 0 and value['status'] == 'offline_plan' and value['connections'] == 0
                    else:
                        assert result.returncode == 2
                        if expected_code:
                            assert json.loads(result.stdout)['code'] == expected_code
                    actual = {'command': command, 'exitCode': result.returncode, 'forbiddenSideEffects': 0}
                report['cases'].append({'case': name, 'status': 'pass', 'actual': actual})
            except Exception as error:
                blocker = name
                report['cases'].append({'case': name, 'status': 'fail', 'errorType': type(error).__name__, 'reason': str(error)})
    finally:
        if private:
            shutil.rmtree(private)
        report['privateMirrorRemoved'] = private is None or not private.exists()
        report['counts'] = {status: sum(c['status'] == status for c in report['cases']) for status in ['pass', 'fail', 'unverified']}
        report['status'] = 'pass' if report['counts'] == {'pass': 8, 'fail': 0, 'unverified': 0} and report['privateMirrorRemoved'] else 'fail'
        report['inputs'] = {p.name: sha(p) for p in (run / 'inputs').iterdir()}
        (run / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps({'status': report['status'], 'counts': report['counts'], 'evidence': str(run / 'result.json')}))
    return 0 if report['status'] == 'pass' else 1

if __name__ == '__main__':
    raise SystemExit(main())
