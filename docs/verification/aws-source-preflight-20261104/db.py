import json
import subprocess
from pathlib import Path
import psycopg

ROOT = Path(__file__).resolve().parents[3]


def connection():
    raw = subprocess.check_output(
        [
            "aws",
            "--profile",
            "statarena",
            "--region",
            "us-east-2",
            "ssm",
            "get-parameter",
            "--name",
            "/statarena/app/rds-runtime",
            "--with-decryption",
            "--query",
            "Parameter.Value",
            "--output",
            "text",
        ]
    )
    cfg = json.loads(raw)
    return psycopg.connect(
        host=cfg["host"],
        dbname=cfg["database"],
        user=cfg["username"],
        password=cfg["password"],
        sslmode="verify-full",
        sslrootcert=str(ROOT / "dashboard/backend/certs/rds-us-east-2.pem"),
        autocommit=True,
        connect_timeout=8,
        application_name="statarena-readonly-shape-preflight",
        options="-c default_transaction_read_only=on -c statement_timeout=15000 -c max_parallel_workers_per_gather=0",
    )
