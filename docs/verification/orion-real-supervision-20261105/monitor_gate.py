"""Actual launcher CLI and owned-PostgreSQL smoke; never uses the RAM corpus."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
TARGET = BASE / 'supervise_real.py'
CASES = ['offline_plan', 'offline_attempt_v2', 'unsigned_real_refused', 'malformed_release_refused',
         'unsigned_attempt_v2_refused', 'owned_source_free_smoke']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    run = BASE / 'gate-runs' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-' + args.label)
    run.mkdir(parents=True)
    report = {'command': [sys.executable, str(Path(__file__)), *sys.argv[1:]], 'expected': 'PROTOCOL.md pre-code matrix',
              'launcherPresentAtStart': TARGET.exists(), 'cases': [], 'sourceAccessAuthorized': False}
    malformed = run / 'malformed-release.json'
    malformed.write_text('{}\n')
    env = {k: os.environ[k] for k in ['PATH', 'HOME', 'TMPDIR', 'USER', 'LANG', 'LC_ALL'] if k in os.environ}
    env['PYTHONPATH'] = '/tmp/statarena-publication-test-python'
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    calls = [([], 0), (['--mode', 'real', '--attempt', 'v2'], 0), (['--run', '--mode', 'real'], 2),
             (['--run', '--mode', 'real', '--release', str(malformed)], 2),
             (['--run', '--mode', 'real', '--attempt', 'v2'], 2),
             (['--run', '--mode', 'smoke', '--attempt', 'v2'], 0)]
    blocked = False
    for case, (flags, expected_exit) in zip(CASES, calls):
        if blocked:
            report['cases'].append({'case': case, 'status': 'unverified', 'reason': 'Prerequisite failed'})
            continue
        command = [sys.executable, str(TARGET), *flags]
        result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, timeout=100)
        (run / (case + '.stdout.log')).write_text(result.stdout)
        (run / (case + '.stderr.log')).write_text(result.stderr)
        try:
            actual = json.loads(result.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError):
            actual = {}
        passed = result.returncode == expected_exit
        if case in ['offline_plan', 'offline_attempt_v2']:
            passed = passed and actual.get('status') == 'offline_plan' and actual.get('childStarted') is False
            if case == 'offline_attempt_v2':passed = passed and actual.get('attempt') == 'v2'
        elif case.endswith('_refused'):
            passed = passed and actual.get('status') == 'real_release_refused' and actual.get('childStarted') is False
        else:
            passed = passed and actual.get('status') == 'pass' and actual.get('mode') == 'smoke'
            passed = passed and actual.get('innerCounts') == {'pass': 1, 'fail': 0, 'unverified': 0}
            passed = passed and actual.get('sourceLedgersUnchanged') is True and actual.get('cleanupVerified') is True
        report['cases'].append({'case': case, 'status': 'pass' if passed else 'fail', 'command': command,
                                'exitCode': result.returncode, 'expectedExitCode': expected_exit, 'actual': actual})
        blocked = not passed
    report['counts'] = {s: sum(c['status'] == s for c in report['cases']) for s in ['pass', 'fail', 'unverified']}
    report['status'] = 'pass' if report['counts'] == {'pass': len(CASES), 'fail': 0, 'unverified': 0} else 'fail'
    report['expectedPreCodeRedObserved'] = not report['launcherPresentAtStart'] and report['counts']['fail'] == 1
    report['gateSha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (run / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'status': report['status'], 'counts': report['counts'], 'expectedPreCodeRedObserved': report['expectedPreCodeRedObserved'], 'evidence': str(run)}))
    return report['status'] != 'pass'


if __name__ == '__main__':
    raise SystemExit(main())
