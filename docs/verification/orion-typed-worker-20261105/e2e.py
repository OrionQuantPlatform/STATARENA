#!/usr/bin/env python3
"""Actual bootstrap/AWS CLI process E2E against an owned SSM protocol fixture."""
import argparse
import datetime
import hashlib
import http.server
import json
import os
from pathlib import Path
import shutil
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
ACTION = ROOT / '.github/actions/aws-database/bootstrap.py'
HOST = 'statarena-postgres.clcy2iqyajbl.us-east-2.rds.amazonaws.com'
KEYS = {'DATABASE_URL', 'DATABASE_CA_PEM', 'DATABASE_POOL_MAX', 'STATARENA_DATA_PROVIDER', 'PGSSLROOTCERT', 'NODE_EXTRA_CA_CERTS', 'PGSSLMODE'}
SCENARIOS = [('typed_success', 'typed-ingest', ''), ('foreign_host', 'typed-ingest', 'host'),
             ('foreign_database', 'typed-ingest', 'database'), ('foreign_port', 'typed-ingest', 'port'),
             ('foreign_actor', 'typed-ingest', 'actor'), ('ssm_denied', 'typed-ingest', 'denied'),
             ('non_secure', 'typed-ingest', 'type'), ('unknown_mode', 'typed-ingest-unknown', 'unknown'),
             ('legacy_ingest_control', 'ingest', ''), ('runtime_control', 'runtime', '')]


def parse_env(path):
    result = {}
    lines = iter(path.read_text().splitlines())
    for line in lines:
        key, term = line.split('<<', 1)
        value = []
        for item in lines:
            if item == term:
                break
            value.append(item)
        result[key] = '\n'.join(value)
    return result


