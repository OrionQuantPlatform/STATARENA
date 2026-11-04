"""Check separate populated pre-008 database, including repeated additive upgrade."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import psycopg
from psycopg.conninfo import conninfo_to_dict, make_conninfo

root = Path(__file__).resolve().parents[3]
source = os.environ["TEST_DATABASE_URL"]
assert "@127.0.0.1:" in source and source.endswith("/publication_fixture")
settings = conninfo_to_dict(source)
settings["dbname"] = "player_upgrade_fixture"
url = make_conninfo(**settings)
with psycopg.connect(source, autocommit=True) as admin:
    admin.execute("CREATE DATABASE player_upgrade_fixture")
with psycopg.connect(url, autocommit=True) as db:
    db.execute("CREATE SCHEMA statarena_app")
    for name in ("004_match_details.sql", "007_match_source_fields.sql"):
        db.execute((root / "dashboard/backend/migrations" / name).read_text())
    with tempfile.TemporaryDirectory() as scratch:
        for name in (
            "relational_match",
            "relational_match_model",
            "relational_match_ddl",
        ):
            (Path(scratch) / (name + ".py")).write_bytes(
                subprocess.check_output(
                    [
                        "git",
                        "-C",
                        root,
                        "show",
                        "d74d6cbc4f:dashboard/scripts/" + name + ".py",
                    ]
                )
            )
        subprocess.run(
            [
                sys.executable,
                "-c",
                "import os,psycopg;from relational_match import publish_match_details;db=psycopg.connect(os.environ['OLD_FIXTURE']);publish_match_details(db,'m_OLD001',{'players':{'status':200,'data':[{'player':{'id':'p_OLD001','position_id':None}}]}});db.commit()",
            ],
            cwd=scratch,
            env=dict(
                os.environ,
                OLD_FIXTURE=url,
                PYTHONPATH=scratch + os.pathsep + os.environ.get("PYTHONPATH", ""),
            ),
            check=True,
        )
    q = "select statarena_app.detail_response(f) from statarena_app.match_families f where f.match_id='m_OLD001'"
    expected = db.execute(q).fetchone()[0]
    assert "position_id" not in expected["data"][0]
    db.execute(
        (
            root / "dashboard/backend/migrations/008_match_player_position.sql"
        ).read_text()
    )
    assert db.execute(q).fetchone()[0] == expected
