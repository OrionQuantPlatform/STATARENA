#!/usr/bin/env python3
"""Separately released one-function RDS adoption; default mode is offline."""
from __future__ import annotations
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import signal
import stat
import sys
import tempfile
import time
from datetime import datetime, timezone

sys.dont_write_bytecode = True
import adapter as policy
import root_readonly as authentication

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
RELEASE = BASE / 'ROOT_RDS_TRANSITION_RELEASE.json'
LEDGER = BASE / 'rds-adoption-budget-v1.json'
AUTH_HELPER_SHA = '699ff24507aae1911db43ca446b2156a163ad63dfb6a14e5d89b95fab0e841be'
LIMITS = {'connections': 2, 'observations': 3, 'selects': 47, 'explicitExecuteCalls': 51,
          'transactionControls': 4, 'decodedBytes': 12582912, 'metadataBytes': 33554432,
          'transientReserveBytes': 8388608, 'seconds': 180, 'statementMs': 8000, 'lockMs': 1000}

def target():
    return {'host': policy.HOST, 'port': 5432, 'database': policy.DATABASE, 'actor': policy.ACTOR,
            'engine': 180006, 'sslmode': 'verify-full', 'caSha256': policy.sha(policy.CA)}

def load_release():
    try:
        value = policy.json_file(RELEASE, 65536)
    except (OSError, policy.Refusal):
        raise policy.Refusal('RELEASE', 'Separate fixed ROOT native RDS release required') from None
    policy.require(value.get('kind') == 'root_rds_one_function_adoption_release_v1' and
                   value.get('authorizedBy') == 'ROOT' and value.get('scope') == 'fixed014_and_one_journal_row_only' and
                   value.get('target') == target() and value.get('proEnabled') is False and value.get('collectorsEnabled') is False and
                   value.get('operatorSha256') == policy.sha(Path(__file__)) and
                   value.get('adapterSha256') == policy.sha(BASE / 'adapter.py') and
                   re.fullmatch('[a-f0-9]{40}', value.get('codeCommit', '')) and
                   value.get('nativeReviewSha256') == policy.sha(BASE / 'ROOT_RDS_NATIVE_BASELINE_REVIEW.json') and
                   value.get('controlsSha256') == policy.sha(BASE / 'ROOT_LIVE_CONTROLS.json') and
                   policy.sha(Path(authentication.__file__)) == AUTH_HELPER_SHA,
                   'RELEASE', 'Exact code/native baseline/target binding differs')
    policy.fixed_inputs()
    return value

def claim():
    try:
        policy.require(stat.S_ISREG(LEDGER.lstat().st_mode), 'CHECKPOINT', 'Regular one-shot ledger required')
        with LEDGER.open('r+') as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            value = json.load(stream)
            policy.require(value == {'kind': 'rds_native_adoption_one_shot_v1', 'state': 'unstarted',
                                     'executions': 0, 'releaseSha256': policy.sha(RELEASE)},
                           'CHECKPOINT', 'Native adoption allocation missing/mismatched/consumed')
            value.update(state='claimed', executions=1, startedAt=datetime.now(timezone.utc).isoformat())
            stream.seek(0)
            json.dump(value, stream, indent=2)
            stream.truncate()
    except (OSError, ValueError):
        raise policy.Refusal('CHECKPOINT', 'Native adoption allocation unavailable') from None

def native_contract(release):
    review = policy.json_file(BASE / 'ROOT_RDS_NATIVE_BASELINE_REVIEW.json')
    policy.require(review['status'] == 'accepted_native_bootstrap_only_no_write_authority' and all(review['checks'].values()),
                   'RELEASE', 'Reviewed real RDS bootstrap required')
    readback = ROOT / review['readonlyReceiptPath']
    prepared = ROOT / review['preparedP1ContractPath']
    policy.require(readback.is_relative_to(BASE / 'rds-readbacks') and prepared.is_relative_to(BASE / 'runs') and
                   policy.sha(readback) == review['readonlyReceiptSha256'] and policy.sha(prepared) == review['preparedP1ContractSha256'],
                   'RELEASE', 'Native/P1 reference bytes differ')
    original = policy.json_file(readback)
    source = original['nativeComplement']
    policy.require(original['connectionClosed'] is True and policy.state_hash(source) == review['nativeStateSha256'],
                   'RELEASE', 'Accepted native RDS state differs')
    controls = policy.json_file(BASE / 'ROOT_LIVE_CONTROLS.json')
    policy.require(controls['lambda']['proApi'] != '1' and controls['lambda']['state'] == 'Active' and
                   controls['workflows']['disabledManually'] == 11 and controls['workflows']['activeNames'] == ['Dependency Graph', 'Verify ingestion'],
                   'RELEASE', 'Observed production controls are not closed')
    template = policy.json_file(prepared)
    policy.require(hashlib.sha256(template['p1Definition'].encode()).hexdigest() == review['p1DefinitionSha256'] and
                   template['adapterSha256'] == policy.sha(BASE / 'adapter.py'),
                   'RELEASE', 'Only the reviewed function definition may be borrowed from local qualification')
    caps = {name: len(rows) + 1 for name, rows in source['groups'].items()}
    caps.update(journal=4, bootstrap=32, nonbootstrap=90, concurrency=129)
    contract = {'baseline': policy.stable(source), 'rowCaps': caps, 'p1Definition': template['p1Definition'],
                'releaseCommit': release['codeCommit']}
    return contract, review['nativeStateSha256'], source['groups']['identity'][0]['started_at']

