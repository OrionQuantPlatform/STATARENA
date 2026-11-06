"""Execute the actual GitHub workflow planner without cloud/provider credentials."""
import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import yaml

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
phase = sys.argv[1]
assert phase.replace('-', '').isalnum()
report = {
    'atUtc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'rerun': 'PYTHONPATH=/tmp/statarena-publication-test-python python3 docs/verification/aws-workflow-consolidation-20261104/verify_plan.py ' + phase,
    'setup': 'Actual workflow Bash step; isolated environment and temporary GitHub output; no cloud/provider calls or credentials.',
    'checks': [],
}

def check(name, operation):
    try:
        actual = operation()
        report['checks'].append({'name': name, 'passed': True, 'actual': actual})
    except Exception as error:
        report['checks'].append({'name': name, 'passed': False, 'error': str(error)[:1000]})

def require(value, message):
    if not value:
        raise AssertionError(message)

def workflow():
    path = ROOT / '.github/workflows/collect-football.yml'
    require(path.exists(), 'Consolidated collector absent')
    w = yaml.safe_load(path.read_text())
    events = w.get('on', w.get(True))
    require(set(events) == {'schedule', 'workflow_dispatch'}, 'Collector runs on an unintended event')
    schedules = [x['cron'] for x in events['schedule']]
    require(sorted(schedules) == sorted(['35 22 * * *', '10 6 * * *']), 'Only the two approved daily trigger times may be scheduled')
    require(w['concurrency'] == {'group': 'statarena-aws-ingestion', 'cancel-in-progress': False, 'queue': 'max'}, 'Writer concurrency changed')
    j = w['jobs']['collect']
    require("github.ref == 'refs/heads/main'" in j['if'] and 'codex/' not in j['if'], 'Collector must run only on main')
    require('secrets.NEON' not in path.read_text(), 'Legacy secret reference')
    require(any(x.get('uses') == './.github/actions/aws-database' for x in j['steps']), 'Missing AWS bootstrap')
    require('--skip-materialize' in path.read_text() and 'relational_materialize.py' in path.read_text(), 'Staging and serving construction not separated')
    for old in ['daily-sync.yml', 'historical-backfill.yml', 'aws-publication-recovery-20261106.yml']:
        require(not (path.parent / old).exists(), 'Duplicate or temporary collector remains: ' + old)
    u = yaml.safe_load((path.parent / 'uefa-standings.yml').read_text())
    require("github.event_name != 'push'" in u['jobs']['refresh']['if'], 'UEFA writes on a verification push')
    step = next(x for x in j['steps'] if x.get('id') == 'plan')
    return step['run']

script = None
def definition():
    global script
    script = workflow()
    return {'collector': 'collect-football.yml', 'dailyTriggerCount': 2, 'historicalSchedule': False, 'oldDefinitions': 0, 'sourcePushCollection': False}
check('workflow roles, schedules and AWS controls', definition)

def plan(inputs, expected=None, rejected=False):
    require(script is not None, 'Planner unavailable')
    with tempfile.TemporaryDirectory() as d:
        output = Path(d) / 'output'
        output.touch()
        env = {'PATH': os.environ['PATH'], 'GITHUB_OUTPUT': str(output), 'EVENT_NAME': 'workflow_dispatch', 'SCHEDULE': '', 'MODE_INPUT': '', 'MINUTES_INPUT': '', 'REQUESTS_INPUT': '', 'PRIORITY_INPUT': '', 'ASSETS_INPUT': '', **inputs}
        p = subprocess.run(['bash', '--noprofile', '--norc', '-e', '-o', 'pipefail', '-c', script], env=env, capture_output=True, text=True, timeout=5)
        actual = dict(line.split('=', 1) for line in output.read_text().splitlines())
        if rejected:
            require(p.returncode != 0 and not actual, 'Invalid input reached executable outputs')
        else:
            require(p.returncode == 0, 'Plan failed: ' + p.stderr)
            require(actual == expected, f'Expected {expected}, got {actual}')
        return {'inputs': inputs, 'expected': 'rejected before outputs' if rejected else expected, 'exit': p.returncode, 'outputs': actual, 'stdout': p.stdout, 'stderr': p.stderr}

def expected(mode, minutes, requests, assets='3000', priority=''):
    return {'mode': mode, 'minutes': str(minutes), 'requests': str(requests), 'priority_league': priority, 'asset_limit': assets, 'supplemental': str(mode == 'daily').lower()}

for cron, mode, minutes, requests, assets in [
    ('35 22 * * *', 'daily', 60, 20000, '3000'),
    ('10 6 * * *', 'pulse', 25, 20000, '1000'),
]:
    check('scheduled plan ' + cron, lambda c=cron, m=mode, t=minutes, r=requests, a=assets: plan({'EVENT_NAME': 'schedule', 'SCHEDULE': c}, expected(m, t, r, a)))
for cron in ['15 0,12 * * *', '50 6 * * *', '15 18 * * *']:
    check('reject retired historical schedule ' + cron, lambda c=cron: plan({'EVENT_NAME': 'schedule', 'SCHEDULE': c}, rejected=True))
for mode, minutes, requests, assets in [('daily', 60, 20000, '3000'), ('pulse', 25, 20000, '1000'), ('historical', 280, 100000, '3000')]:
    check('manual ' + mode, lambda m=mode, t=minutes, r=requests, a=assets: plan({'MODE_INPUT': m}, expected(m, t, r, a)))
check('bounded historical run', lambda: plan({'MODE_INPUT': 'historical', 'MINUTES_INPUT': '1', 'REQUESTS_INPUT': '1', 'ASSETS_INPUT': 'false', 'PRIORITY_INPUT': 'l_123456'}, expected('historical', 1, 1, '0', 'l_123456')))
for bad in [
    {'MODE_INPUT': 'oops'}, {'MINUTES_INPUT': '0'}, {'MINUTES_INPUT': '301'},
    {'MINUTES_INPUT': '1; touch /tmp/unexpected-plan'}, {'REQUESTS_INPUT': '-1'},
    {'REQUESTS_INPUT': '100001'}, {'PRIORITY_INPUT': 'l_123456\nmode=daily'},
    {'ASSETS_INPUT': 'maybe'}, {'EVENT_NAME': 'schedule', 'SCHEDULE': 'unknown'},
]:
    check('reject ' + json.dumps(bad), lambda b=bad: plan(b, rejected=True))
report['passed'] = all(x['passed'] for x in report['checks'])
report['passedChecks'] = sum(x['passed'] for x in report['checks'])
report['totalChecks'] = len(report['checks'])
(OUT / (phase + '.json')).write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k: report[k] for k in ['passed', 'passedChecks', 'totalChecks']}))
for x in report['checks']:
    if not x['passed']:
        print(x['name'], x.get('error'))
raise SystemExit(not report['passed'])
