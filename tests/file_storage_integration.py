"""Exercise copy removal with an isolated PostgreSQL and an S3-compatible stub."""

import hashlib
import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

import psycopg

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "dashboard" / "scripts"))
from neon_store import Store

files = {}


class ObjectServer(BaseHTTPRequestHandler):
    def do_PUT(self):
        body = self.rfile.read(int(self.headers["Content-Length"]))
        files[unquote(urlsplit(self.path).path)] = body
        self.send_response(200)
        self.send_header("ETag", '"' + hashlib.md5(body).hexdigest() + '"')
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        body = files.get(unquote(urlsplit(self.path).path))
        if body is None:
            body = b"<Error><Code>NoSuchKey</Code></Error>"
            self.send_response(404)
        else:
            self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass


server = ThreadingHTTPServer(("127.0.0.1", 0), ObjectServer)
threading.Thread(target=server.serve_forever, daemon=True).start()
env = os.environ.copy()
env.update(
    {
        "NEON_DATABASE_URL": env["TEST_DATABASE_URL"],
        "NEON_STORAGE_ENDPOINT": f"http://127.0.0.1:{server.server_port}",
        "NEON_STORAGE_BUCKET": "statarena-data",
        "NEON_STORAGE_ACCESS_KEY_ID": "fixture",
        "NEON_STORAGE_SECRET_ACCESS_KEY": "fixture",
    }
)
os.environ.update(env)


def run(*args):
    return subprocess.run(
        [sys.executable, str(ROOT / "dashboard/scripts/prune_inline_file_copies.py"), *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


try:
    with psycopg.connect(env["TEST_DATABASE_URL"], autocommit=True) as db:
        db.execute("create schema statarena")
        db.execute(
            "create table statarena.objects (path text primary key, size bigint not null, sha256 bytea not null, etag text not null, body bytea, content_type text not null, updated_at timestamptz not null default now())"
        )
        store = Store()
        for path, body in [("raw/a.json", b"alpha"), ("raw/b.json", b"bravo")]:
            store.put(path, body, hot=True)
            db.execute("update statarena.objects set body=%s where path=%s", (body, path))

        dry = run()
        assert dry.returncode == 0, dry.stderr
        assert json.loads(dry.stdout) == {"verified": 2, "bytes": 10, "updated": 0, "applied": False}
        assert db.execute("select count(*) from statarena.objects where body is not null").fetchone()[0] == 2

        db.execute("select pg_advisory_lock(97813003)")
        locked = run("--apply")
        assert locked.returncode != 0 and "collection is running" in locked.stderr
        db.execute("select pg_advisory_unlock(97813003)")

        files["/statarena-data/data/raw/b.json"] = b"broken"
        bad = run("--apply")
        assert bad.returncode != 0 and "does not match catalog" in bad.stderr
        assert db.execute("select count(*) from statarena.objects where body is not null").fetchone()[0] == 2

        files["/statarena-data/data/raw/b.json"] = b"bravo"
        applied = run("--apply")
        assert applied.returncode == 0, applied.stderr
        assert json.loads(applied.stdout) == {"verified": 2, "bytes": 10, "updated": 2, "applied": True}
        assert db.execute("select count(*) from statarena.objects where body is not null").fetchone()[0] == 0
        assert store.bytes("raw/a.json") == b"alpha"
        assert store.bytes("raw/b.json") == b"bravo"
        store.db.close()
    print(json.dumps({"status": "passed", "cases": ["dry_run", "lock", "mismatch_rollback", "apply", "read_after_apply"]}))
finally:
    server.shutdown()
    server.server_close()
