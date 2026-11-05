#!/usr/bin/env python3
"""Once-only real P2/015 core transport supervision, default offline."""
from __future__ import annotations
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time

sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
RUN = BASE/'real-core-operation-v4-p2'
WRITER = ROOT/'dashboard/scripts/orion_pro_native_transport_real_v3.py'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, default=str)+'\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--preflight', action='store_true')
    mode.add_argument('--apply', action='store_true')
    parser.add_argument('--authority-sha256')
    args = parser.parse_args()
    if not (args.preflight or args.apply):
        print(json.dumps({'status': 'offline_plan', 'connections': 0, 'sourceCalls': 0, 'businessWrites': []}))
        return 0
    assert not any(k.startswith('PG') for k in os.environ), 'Inherited libpq settings refused before AWS'
    assert args.authority_sha256 == sha(RUN/'ROOT_AUTHORITY.json'), 'Exact out-of-band ROOT authority required'
    authority = json.loads((RUN/'ROOT_AUTHORITY.json').read_text())
    assert authority['kind'] == 'ROOT_VERIFIED_REAL_CORE_TRANSPORT_P2_AUTHORITY_V4'
    for name, expected in authority['files'].items():
        assert sha(ROOT/name) == expected, 'Real transport input differs: '+name
    assert authority['fullAcceptance'] is False and authority['productionActivation'] is False
    # Logical content approval and current endpoint liveness are separate identities.
    old_checkpoint = json.loads((ROOT/authority['continuity']['logicalCheckpoint']).read_text())
    live_checkpoint = json.loads((ROOT/authority['continuity']['currentCheckpoint']).read_text())
    routing_fields = authority['continuity']['routingFields']
    assert routing_fields == ['marker','markerPath','sourceDescriptor','sourceDescriptorSha256','native94Evidence']
    assert {k:v for k,v in old_checkpoint.items() if k not in routing_fields} == {k:v for k,v in live_checkpoint.items() if k not in routing_fields}
    assert json.loads((ROOT/authority['continuity']['logicalNative94']).read_text()) == json.loads((ROOT/authority['continuity']['currentNative94']).read_text())
    assert sha(authority['sourceMarker']) == authority['sourceMarkerSha256'], 'Current private marker differs'
    pair = json.loads((RUN/'pair.json').read_text())
    accepted = json.loads((RUN/'acceptance.json').read_text())
    service_path = ROOT/authority['continuity']['currentCheckpoint']
    readback_path = ROOT/authority['targetReadbackPath']
    target_policy_path = BASE/'transport-real-v3/TARGET_POLICY.json'
    assert accepted['sourceServiceCheckpointSha256'] == sha(service_path)
    assert accepted['targetReadbackSha256'] == sha(readback_path)
    assert accepted['sourceCheckpointSha256'] == sha(ROOT/authority['continuity']['logicalCheckpoint'])
    assert pair['source'] == json.loads(Path(live_checkpoint['sourceDescriptor']).read_text())
    assert json.loads(Path(authority['sourceMarker']).read_text()) == live_checkpoint['marker']
    import ingest_actor
    sys.path.insert(0, str(ROOT/'tests'))
    from orion_e2e_process import run_bounded
    label = 'apply' if args.apply else 'preflight'
    checkpoint = RUN/(label+'.started.json')
    assert not checkpoint.exists(), 'Operation consumed; inspect target before any new release'
    if args.apply:
        previous = json.loads((RUN/'preflight.result.json').read_text())
        assert previous['status'] == 'preflight' and previous['privateAuthenticationRemoved'] and previous['childExitCode'] == 0
        assert previous['authoritySha256'] == sha(RUN/'ROOT_AUTHORITY.json'), 'Preflight authority changed'
    started = time.monotonic()
    descriptor = os.open(checkpoint, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, 'w') as stream:
        json.dump({'atUtc': datetime.now(timezone.utc).isoformat(), 'authoritySha256': sha(RUN/'ROOT_AUTHORITY.json'),
                   'mode': label, 'executions': 1, 'resetPermitted': False}, stream, indent=2)
        stream.write('\n')
    release = {'kind': 'native_transport_operation_release_v3', 'scope': 'typed_real_core_p2_015',
               'mode': label+'-rds', 'writerSha256': sha(WRITER),
               'bindingSha256': sha(BASE/'transport-real-v3/BINDINGS.json'), 'pairSha256': sha(RUN/'pair.json'),
               'acceptanceSha256': sha(RUN/'acceptance.json'),
               'sourceServiceCheckpointSha256': sha(service_path), 'targetReadbackSha256': sha(readback_path),
               'targetPolicySha256': sha(target_policy_path),
               'expiresAt': (datetime.now(timezone.utc)+timedelta(minutes=30)).isoformat(), 'fullAcceptance': False}
    release_path = RUN/(label+'.release.json')
    save(release_path, release)
    report = {'kind': 'root_actual_rds_core_p2_operation_v4', 'mode': label, 'command': [sys.executable, *sys.argv],
              'authoritySha256': sha(RUN/'ROOT_AUTHORITY.json'), 'releaseSha256': sha(release_path),
              'providerSourceCalls': 0, 'sourceCalls': 0, 'liveTypedSourceReads': True, 'rawBodiesPersisted': False,
              'targetPolicySha256': sha(target_policy_path), 'sourceServiceCheckpointSha256': sha(service_path),
              'targetReadbackSha256': sha(readback_path), 'productionActivation': False, 'fullAcceptance': False}
    private_path = None
    try:
        with ingest_actor.private_authentication() as private_path:
            command = [sys.executable, str(WRITER), '--'+label+'-rds', '--source-marker', authority['sourceMarker'],
                       '--pair', str(RUN/'pair.json'), '--pair-sha256', sha(RUN/'pair.json'),
                       '--acceptance', str(RUN/'acceptance.json'), '--acceptance-sha256', sha(RUN/'acceptance.json'),
                       '--release', str(release_path), '--release-sha256', sha(release_path),
                       '--source-service-checkpoint', str(service_path), '--source-service-checkpoint-sha256', sha(service_path),
                       '--target-readback', str(readback_path), '--target-readback-sha256', sha(readback_path),
                       '--target-passfile', str(private_path)]
            report['childCommand'] = command
            env = {k: v for k, v in os.environ.items() if not k.startswith('PG')}
            env.update(PYTHONPATH='/tmp/statarena-publication-test-python', PYTHONDONTWRITEBYTECODE='1')
            result = run_bounded(command, cwd=ROOT, env=env, deadline=started+900,
                                 term_seconds=3, drain_seconds=1, output_limit=8*1024**2)
            (RUN/(label+'.stdout.log')).write_text(result.stdout)
            (RUN/(label+'.stderr.log')).write_text(result.stderr)
            report['childExitCode'] = result.returncode
            child = json.loads(result.stdout)
            report['child'] = child
            assert result.returncode == 0 and child['connectionsClosed'], 'Actual transport refused; no retry'
            if not args.apply:
                assert child['status'] == 'preflight' and child['copyCommands'] == child['nextvalCalls'] == 0
            else:
                assert child['status'] in ['applied', 'noop']
            report['status'] = child['status']
    except BaseException as error:
        report.update(status='fail', errorType=type(error).__name__, sqlstate=getattr(error, 'sqlstate', None))
        for name in ['reason', 'pid', 'returncode']:
            if hasattr(error, name):
                report[name] = getattr(error, name)
    finally:
        report['privateAuthenticationRemoved'] = private_path is None or not private_path.exists()
        report['elapsedSeconds'] = round(time.monotonic()-started, 3)
        save(RUN/(label+'.result.json'), report)
        print(json.dumps({'status': report['status'], 'evidence': str(RUN/(label+'.result.json')),
                          'privateAuthenticationRemoved': report['privateAuthenticationRemoved']}), flush=True)
    return 0 if report['status'] in ['preflight', 'applied', 'noop'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
