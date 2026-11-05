#!/usr/bin/env python3
"""Test-only publisher launcher/probe: exact owned DB, source/network fences."""
from __future__ import annotations
import argparse
import builtins
import io
import json
import os
from pathlib import Path
import runpy
import socket
import sys
import time

sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[2]
sys.path[:0]=[str(BASE),'/tmp/statarena-publication-test-python',str(ROOT/'dashboard/scripts')]
import psycopg
from workflow_budget import SharedBudget,OPTIONS,connection_factory


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--probe',action='store_true');parser.add_argument('publisher_args',nargs=argparse.REMAINDER)
    args=parser.parse_args();run=Path(os.environ['ORION_PUBLISHER_TEST_RUN']).resolve()
    assert run.is_relative_to(BASE/'runs')
    worker=os.environ['ORION_PUBLISHER_WORKER_ID'];assert worker in ['worker1','worker2']
    port=int(os.environ['ORION_PUBLISHER_OWNED_PORT'])
    budget=SharedBudget(run/'budget.json');trace=run/(worker+'-sql.jsonl')
    Connection=connection_factory(psycopg,budget,trace,phase=lambda:'operational',owned_port=port,role='statarena_ingest',policy=not args.probe)
    events=run/(worker+'-access.jsonl');original_open=builtins.open;original_io_open=io.open
    def access(kind,target):
        with original_open(events,'a') as f:f.write(json.dumps({'kind':kind,'targetKind':type(target).__name__})+'\n')
        raise RuntimeError('Forbidden source/file/provider access: '+kind)
    allowed_model=ROOT/'docs/architecture/orion-plan-20261104/target-schema.proposed.json'
    code_roots=[Path(sys.base_prefix).resolve(),Path('/tmp/statarena-publication-test-python').resolve(),ROOT/'dashboard/scripts',BASE]
    def permitted(file,mode):
        if isinstance(file,int):return True
        path=Path(file).resolve()
        if path.is_relative_to(run):return path.suffix in ['.json','.jsonl','.log','.release','.tmp'] or path.name.endswith('.lock')
        if any(v in mode for v in ['w','a','+','x']):return False
        if path==allowed_model:return True
        return path.suffix in ['.py','.pyc','.so','.dylib'] and any(path.is_relative_to(r) for r in code_roots)
    def opened(file,mode='r',*a,**kw):
        if not permitted(file,mode):access('file_read_or_write',file)
        return original_open(file,mode,*a,**kw)
    def io_opened(file,mode='r',*a,**kw):
        if not permitted(file,mode):access('path_read_or_write',file)
        return original_io_open(file,mode,*a,**kw)
    builtins.open=opened;io.open=io_opened
    real_connect=socket.socket.connect;real_connect_ex=socket.socket.connect_ex
    def socket_allowed(address):return isinstance(address,tuple) and address[0] in ['127.0.0.1','localhost','::1'] and address[1]==port
    def connect(sock,address):
        if not socket_allowed(address):access('network_connect',address)
        return real_connect(sock,address)
    def connect_ex(sock,address):
        if not socket_allowed(address):access('network_connect_ex',address)
        return real_connect_ex(sock,address)
    socket.socket.connect=connect;socket.socket.connect_ex=connect_ex
    psycopg.connect=Connection.connect;psycopg.Connection=Connection
    if args.probe:
        info={'worker':worker,'calibration':[]}
        for name,fn in [('sourceFile',lambda:Path('/forbidden-source-body.json').read_text()),
                        ('externalNetwork',lambda:socket.socket().connect(('192.0.2.1',443)))]:
            try:fn()
            except RuntimeError as e:assert 'Forbidden source/file/provider access' in str(e);info['calibration'].append(name)
            else:raise AssertionError('Tripwire calibration did not reject')
        # Calibration is separate from the later product request-access ledger.
        events.rename(run/(worker+'-calibration.jsonl'))
        url=os.environ['ORION_PUBLISHER_DATABASE_URL']
        with Connection.connect(url,autocommit=True) as conn:
            row=conn.execute("SELECT current_user,current_setting('statement_timeout'),current_setting('lock_timeout'),current_setting('idle_in_transaction_session_timeout')").fetchone()
            assert row==('statarena_ingest','8s','1s','5s'),row;info['settings']=list(row)
            start=time.monotonic()
            try:conn.execute('SELECT pg_advisory_xact_lock(20261105,987)')
            except psycopg.Error as e:assert e.sqlstate=='55P03';info['lockDeadline']={'sqlstate':e.sqlstate,'elapsedSeconds':round(time.monotonic()-start,3)}
            else:raise AssertionError('Contended advisory lock did not time out')
            start=time.monotonic()
            try:conn.execute('SELECT pg_sleep(9)')
            except psycopg.Error as e:assert e.sqlstate=='57014';info['statementDeadline']={'sqlstate':e.sqlstate,'elapsedSeconds':round(time.monotonic()-start,3)}
            else:raise AssertionError('Statement deadline did not cancel9s sleep')
        assert .8<=info['lockDeadline']['elapsedSeconds']<2
        assert 7.5<=info['statementDeadline']['elapsedSeconds']<9
        (run/(worker+'-probe.json')).write_text(json.dumps(info,indent=2)+'\n');return 0
    target=ROOT/'dashboard/scripts/orion_pro_publish.py'
    argv=args.publisher_args[1:] if args.publisher_args[:1]==['--'] else args.publisher_args
    sys.argv=[str(target),*argv]
    assert '--local' in argv,'Owned workflow must use local publisher mode'
    runpy.run_path(str(target),run_name='__main__')
    return 0


if __name__=='__main__':raise SystemExit(main())
