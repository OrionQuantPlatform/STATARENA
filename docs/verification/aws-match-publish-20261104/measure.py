import collections
import hashlib
import inspect
import json
import os
import resource
import sys
import time
from pathlib import Path

import psycopg

root = Path(__file__).resolve().parents[3]
sys.path.insert(
    0, os.environ.get("STATARENA_MATCH_WRITER", str(root / "dashboard/scripts"))
)
import relational_match as writer

phase = sys.argv[1]
source = json.loads(
    (root / "dashboard/outputs/data-completeness/production-archive.json").read_text()
)
original = source["fixture"]["id"]
compact = json.dumps(source, ensure_ascii=False, separators=(",", ":"))
canonical = lambda x: json.dumps(
    x, sort_keys=True, separators=(",", ":"), ensure_ascii=False
)
cases = []
checks = []
trace = collections.Counter()
simulated_rtt = float(os.environ.get("STATARENA_SIMULATED_RTT_MS", "0")) / 1000


def latency(exchanges):
    if simulated_rtt:
        time.sleep(simulated_rtt * exchanges)


class CountingConnection(psycopg.Connection):
    def _exec_command(self, command, *args, **kwargs):
        trace["tx:" + str(command).split(maxsplit=1)[0].replace("b'", "").upper()] += 1
        latency(1)
        return super()._exec_command(command, *args, **kwargs)


class CountingCursor(psycopg.Cursor):
    def execute(self, query, *args, **kwargs):
        trace["sql:" + query.lstrip().split()[0].upper()] += 1
        latency(1)
        return super().execute(query, *args, **kwargs)

    def copy(self, statement, *args, **kwargs):
        trace["copy:" + statement.split()[1].split(".")[-1]] += 1
        latency(2)
        return super().copy(statement, *args, **kwargs)


def clone(i):
    mid = f"m_{i:06d}"
    rec = json.loads(compact.replace(original, mid))
    endpoints = rec.pop("endpoints")
    return (mid, endpoints, rec, [])


def publish(db, records):
    if phase == "after":
        return writer.publish_match_batch(db, records)
    for mid, ends, meta, variants in records:
        writer.publish_match_details(db, mid, ends, meta)
        for endpoint, params, response in variants:
            writer.publish_match_resource(db, endpoint, params, response)


def measure(db, name, items):
    trace.clear()
    started = time.monotonic()
    with db.transaction():
        publish(db, items)
    elapsed = time.monotonic() - started
    copy = sum(v for k, v in trace.items() if k.startswith("copy:"))
    sql = sum(v for k, v in trace.items() if k.startswith("sql:"))
    tx = sum(v for k, v in trace.items() if k.startswith("tx:"))
    exchanges = sql + tx + 2 * copy
    rows = {
        "name": name,
        "matches": len(items),
        "sql": sql,
        "copy": copy,
        "transactionCommands": tx,
        "exchangesModel": exchanges,
        "localSeconds": round(elapsed, 4),
        "addedSerialSecondsAt5ms": round(exchanges * 0.005, 3),
        "addedSerialSecondsAt30ms": round(exchanges * 0.03, 3),
        "counts": dict(trace),
    }
    cases.append(rows)
    return rows


