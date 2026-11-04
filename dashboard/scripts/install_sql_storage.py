"""Install SQL-only storage and migration staging tables with a schema owner."""
import hashlib
import json
import os
from pathlib import Path

import psycopg


SCHEMA = Path(__file__).resolve().parents[1] / "backend/migrations"
PREFIXES = ("012_", "013_", "014_", "015_", "016_", "017_", "018_", "019_", "020_")


def install(db):
    installed = []
    with db.transaction():
        if not db.execute("SELECT to_regnamespace('statarena')").fetchone()[0]:
            raise RuntimeError("The existing statarena schema must be provisioned first")
        db.execute("""CREATE TABLE IF NOT EXISTS statarena.sql_storage_schema (
            version text PRIMARY KEY,digest text NOT NULL)""")
        for prefix in PREFIXES:
            (path,) = SCHEMA.glob(prefix + "*.sql")
            # Git may check files out with CRLF on Windows, unlike the Linux runner.
            source = path.read_bytes().replace(b"\r\n", b"\n")
            digest = hashlib.sha256(source).hexdigest()
            prior = db.execute("SELECT digest FROM statarena.sql_storage_schema WHERE version=%s", (path.name,)).fetchone()
            if prior:
                if prior[0] != digest:
                    raise RuntimeError("Applied SQL storage migration changed: " + path.name)
                continue
            db.execute(source.decode("utf-8"))
            db.execute("INSERT INTO statarena.sql_storage_schema(version,digest) VALUES(%s,%s)", (path.name, digest))
            installed.append(path.name)
    return installed


def main():
    # This separate credential must be able to create tables in statarena.
    # The regular publication worker does not need that privilege.
    with psycopg.connect(os.environ["STATARENA_MIGRATION_DATABASE_URL"], autocommit=True) as db:
        print(json.dumps({"installed": install(db)}), flush=True)


if __name__ == "__main__":
    main()
