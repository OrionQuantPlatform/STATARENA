#!/usr/bin/env python3
"""Actual adapter launcher with native TLS actor/endpoint and I/O fences."""
from __future__ import annotations
import builtins
import io
import json
import os
from pathlib import Path
import re
import runpy
import socket
import subprocess
import sys

sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[3]
sys.path[:0] = [str(ROOT / "dashboard/scripts"), "/tmp/statarena-publication-test-python", str(BASE.parent / "product-campaign")]
import psycopg
from workflow_budget import SharedBudget

run = Path(os.environ["ORION_REAL_E2E_RUN"]).resolve()
assert run.is_relative_to(BASE / "runtime-runs")
marker = json.loads((run / "endpoint.json").read_text())
stage = os.environ["ORION_REAL_E2E_STAGE"]
assert stage in ["admit", "publish"]
worker = os.environ["ORION_REAL_E2E_WORKER"]
assert worker in ["worker1", "worker2"]
budget = SharedBudget(run / "budget.json")
trace = run / (worker + "-sql.jsonl")
access_file = run / (worker + "-access.jsonl")
original_open = builtins.open
original_io_open = io.open


def denied(kind):
    with original_open(access_file, "a") as out:
        out.write(json.dumps({"kind": kind}) + "\n")
    raise RuntimeError("Unexpected non-owned operation: " + kind)


allowed_writes = {"analytics.aggregation_builds", "analytics.match_summary", "analytics.competition_summary",
                  "analytics.publication_versions", "analytics.catalog_publication"} if stage == "publish" else {
                  "football.matches", "football.match_teams", "football.match_players", "football.competition_teams",
                  "ingest.public_aliases", "ingest.dirty_editions", "ingest.import_runs"}


def record(query, params=None):
    budget.reserve("sql")
    sql = query.decode() if isinstance(query, bytes) else query.as_string(None) if hasattr(query, "as_string") else str(query)
    cleaned = re.sub(r"/\*.*?\*/|--[^\n]*", "", sql, flags=re.S).strip()
    if ";" in cleaned.rstrip(";") or re.match(r"(?is)^(CREATE|ALTER|DROP|TRUNCATE|GRANT|REVOKE|DELETE)\b", cleaned):
        denied("forbidden_sql")
    if re.match(r"(?is)^(SET|RESET)\s+(ROLE|SESSION|statement_timeout|lock_timeout|idle_in_transaction_session_timeout)\b", cleaned):
        denied("changed_actor_or_deadline")
    for _, target in re.findall(r'(?is)\b(INSERT\s+INTO|UPDATE|COPY)\s+([\w.\"]+)', cleaned):
        if target.replace('"', '').lower() not in allowed_writes:
            denied("unexpected_write_target")
    with original_open(trace, "a") as out:
        out.write(json.dumps({"sql": sql, "stage": stage, "parameterTypes": [type(v).__name__ for v in params] if isinstance(params, (tuple, list)) else type(params).__name__}) + "\n")


class Cursor(psycopg.Cursor):
    def execute(self, query, params=None, **kwargs):
        record(query, params)
        result = super().execute(query, params, **kwargs)
        if self.pgresult is not None:
            assert self.pgresult.ntuples <= 1000, "A large business result requires a bounded server cursor"
        return result

    def executemany(self, query, params_seq, **kwargs):
        values = list(params_seq)
        assert len(values) <= 1000, "Business write batches stay bounded"
        for params in values:
            record(query, params)
        return super().executemany(query, values, **kwargs)

    def copy(self, statement, params=None, **kwargs):
        record(statement, params)
        return super().copy(statement, params, **kwargs)

    def fetchall(self):
        rows = super().fetchall()
        self.observe_fetch(rows)
        return rows

    def fetchmany(self, size=None):
        rows = super().fetchmany() if size is None else super().fetchmany(size)
        self.observe_fetch(rows)
        return rows

    def observe_fetch(self, rows):
        with original_open(run / (worker + "-fetch.jsonl"), "a") as out:
            out.write(json.dumps({"stage": stage, "rows": len(rows)}) + "\n")
        assert len(rows) <= 1000, "No inherited5000 cutoff or unbounded native row fetch"


