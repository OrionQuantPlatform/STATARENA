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
    initial_bootstrap_sha = sql1("select encode(sha256,'hex') from statarena.objects where path='old-packed'")
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

    def schema_only():
        original = store.json
        def forbidden(path):
            raise AssertionError('Schema-only build read staged content: ' + path)
        store.json = forbidden
        try:
            r = worker(install_only=True)
            check(r.get('schema_installed') is True and sql1('select count(*) from statarena_app.partitions') == 0, 'Schema-only install constructed business data')
            check(not db.execute("select 1 from statarena_app.workflow_state").fetchall(), 'Schema-only install fabricated worker completion')
            return r
        finally:
            store.json = original
    case('schema-only installation leaves data and workflow state untouched', schema_only)

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

    def bootstrap_receipt():
        row = db.execute("select source_path,sha256 from statarena_app.partition_bootstrap_sources where season=%s and league_id=%s", (season, league)).fetchone()
        check(row == ('old-packed', initial_bootstrap_sha), 'Initial physical source SHA was not captured with the content')
        return {'source_path': row[0], 'physical_sha256': row[1]}

    case("first construction records actual bootstrap source", bootstrap_receipt)

    def season_aliases():
        from relational_materialize import Inputs, prepare, publish_partition, queue_dirty
        year = season.split('/')[0]
        calendar, populated, provenance = 'l_CAL026', 'l_SAFE26', 'l_REC026'
        manifest = copy.deepcopy(store.inputs[index])
        manifest['seasons'].append({'id': year, 'chunks': [{'leagueId': calendar, 'path': 'old-packed'}]})
        manifest['seasons'][0]['chunks'].extend(
            {'leagueId': key, 'path': 'old-packed'} for key in (populated, provenance))
        with db.transaction(force_rollback=True):
            db.execute('UPDATE statarena.fixtures SET season=%s WHERE league_id=%s', (year, league))
            for label in (year, season):
                db.execute('INSERT INTO statarena.dirty_partitions(season,league_id) VALUES(%s,%s)', (label, league))
            db.execute('INSERT INTO statarena_app.publication_jobs(season,league_id) VALUES(%s,%s)', (year, league))
            for key in (league, calendar, populated, provenance):
                db.execute('INSERT INTO statarena_app.competitions(id,latest_season) VALUES(%s,%s) ON CONFLICT DO NOTHING', (key, year))
                db.execute('INSERT INTO statarena_app.partitions(season,league_id,source_digest) VALUES(%s,%s,%s)', (year, key, 'empty-shell'))
                db.execute('INSERT INTO statarena_app.competition_seasons(competition_id,season) VALUES(%s,%s)', (key, year))
            db.execute("INSERT INTO statarena_app.fixtures(id,season,league_id) VALUES('m_SF0026',%s,%s)", (year, populated))
            db.execute('INSERT INTO statarena_app.partition_bootstrap_sources(season,league_id,source_path,sha256) VALUES(%s,%s,%s,%s)', (year, provenance, 'old-packed', initial_bootstrap_sha))
            db.execute("INSERT INTO statarena.fixtures(id,league_id,season,status,body) VALUES('m_CA0026',%s,%s,'scheduled','{}')", (calendar, year))
            db.execute('INSERT INTO statarena.dirty_partitions(season,league_id) VALUES(%s,%s)', (year, calendar))
            inputs = Inputs(store)
            prepare(inputs, manifest, False)
            check(sql1('SELECT count(*) FROM work_dirty WHERE season=%s AND league_id=%s', (season, league)) == 2, 'Year aliases did not retain both exact source markers')
            check(sql1('SELECT count(*) FROM statarena_app.publication_jobs WHERE season=%s AND league_id=%s', (year, league)) == 0, 'Native-year duplicate still queued')
            check(sql1('SELECT count(*) FROM statarena_app.partitions WHERE season=%s AND league_id=%s', (year, league)) == 0, 'Empty derived alias survived')
            check(sql1('SELECT count(*) FROM statarena_app.competition_seasons WHERE season=%s AND competition_id=%s', (year, league)) == 0, 'Empty competition alias survived')
            check(sql1('SELECT count(*) FROM statarena_app.partitions WHERE season=%s AND league_id=ANY(%s)', (year, [calendar, populated, provenance])) == 3, 'A real calendar year, business row, or bootstrap was deleted')
            check(sql1("SELECT season FROM work_matches WHERE id='m_CA0026'") == year, 'Known calendar-year fixture was relabelled')
            check(sql1('SELECT season FROM work_dirty WHERE league_id=%s', (calendar,)) == year, 'Known calendar-year marker was relabelled')
            # A newer raw-year marker must survive publication of the captured
            # snapshot and be requeued under the same canonical season.
            db.execute("UPDATE statarena.dirty_partitions SET changed_at=changed_at+interval '1 second' WHERE season=%s AND league_id=%s", (year, league))
            marked = sql1('SELECT changed_at FROM statarena_app.publication_jobs WHERE season=%s AND league_id=%s', (season, league))
            publish_partition(inputs, manifest, season, league, marked)
            check(sql1('SELECT count(*) FROM statarena.dirty_partitions WHERE season=%s AND league_id=%s', (year, league)) == 1, 'Newer native-year marker was acknowledged')
            check(sql1('SELECT count(*) FROM statarena.dirty_partitions WHERE season=%s AND league_id=%s', (season, league)) == 0, 'Unchanged canonical marker was not acknowledged')
            queue_dirty(db)
            check(db.execute('SELECT season FROM statarena_app.publication_jobs WHERE league_id=%s', (league,)).fetchall() == [(season,)], 'Late native-year update was not canonically queued')
            return {'canonical_markers': 2, 'empty_alias_removed': True, 'calendar_and_populated_scopes_preserved': True, 'late_marker_preserved': True}

    case("native-year queue aliases preserve data and exact dirty acknowledgements", season_aliases)

    def prefetch_integrity():
        import sqlite3
        from relational_materialize import Inputs, compact

        value = {"status": 200, "data": {"value": 0, "nullable": None}}
        path = "raw/prefetch-verification.json"
        input_(path, value)
        physical = sql1("select encode(sha256,'hex') from statarena.objects where path=%s", (path,))
        logical = hashlib.sha256(compact(value).encode()).hexdigest()
        world_path = f"raw/pitchapi-world/blobs/{logical}.json.gz"
        input_(world_path, value)
        with sqlite3.connect(":memory:") as scratch:
            scratch.execute("CREATE TABLE body_cache(path text,sha text,body text,PRIMARY KEY(path,sha))")
            reader = Inputs(store)
            reader.prefetch([(path, None), (path, physical), (world_path, logical)], scratch)
            bodies = scratch.execute("SELECT body FROM body_cache").fetchall()
            check(len(bodies) == 3 and all(json.loads(row[0]) == value for row in bodies), "Prefetch changed native values or lost a reference")
            try:
                reader.prefetch([(path, "0" * 64)], scratch)
            except ValueError:
                pass
            else:
                raise AssertionError("Prefetch accepted a stale physical digest")
            input_(world_path, {"status": 200, "data": {"value": 1}})
            try:
                reader.prefetch([(world_path, logical)], scratch)
            except ValueError:
                pass
            else:
                raise AssertionError("Prefetch accepted altered logical content")
        return {"native_values_preserved": True, "physical_and_logical_pins_checked": True}

    case("batched input spool preserves values and rejects changed versions", prefetch_integrity)

    def streamed_input_contract():
        import sqlite3
        from relational_materialize import Inputs

        calls = []

        class CountedCursor:
            def __init__(self):
                self.cursor = db.cursor()

            def __enter__(self):
                self.cursor.__enter__()
                return self

            def __exit__(self, *args):
                return self.cursor.__exit__(*args)

            def stream(self, statement, params):
                calls.append(len(params[0]))
                return self.cursor.stream(statement, params)

        class CountedConnection:
            def cursor(self):
                return CountedCursor()

            def __getattr__(self, key):
                return getattr(db, key)

        with db.transaction(force_rollback=True):
            expected = {}
            for index in range(257):
                path = f"raw/stream-verification/{index:04d}.json"
                expected[path] = {"index": index, "zero": 0, "flag": False,
                                  "missing_value": None, "shirt": "00", "name": "Léa"}
                input_(path, expected[path], indexed=index != 7)
            reader = Inputs(store)
            reader.db = CountedConnection()
            with sqlite3.connect(":memory:") as scratch:
                scratch.execute("CREATE TABLE body_cache(path text,sha text,body text,PRIMARY KEY(path,sha))")
                reader.prefetch([(path, None) for path in expected], scratch)
                actual = {path: json.loads(body) for path, body in scratch.execute("SELECT path,body FROM body_cache")}
                check(actual == expected, "Streamed inputs changed values or omitted a chunk")
                check(len(calls) <= 3 and max(calls) <= 128, "Input stream requires too many round trips or an unbounded statement")
                check(store.reads["raw/stream-verification/0007.json"] == 1, "Missing indexed document did not use its verified source")
                scratch.execute("DELETE FROM body_cache")
                try:
                    with db.transaction():
                        reader.prefetch([(path, "0" * 64 if index == 3 else None)
                                         for index, path in enumerate(expected)], scratch)
                except ValueError:
                    pass
                else:
                    raise AssertionError("Streamed input accepted an invalid source checksum")
                check(sql1("SELECT 1") == 1, "Early stream rejection left the SQL connection busy")
                scratch.execute("DELETE FROM body_cache")
                try:
                    reader.prefetch([("raw/stream-verification/absent.json", None)], scratch)
                except FileNotFoundError:
                    pass
                else:
                    raise AssertionError("Stream silently omitted an absent source")
        return {"documents": 257, "read_statements": 3,
                "fallback_verified": True, "connection_recovered_after_rejection": True}

    case("streamed inputs stay complete, bounded and recoverable after rejection", streamed_input_contract)

    def bulk_insert_contract():
        from relational_core import _many

        rows = [dict(metric_key=f"copy-check-{i}", label='é\\"' + str(i), unit=None, decimals=i % 5) for i in range(120)]
        with db.transaction():
            _many(db, "metric_definitions", rows)
            _many(db, "metric_definitions", [dict(row, label="must not replace") for row in rows])
            actual = db.execute("SELECT metric_key,label,unit,decimals FROM statarena_app.metric_definitions WHERE metric_key LIKE 'copy-check-%' ORDER BY metric_key").fetchall()
            expected = sorted((row['metric_key'], row['label'], row['unit'], row['decimals']) for row in rows)
            check(actual == expected, "Bulk insertion changed values or conflict behavior")
            try:
                with db.transaction():
                    _many(db, "metric_definitions", [dict(row, metric_key=None if i == 119 else f"copy-invalid-{i}") for i, row in enumerate(rows)])
            except psycopg.errors.NotNullViolation:
                pass
            else:
                raise AssertionError("Bulk insertion bypassed the target constraint")
            check(sql1("SELECT count(*) FROM statarena_app.metric_definitions WHERE metric_key LIKE %s", ("copy-invalid-%",)) == 0, "Failed bulk insert leaked partial rows")
            db.execute("DELETE FROM statarena_app.metric_definitions WHERE metric_key LIKE 'copy-check-%'")
        return {"rows": len(rows), "conflicts_preserved": True, "constraint_failure_atomic": True}

    case("bulk fact insertion retains conflicts, constraints and rollback", bulk_insert_contract)

    def catalog_bulk_contract():
        from relational_catalog import publish_catalog

        class Counted:
            def __init__(self, connection):
                self.connection = connection
                self.calls = 0

            def execute(self, *args, **kwargs):
                self.calls += 1
                return self.connection.execute(*args, **kwargs)

            def cursor(self, *args, **kwargs):
                self.calls += 1
                return self.connection.cursor(*args, **kwargs)

            def transaction(self, *args, **kwargs):
                return self.connection.transaction(*args, **kwargs)

        def profile(pid):
            return {"status": 200, "data": {"id": pid, "name": "Joueur é " + pid,
                    "shirt_number": "00", "position_id": 0, "image_url": None}, "error": None}

        expected = {f"p_B{i:05d}": profile(f"p_B{i:05d}") for i in range(100)}
        records = [("/players/" + pid, body) for pid, body in expected.items()]
        with db.transaction(force_rollback=True):
            counted = Counted(db)
            check(publish_catalog(counted, records) == {"changed": 100, "unchanged": 0}, "Batch omitted a profile")
            initial_calls = counted.calls
            check(initial_calls <= 16, "Profile publication retained per-profile SQL round trips")
            actual = dict(db.execute("""SELECT c.edition,statarena_app.read_cat_profile_players(p)
                FROM statarena_app.catalog_editions c JOIN statarena_app.cat_profile_players p USING(resource_id)
                WHERE c.catalog='profile' AND c.scope='players' AND c.edition=ANY(%s)""", (list(expected),)))
            check(actual == expected, "Bulk profile publication changed missing, null or scalar values")
            check(publish_catalog(db, records) == {"changed": 0, "unchanged": 100}, "Identical replay changed profiles")
            updated = copy.deepcopy(records[0][1])
            updated["data"]["name"] = "Corrected name"
            correction = (records[0][0], updated)
            check(publish_catalog(db, [records[0], correction, correction]) == {"changed": 1, "unchanged": 2},
                  "Duplicate keys lost sequential correction or idempotency")
            check(sql1("""SELECT statarena_app.read_cat_profile_players(p) FROM statarena_app.cat_profile_players p
                JOIN statarena_app.catalog_editions c USING(resource_id) WHERE c.catalog='profile'
                AND c.scope='players' AND c.edition=%s""", ("p_B00000",)) == updated, "Last duplicate did not win")
            invalid = [(f"/players/p_T{i:05d}", profile(f"p_T{i:05d}")) for i in range(100)]
            invalid.append(("/players/p_TZZ999", {"status": 200, "data": {"unknown_field": True}}))
            try:
                publish_catalog(db, invalid)
            except ValueError:
                pass
            else:
                raise AssertionError("Unknown catalog field was silently accepted")
            check(sql1("SELECT count(*) FROM statarena_app.catalog_editions WHERE catalog='profile' AND scope='players' AND edition=ANY(%s)",
                       ([f"p_T{i:05d}" for i in range(100)],)) == 0, "Late invalid input leaked an earlier committed group")
        return {"profiles": 100, "initial_database_calls": initial_calls, "duplicates_preserved": True,
                "native_values_exact": True, "late_failure_atomic": True}

    case("catalog batches preserve values, corrections and atomic failure", catalog_bulk_contract)

    def match_bulk_contract():
        from relational_match import publish_match_batch

        class Counted:
            def __init__(self, connection):
                self.connection, self.copies = connection, 0
            def execute(self, *args, **kwargs):
                return self.connection.execute(*args, **kwargs)
            def cursor(self, *args, **kwargs):
                self.copies += 1
                return self.connection.cursor(*args, **kwargs)
            def transaction(self, *args, **kwargs):
                return self.connection.transaction(*args, **kwargs)

        ids = [f'm_B{i:05d}' for i in range(64)]
        with db.transaction(force_rollback=True):
            counted = Counted(db)
            rows = [(key, {'players': endpoints['players']}, None, []) for key in ids]
            publish_match_batch(counted, rows)
            check(counted.copies == 4, 'Compact player families retained per-match COPY round trips')
            actual = db.execute("SELECT match_id,statarena_app.detail_response(f) FROM statarena_app.match_families f WHERE match_id=ANY(%s) AND family='players'", (ids,)).fetchall()
            check(len(actual) == 64 and all(body == endpoints['players'] for _, body in actual), 'Batched native player responses changed')
            counted.copies = 0
            publish_match_batch(counted, rows)
            check(counted.copies == 0, 'Identical replay rewrote typed details')
            failed_ids = [f'm_C{i:05d}' for i in range(64)]
            bigger = [(key, {k: endpoints[k] for k in ('players', 'player_halves')}, None, []) for key in failed_ids]
            bigger[-1][1]['players'] = {'status': 200, 'data': {'unknown_field': True}}
            try:
                publish_match_batch(counted, bigger)
            except (ValueError, TypeError):
                pass
            else:
                raise AssertionError('Invalid final match was accepted')
            check(counted.copies > 0, 'Failure did not exercise rollback after a flushed 8 MiB group')
            check(sql1('SELECT count(*) FROM statarena_app.match_details WHERE match_id=ANY(%s)', (failed_ids,)) == 0, 'Late failed group leaked partial match details')
            try:
                publish_match_batch(counted, rows + [('m_B99999', {}, None, [])])
            except ValueError:
                pass
            else:
                raise AssertionError('Unbounded match batch was accepted')
            return {'matches': 64, 'player_table_copies': 4, 'exact_responses': True, 'late_failure_atomic': True}

    case("remote match batches preserve exact values, byte bounds and atomic replay", match_bulk_contract)

    def staging_reconciliation():
        from reconcile_aws_staging import SPECS, stage_rows, apply_staged, verified

        columns = SPECS["fixtures"][1]
        before = db.execute("SELECT id,league_id,season,day,status,body,updated_at FROM statarena.fixtures WHERE id=%s", (mid,)).fetchone()
        original = dict(zip(columns, before))
        changed = dict(original, body=dict(original["body"], round_name="Captured source round"))
        inputs = {"fixtures": [changed], "resources": [], "projections": [],
            "assets": [{"url": "https://example.test/reconciliation", "path": "raw/absent-reconciliation-object", "content_type": "image/png"}]}
        try:
            plans = {kind: stage_rows(db, kind, inputs[kind]) for kind in SPECS}
            check(plans["fixtures"]["changed"] == 1, "Dry run failed to detect a changed fixture")
            check(db.execute("SELECT body FROM statarena.fixtures WHERE id=%s", (mid,)).fetchone()[0] == original["body"], "Dry run wrote fixture data")
            try:
                with db.transaction():
                    apply_staged(db, "2999-01-01T00:00:00Z")
            except psycopg.errors.ForeignKeyViolation:
                pass
            else:
                raise AssertionError("Captured asset bypassed its object foreign key")
            check(db.execute("SELECT body FROM statarena.fixtures WHERE id=%s", (mid,)).fetchone()[0] == original["body"], "Failed reconciliation partially committed")
            db.execute("DELETE FROM _statarena_delta_assets")
            try:
                with db.transaction():
                    apply_staged(db, "1900-01-01T00:00:00Z")
            except ValueError:
                pass
            else:
                raise AssertionError("Reconciliation overwrote a source newer than the capture")
            try:
                with db.transaction():
                    result = apply_staged(db, "2999-01-01T00:00:00Z")
                    check(result["fixtures"] == 1, "Captured fixture was not applied")
                    check(db.execute("SELECT body FROM statarena.fixtures WHERE id=%s", (mid,)).fetchone()[0] == changed["body"], "Captured JSON values changed")
                    check(not any(apply_staged(db, "2999-01-01T00:00:00Z").values()), "Reconciliation was not idempotent")
                    raise RuntimeError("rollback verification fixture")
            except RuntimeError as error:
                if str(error) != "rollback verification fixture":
                    raise
            try:
                verified(b"altered capture", "0" * 64)
            except ValueError:
                pass
            else:
                raise AssertionError("Altered capture passed its checksum")
            return {"dry_run_read_only": True, "foreign_key_rollback": True, "newer_aws_source_protected": True, "repeat_is_noop": True}
        finally:
            for kind in SPECS:
                db.execute("DROP TABLE IF EXISTS pg_temp._statarena_delta_" + kind)

    case("source reconciliation is atomic, pinned and repeatable", staging_reconciliation)

    def manifest_only(bad_pin=False):
        new_league = 'l_ZZ8811' if bad_pin else 'l_ZZ8812'
        new_season = '1888/1889'
        path = 'manifest-only-' + new_league
        original = copy.deepcopy(store.inputs[index])
        input_(path, {'tables': {k: {'keys': [], 'rows': []} for k in bare_tables}, 'meta': {}, 'metrics': []})
        physical = sql1("select encode(sha256,'hex') from statarena.objects where path=%s", (path,))
        new = copy.deepcopy(original)
        new['seasons'].append({'id': new_season, 'chunks': [{'leagueId': new_league, 'path': path, 'sha256': '0' * 64 if bad_pin else physical}]})
        input_(index, new)
        try:
            try:
                r = worker()
            except ValueError:
                check(bad_pin, 'Valid bootstrap failed')
                check(sql1('select count(*) from statarena_app.partitions where season=%s and league_id=%s', (new_season, new_league)) == 0, 'Bad pin published a partition')
                check(sql1('select count(*) from statarena_app.partition_bootstrap_sources where season=%s and league_id=%s', (new_season, new_league)) == 0, 'Bad pin committed a receipt')
                check(sql1('select count(*) from statarena_app.publication_jobs where season=%s and league_id=%s', (new_season, new_league)) == 1, 'Bad pin lost queued work')
                return {'bad_pin_rejected': True, 'partition_and_receipt_rolled_back': True, 'queue_retained': True}
            check(not bad_pin, 'Bad pinned source was ignored or accepted')
            check(r['partitions'] == 1, 'New manifest-only scope missed without --all')
            row = db.execute('select source_path,sha256,recorded_at from statarena_app.partition_bootstrap_sources where season=%s and league_id=%s', (new_season, new_league)).fetchone()
            check(row and row[:2] == (path, physical), 'Manifest-only bootstrap receipt missing/wrong')
            again = worker()
            check(again['partitions'] == 0 and row == db.execute('select source_path,sha256,recorded_at from statarena_app.partition_bootstrap_sources where season=%s and league_id=%s', (new_season, new_league)).fetchone(), 'Unchanged scope was rebuilt or receipt rewritten')
            return {'first_partitions': r['partitions'], 'repeat_partitions': again['partitions'], 'source_sha256': physical}
        finally:
            input_(index, original)
            if sql1("select to_regclass('statarena_app.partition_bootstrap_sources') is not null"):
                db.execute('delete from statarena_app.partition_bootstrap_sources where season=%s and league_id=%s', (new_season, new_league))
            db.execute('delete from statarena_app.partitions where season=%s and league_id=%s', (new_season, new_league))
            db.execute('delete from statarena_app.publication_jobs where season=%s and league_id=%s', (new_season, new_league))

    case("new manifest-only scope builds without forced requeue", manifest_only)
    case("bad bootstrap pin leaves queue and no committed receipt", lambda: manifest_only(True))

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
        bootstrap_before = db.execute('select source_path,sha256,recorded_at from statarena_app.partition_bootstrap_sources where season=%s and league_id=%s', (season, league)).fetchone()
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
        check(bootstrap_before == db.execute('select source_path,sha256,recorded_at from statarena_app.partition_bootstrap_sources where season=%s and league_id=%s', (season, league)).fetchone(), 'Partial typed refresh fabricated/replaced its bootstrap source receipt')
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