def execute(release):
    started = time.monotonic()
    out = BASE / 'rds-adoption' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out.mkdir(parents=True)
    report = {'kind': 'real_rds_native014_adoption_v1', 'status': 'unverified', 'limits': LIMITS,
              'command': [sys.executable, str(Path(__file__)), '--execute-released-rds'],
              'releaseSha256': policy.sha(RELEASE), 'connections': 0, 'explicitExecuteCalls': 0, 'selects': 0,
              'observations': [], 'decodedBytes': 0, 'maxRetainedMetadataBytes': 0,
              'remoteBusinessWrites': [], 'fullAcceptance': False}
    states = []
    connections = []
    private_path = None
    original_observe = policy.observe
    contract = None

    def within_wall():
        policy.require(time.monotonic() - started < LIMITS['seconds'], 'BOUND', 'Native adoption wall allocation exceeded')

    class Counted:
        def __init__(self, connection):
            self.connection = connection
        def __getattr__(self, key):
            return getattr(self.connection, key)
        def execute(self, sql, *args, **kwargs):
            within_wall()
            report['explicitExecuteCalls'] += 1
            report['selects'] += int(sql.lstrip().upper().startswith(('SELECT', 'WITH')))
            policy.require(report['explicitExecuteCalls'] <= LIMITS['explicitExecuteCalls'] and
                           report['selects'] <= LIMITS['selects'], 'BOUND', 'Native execute/SELECT allocation exceeded')
            return self.connection.execute(sql, *args, **kwargs)

    def observed(*args, **kwargs):
        state = original_observe(*args, **kwargs)
        states.append(state)
        report['decodedBytes'] += state['budget']['decodedBytes']
        retained = policy.metadata_bytes(contract, states, report)
        report['maxRetainedMetadataBytes'] = max(report['maxRetainedMetadataBytes'], retained)
        policy.require(len(report['observations']) + len(states) <= LIMITS['observations'] and
                       report['decodedBytes'] <= LIMITS['decodedBytes'] and
                       retained + LIMITS['transientReserveBytes'] <= LIMITS['metadataBytes'],
                       'BOUND', 'Native observation byte/metadata allocation exceeded')
        return state

    def store_states():
        for state in states:
            path = out / ('native-' + str(len(report['observations'])) + '.json')
            with path.open('w') as stream:
                json.dump(state, stream, ensure_ascii=False, separators=(',', ':'))
            report['observations'].append({'path': str(path.relative_to(ROOT)), 'sha256': policy.sha(path),
                                           'budget': state['budget'], 'stateSha256': policy.state_hash(state)})
        states.clear()

    try:
        contract, expected, epoch = native_contract(release)
        acceptance = {'beforeStateSha256': expected}
        identity = authentication.aws('sts', 'get-caller-identity')
        policy.require(identity['Account'] == '361769570630' and identity['Arn'] == 'arn:aws:iam::361769570630:user/hugo.lemonnier',
                       'IDENTITY', 'Expected AWS account/actor required')
        report['awsIdentity'] = {k: identity[k] for k in ['Account', 'Arn']}
        raw = authentication.aws('ssm', 'get-parameter', '--name', '/statarena/app/rds-admin', '--with-decryption')
        data = json.loads(raw['Parameter']['Value'])
        password = data.get('password')
        policy.require((data.get('username') or data.get('user')) == policy.ACTOR and isinstance(password, str) and
                       bool(password) and not any(c in password for c in '\r\n\x00'), 'AUTH', 'Private authentication metadata differs')
        def escaped(value):
            return str(value).replace('\\', '\\\\').replace(':', '\\:')
        with tempfile.TemporaryDirectory(prefix='orion-rds-adoption-private-', dir='/tmp') as private:
            private_path = Path(private)
            private_path.chmod(0o700)
            path = private_path / 'auth.pgpass'
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, 'w') as stream:
                stream.write(':'.join(escaped(v) for v in [policy.HOST, 5432, policy.DATABASE, policy.ACTOR, password]) + '\n')
            passfile = policy.validated_rds_passfile({'ORION_RDS_PASSFILE': str(path)})
            addresses = sorted({entry[4][0] for entry in socket.getaddrinfo(policy.HOST, 5432, type=socket.SOCK_STREAM)})
            policy.require(bool(addresses), 'ROUTE', 'Fixed RDS DNS resolution required')
            import psycopg
            def connect():
                within_wall()
                policy.require(report['connections'] < 2, 'BOUND', 'Connection allocation exceeded')
                conn = psycopg.connect(**policy._rds_connection_kwargs(passfile, addresses[0]))
                connections.append(conn)
                report['connections'] += 1
                policy.require(conn.info.host == policy.HOST and conn.info.dbname == policy.DATABASE and conn.info.user == policy.ACTOR,
                               'ROUTE', 'Exact RDS route/actor differs')
                return Counted(conn)
            def native_identity(row):
                policy.require(row['database'] == policy.DATABASE and row['started_at'] == epoch,
                               'IDENTITY', 'Real RDS database/postmaster epoch differs')
            policy.observe = observed
            writer = connect()
            try:
                report['transition'] = policy._transition_core(writer, contract, acceptance, native_identity)
            except Exception as error:
                report['transitionError'] = {'type': type(error).__name__, 'code': getattr(error, 'code', None), 'sqlstate': getattr(error, 'sqlstate', None)}
            finally:
                writer.close()
            store_states()
            reader = connect()
            try:
                with reader.transaction():
                    reader.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
                    final = observed(reader, contract['rowCaps'], identity_check=native_identity)
                    classification = policy.verify_state(final, contract)
                    policy.require(final['groups']['identity'][0]['read_only'] == 'on', 'IDENTITY', 'Independent readback must be read-only')
                report['independentPolicy'] = classification
                if classification == 'P1':
                    report['status'] = 'applied_and_independently_verified' if 'transitionError' not in report else 'commit_outcome_verified_P1'
                else:
                    report['status'] = 'not_applied_P0_verified'
            finally:
                reader.close()
            store_states()
    except Exception as error:
        report['error'] = {'type': type(error).__name__, 'code': getattr(error, 'code', None), 'sqlstate': getattr(error, 'sqlstate', None)}
    finally:
        policy.observe = original_observe
        for conn in connections:
            conn.close()
        store_states()
        report['connectionsClosed'] = all(c.closed for c in connections)
        report['privateAuthenticationRemoved'] = private_path is None or not private_path.exists()
        report['elapsedSeconds'] = round(time.monotonic() - started, 3)
        report['credentialBodyArchived'] = False
        report['transactionControlsMaximum'] = 4
        result = out / 'result.json'
        policy.save(result, report)
        with LEDGER.open('r+') as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            value = json.load(stream)
            value.update(state='consumed', outcome=report['status'], result=str(result.relative_to(ROOT)))
            stream.seek(0)
            json.dump(value, stream, indent=2)
            stream.truncate()
    return report, result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-released-rds', action='store_true')
    args = parser.parse_args()
    if not args.execute_released_rds:
        print(json.dumps({'status': 'offline_plan', 'connections': 0, 'remoteWrites': [], 'fullAcceptance': False}))
        return 0
    try:
        def stopped(signum, frame):
            raise policy.Refusal('BOUND', 'Owned process supervision requested termination')
        signal.signal(signal.SIGTERM, stopped)
        policy.no_pg_environment()
        release = load_release()
        claim()
        report, path = execute(release)
        print(json.dumps({'status': report['status'], 'evidence': str(path), 'fullAcceptance': False}))
        return 0 if report['status'] in {'applied_and_independently_verified', 'commit_outcome_verified_P1'} and report['connectionsClosed'] and report['privateAuthenticationRemoved'] else 1
    except Exception as error:
        print(json.dumps({'status': 'refused', 'code': getattr(error, 'code', 'RELEASE'), 'errorType': type(error).__name__, 'fullAcceptance': False}))
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
