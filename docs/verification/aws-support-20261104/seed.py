import gzip, json, os, sys
from pathlib import Path
import psycopg

here = Path(__file__).resolve().parent
sys.path.insert(0, str(here.parents[2] / "dashboard/scripts"))
from relational_support import publish_supporting
from psycopg.types.json import Jsonb

rows = json.load(gzip.open(here / "projections.json.gz", "rt"))
with psycopg.connect(os.environ["LOCAL_FIXTURE_DB"]) as db:
    db.execute("create schema statarena")
    db.execute("create table statarena.projections(name text, params text, body jsonb)")
    with db.cursor() as cur:
        cur.executemany(
            "insert into statarena.projections values (%s,%s,%s)",
            [(n, p, Jsonb(b)) for n, p, b in rows],
        )
    initial = publish_supporting(db)
    db.commit()
    snapshot = lambda: db.execute(
        "select xmin::text, id, digest from statarena_app.support_projection order by id"
    ).fetchall()
    before = snapshot()
    second = publish_supporting(db)
    assert second["changed"] == second["rows"] == 0
    assert before == snapshot()
    n, p, b = next(row for row in rows if row[0] == "standings")
    # Replace one projection and remove its child rows, restore source to test retry and full HTTP parity.
    short = {**b, "tables": []}
    publish_supporting(db, [(n, p, short)])
    assert (
        db.execute(
            "select count(*) from statarena_app.support_standing_row r join statarena_app.support_projection p on p.id=r.projection_id where p.name=%s and p.params=%s",
            (n, p),
        ).fetchone()[0]
        == 0
    )
    publish_supporting(db, [(n, p, b)])
    db.commit()
    assert len(before) == len(snapshot())
    # First a valid replacement, then a source schema change. Roll back the entire outer transaction.
    rejection = []
    for bad, expected in [
        ({**b, "unexpected": True}, "Unknown standing fields"),
        (
            {**b, "tables": [{"name": "bad", "rows": [{"points": "bad"}]}]},
            "Invalid integer field points",
        ),
    ]:
        with db.transaction(force_rollback=True):
            try:
                publish_supporting(db, [(n, p, short)])
                publish_supporting(db, [(n, p, bad)])
            except ValueError as error:
                assert expected in str(error), str(error)
                rejection.append(str(error))
            else:
                raise AssertionError("unknown schema silently published")
    sample = db.execute(
        "select points,position,team_id from statarena_app.support_standing_row where team_id is not null order by projection_id,ordinal_1,ordinal_2 limit 1"
    ).fetchone()
    assert sample
    print(
        json.dumps(
            dict(
                initial=initial,
                repeat=second,
                rejections=rejection,
                sqlStandingsSample=dict(zip(("points", "position", "teamId"), sample)),
            )
        )
    )
    db.execute("drop schema statarena cascade")
    db.execute("create role support_reader login password 'fixture'")
    db.execute("grant usage on schema statarena_app to support_reader")
    db.execute("grant select on all tables in schema statarena_app to support_reader")
