#!/usr/bin/env python3
"""Exact readonly actor inspection; private authentication also serves the frozen capture."""
from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone
import argparse
import importlib.util
import json
import os
from pathlib import Path
import socket
import tempfile

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
HOST = 'statarena-postgres.clcy2iqyajbl.us-east-2.rds.amazonaws.com'
DATABASE = 'statarena_prod'
ACTOR = 'statarena_ingest'
POLICY_BASE = ROOT / 'docs/verification/orion-pro-policy-rds-20261105'

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

@contextmanager
def private_authentication():
    guard = load(POLICY_BASE / 'adapter.py', 'fixed_ingest_auth_metadata_guard')
    aws = load(POLICY_BASE / 'root_readonly.py', 'fixed_ingest_auth_cli').aws
    identity = aws('sts', 'get-caller-identity')
    assert identity['Account'] == '361769570630' and identity['Arn'] == 'arn:aws:iam::361769570630:user/hugo.lemonnier'
    value = json.loads(aws('ssm', 'get-parameter', '--name', '/statarena/app/rds-ingest', '--with-decryption')['Parameter']['Value'])
    password = value.get('password')
    assert (value.get('username') or value.get('user')) == ACTOR and isinstance(password, str) and password and not any(c in password for c in '\r\n\x00')
    def escaped(value):
        return str(value).replace('\\', '\\\\').replace(':', '\\:')
    with tempfile.TemporaryDirectory(prefix='orion-real-ingest-auth-', dir='/tmp') as private:
        directory = Path(private)
        directory.chmod(0o700)
        path = directory / 'auth.pgpass'
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, 'w') as stream:
            stream.write(':'.join(escaped(x) for x in [HOST, 5432, DATABASE, ACTOR, password]) + '\n')
        guard.validated_rds_passfile({'ORION_RDS_PASSFILE': str(path)})
        yield path

IDENTITY = """SELECT current_database(),current_user,session_user,current_setting('server_version_num'),
 current_setting('transaction_read_only'),current_setting('transaction_isolation'),
 current_setting('statement_timeout'),current_setting('lock_timeout'),
 (SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()),
 (SELECT bool_or(rolsuper OR rolcreaterole OR rolcreatedb OR rolreplication OR rolbypassrls) FROM pg_roles WHERE rolname=current_user),
 has_table_privilege(current_user,'football.players','SELECT'),
 has_table_privilege(current_user,'football.players','INSERT'),
 has_table_privilege(current_user,'ingest.schema_migrations','INSERT,UPDATE,DELETE')"""
SEQUENCES = """SELECT s.schemaname||'.'||s.sequencename,s.increment_by,s.cycle,s.cache_size,
 has_sequence_privilege(current_user,c.oid,'USAGE'),has_sequence_privilege(current_user,c.oid,'SELECT')
 FROM pg_sequences s JOIN pg_namespace n ON n.nspname=s.schemaname JOIN pg_class c ON c.relnamespace=n.oid AND c.relname=s.sequencename
 WHERE s.schemaname IN ('ingest','football','analytics') ORDER BY 1 LIMIT 68"""

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inspect-ingest', action='store_true')
    args = parser.parse_args()
    if not args.inspect_ingest:
        print(json.dumps({'status': 'offline_plan', 'connections': 0, 'writes': []}))
        return 0
    run = BASE / 'actor-readbacks' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    run.mkdir(parents=True)
    report = {'kind': 'actual_rds_ingest_actor_readonly_probe', 'command': ['python3', str(Path(__file__)), '--inspect-ingest'],
              'expected': 'PLAN.md', 'sql': [IDENTITY, SEQUENCES], 'selects': 0, 'writes': [], 'fullAcceptance': False}
    connection = None
    private_path = None
    try:
        assert not any(k.startswith('PG') for k in os.environ), 'Inherited libpq options refused'
        with private_authentication() as path:
            private_path = path
            import psycopg
            address = sorted({v[4][0] for v in socket.getaddrinfo(HOST, 5432, type=socket.SOCK_STREAM)})[0]
            connection = psycopg.connect(host=HOST,hostaddr=address,port=5432,dbname=DATABASE,user=ACTOR,passfile=str(path),sslmode='verify-full',
                sslrootcert=str(ROOT/'dashboard/backend/certs/rds-us-east-2.pem'),autocommit=True,connect_timeout=7,
                options='-c default_transaction_read_only=on -c statement_timeout=8000 -c lock_timeout=1000 -c timezone=UTC')
            with connection.transaction():
                connection.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
                report['selects'] += 1
                identity = connection.execute(IDENTITY).fetchone()
                assert identity[:10] == (DATABASE, ACTOR, ACTOR, '180006', 'on', 'repeatable read', '8s', '1s', True, False)
                assert identity[10:] == (True, True, False)
                report['identity'] = identity
                report['selects'] += 1
                rows = list(connection.execute(SEQUENCES))
                assert len(rows) == 67 and all(r[1:4] == (1, False, 1) for r in rows)
                report['sequenceMetadata'] = rows
                report['decodedBytes'] = len(json.dumps([identity,rows],default=str).encode())
                assert report['decodedBytes'] <= 32768
            connection.close()
        report['status'] = 'pass'
    except Exception as error:
        report.update(status='fail', errorType=type(error).__name__, sqlstate=getattr(error, 'sqlstate', None))
    finally:
        if connection is not None:
            connection.close()
        report['connectionClosed'] = connection is None or connection.closed
        report['privateAuthenticationRemoved'] = private_path is None or not private_path.exists()
        (run/'result.json').write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps({'status':report['status'],'selects':report['selects'],'decodedBytes':report.get('decodedBytes'),'evidence':str(run/'result.json')}))
    return 0 if report['status']=='pass' else 1

if __name__ == '__main__':
    raise SystemExit(main())
