#!/usr/bin/env python3
"""ROOT's single read-only target descriptor observation after verified015."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import socket
import sys
import time

sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[3]


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    assert sys.argv[1:] == ['--one-readonly-observation']
    assert not any(k.startswith('PG') for k in os.environ)
    helper_path = BASE / 'target_readback.py'
    assert hashlib.sha256(helper_path.read_bytes()).hexdigest() == '82e7b6b46499962c1ba9c40c074879a4ee53b721c23e2ac1d2f7ab6383a36d08'
    assert hashlib.sha256((BASE/'TARGET_POLICY.json').read_bytes()).hexdigest() == '33b1feda0e47bf24da6c8e0c2d40160485acaac242b8c33572c3e9881a65ee83'
    helper = load(helper_path, 'root_target015_descriptor_helper')
    policy = helper.boundary.load_target_policy()
    auth = load(BASE.parent / 'ingest_actor.py', 'root015_ingest_ephemeral_auth')
    out = BASE/'target-readbacks'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    ledger = BASE/'ROOT_TARGET_READBACK_ONESHOT.json'
    command = [sys.executable, str(Path(__file__)), *sys.argv[1:]]
    with ledger.open('x') as stream:
        json.dump({'startedAtUtc':datetime.now(timezone.utc).isoformat(),'scope':'One actual RDS readonly connection; no source, RAM or database writes','command':command,'target':policy['target']['host'],'maximumSelects':8,'maximumDbSeconds':90},stream,indent=2)
        stream.write('\n')
    started = time.monotonic()
    conn = passfile = None
    report = {'kind':'root_actual015_readonly_target_descriptor','command':command,'status':'unverified','writes':[],'connections':0,'sourceCalls':0}
    def timed_out(signum, frame):
        raise TimeoutError('ROOT readonly descriptor deadline')
    signal.signal(signal.SIGALRM, timed_out)
    signal.setitimer(signal.ITIMER_REAL, 130)
    try:
        import psycopg
        host = policy['target']['host']
        addresses = sorted({r[4][0] for r in socket.getaddrinfo(host,5432,type=socket.SOCK_STREAM)})
        assert addresses
        with auth.private_authentication() as passfile:
            options = ('-c default_transaction_read_only=on -c statement_timeout=8000 -c lock_timeout=1000 '
                       '-c timezone=UTC -c datestyle=ISO,YMD -c extra_float_digits=3 '
                       '-c idle_in_transaction_session_timeout=15000')
            conn = psycopg.connect(host=host,hostaddr=addresses[0],port=5432,dbname=auth.DATABASE,user=auth.ACTOR,
                                   passfile=str(passfile),sslmode='verify-full',sslrootcert=str(ROOT/'dashboard/backend/certs/rds-us-east-2.pem'),
                                   connect_timeout=7,autocommit=True,options=options,application_name='root-real-v3-target-readback')
            report['connections'] = 1
            try:
                result = helper.read_target(conn,out,root_command=command)
                report.update(status=result['status'],targetDescriptorSha256=result['targetDescriptorSha256'],selects=result['selects'])
            finally:
                conn.close()
    except BaseException as error:
        report.update(status='fail_or_unverified',errorType=type(error).__name__,sqlstate=getattr(error,'sqlstate',None))
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        report.update(connectionClosed=conn is None or conn.closed,privateAuthRemoved=passfile is None or not passfile.exists(),elapsedSeconds=round(time.monotonic()-started,3))
        out.mkdir(parents=True,exist_ok=True)
        (out/'root-result.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({'status':report['status'],'evidence':str(out),'connectionClosed':report['connectionClosed'],'privateAuthRemoved':report['privateAuthRemoved']}))
    return 0 if report['status']=='verified_actual_p2_target_descriptor' and report['connectionClosed'] and report['privateAuthRemoved'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
