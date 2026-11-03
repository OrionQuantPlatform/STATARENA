"""Prepare only the local disposable database used by the integration test."""
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import psycopg

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "dashboard/scripts"))
from neon_store import Store

url = urlparse(os.environ["NEON_DATABASE_URL"])
assert url.hostname in ("localhost", "127.0.0.1", "::1") and url.path == "/statarena_file_test"
assert os.environ.get("STATARENA_LOCAL_TEST") == "1" and os.environ.get("FILE_STORAGE_ROOT")
with psycopg.connect(os.environ["NEON_DATABASE_URL"], autocommit=True) as db:
    db.execute((ROOT / "dashboard/backend/migrations/001_neon.sql").read_text())
    db.execute("insert into statarena.state(name,value) values('validation_branch','true')")
store = Store()
store.put_json("raw/index.json", {"seasons": []}, hot=True)
store.put_json("computed/dashboard/index.json", {"seasons": [], "storage": "json-packed"}, hot=True)
store.db.close()
print(json.dumps({"seed": "ok"}))
