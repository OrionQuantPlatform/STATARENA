import gzip
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import psycopg

folder = Path(__file__).resolve().parent
root = folder.parents[2]
phase = sys.argv[1]
out = folder / phase
sys.path.insert(0, str(root / "dashboard/scripts"))
from relational_match import publish_match_batch, publish_match_details

source = Path(
    os.environ.get("METRIC_COPY_INPUT", "/tmp/statarena-metric-values-20261104")
)
report = {
    "status": "failed",
    "setup": "actual PostgreSQL fixture with copied published metrics; original source hashes in published-metrics.json",
    "command": "node docs/verification/aws-compact-metrics-20261104/run.mjs " + phase,
    "families": {},
    "checks": [],
}
schema = root / "dashboard/backend/migrations"
try:
    with psycopg.connect(os.environ["TEST_DATABASE_URL"], autocommit=True) as db:
        db.execute("CREATE SCHEMA statarena_app")
        for m in (
            "004_match_details.sql",
            "007_match_source_fields.sql",
            "008_match_player_position.sql",
        ):
            db.execute((schema / m).read_text())
        for i, (prefix, family, ancestors) in enumerate(
            [
                (
                    "half",
                    "player_halves",
                    ["half_sheets", "half_players", "player_periods"],
                ),
                ("player", "players", ["player_sheets", "match_players"]),
            ]
        ):
            tbl = prefix + "_stat_metrics"
            db.execute(
                "create table public."
                + tbl
                + " as table statarena_app."
                + tbl
                + " with no data"
            )
            digest = hashlib.sha256()
            with (
                gzip.open(source / (tbl + ".tsv.gz"), "rb") as f,
                db.cursor() as c,
                c.copy("COPY public." + tbl + " FROM STDIN") as copy,
            ):
                while block := f.read(1048576):
                    digest.update(block)
                    copy.write(block)
            db.execute(
                f"insert into statarena_app.match_details(match_id) select distinct 'proof_'||resource_id from public.{tbl} on conflict do nothing"
            )
            db.execute(
                f"""insert into statarena_app.match_families(resource_id,match_id,params,family,subject_id,status,has_data,has_error,error_object,error_has_code,error_has_message,source_digest) overriding system value select distinct resource_id,'proof_'||resource_id,'{{}}',%s,'',200,true,true,false,false,false,repeat('0',64) from public.{tbl}""",
                (family,),
            )
            group_tbl = prefix + "_stat_groups"
            ghash = hashlib.sha256()
            db.execute(
                "create table public."
                + group_tbl
                + " as table statarena_app."
                + group_tbl
                + " with no data"
            )
            with (
                gzip.open(source / (group_tbl + ".tsv.gz"), "rb") as gf,
                db.cursor() as gcur,
                gcur.copy("copy public." + group_tbl + " from stdin") as gc,
            ):
                while block := gf.read(1048576):
                    ghash.update(block)
                    gc.write(block)
            for idx, name in enumerate(ancestors):
                fields = "resource_id,record_no,missing,null_groups"
                vals = "resource_id,0,'{}'::text[],'{}'::text[]"
                if idx:
                    fields += ",parent_no,position"
                    vals = (
                        "resource_id,parent_no,'{}'::text[],'{}'::text[],0,parent_no"
                        if idx == len(ancestors) - 1
                        else vals + ",0,0"
                    )
                db.execute(
                    f"insert into statarena_app.{name}({fields}) select distinct {vals} from public.{group_tbl}"
                )
            db.execute(
                f"insert into statarena_app.{group_tbl} select * from public.{group_tbl}"
            )
            db.execute(f"insert into statarena_app.{tbl} select * from public.{tbl}")
            report["families"][prefix] = {
                "inputSha256": digest.hexdigest(),
                "groupSha256": ghash.hexdigest(),
                "groupRows": db.execute(
                    "select count(*) from public." + group_tbl
                ).fetchone()[0],
                "rows": db.execute(f"select count(*) from public.{tbl}").fetchone()[0],
                "beforeBytes": db.execute(
                    "select pg_total_relation_size(%s)", ("statarena_app." + tbl,)
                ).fetchone()[0],
            }
        db.execute(
            "select setval(pg_get_serial_sequence('statarena_app.match_families','resource_id'),(select max(resource_id) from statarena_app.match_families))"
        )

        def all_bodies():
            out = {}
            for family in ("players", "player_halves"):
                pairs = db.execute(
                    "select resource_id,encode(sha256(convert_to(statarena_app.detail_response(f)::text,'UTF8')),'hex') from statarena_app.match_families f where family=%s order by resource_id",
                    (family,),
                ).fetchall()
                out[family] = dict(pairs)
            return out

        db.execute("create role fixture_metric_reader")
        db.execute("grant usage on schema statarena_app to fixture_metric_reader")
        db.execute(
            "grant select on statarena_app.half_stat_metrics,statarena_app.player_stat_metrics to fixture_metric_reader"
        )
        read_started = time.monotonic()
        body_baseline = all_bodies()
        report["allBodiesBeforeSeconds"] = time.monotonic() - read_started
        migration = (schema / "009_compact_player_metrics.sql").read_text()
        if phase != "before":
            import threading
            from concurrent.futures import ThreadPoolExecutor


            prefix = migration.split("-- Backfill existing derived metrics")[0].split(
                "DO $cutover$"
            )[0]
            assert len(prefix) < len(migration)
            db.execute(prefix)

            def migration_attempt():
                with psycopg.connect(
                    os.environ["TEST_DATABASE_URL"]
                    + "?application_name=visibility_migration"
                ) as w:
                    try:
                        with w.transaction():
                            w.execute(migration)
                            raise ValueError("rollback visibility probe")
                    except ValueError:
                        pass

            with (
                ThreadPoolExecutor(max_workers=1) as pool,
                psycopg.connect(os.environ["TEST_DATABASE_URL"]) as blocker,
            ):
                blocker.execute(
                    "lock table statarena_app.compact_half_groups in share mode"
                )
                thread = pool.submit(migration_attempt)
                deadline = time.monotonic() + 12
                while not db.execute(
                    "select exists(select from pg_stat_activity where application_name='visibility_migration' and wait_event_type='Lock')"
                ).fetchone()[0]:
                    if time.monotonic() > deadline:
                        raise RuntimeError("did not observe migration COPY block")
                    time.sleep(0.025)
                try:
                    with psycopg.connect(os.environ["TEST_DATABASE_URL"]) as r:
                        r.execute("set local lock_timeout='500ms'")
                        assert (
                            r.execute(
                                "select count(*) from statarena_app.half_stat_metrics"
                            ).fetchone()[0]
                            == report["families"]["half"]["rows"]
                        )
                finally:
                    blocker.rollback()
                thread.result()
            report["checks"].append(
                "live reader proceeds during blocked backfill; failed transaction retains both heaps"
            )
            try:
                with db.transaction():
                    db.execute(
                        "update statarena_app.player_stat_metrics set missing=array_append(missing,'unknown_shape') where (resource_id,record_no)=(select resource_id,record_no from statarena_app.player_stat_metrics limit 1)"
                    )
                    db.execute(migration)
            except psycopg.errors.RaiseException as e:
                assert "typed row difference" in str(e), e
            else:
                raise AssertionError("second family corruption accepted")
            for prefix2 in ["half", "player"]:
                assert (
                    db.execute(
                        "select relkind from pg_class where oid=%s::regclass",
                        ("statarena_app." + prefix2 + "_stat_metrics",),
                    ).fetchone()[0]
                    == "r"
                )
            report["checks"].append(
                "second-family parity failure restores both original physical heaps"
            )
        dest = [
            "statarena_app.compact_" + f + "_" + t
            for f in ["half", "player"]
            for t in ["overflow", "groups", "members", "templates", "definitions"]
        ]
        assert all(
            db.execute("select count(*) from " + t).fetchone()[0] == 0 for t in dest
        )
        report["faultFixtureDeadAllocationBytes"] = sum(
            db.execute("select pg_total_relation_size(%s)", (t,)).fetchone()[0]
            for t in dest
        )
        # These destinations pre-existed only to hold the synthetic reader lock.
        # An actual first migration creates them transactionally. Reset the strictly
        # empty local fixture to measure a clean successful allocation.
        db.execute("truncate " + ",".join(dest) + " restart identity")
        start = time.monotonic()
        with db.transaction():
            db.execute(migration)
        migration_elapsed = time.monotonic() - start
        read_started = time.monotonic()
        assert all_bodies() == body_baseline
        report["allBodiesAfterSeconds"] = time.monotonic() - read_started
        with db.transaction():
            db.execute("set local role fixture_metric_reader")
            for family, total in (("half", 221906), ("player", 189510)):
                assert (
                    db.execute(
                        "select count(*) from statarena_app." + family + "_stat_metrics"
                    ).fetchone()[0]
                    == total
                )
        report["checks"].append(
            "existing SELECT-only role retains access to both compatibility views"
        )
        report["allResourceLayerDigests"] = {
            k: {
                "resources": len(v),
                "sha256": hashlib.sha256(
                    json.dumps(v, sort_keys=True).encode()
                ).hexdigest(),
            }
            for k, v in body_baseline.items()
        }
        report["migrationSeconds"] = migration_elapsed
        for prefix, v in report["families"].items():
            tbl = prefix + "_stat_metrics"
            q = f"(select * from public.{tbl} except all select * from statarena_app.{tbl}) union all (select * from statarena_app.{tbl} except all select * from public.{tbl})"
            assert (
                db.execute("select count(*) from (" + q + ") diff").fetchone()[0] == 0
            )
            assert (
                db.execute(
                    "select relkind from pg_class where oid=%s::regclass",
                    ("statarena_app." + tbl,),
                ).fetchone()[0]
                == "v"
            )
            v["afterBytes"] = db.execute(
                "select sum(pg_total_relation_size(oid))::bigint from pg_class where relnamespace='statarena_app'::regnamespace and relkind='r' and starts_with(relname,%s)",
                ("compact_" + prefix + "_",),
            ).fetchone()[0]
            expected = {
                "half": (
                    221906,
                    "5a7cae7693d51115b0df9b53104857f7b79d3c0ee4c9e2b5e0f633108ed16198",
                ),
                "player": (
                    189510,
                    "67538ed4e41dfb5fa40f3d36daeb33ee1c74625268b332251f1ff8542effbad7",
                ),
            }
            assert (v["rows"], v["inputSha256"]) == expected[prefix]
            v["differences"] = 0
            v["physicalRelations"] = {
                t.split(".")[-1]: {
                    "bytes": db.execute(
                        "select pg_total_relation_size(%s)", (t,)
                    ).fetchone()[0],
                    "rows": db.execute("select count(*) from " + t).fetchone()[0],
                }
                for t in dest
                if "compact_" + prefix + "_" in t
            }
        db.execute(migration)

        def payload(metrics):
            return {
                "status": 200,
                "error": None,
                "data": [
                    {
                        "player": {"id": "p_000001"},
                        "stats": [{"key": "test", "stats": metrics}],
                    }
                ],
            }

        weird = {
            "primary": {"key": "goals", "stat": {"type": "integer", "value": 0}},
            "again": {
                "key": "goals",
                "stat": {"type": "fraction", "value": 99999, "total": 12.5},
            },
            "third": {"stat": None},
            "fourth": {},
            "fifth": {"key": None, "stat": {"value": None, "total": None}},
            "rare": {"key": "unknown key", "stat": {"type": "decimal", "value": 3.125}},
            "no key": {"key": "", "stat": {"value": 1}},
        }
        long_label = "".join(
            hashlib.sha256(str(i).encode()).hexdigest() for i in range(140)
        )
        weird[long_label] = {
            "key": "unknown_" + long_label,
            "stat": {"type": "decimal", "value": 0.75},
        }
        weird["é"] = {"key": "new_é", "stat": {"value": 12}}
        weird["e\u0301"] = {"key": "new_e\u0301", "stat": {"value": 17}}
        weird["signed zero"] = {"key": "goals", "stat": {"value": -0.0}}
        mid = "m_099999"
        read = "select statarena_app.detail_response(f) from statarena_app.match_families f where match_id=%s and family='players'"
        publish_match_details(db, mid, {"players": payload(weird)})
        assert db.execute(read, (mid,)).fetchone()[0] == payload(weird)
        report["checks"].append(
            "typed overflow, duplicates, missing, explicit null, zero equal source"
        )
        signed = db.execute(
            "select encode(float8send(stat_value),'hex') from statarena_app.player_stat_metrics m join statarena_app.match_families f using(resource_id) where f.match_id=%s and m.metric_label='signed zero'",
            (mid,),
        ).fetchone()[0]
        assert signed == "8000000000000000", signed
        report["checks"].append(
            "unbounded source label and key, IEEE signed zero survive compact storage"
        )
        next_payload = payload(
            {"wide fractional": {"key": "goals", "stat": {"value": 2.625}}}
        )
        publish_match_batch(db, [(mid, {"players": next_payload}, None, [])])
        assert db.execute(read, (mid,)).fetchone()[0] == next_payload
        publish_match_details(db, mid, {"players": next_payload})
        report["checks"].append(
            "replacement drops obsolete overflow, retry preserves read"
        )
        prev = db.execute(read, (mid,)).fetchone()[0]
        try:
            with db.transaction():
                publish_match_details(db, mid, {"players": payload(weird)})
                raise ValueError("injected rollback")
        except ValueError:
            pass
        assert db.execute(read, (mid,)).fetchone()[0] == prev
        report["checks"].append(
            "transaction rollback leaves prior body and dictionary intact"
        )
        barrier = threading.Barrier(2)

        def concurrent(order):
            cmid = "m_RACE0" + str(order)

            def metric(f):
                inner = {
                    "key": "new_parallel_" + f,
                    "stats": {
                        "novel_" + f: {"key": "novel_" + f, "stat": {"value": 1.25}}
                    },
                }
                return (
                    {
                        "status": 200,
                        "data": [{"player": {"id": "p_000001"}, "stats": [inner]}],
                    }
                    if f == "players"
                    else {
                        "status": 200,
                        "data": {
                            "players": [
                                {
                                    "player": {"id": "p_000001"},
                                    "periods": [{"period": "1", "stats": [inner]}],
                                }
                            ]
                        },
                    }
                )

            with psycopg.connect(os.environ["TEST_DATABASE_URL"]) as c:
                c.execute("set local lock_timeout='6s'")
                barrier.wait(timeout=6)
                for f in (
                    ["players", "player_halves"]
                    if order
                    else ["player_halves", "players"]
                ):
                    publish_match_details(c, cmid, {f: metric(f)})
                    time.sleep(0.12)
            return cmid

        with ThreadPoolExecutor(max_workers=2) as pool:
            cids = list(pool.map(concurrent, [0, 1]))
        assert (
            db.execute(
                "select count(*) from statarena_app.match_families where match_id=any(%s)",
                (cids,),
            ).fetchone()[0]
            == 4
        )
        report["checks"].append(
            "reversed cross-family dictionary insertions both committed"
        )
        report["status"] = "passed"
except Exception as e:
    report["error"] = str(e)[:2000]
    raise
finally:
    (out / "results.json").write_text(json.dumps(report, indent=2) + "\n")
