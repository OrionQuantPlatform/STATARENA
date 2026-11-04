"""Replay a saved, previously rejected real player response via the partition publisher."""

import gzip
import json
import os
import subprocess
import sys
from pathlib import Path

import psycopg

folder = Path(__file__).resolve().parent
root = folder.parents[2]
phase = sys.argv[1]
suite = folder.parent / "aws-rematerialize-20261104/verify.py"
ns = {"__file__": str(Path(__file__).resolve()), "__name__": "__main__"}
try:
    exec(compile(suite.read_text(), str(suite), "exec"), ns)  # noqa: S102 (trusted local E2E)
except SystemExit as end:
    assert not end.code, end
actual = json.loads(gzip.decompress((folder / "source.json.gz").read_bytes()))
mid = actual["endpoint"].split("/")[2]
pid = actual["endpoint"].split("/")[4]
value = actual["data"]
receipt = {"passed": False, "checks": [], "sourceSha256": actual["sourceSha256"]}
with psycopg.connect(os.environ["TEST_DATABASE_URL"], autocommit=True) as db:
    ns["db"] = db
    ns["store"].db = db
    ns["worker"]()
    ns["fixture"](mid, dict(ns["base"]["fixture"], id=mid), False)
    single = {"status": 200, "data": value, "error": None}
    ns["resource"](actual["endpoint"], single)
    cases = [
        dict(value),
        dict(value, position_id=0),
        dict(value, position_id=None),
        {k: v for k, v in value.items() if k != "position_id"},
    ]
    batch = {"status": 200, "data": cases, "error": None}
    ns["resource"]("/matches/" + mid + "/players", batch)
    ns["mark"]()
    initial = db.execute("select generation from statarena_app.publications").fetchone()
    try:
        ns["worker"]()
    except ValueError as e:
        receipt["error"] = str(e)
        assert (
            db.execute("select generation from statarena_app.publications").fetchone()
            == initial
        )
        assert (
            db.execute(
                "select count(*) from statarena.dirty_partitions where season=%s and league_id=%s",
                (ns["season"], ns["league"]),
            ).fetchone()[0]
            == 1
        )
        receipt["checks"].append("failed publication kept generation and dirty marker")
    else:

        def read(family, subject):
            return db.execute(
                "select statarena_app.detail_response(f) from statarena_app.match_families f where match_id=%s and family=%s and subject_id=%s and params='{}'",
                (mid, family, subject),
            ).fetchone()[0]

        assert read("single_player", pid) == single and read("players", "") == batch
        receipt["checks"].append(
            "saved individual and full player array JSON equal input with independent positions"
        )
        db.execute(
            (
                root / "dashboard/backend/migrations/008_match_player_position.sql"
            ).read_text()
        )
        assert read("single_player", pid) == single and read("players", "") == batch
        receipt["checks"].append("008 replay preserves explicit null, zero and absence")
        subprocess.run([sys.executable, str(folder / "old_rows.py")], check=True)
        receipt["checks"].append(
            "pre-008 row from sealed 007 writer retains absence after migration"
        )
        receipt["passed"] = True
(folder / phase / "player-position.json").write_text(
    json.dumps(receipt, indent=2) + "\n"
)
print(receipt)
sys.exit(not receipt["passed"])
