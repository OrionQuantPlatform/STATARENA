"""Exercise committed/failed publication against isolated PostgreSQL and indexed worker input."""

import copy, hashlib, json, os, sys, traceback
from collections import Counter
from pathlib import Path
import psycopg
from psycopg.types.json import Jsonb

folder = Path(__file__).resolve().parent
root = folder.parents[2]
sys.path[:0] = [str(root / "dashboard/scripts"), str(root / "tests")]
phase = sys.argv[1]
out = folder / phase
url = os.environ["TEST_DATABASE_URL"]
assert "@127.0.0.1:" in url and url.endswith("/publication_fixture")
cases = []


def case(name, fn):
    try:
        cases.append({"name": name, "pass": True, "actual": fn()})
    except Exception as e:
        cases.append(
            {
                "name": name,
                "pass": False,
                "error": str(e),
                "trace": traceback.format_exc()[-1800:],
            }
        )


def check(ok, message):
    if not ok:
        raise AssertionError(message)


def sql1(query, params=()):
    return db.execute(query, params).fetchone()[0]


class Store:
    def __init__(self, db):
        self.db = db
        self.inputs = {}
        self.reads = Counter()

    def json(self, path):
        self.reads[path] += 1
        if path not in self.inputs:
            raise FileNotFoundError(path)
        return copy.deepcopy(self.inputs[path])

    def put_json(self, *a, **kw):
        raise AssertionError("file publication forbidden")

    put = put_json


def input_(path, value, indexed=True):
    store.inputs[path] = copy.deepcopy(value)
    b = json.dumps(value).encode()
    sha = hashlib.sha256(b).digest()
    db.execute(
        "INSERT INTO statarena.objects(path,size,sha256,etag) VALUES(%s,%s,%s,'local') ON CONFLICT(path) DO UPDATE SET sha256=excluded.sha256,size=excluded.size,updated_at=clock_timestamp()",
        (path, len(b), sha),
    )
    if indexed:
        db.execute(
            "INSERT INTO statarena.file_document_sources VALUES(%s,%s,'ready',1,0,now()) ON CONFLICT(source_path) DO UPDATE SET source_sha256=excluded.source_sha256",
            (path, sha),
        )
        db.execute(
            "INSERT INTO statarena.file_documents(document_path,source_path,source_sha256,format,document) VALUES(%s,%s,%s,'json',%s) ON CONFLICT(document_path) DO UPDATE SET source_sha256=excluded.source_sha256,document=excluded.document",
            (path, path, sha, Jsonb(value)),
        )


def resource(endpoint, body, params=None, status=200):
    path = (
        "raw/worker/"
        + hashlib.sha256((endpoint + json.dumps(params)).encode()).hexdigest()
        + ".json"
    )
    input_(path, body)
    db.execute(
        "INSERT INTO statarena.resources(endpoint,params,status,ref,error) VALUES(%s,%s,%s,%s,%s) ON CONFLICT(endpoint,params) DO UPDATE SET ref=excluded.ref,status=excluded.status,error=excluded.error,updated_at=clock_timestamp()",
        (
            endpoint,
            json.dumps(params or {}, sort_keys=True, separators=(",", ":")),
            status,
            Jsonb({"path": path}),
            Jsonb(body.get("error")),
        ),
    )


def mark():
    db.execute(
        "INSERT INTO statarena.dirty_partitions(season,league_id) VALUES(%s,%s) ON CONFLICT(season,league_id) DO UPDATE SET changed_at=clock_timestamp()",
        (season, league),
    )


def fixture(mid, source, finished=True):
    f = {
        **source,
        "id": mid,
        "season": season,
        "league": {"id": league, "name": "Fixture league"},
        "status": "finished" if finished else "scheduled",
    }
    db.execute(
        "INSERT INTO statarena.fixtures(id,league_id,season,day,status,body) VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT(id) DO UPDATE SET body=excluded.body,updated_at=clock_timestamp()",
        (mid, league, season, f.get("date"), f["status"], Jsonb(f)),
    )


