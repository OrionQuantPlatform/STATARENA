import contextlib
import importlib.util
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("aws_database_bootstrap", ROOT / ".github/actions/aws-database/bootstrap.py")
bootstrap = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bootstrap)


class AwsSqlBootstrapTest(unittest.TestCase):
    def test_sql_only_does_not_request_s3_credentials(self):
        db = {"host": "sample.abcdef.us-east-2.rds.amazonaws.com", "database": "statarena_prod",
              "username": "statarena_ingest", "password": "local-test-password"}

        def parameter(name):
            if name != "rds-ingest":
                raise AssertionError("SQL-only bootstrap must not read S3 credentials")
            return db

        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "github-env"
            env = {"GITHUB_WORKSPACE": str(ROOT), "GITHUB_ENV": str(target), "STATARENA_SQL_ONLY": "1"}
            with patch.dict(os.environ, env, clear=True), patch.object(bootstrap, "parameter", side_effect=parameter), contextlib.redirect_stdout(io.StringIO()):
                bootstrap.bootstrap("ingest")
            output = target.read_text()
            self.assertIn("STATARENA_SQL_ONLY<<", output)
            self.assertIn("STATARENA_SQL_DOCUMENTS<<", output)
            self.assertNotIn("NEON_STORAGE_", output)


if __name__ == "__main__":
    unittest.main()