with CountingConnection.connect(
    os.environ["LOCAL_FIXTURE_DB"], autocommit=True, cursor_factory=CountingCursor
) as db:
    default = psycopg.connect(os.environ["LOCAL_FIXTURE_DB"], autocommit=True)
    for i, size in enumerate((1, 16, 32)):
        group = [clone(10000 * i + n + 1) for n in range(size)]
        result = measure(db, "publish-" + str(size), group)
        checksums = []
        for mid, ends, meta, _ in group:
            expected = dict(meta, endpoints=ends)
            actual = default.execute(
                """select statarena_app.detail_context(c)||jsonb_build_object('endpoints',(select jsonb_object_agg(f.family,statarena_app.detail_response(f)) from statarena_app.match_families f where f.match_id=c.match_id and f.params='{}' and f.subject_id='')) from statarena_app.match_details c where c.match_id=%s""",
                (mid,),
            ).fetchone()[0]
            assert actual == expected, mid
            checksums.append(hashlib.sha256(canonical(actual).encode()).hexdigest())
        result["responseDigests"] = checksums
        repeat = measure(db, "retry-" + str(size), group)
        checks.append([repeat["copy"] == 0, "unchanged inputs skip COPY " + str(size)])
    mid, ends, meta, _ = group[0]
    updated = {"status": 200, "data": {"match_id": mid, "points": []}, "error": None}
    variant = (
        "/matches/" + mid + "/heatmaps",
        {"frame": "acting_ltr"},
        ends["heatmaps"],
    )
    measure(db, "partial-variant", [(mid, {"momentum": updated}, None, [variant])])
    actual = default.execute(
        "select statarena_app.detail_response(f) from statarena_app.match_families f where match_id=%s and family='momentum'",
        (mid,),
    ).fetchone()[0]
    assert actual == updated
    preserved = default.execute(
        "select statarena_app.detail_context(c) from statarena_app.match_details c where match_id=%s",
        (mid,),
    ).fetchone()[0]
    assert preserved == meta
    assert (
        default.execute(
            "select count(*) from statarena_app.match_families where match_id=%s",
            (mid,),
        ).fetchone()[0]
        == 14
    )
    failure = [
        (f"m_{900000 + i}", {"momentum": {"status": 404, "error": None}}, None, [])
        for i in range(17)
    ]
    failure[-1] = (
        failure[-1][0],
        {"events": {"status": 200, "data": {"unmapped": 2}}},
        None,
        [],
    )
    try:
        with db.transaction():
            publish(db, failure)
    except (TypeError, ValueError):
        pass
    else:
        raise AssertionError("schema mismatch was accepted")
    assert (
        default.execute(
            "select count(*) from statarena_app.match_details where match_id like 'm_9%%'"
        ).fetchone()[0]
        == 0
    )
    # Two saved variants can come from different textual encodings of the same
    # canonical parameter set. The later one has the same precedence as separate calls.
    later = {"status": 429, "error": {"code": "RETRY"}}
    publish(db, [(mid, {}, None, [variant, (variant[0], dict(variant[1]), later)])])
    alias = default.execute(
        "select statarena_app.detail_response(f) from statarena_app.match_families f where match_id=%s and family='heatmaps' and params=%s",
        (mid, writer.canonical(variant[1])),
    ).fetchone()[0]
    assert alias == later
    checks.append([True, "repeated variant retains last supplied response"])
    # Opposite source ordering with overlapping SQL keys. Metadata and family
    # writes may interleave across callers but each transaction publishes fully.
    if phase == "after":
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier

        barrier = Barrier(2)
        pair = [group[0][0], group[1][0]]

        def simultaneous(reverse):
            ids = pair[::-1] if reverse else pair
            family = "momentum" if reverse else "events"
            data_key = "points" if reverse else "events"
            with psycopg.connect(os.environ["LOCAL_FIXTURE_DB"]) as connection:
                connection.execute("SET LOCAL lock_timeout='3s'")
                barrier.wait(timeout=5)
                writer.publish_match_batch(
                    connection,
                    [
                        (
                            identity,
                            {
                                family: {
                                    "status": 200,
                                    "data": {"match_id": identity, data_key: []},
                                    "error": None,
                                }
                            },
                            None,
                            [],
                        )
                        for identity in ids
                    ],
                )

        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(simultaneous, [False, True]))
        for identity in pair:
            rows = default.execute(
                "select family,statarena_app.detail_response(f) from statarena_app.match_families f where match_id=%s and family=any(%s) and params='{}' and subject_id=''",
                (identity, ["events", "momentum"]),
            ).fetchall()
            assert len(rows) == 2
            for family, value in rows:
                assert value["data"]["events" if family == "events" else "points"] == []
        checks.append(
            [True, "reversed overlapping transactions retain independent families"]
        )
        try:
            writer.publish_match_batch(
                db, [(f"m_{800000 + i}", {}, None, []) for i in range(33)]
            )
        except ValueError:
            pass
        else:
            raise AssertionError("unbounded batch accepted")
        checks.append([True, "batch input bounded to 32 records before publication"])
    default.close()
cold = [r for r in cases if r["name"].startswith("publish")]
checks.append(
    [
        cold[1]["copy"] <= cold[0]["copy"] * 2,
        "16 matches copy each relation once or twice",
    ]
)
checks.append(
    [cold[2]["copy"] <= cold[0]["copy"] * 4, "32 matches require two bounded groups"]
)
if phase == "after":
    baseline = json.loads((Path(__file__).parent / "before.json").read_text())[
        "benchmark"
    ]["cases"]
    for item in cold[1:]:
        earlier = next(x for x in baseline if x["name"] == item["name"])
        checks.append(
            [
                item["exchangesModel"] * 3 < earlier["exchangesModel"],
                "over two thirds fewer modeled exchanges for " + item["name"],
            ]
        )
print(
    json.dumps(
        {
            "passed": all(x[0] for x in checks),
            "setup": "identical captured 13-family structure; different local match IDs",
            "psycopg": psycopg.__version__,
            "injectedMsPerExchange": simulated_rtt * 1000,
            "writerSha256": hashlib.sha256(
                Path(inspect.getfile(writer)).read_bytes()
            ).hexdigest(),
            "peakProcessRSSPlatformBytes": resource.getrusage(
                resource.RUSAGE_SELF
            ).ru_maxrss,
            "cases": cases,
            "checks": checks,
        }
    )
)
