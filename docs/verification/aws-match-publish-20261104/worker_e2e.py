"""Run the existing 16 real worker workflows with one passive COPY counter."""

import hashlib
import json
import os
import sys
from pathlib import Path

import psycopg

folder = Path(__file__).resolve().parent
source = folder.parent / "aws-rematerialize-20261104/verify.py"
phase = sys.argv[1]
path = folder / phase
copy = psycopg.Cursor.copy
starts = 0
late_starts = 0
measuring_late = False


def counted(self, statement, *args, **kwargs):
    global starts, late_starts
    if "COPY statarena_app.event_sheets " in str(statement):
        if measuring_late:
            late_starts += 1
        frame = sys._getframe(1)
        while frame is not None:
            if (
                frame.f_code.co_name == "interleaved"
                and frame.f_code.co_filename == str(source)
            ):
                starts += 1
                break
            frame = frame.f_back
    return copy(self, statement, *args, **kwargs)


ns = {"__file__": str(Path(__file__).resolve()), "__name__": "__main__"}
psycopg.Cursor.copy = counted
try:
    # Preserve the reference suite's root and redirect its output to this receipt.
    exec(compile(source.read_text(), str(source), "exec"), ns)  # noqa: S102 (trusted, pinned local verification suite)
except SystemExit as end:
    successful = not end.code
finally:
    psycopg.Cursor.copy = copy
# The suite closed its temporary DB handle; reuse its normal staging fixtures
# and worker entrypoint against the same disposable local database.
late = {}
with psycopg.connect(os.environ["TEST_DATABASE_URL"], autocommit=True) as conn:
    ns["db"] = conn
    ns["store"].db = conn
    ns["worker"]()
    ids = [f"m_{980000 + i:06d}" for i in range(18)]
    for mid in ids:
        fx = dict(ns["base"]["fixture"], id=mid, date="2099-01-01")
        ns["fixture"](mid, fx, False)
        if mid != ids[-1]:
            ns["resource"](
                "/matches/" + mid + "/events",
                {"status": 200, "data": {"match_id": mid, "events": []}},
            )
    bad = "/matches/" + ids[-2] + "/unknown-provider-resource"
    ns["resource"](bad, {"status": 200, "data": {}})
    ns["mark"]()
    original = conn.execute(
        "select generation from statarena_app.publications"
    ).fetchone()
    recorded = conn.execute(
        "select * from statarena_app.worker_inputs where kind='partition' order by 2"
    ).fetchall()
    measuring_late = True
    psycopg.Cursor.copy = counted
    try:
        ns["worker"]()
    except ValueError as exc:
        assert "Unmapped saved match endpoint" in str(exc), exc
    else:
        raise AssertionError("unknown saved variant was acknowledged")
    finally:
        psycopg.Cursor.copy = copy
        measuring_late = False
    assert late_starts > 0
    assert (
        conn.execute("select generation from statarena_app.publications").fetchone()
        == original
    )
    assert (
        conn.execute(
            "select * from statarena_app.worker_inputs where kind='partition' order by 2"
        ).fetchall()
        == recorded
    )
    assert (
        conn.execute(
            "select count(*) from statarena_app.match_details where match_id=any(%s)",
            (ids,),
        ).fetchone()[0]
        == 0
    )
    assert (
        conn.execute(
            "select count(*) from statarena.dirty_partitions where season=%s and league_id=%s",
            (ns["season"], ns["league"]),
        ).fetchone()[0]
        == 1
    )
    conn.execute("delete from statarena.resources where endpoint=%s", (bad,))
    ns["worker"]()
    assert (
        conn.execute(
            "select count(*) from statarena_app.match_details where match_id=any(%s)",
            (ids,),
        ).fetchone()[0]
        == 17
    )
    assert (
        conn.execute(
            "select count(*) from statarena_app.match_details where match_id=%s",
            (ids[-1],),
        ).fetchone()[0]
        == 0
    )
    late = {
        "copiedGroupsBeforeFailure": late_starts,
        "generationPreserved": True,
        "partitionReceiptsPreserved": True,
        "dirtyMarkerPreserved": True,
        "repairedMatches": 17,
        "emptyFixtureHasNoDetailHeader": True,
    }
results = json.loads((path / "results.json").read_text())
passed = successful and results["pass"] == results["total"] == 16 and 1 <= starts <= 5
receipt = {
    "suiteSha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    "setup": "PROTOCOL.md, production partition entry point, PostgreSQL 18, retained source bodies",
    "command": "node docs/verification/aws-match-publish-20261104/worker.mjs " + phase,
    "workerCasesPassed": results["pass"],
    "workerCases": results["total"],
    "interleavedEventSheetCopies": starts,
    "expectedMax": 5,
    "lateUnknownVariant": late,
    "passed": passed,
}
(path / "batch-integration.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(receipt)
sys.exit(not passed)
