"""Owned-test counters and connection tracing; never imported by product code."""
from __future__ import annotations
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import time

LIMITS={'sql':1500,'http':200,'typedRows':5000,'builds':20,'matchSummaries':100,'editionSummaries':20,'generations':24,'publications':30}
OPTIONS='-c statement_timeout=8000 -c lock_timeout=1000 -c idle_in_transaction_session_timeout=5000'


class LimitExceeded(RuntimeError):pass


class SharedBudget:
    def __init__(self,path,*,create=False):
        self.path=Path(path);self.lock=self.path.with_suffix('.lock')
        if create:
            self.path.write_text(json.dumps({'deadlineEpoch':time.time()+600,'limits':LIMITS,'counts':{'sql':0,'http':0},'violations':[]})+'\n')

    @contextmanager
    def locked(self):
        start=time.monotonic()
        while True:
            try:self.lock.mkdir();break
            except FileExistsError:
                if time.monotonic()-start>1:raise LimitExceeded('Shared budget lock exceeded1s')
                time.sleep(.005)
        try:yield
        finally:self.lock.rmdir()

    def read(self):return json.loads(self.path.read_text())

    def reserve(self,kind,amount=1):
        with self.locked():
            data=self.read()
            if time.time()>data['deadlineEpoch']:raise LimitExceeded('10-minute workflow deadline reached')
            value=data['counts'][kind]+amount
            if value>data['limits'][kind]:raise LimitExceeded(f'{kind} budget exceeded')
            data['counts'][kind]=value
            temp=self.path.with_suffix(f'.{os.getpid()}.tmp');temp.write_text(json.dumps(data)+'\n');temp.replace(self.path)

    def check(self):
        data=self.read()
        if time.time()>data['deadlineEpoch']:raise LimitExceeded('10-minute workflow deadline reached')
        return data


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()


def connection_factory(psycopg,budget,trace_file,*,phase,owned_port,role,policy=False):
    """All actual main/worker connections get startup deadlines and role binding."""
    import re
    trace_file=Path(trace_file)
    allowed_writes={'analytics.aggregation_builds','analytics.match_summary','analytics.competition_summary',
                    'analytics.publication_versions','analytics.catalog_publication'}
    def record(query,params=None,amount=1):
        text=query.decode() if isinstance(query,bytes) else query.as_string(None) if hasattr(query,'as_string') else str(query)
        if phase()=='operational':budget.reserve('sql',amount)
        if policy:
            cleaned=re.sub(r'/\*.*?\*/|--[^\n]*','',text,flags=re.S).strip()
            if ';' in cleaned.rstrip(';'):raise LimitExceeded('Publisher multi-command SQL is not allowed in this bounded harness')
            if re.match(r'(?is)^(CREATE|ALTER|DROP|TRUNCATE|GRANT|REVOKE|DELETE)\b',cleaned):raise LimitExceeded('Publisher attempted forbiddenDDL/grant/delete')
            if re.match(r'(?is)^(SET|RESET)\s+(ROLE|SESSION|statement_timeout|lock_timeout|idle_in_transaction_session_timeout)\b',cleaned):raise LimitExceeded('Publisher attempted to change role/deadlines')
            for _,target in re.findall(r'(?is)\b(INSERT\s+INTO|UPDATE|COPY)\s+([\w.\"]+)',cleaned):
                if target.replace('"','').lower() not in allowed_writes:raise LimitExceeded('Publisher attempted business/admission/dirty mutation')
        row={'phase':phase(),'sql':text,'parameterTypes':[type(v).__name__ for v in params] if isinstance(params,(tuple,list)) else type(params).__name__,
             'parametersSha256':digest(params),'statementCalls':amount}
        with trace_file.open('a') as out:out.write(json.dumps(row)+'\n')
    class Cursor(psycopg.Cursor):
        def execute(self,query,params=None,**kwargs):record(query,params);return super().execute(query,params,**kwargs)
        def executemany(self,query,params_seq,**kwargs):
            params=list(params_seq)
            if len(params)>5000:raise LimitExceeded('Publisher batch exceeds typed-row cap')
            record(query,params,len(params));return super().executemany(query,params,**kwargs)
        def copy(self,statement,params=None,**kwargs):record(statement,params);return super().copy(statement,params,**kwargs)
    real_class=psycopg.Connection
    class Connection(real_class):
        def _exec_command(self,command,*args,**kwargs):
            # psycopg uses this internal path for BEGIN/COMMIT/savepoints. They
            # are real operations and must reserve the same shared budget.
            record(command)
            return (yield from super()._exec_command(command,*args,**kwargs))
        @classmethod
        def connect(cls,conninfo='',**kwargs):
            info=psycopg.conninfo.conninfo_to_dict(conninfo,**{k:v for k,v in kwargs.items() if k not in {'autocommit','row_factory','cursor_factory','context','prepare_threshold'}})
            assert info.get('host')=='127.0.0.1' and int(info.get('port',0))==owned_port,'Only owned loopback PostgreSQL is allowed'
            assert info.get('dbname')=='postgres' and info.get('user')==role,'Unexpected DB/role'
            assert not info.get('password'),'This owned fixture uses no password credential'
            options=info.get('options','')
            assert 'statement_timeout=8000' in options and 'lock_timeout=1000' in options,'Startup deadlines required'
            kwargs['cursor_factory']=Cursor;kwargs['connect_timeout']=2;kwargs['passfile']=os.devnull
            return super().connect(conninfo,**kwargs)
    return Connection