class ServerCursor(psycopg.ServerCursor):
    def execute(self, query, params=None, **kwargs):
        # DECLARE is sent directly by psycopg; the native Connection path below
        # independently records every later FETCH/CLOSE command.
        record(query, params)
        return super().execute(query, params, **kwargs)

    def _fetch_gen(self, num):
        assert type(num) is int and 0 < num <= 1000, "Server cursor fetches must be bounded"
        rows = yield from super()._fetch_gen(num)
        with original_open(run / (worker + "-fetch.jsonl"), "a") as out:
            out.write(json.dumps({"stage": stage, "rows": len(rows), "serverCursor": True}) + "\n")
        return rows


original_connection = psycopg.Connection


class Connection(original_connection):
    def _exec_command(self, command, *args, **kwargs):
        record(command)
        return (yield from super()._exec_command(command, *args, **kwargs))

    @classmethod
    def connect(cls, conninfo="", **kwargs):
        # libpq uses C sockets; the native connection guard, not Python socket
        # monkeypatching alone, pins both the hostname and actual address.
        with original_open(run / (worker + "-driver.jsonl"), "a") as out:
            out.write(json.dumps({"stage": stage, "called": True}) + "\n")
        assert not conninfo, "Free DSNs are not an owned native interface"
        assert kwargs.get("host") == kwargs.get("hostaddr") == "127.0.0.1"
        assert int(kwargs.get("port", 0)) == marker["port"] and kwargs.get("dbname") == marker["database"]
        assert kwargs.get("user") == "statarena_ingest" and kwargs.get("sslmode") == "verify-full"
        assert re.fullmatch(r"[a-z_][a-z0-9_]{0,63}", kwargs.get("application_name", ""))
        assert Path(kwargs["sslrootcert"]).resolve() == Path(marker["caPath"]).resolve()
        assert not kwargs.get("service") and not kwargs.get("password")
        options = kwargs.get("options", "")
        assert all(v in options for v in ["statement_timeout=8000", "lock_timeout=1000", "idle_in_transaction_session_timeout=5000"])
        kwargs.update(cursor_factory=Cursor, connect_timeout=2, passfile=os.devnull)
        connection = super().connect(**kwargs)
        connection.server_cursor_factory = ServerCursor
        return connection


psycopg.Connection = Connection
psycopg.connect = Connection.connect


def permitted(path, mode):
    if isinstance(path, int):
        return True
    target = Path(path).resolve()
    if target.is_relative_to(run):
        return target.suffix in [".json", ".jsonl", ".log", ".tmp", ".release"] or target.name.endswith(".lock")
    if any(v in mode for v in ["w", "a", "+", "x"]):
        return False
    if target == (ROOT / "docs/architecture/orion-plan-20261104/target-schema.proposed.json") or target == Path(marker["caPath"]).resolve():
        return True
    code_roots = [Path(sys.base_prefix), Path("/tmp/statarena-publication-test-python"), ROOT / "dashboard/scripts"]
    return target.suffix in [".py", ".pyc", ".so", ".dylib"] and any(target.is_relative_to(p.resolve()) for p in code_roots)


def opened(path, mode="r", *args, **kwargs):
    if not permitted(path, mode):
        denied("file_access")
    return original_open(path, mode, *args, **kwargs)


def io_opened(path, mode="r", *args, **kwargs):
    if not permitted(path, mode):
        denied("path_access")
    return original_io_open(path, mode, *args, **kwargs)


builtins.open = opened
io.open = io_opened
socket.socket.connect = lambda *args, **kwargs: denied("python_socket")
socket.getaddrinfo = lambda *args, **kwargs: denied("dns_discovery")
subprocess.Popen = lambda *args, **kwargs: denied("subprocess")
target = ROOT / "dashboard/scripts" / ("orion_pro_admit_real.py" if stage == "admit" else "orion_pro_publish_real.py")
sys.argv = [str(target), *sys.argv[1:]]
runpy.run_path(str(target), run_name="__main__")
