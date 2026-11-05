#!/usr/bin/env python3
"""Fresh RO native P1 attestation and target descriptor, never business writes."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import signal
import socket
import sys
import tempfile
import time

sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
POLICY = ROOT/'docs/verification/orion-pro-policy-rds-20261105'
EXPECTED = 'e24d2f4864f2a24c639d5556b4012d276b8958f5df3d02e2a80e52a601ae9a32'


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--observe', action='store_true')
    args = parser.parse_args()
    if not args.observe:
        print(json.dumps({'status': 'offline_plan', 'sourceCalls': 0, 'connections': 0, 'remoteWrites': []}))
        return 0
    assert not any(k.startswith('PG') for k in os.environ), 'Inherited libpq settings refused before AWS'
    sys.path.insert(0, str(ROOT/'dashboard/scripts'))
    policy = load(POLICY/'adapter.py', 'real_pair_native_policy')
    transport = load(ROOT/'dashboard/scripts/orion_pro_native_transport.py', 'real_pair_transport_descriptor')
    assert policy.sha(POLICY/'adapter.py') == 'a6e5213e54de057562b10f57b4dd675e1501b4dd82449dd7a3ab19e7caf250d6'
    assert policy.sha(ROOT/'dashboard/scripts/orion_pro_native_transport.py') == '9ec803b5caa6a5c5a47c2154256ea8199847281931fe73a538862c70fa371487'
    before_path = POLICY/'rds-adoption/20261105T101932138463Z/native-2.json'
    original = policy.json_file(before_path)
    assert policy.state_hash(original) == EXPECTED
    run = BASE/'rds-pair-readbacks'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    run.mkdir(parents=True)
    report = {'kind': 'root_real_rds_pair_readonly_attestation', 'command': [sys.executable, *sys.argv],
              'expected': str(BASE/'RDS_PAIR_PROTOCOL.md'), 'priorNativeSha256': policy.sha(before_path),
              'expectedStateSha256': EXPECTED, 'selects': 0, 'connections': 0, 'remoteWrites': [], 'fullAcceptance': False}
    connection = None
    private = None
    started = time.monotonic()
    def alarm(signum, frame):
        raise TimeoutError('Readonly pair90s deadline')
    signal.signal(signal.SIGALRM, alarm)
    signal.setitimer(signal.ITIMER_REAL, 90)
    try:
        aws = load(POLICY/'root_readonly.py', 'real_pair_private_cli').aws
        identity = aws('sts', 'get-caller-identity')
        assert identity['Account'] == '361769570630' and identity['Arn'] == 'arn:aws:iam::361769570630:user/hugo.lemonnier'
        data = json.loads(aws('ssm', 'get-parameter', '--name', '/statarena/app/rds-admin', '--with-decryption')['Parameter']['Value'])
        password = data.get('password')
        assert (data.get('username') or data.get('user')) == policy.ACTOR and isinstance(password, str) and password and not any(c in password for c in '\r\n\x00')
        def escaped(value):
            return str(value).replace('\\', '\\\\').replace(':', '\\:')
        with tempfile.TemporaryDirectory(prefix='orion-real-pair-auth-', dir='/tmp') as folder:
            private = Path(folder)
            private.chmod(0o700)
            path = private/'auth.pgpass'
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'w') as stream:
                stream.write(':'.join(escaped(x) for x in [policy.HOST, 5432, policy.DATABASE, policy.ACTOR, password])+'\n')
            policy.validated_rds_passfile({'ORION_RDS_PASSFILE': str(path)})
            address = sorted({v[4][0] for v in socket.getaddrinfo(policy.HOST, 5432, type=socket.SOCK_STREAM)})[0]
            import psycopg
            connection = psycopg.connect(**policy._rds_connection_kwargs(str(path), address))
            report['connections'] = 1
            class Cursor:
                def __init__(self, cursor): self.cursor = cursor
                def __getattr__(self, key): return getattr(self.cursor, key)
                def __enter__(self): self.cursor.__enter__(); return self
                def __exit__(self, *args): return self.cursor.__exit__(*args)
                def execute(self, sql, *args, **kwargs): count(sql); self.cursor.execute(sql, *args, **kwargs); return self
                def stream(self, sql, *args, **kwargs): count(sql); return self.cursor.stream(sql, *args, **kwargs)
            def count(sql):
                if sql.lstrip().upper().startswith(('SELECT', 'WITH')):
                    report['selects'] += 1
                    assert report['selects'] <= 24
            class Counted:
                def __getattr__(self, key): return getattr(connection, key)
                def cursor(self, *a, **kw): return Cursor(connection.cursor(*a, **kw))
                def execute(self, sql, *a, **kw): count(sql); return connection.execute(sql, *a, **kw)
            with connection.transaction():
                connection.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
                state = policy.observe(Counted())
                report.update(actualStateSha256=policy.state_hash(state), nativeBudget=state['budget'])
                assert report['actualStateSha256'] == EXPECTED, 'Real P1 differs; no self-derived replacement baseline'
                assert not state['groups']['nonbootstrap']
                descriptor = transport.describe_endpoint(Counted(), source=False, origin='existing_rds_p1')
                report['maxRetainedMetadataBytes'] = policy.metadata_bytes(state, descriptor, report)
                policy.save(run/'native.json', state)
                policy.save(run/'target-descriptor.json', descriptor)
                report.update(nativeSha256=policy.sha(run/'native.json'), targetDescriptorSha256=policy.sha(run/'target-descriptor.json'))
            connection.close()
        report['status'] = 'accepted_exact_P1_bootstrap_only'
    except Exception as error:
        report.update(status='fail', errorType=type(error).__name__, code=getattr(error, 'code', None), sqlstate=getattr(error, 'sqlstate', None))
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        if connection is not None:
            connection.close()
        report.update(connectionClosed=connection is None or connection.closed,
                      privateAuthenticationRemoved=private is None or not private.exists(), elapsedSeconds=round(time.monotonic()-started, 3))
        policy.save(run/'result.json', report)
        print(json.dumps({'status': report['status'], 'selects': report['selects'], 'evidence': str(run/'result.json')}))
    return 0 if report['status'] == 'accepted_exact_P1_bootstrap_only' else 1


if __name__ == '__main__':
    raise SystemExit(main())