def scenario(name, mode, fault):
    calls, handler_errors = [], []
    password = "declared-fixture:@ /%'&\""
    storage_secret = 'declared-fixture-storage-secret'

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_POST(self):
            length = int(self.headers['Content-Length'])
            if length > 4096:
                self.send_error(413)
                return
            query = json.loads(self.rfile.read(length))
            signed = 'AWS4-HMAC-SHA256' in self.headers.get('Authorization', '')
            if not signed or query.get('WithDecryption') is not True:
                handler_errors.append('SIGNATURE_OR_DECRYPTION')
            parameter = query.get('Name')
            calls.append(parameter)
            data = {'host': HOST, 'database': 'statarena_prod', 'port': 5432, 'username': 'statarena_ingest' if mode != 'runtime' else 'statarena_runtime', 'password': password}
            if fault == 'host':
                data['host'] = 'foreign-instance.clcy2iqyajbl.us-east-2.rds.amazonaws.com'
            elif fault == 'database':
                data['database'] = 'statarena'
            elif fault == 'port':
                data['port'] = 5433
            elif fault == 'actor':
                data['username'] = 'statarena_admin'
            if parameter == '/statarena/app/s3-ingest':
                data = {'access_key_id': 'declared-fixture-access', 'secret_access_key': storage_secret}
            denied = fault == 'denied'
            response = {'__type': 'AccessDeniedException', 'message': 'Declared fixture denial'} if denied else {'Parameter': {'Name': parameter, 'Type': 'String' if fault == 'type' else 'SecureString', 'Value': json.dumps(data)}}
            body = json.dumps(response).encode()
            self.send_response(400 if denied else 200)
            self.send_header('Content-Type', 'application/x-amz-json-1.1')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    start = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='orion-typed-worker-') as temp:
        folder = Path(temp)
        os.chmod(folder, 0o700)
        env_file = folder / 'github-env'
        env_file.touch(mode=0o600)
        with http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            env = {k: os.environ[k] for k in ('PATH', 'HOME', 'LANG', 'USER', 'TMPDIR') if k in os.environ}
            env.update(AWS_ACCESS_KEY_ID='fixture', AWS_SECRET_ACCESS_KEY='fixture', AWS_EC2_METADATA_DISABLED='true',
                       AWS_CONFIG_FILE='/dev/null', AWS_SHARED_CREDENTIALS_FILE='/dev/null', AWS_REGION='us-east-2',
                       AWS_DEFAULT_REGION='us-east-2', AWS_ENDPOINT_URL_SSM=f'http://127.0.0.1:{server.server_port}',
                       AWS_MAX_ATTEMPTS='1', AWS_RETRY_MODE='standard', GITHUB_ENV=str(env_file), GITHUB_WORKSPACE=str(ROOT))
            try:
                got = subprocess.run([sys.executable, str(ACTION), mode], env=env, capture_output=True, text=True, timeout=15)
            finally:
                server.shutdown()
                thread.join(3)
            visible = '\n'.join(line for line in (got.stdout + got.stderr).splitlines() if not line.startswith('::add-mask::'))
            assert password not in visible and storage_secret not in visible, 'VISIBLE_CREDENTIAL'
            assert not handler_errors, 'UNSIGNED_OR_NOT_DECRYPTED'
            actual = {'case': name, 'exitCode': got.returncode, 'parameterReads': calls, 'exportedKeys': [],
                      'visibleCredentialMatches': 0, 'elapsedSeconds': round(time.monotonic() - start, 3),
                      'fixtureEndpoint': 'owned-loopback-only', 'gitHubMaskDirectives': sum(line.startswith('::add-mask::') for line in got.stdout.splitlines())}
            if fault:
                assert got.returncode != 0 and not env_file.read_bytes(), 'REFUSAL_MUST_EXPORT_NOTHING'
                assert calls == ([] if fault == 'unknown' else ['/statarena/app/rds-ingest']), 'NEGATIVE_REQUEST_SCOPE'
            else:
                assert got.returncode == 0, 'NEW_MODE_OR_CONTROL_NOT_AVAILABLE'
                exported = parse_env(env_file)
                actual['exportedKeys'] = sorted(exported)
                parsed = urllib.parse.urlsplit(exported['DATABASE_URL'])
                assert parsed.hostname == HOST and parsed.port == 5432 and parsed.path == '/statarena_prod', 'TARGET_TUPLE'
                assert urllib.parse.unquote(parsed.password) == password and urllib.parse.parse_qs(parsed.query) == {'sslmode': ['verify-full']}, 'CREDENTIAL_ENCODING_TLS'
                ssl.create_default_context(cafile=exported['PGSSLROOTCERT'])
                assert exported['DATABASE_POOL_MAX'] == '1' and exported['STATARENA_DATA_PROVIDER'] == 'aws' and exported['PGSSLMODE'] == 'verify-full', 'CANONICAL_SETTINGS'
                expected = ['/statarena/app/rds-ingest', '/statarena/app/s3-ingest'] if mode == 'ingest' else ['/statarena/app/rds-runtime'] if mode == 'runtime' else ['/statarena/app/rds-ingest']
                assert calls == expected, 'SSM_REQUEST_SCOPE'
                if mode == 'typed-ingest':
                    assert set(exported) == KEYS and parsed.username == 'statarena_ingest', 'TYPED_EXPORT_BOUNDARY'
                elif mode == 'runtime':
                    assert set(exported) == KEYS, 'RUNTIME_EXPORT_BOUNDARY'
                else:
                    assert exported['NEON_STORAGE_SECRET_ACCESS_KEY'] == storage_secret and exported['NEON_DATABASE_URL'] == exported['DATABASE_URL'], 'LEGACY_CONTROL'
    assert not Path(temp).exists(), 'OWNED_TEMP_NOT_REMOVED'
    actual['privateTempRemoved'] = True
    return actual


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--label', required=True)
    args = ap.parse_args()
    assert args.label and all(c.isalnum() or c in '-_' for c in args.label)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    run = BASE / 'runs' / (stamp + '-' + args.label)
    (run / 'inputs').mkdir(parents=True)
    for p in (Path(__file__), BASE / 'PROTOCOL.md', ACTION, ROOT / '.github/actions/aws-database/action.yml'):
        dest = run / 'inputs' / p.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, dest)
    started = time.monotonic()
    report = {'kind': 'real_cli_loopback_ssm_typed_worker_e2e', 'command': ['python3', str(Path(__file__).relative_to(ROOT)), '--label', args.label],
              'fixture': 'Declared synthetic SSM responses, real bootstrap and AWS CLI processes, private GitHub env file; no live AWS or RDS',
              'expected': 'PROTOCOL.md', 'cases': [], 'remoteCloudCalls': 0, 'rdsConnections': 0, 'fullAcceptance': False,
              'suggestedCommit': 'feat: add RDS-only typed ingestion worker credentials'}
    for name, mode, fault in SCENARIOS:
        try:
            assert time.monotonic() - started < 180, 'WALL_BUDGET'
            actual = scenario(name, mode, fault)
            report['cases'].append({'case': name, 'status': 'pass', 'actual': actual})
        except Exception as error:
            report['cases'].append({'case': name, 'status': 'fail', 'errorType': type(error).__name__, 'assertion': str(error) if isinstance(error, AssertionError) else None})
            break
    done = {c['case'] for c in report['cases']}
    report['unverifiedCases'] = [name for name, _, _ in SCENARIOS if name not in done]
    report['counts'] = {'pass': sum(c['status'] == 'pass' for c in report['cases']), 'fail': sum(c['status'] == 'fail' for c in report['cases']), 'unverified': len(report['unverifiedCases'])}
    report['status'] = 'pass' if report['counts'] == {'pass': 10, 'fail': 0, 'unverified': 0} else 'fail'
    report['elapsedSeconds'] = round(time.monotonic() - started, 3)
    report['inputSha256'] = {str(p.relative_to(run / 'inputs')): hashlib.sha256(p.read_bytes()).hexdigest() for p in (run / 'inputs').rglob('*') if p.is_file()}
    (run / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'status': report['status'], 'counts': report['counts'], 'result': str(run / 'result.json')}))
    return 0 if report['status'] == 'pass' else 1


if __name__ == '__main__':
    sys.exit(main())