def shard(shard_id, rows, unindexed=False):
    docs = []
    tables = {}
    for i, (m, meta, endpoints) in enumerate(rows):
        d = "doc-" + m
        docs.append({"id": d, "metadata": meta})
        for family, envelope in endpoints.items():
            tables.setdefault(family, []).append(
                {"documentId": d, "response": envelope}
            )
    prefix = "raw/shard/" + shard_id + "/"
    input_(prefix + "documents", docs, not unindexed)
    refs = {}
    for family, data in tables.items():
        input_(prefix + family, data, not unindexed)
        refs[family] = {"path": prefix + family}
    db.execute(
        "INSERT INTO statarena.shards VALUES(%s,%s)",
        (shard_id, Jsonb({"document": {"path": prefix + "documents"}, "tables": refs})),
    )
    db.cursor().executemany(
        "INSERT INTO statarena.observations VALUES(%s,%s,%s)",
        [(r[0], shard_id, i) for i, r in enumerate(rows)],
    )


def worker(**kwargs):
    import relational_materialize as worker

    return worker.run(store, minutes=4, batch=2, **kwargs)


with psycopg.connect(url, autocommit=True) as db:
    store = Store(db)
    db.execute((root / "dashboard/backend/migrations/001_neon.sql").read_text())
    db.execute(
        (root / "dashboard/backend/migrations/002_aws_documents.sql").read_text()
    )
    base = json.loads(
        (
            root / "dashboard/outputs/data-completeness/production-archive.json"
        ).read_text()
    )
    endpoints = base.pop("endpoints")
    mid = base["fixture"]["id"]
    season = base["season"]
    league = base["competition_id"]
    upcoming = "m_ZZ1122"
    fixture(mid, base["fixture"])
    fixture(upcoming, base["fixture"], False)
    shard("original", [(mid, base, endpoints)])
    index = "computed/dashboard/index.json"
    bare_tables = [
        "matches",
        "players",
        "performances",
        "teams",
        "shots",
        "team_statistics",
        "fixtures",
        "competitions",
    ]
    input_(
        index,
        {
            "seasons": [
                {"id": season, "chunks": [{"leagueId": league, "path": "old-packed"}]}
            ]
        },
    )
    input_(
        "old-packed",
        {
            "tables": {k: {"keys": [], "rows": []} for k in bare_tables},
            "meta": {},
            "metrics": [],
        },
    )
    input_(
        "computed/matchdays/" + season.replace("/", "-") + ".json.gz",
        {league: {mid: {"name": "9", "playoff": False}}},
    )
    db.execute(
        "INSERT INTO statarena.objects(path,size,sha256,etag,content_type) VALUES('raw/avatar.webp',11,%s,'abc','image/webp')",
        (b"a" * 32,),
    )
    db.execute(
        "INSERT INTO statarena.assets VALUES('https://example.test/portrait','raw/avatar.webp','image/webp')"
    )
    resource(
        "/matches/" + upcoming + "/events",
        {
            "status": 404,
            "data": None,
            "error": {"code": "MISSING", "message": "no data"},
        },
        status=404,
    )

    def bootstrap():
        r = worker(queue_all=True)
        a = sql1("select count(*) from statarena_app.appearances")
        families = sql1(
            "select count(*) from statarena_app.match_families where match_id=%s",
            (mid,),
        )
        check(a > 10 and families == 13, "core/detail coverage")
        check(
            sql1("select count(*) from statarena_app.assets") == 1
            and sql1("select count(*) from statarena_app.catalog_editions") > 0
            and sql1("select count(*) from statarena_app.support_projection") > 0,
            "globals incomplete",
        )
        check(
            sql1("select count(*) from statarena_app.fixtures") == 2,
            "upcoming fixture lost",
        )
        return {
            "appearances": a,
            "families": families,
            "receipt": r,
            "application_tables": sql1(
                "select count(*) from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='statarena_app' and c.relkind='r'"
            ),
            "allocated_application_table_index_toast_bytes": sql1(
                "select sum(pg_total_relation_size(c.oid))::bigint from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='statarena_app' and c.relkind='r'"
            ),
            "worker_file_fallbacks": sum(store.reads.values()),
            "published_provider_jobs": sql1("select count(*) from statarena.jobs"),
        }

    case("all from archived source", bootstrap)

    def precedence():
        newer = copy.deepcopy(endpoints["match"])
        newer["data"]["stadium"] = "Latest stadium"
        resource("/matches/" + mid, newer)
        resource(
            "/matches/" + mid + "/shots",
            {
                "status": 404,
                "data": None,
                "error": {"code": "MISSING", "message": "unavailable"},
            },
            status=404,
        )
        mark()
        worker()
        check(
            sql1("select stadium from statarena_app.matches where id=%s", (mid,))
            == "Latest stadium",
            "successful current response lost",
        )
        count = sql1("select count(*) from statarena_app.shots")
        check(count > 0, "archive lost on failed current request")
        return {"shots_preserved": count}

    case("recent 200 wins, older good source survives provider error", precedence)

    def nested():
        nested = json.loads(
            (
                root / "docs/verification/relational-match-20261104/nested-source.json"
            ).read_text()
        )["sample"]
        for row in nested:
            endpoint = "/matches/" + upcoming + "/" + row["endpoint"].split("/", 3)[3]
            resource(
                endpoint,
                {
                    "status": row["status"],
                    "data": row.get("sample", {}).get("data"),
                    "error": row["error"] or row.get("sample", {}).get("error"),
                },
                status=row["status"],
            )
        resource(
            "/matches/" + upcoming + "/heatmaps",
            endpoints["heatmaps"],
            {"frame": "home_ltr"},
        )
        mark()
        worker()
        count = sql1(
            "select count(distinct family) from statarena_app.match_families where match_id=%s and subject_id<>''",
            (upcoming,),
        )
        check(
            count == 5
            and sql1(
                "select count(*) from statarena_app.match_families where match_id=%s and params<>'{}'",
                (upcoming,),
            )
            == 1,
            "nested/params lost",
        )
        check(
            sql1(
                "select status from statarena_app.match_families where match_id=%s and family='events'",
                (upcoming,),
            )
            == 404,
            "provider error lost",
        )
        return {"nested_families": count}

    case("upcoming nested/parameter variants and provider errors", nested)

    def partial():
        old = db.execute(
            "select id,goals from statarena_app.appearances order by id"
        ).fetchall()
        before = db.execute(
            "select stadium,detail_collected,(select count from statarena_app.match_coverage where match_id=m.id and coverage_key='ratedPlayers') from statarena_app.matches m where id=%s",
            (mid,),
        ).fetchone()
        db.execute(
            "delete from statarena.resources where endpoint=%s", ("/matches/" + mid,)
        )
        db.execute("delete from statarena.observations")
        db.execute(
            "delete from statarena.resources where endpoint=%s",
            ("/matches/" + mid + "/shots",),
        )
        resource("/matches/" + mid + "/shots", endpoints["shots"])
        input_("old-packed", {"corrupt": "cannot use an obsolete initial snapshot"})
        mark()
        worker()
        check(
            old
            == db.execute(
                "select id,goals from statarena_app.appearances order by id"
            ).fetchall()
            and old,
            "typed appearances lost",
        )
        after = db.execute(
            "select stadium,detail_collected,(select count from statarena_app.match_coverage where match_id=m.id and coverage_key='ratedPlayers') from statarena_app.matches m where id=%s",
            (mid,),
        ).fetchone()
        check(
            before == after,
            "partial family downgraded typed coverage/context: "
            + repr((before, after)),
        )
        return {"preserved": len(old), "context": after}

    case("partial refresh reuses typed prior rows", partial)

    def rollback():
        before = sql1("select generation from statarena_app.publications")
        bad = copy.deepcopy(endpoints["events"])
        bad["data"]["unmapped_test_field"] = 1
        resource("/matches/" + mid + "/events", bad)
        mark()
        try:
            worker()
        except (ValueError, TypeError):
            pass
        else:
            raise AssertionError("bad typed value published")
        check(
            before == sql1("select generation from statarena_app.publications")
            and sql1("select count(*) from statarena.dirty_partitions") > 0,
            "partial publication or premature acknowledgment",
        )
        resource("/matches/" + mid + "/events", endpoints["events"])
        worker()
        return {"generation_unchanged_on_failure": before}

    case("rollback then corrected retry", rollback)

    def late():
        # Writer changes the legacy marker while the publisher resolves one uncached input.
        path = "raw/later.json"
        value = endpoints["match"]
        input_(path, value, False)
        db.execute(
            "INSERT INTO statarena.resources(endpoint,params,status,ref) VALUES(%s,'{}',200,%s) ON CONFLICT(endpoint,params) DO UPDATE SET ref=excluded.ref,updated_at=clock_timestamp()",
            ("/matches/" + mid, Jsonb({"path": path})),
        )
        mark()
        original = store.json

        def raced(p):
            if p == path:
                with psycopg.connect(url, autocommit=True) as other:
                    other.execute(
                        "update statarena.dirty_partitions set changed_at=clock_timestamp() where season=%s and league_id=%s",
                        (season, league),
                    )
            return original(p)

        store.json = raced
        try:
            r = worker(max_partitions=1)
        finally:
            store.json = original
        check(
            sql1("select count(*) from statarena.dirty_partitions") == 1,
            "late marker was deleted",
        )
        worker()
        return {"still_queued_after_first": True, "receipt": r}

    case("later source transaction survives acknowledgement", late)

    def interleaved():
        store.reads.clear()
        for i in range(32):
            pair = []
            for j in (i, i + 32):
                key = "m_" + str(j + 100).zfill(6)
                f = {**base["fixture"], "id": key}
                fixture(key, f, False)
                pair.append(
                    (
                        key,
                        {"fixture": f},
                        {"events": {"status": 200, "data": {"events": []}}},
                    )
                )
            shard("interleaved-" + str(i), pair, True)
        mark()
        worker()
        reads = {k: v for k, v in store.reads.items() if "interleaved-" in k}
        check(
            len(reads) == 64 and max(reads.values()) == 1,
            "shard reloads or missed inputs",
        )
        return {
            "shards": 32,
            "matches": 64,
            "files": len(reads),
            "max_reads": max(reads.values()),
        }

    case("32 interleaved shards", interleaved)

    def resume():
        for i in range(2):
            name = "l_" + str(900000 + i)
            db.execute(
                "insert into statarena.dirty_partitions(season,league_id) values(%s,%s)",
                (season, name),
            )
        r = worker(max_partitions=1)
        check(
            sql1("select count(*) from statarena_app.publication_jobs") > 0,
            "remaining work lost",
        )
        worker()
        before = sql1("select generation from statarena_app.publications")
        r = worker()
        check(
            before == sql1("select generation from statarena_app.publications")
            and r["partitions"] == 0,
            "clean repeat changed",
        )
        return {"clean_repeat_partitions": r["partitions"], "generation": before}

    case("bounded checkpoint, resume, idempotent rerun", resume)

    def capacity():
        mark()
        os.environ["STATARENA_SQL_LIMIT_BYTES"] = "1"
        try:
            try:
                worker()
            except RuntimeError:
                pass
            else:
                raise AssertionError("capacity exceeded")
        finally:
            os.environ.pop("STATARENA_SQL_LIMIT_BYTES")
        check(
            sql1("select count(*) from statarena.dirty_partitions") > 0,
            "capacity refusal acknowledged input",
        )
        return {"staging_marker_retained": True}

    case("capacity refusal", capacity)

    def pinned():
        source = "/matches/" + mid + "/momentum"
        body = {"status": 200, "data": {"match_id": mid, "points": []}}
        resource(source, body)
        path = sql1(
            "select ref->>'path' from statarena.resources where endpoint=%s", (source,)
        )
        store.reads.clear()
        db.execute(
            "update statarena.file_documents set source_sha256=%s where document_path=%s",
            (b"x" * 32, path),
        )
        worker()
        check(
            store.reads[path] == 1,
            "stale document was used or verified fallback was missed",
        )
        return {"verified_fallback_reads": store.reads[path]}

    case("source digest mismatch uses verified fallback", pinned)

    def lock():
        with psycopg.connect(url, autocommit=True) as other:
            other.execute("select pg_advisory_lock(97813003)")
            r = worker()
            check(r.get("locked") is True, "failed to honor writer lease")
        return r

    case("respects existing writer lease", lock)

    def orphan():
        orphan_id = "m_ZZ0009"
        shard(
            "orphan-archive",
            [
                (
                    orphan_id,
                    {"fixture": {"id": orphan_id}},
                    {"events": {"status": 200, "data": {"events": []}}},
                )
            ],
        )
        r = worker()
        count = sql1(
            "select count(*) from statarena_app.match_families where match_id=%s",
            (orphan_id,),
        )
        check(
            count == 1
            and sql1(
                "select count(*) from statarena_app.fixtures where id=%s", (orphan_id,)
            )
            == 0,
            "archived orphan missed or fixture fabricated",
        )
        return {"families": count, "partitions": r["partitions"]}

    case("archive-only match without staging fixture", orphan)

    def calendar():
        current = copy.deepcopy(endpoints["match"])
        current["data"]["round_name"] = "15"
        resource("/matches/" + mid, current)
        mark()
        worker()
        q = "SELECT m.name FROM statarena_app.cat_matchdays_matches m JOIN statarena_app.catalog_editions c USING(resource_id) WHERE c.catalog='matchdays' AND c.scope=%s AND c.edition=%s AND m.metric_label=%s"
        check(
            sql1(q, (league, season, mid)) == "15",
            "newly collected round absent from typed calendar",
        )
        path = "computed/matchdays/" + season.replace("/", "-") + ".json.gz"
        input_(
            path,
            {
                league: {
                    mid: {"name": "9", "playoff": False},
                    upcoming: {"name": "16", "playoff": False},
                }
            },
        )
        worker()
        check(
            sql1(q, (league, season, mid)) == "15"
            and sql1(q, (league, season, upcoming)) == "16",
            "calendar source reindex reverted current round",
        )
        return {"current_round": "15", "imported_other": "16"}

    case("typed calendar follows refreshed match round", calendar)

    def scalar_positions():
        values = [
            (7, "int"),
            (1.5, "float"),
            ("07", "str"),
            (None, "NoneType"),
            (False, "bool"),
            (True, "bool"),
        ]
        ids = [
            r[0]
            for r in db.execute(
                "select id from statarena_app.appearances where match_id=%s order by id limit 6",
                (mid,),
            )
        ]
        check(len(ids) == len(values), "appearance fixture missing")
        for i, (v, t) in zip(ids, values, strict=True):
            db.execute(
                "update statarena_app.appearances set position_id=%s,position_id_type=%s where id=%s",
                (str(v) if v is not None else None, t, i),
            )
        # Missing successful players input must reuse already committed appearance rows.
        db.execute(
            "delete from statarena_app.match_families where match_id=%s and family='players'",
            (mid,),
        )
        mark()
        worker()
        result = db.execute(
            "select position_id,position_id_type from statarena_app.appearances where id=any(%s) order by id",
            (ids,),
        ).fetchall()
        expected = [(str(v) if v is not None else None, t) for v, t in values]
        check(result == expected, "positionId source types changed: " + repr(result))
        return {"positions": result}

    case("partial refresh preserves native appearance position types", scalar_positions)

    def least_privilege(owns=True):
        db.execute("DROP SCHEMA statarena_app CASCADE")
        if owns:
            db.execute("CREATE ROLE worker_limited")
        db.execute(
            "REVOKE CREATE ON DATABASE publication_fixture FROM PUBLIC,worker_limited"
        )
        if owns:
            db.execute("CREATE SCHEMA statarena_app AUTHORIZATION worker_limited")
        else:
            db.execute("CREATE SCHEMA statarena_app")
            db.execute("GRANT USAGE, CREATE ON SCHEMA statarena_app TO worker_limited")
        db.execute("GRANT USAGE ON SCHEMA statarena TO worker_limited")
        db.execute("GRANT SELECT ON ALL TABLES IN SCHEMA statarena TO worker_limited")
        db.execute("GRANT DELETE ON statarena.dirty_partitions TO worker_limited")
        # Use the initial empty packed fixture for this separate fresh bootstrap.
        input_(
            "old-packed",
            {
                "tables": {k: {"keys": [], "rows": []} for k in bare_tables},
                "meta": {},
                "metrics": [],
            },
        )
        with psycopg.connect(url, autocommit=True) as limited:
            limited.execute("SET ROLE worker_limited")
            store.db = limited
            try:
                check(
                    not limited.execute(
                        "select has_database_privilege(current_user,current_database(),'CREATE')"
                    ).fetchone()[0],
                    "fixture unexpectedly owns database",
                )
                r = worker(queue_all=True)
                actual = limited.execute(
                    "select nspowner=current_user::regrole::oid from pg_namespace where nspname='statarena_app'"
                ).fetchone()[0]
                check(actual == owns, "unexpected namespace owner")
                return {"db_create": False, "owns_schema": actual, "publication": r}
            finally:
                store.db = db

    case("schema owner without database CREATE", least_privilege)
    case(
        "admin-owned namespace with worker schema CREATE only",
        lambda: least_privilege(False),
    )
report = {
    "setup": "PostgreSQL18 ephemeral, actual SQL schemas + captured match families + local indexed sources",
    "rerun": f"node docs/verification/aws-rematerialize-20261104/run.mjs {phase}",
    "pass": sum(c["pass"] for c in cases),
    "total": len(cases),
    "cases": cases,
}
(out / "results.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
print(f"{report['pass']}/{report['total']}")
for c in cases:
    if not c["pass"]:
        print(c["name"], c["error"][:180])
sys.exit(report["pass"] != report["total"])
