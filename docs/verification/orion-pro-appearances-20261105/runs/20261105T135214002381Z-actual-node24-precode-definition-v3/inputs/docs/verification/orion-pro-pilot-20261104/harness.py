"""Owned local PostgreSQL lifecycle and inspectable E2E evidence, no cloud access."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time


class LocalPostgres:
    def __init__(self, binaries: Path, evidence: Path):
        self.binaries, self.evidence = binaries, evidence
        self.root = Path(tempfile.mkdtemp(prefix="orion-pro-e2e-"))
        self.data, self.socket_dir = self.root / "data", self.root / "socket"
        self.socket_dir.mkdir()
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            self.port = s.getsockname()[1]
        self.dsn = f"host=127.0.0.1 port={self.port} dbname=postgres user={os.environ.get('USER', 'postgres')}"
        self.started = False
        self.commands = []

    def command(self, args, *, env=None, check=True, name="command"):
        start = time.monotonic()
        result = subprocess.run([str(x) for x in args], env=env, text=True, capture_output=True, timeout=120)
        index = len(self.commands) + 1
        entry = {"argv": [str(x) for x in args], "exit_code": result.returncode,
                 "elapsed_ms": round((time.monotonic() - start) * 1000, 3),
                 "stdout": f"{index:03d}-{name}.stdout.log", "stderr": f"{index:03d}-{name}.stderr.log"}
        self.commands.append(entry)
        (self.evidence / entry["stdout"]).write_text(result.stdout)
        (self.evidence / entry["stderr"]).write_text(result.stderr)
        (self.evidence / "commands.json").write_text(json.dumps(self.commands, indent=2) + "\n")
        if check and result.returncode:
            raise RuntimeError(f"{name}: exit {result.returncode}: {result.stderr[-2500:]}")
        return result

    def start(self):
        if not self.data.exists():
            self.command([self.binaries / "initdb", "-D", self.data, "--auth=trust", "--no-locale", "--encoding=UTF8"], name="initdb")
        self.command([self.binaries / "pg_ctl", "-D", self.data, "-l", self.evidence / "postgres.log",
                      "-o", f"-h 127.0.0.1 -p {self.port} -k {self.socket_dir} -c fsync=on", "-w", "start"], name="postgres-start")
        self.started = True

    def stop(self):
        if self.started:
            self.command([self.binaries / "pg_ctl", "-D", self.data, "-m", "fast", "-w", "stop"], name="postgres-stop")
            self.started = False

    def cleanup(self):
        self.stop()
        # The directory was made by this instance and contains no preexisting database.
        shutil.rmtree(self.root)
        return {"owned_root": str(self.root), "server_stopped": not self.started, "owned_directory_removed": not self.root.exists()}

    def migration(self, repo: Path, target="013", rollback_to=None):
        args = ["python3", repo / "dashboard/scripts/orion_pro_migrate.py", "--local", "--target", target]
        if rollback_to:
            args += ["--rollback-to", rollback_to]
        env = os.environ.copy()
        env.update(ORION_PILOT_DATABASE_URL=self.dsn, STATARENA_TEST_DATABASE="1")
        return self.command(args, env=env, name="migration" if not rollback_to else f"rollback-{rollback_to}")
