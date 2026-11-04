"""Exercise discovery twice on exactly the same populated PG18 metadata fixture."""

import ast, gzip, hashlib, json, os, re, subprocess, sys, time, traceback
from pathlib import Path
from types import SimpleNamespace
import psycopg

folder = Path(__file__).resolve().parent
root = folder.parents[2]
phase = sys.argv[1]
out = folder / phase
sys.path.insert(0, str(root / "dashboard/scripts"))
import relational_materialize as live

source = Path("/tmp/statarena-prepare-meta-20261104")
rev = (folder / "baseline.txt").read_text().strip()
baseline = subprocess.check_output(
    ["git", "show", rev + ":dashboard/scripts/relational_materialize.py"], text=True
)
fn = next(
    x
    for x in ast.parse(baseline).body
    if isinstance(x, ast.FunctionDef) and x.name == "prepare"
)
env = vars(live).copy()
exec(compile(ast.Module(body=[fn], type_ignores=[]), "baseline", "exec"), env)
url = os.environ["TEST_DATABASE_URL"]
assert "@127.0.0.1:" in url
report = {
    "command": "node docs/verification/aws-prepare-20261104/run.mjs " + phase,
    "setup": "Full live staging shape from source-metadata.json; synthetic no-payload objects; 4 MB work_mem; temporary PG18",
    "baselineRevision": rev,
    "runs": [],
    "passed": False,
}


def fingerprint(db, table, expr, order):
    return db.execute(
        "SELECT count(*),md5(string_agg(md5("
        + expr
        + "),'' ORDER BY "
        + order
        + ")) FROM "
        + table
    ).fetchone()


def walk(p):
    yield p
    for child in p.get("Plans", []):
        yield from walk(child)


class Probe:
    def __init__(self, d):
        self.d = d
        self.stats = []
        self.plan = {}

    def __getattr__(self, k):
        return getattr(self.d, k)

    def execute(self, query, *args):
        start = time.monotonic()
        sql = " ".join(query.split())
        tok = sql.split()
        explain = (
            sql.startswith("CREATE TEMP TABLE ")
            and " AS SELECT" in sql
            or sql.startswith("INSERT INTO work_matches SELECT")
        )
        if explain:
            tag = " ".join(tok[:4]) + (
                " " + str(len(self.stats)) if sql.startswith("INSERT") else ""
            )
            plan = self.d.execute(
                "EXPLAIN (ANALYZE, BUFFERS, TIMING OFF, FORMAT JSON) " + query, *args
            ).fetchone()[0][0]
            self.plan[tag] = plan
            result = None
        else:
            tag = " ".join(tok[:6])
            result = self.d.execute(query, *args)
        self.stats.append([tag, round(time.monotonic() - start, 4)])
        return result


try:
    with psycopg.connect(url, autocommit=True) as d:
        d.execute((root / "dashboard/backend/migrations/001_neon.sql").read_text())
        live.install(d)
        d.execute("SET work_mem='4MB'")
        d.execute("SET statement_timeout='120s'")
        d.execute(
            "CREATE TEMP TABLE source_fixtures(id text,league_id text,season text)"
        )
        d.execute("CREATE TEMP TABLE source_objects(path text)")
        d.execute(
            "CREATE TEMP TABLE source_resources(endpoint text,params text,status smallint,path text,ordinal int,docid text,has_sha int,error jsonb)"
        )
        ddl = {
            "fixtures": "source_fixtures",
            "observations": "statarena.observations",
            "shards": "statarena.shards",
            "objects": "source_objects",
            "resources": "source_resources",
        }
        for k in ("fixtures", "objects", "resources", "shards", "observations"):
            with (
                gzip.open(source / (k + ".tsv.gz"), "rb") as file,
                d.cursor().copy("COPY " + ddl[k] + " FROM STDIN") as cp,
            ):
                while buf := file.read(1024 * 1024):
                    cp.write(buf)
        d.execute(
            """INSERT INTO statarena.objects(path,size,sha256,etag) SELECT path,1000,sha256(convert_to(path,'UTF8')),'local' FROM source_objects"""
        )
        d.execute(
            """INSERT INTO statarena.resources(endpoint,params,status,ref,error,updated_at) SELECT endpoint,params,status,CASE WHEN path IS NOT NULL THEN jsonb_strip_nulls(jsonb_build_object('path',path,'ordinal',ordinal,'documentId',docid,'sha256',CASE WHEN has_sha=1 THEN encode(sha256(convert_to(path,'UTF8')),'hex') END)) END,error,'2026-11-04'::timestamptz FROM source_resources"""
        )
        d.execute(
            """INSERT INTO statarena.fixtures(id,league_id,season,body,updated_at) SELECT id,league_id,season,'{}','2026-11-04'::timestamptz FROM source_fixtures"""
        )
        d.execute("ANALYZE")
        known = {}
        for s, l in d.execute(
            "SELECT DISTINCT season,league_id FROM statarena.fixtures WHERE season ~ '^[0-9]{4}(/[0-9]{4})?$'"
        ):
            known.setdefault(s, []).append({"leagueId": l})
        manifest = {"seasons": [{"id": k, "chunks": v} for k, v in known.items()]}
        ops = (
            [("old", env["prepare"])]
            if phase == "before"
            else [("old", env["prepare"]), ("new", live.prepare)]
        )
        for name, operation in ops:
            probe = Probe(d)
            t = time.monotonic()
            operation(SimpleNamespace(db=probe), manifest, True)
            elapsed = time.monotonic() - t
            f = {
                key: fingerprint(d, *spec)
                for key, spec in {
                    "matches": (
                        "work_matches",
                        "concat_ws('|',id,season,league_id,stamp)",
                        "id",
                    ),
                    "scopes": (
                        "work_scopes",
                        "concat_ws('|',season,league_id,digest)",
                        "season,league_id",
                    ),
                    "jobs": (
                        "statarena_app.publication_jobs",
                        "concat_ws('|',season,league_id)",
                        "season,league_id",
                    ),
                    "catalog": (
                        "work_catalog",
                        "concat_ws('|',kind,key,digest)",
                        "kind,key",
                    ),
                }.items()
            }
            hot = probe.plan["CREATE TEMP TABLE work_matches"]
            scans = [
                p.get("Relation Name")
                for p in walk(hot["Plan"])
                if p.get("Relation Name")
            ]
            most = max(
                (p.get("Actual Loops", 1) * (p.get("Rows Removed by Join Filter", 0)))
                for p in walk(hot["Plan"])
            )
            run = {
                "implementation": name,
                "seconds": round(elapsed, 3),
                "fixtureJoinMs": hot["Execution Time"],
                "hotRelations": scans,
                "maxJoinFilterDiscards": most,
                "fingerprints": f,
                "steps": probe.stats,
            }
            report["runs"].append(run)
            (out / (name + "-plans.json")).write_text(
                json.dumps(probe.plan, indent=1) + "\n"
            )
            print(name, elapsed, hot["Execution Time"], scans, most, flush=True)
            d.execute("TRUNCATE statarena_app.publication_jobs")
        rs = report["runs"]
        last = rs[-1]
        report["passed"] = (
            len(rs) == 2
            and rs[0]["fingerprints"] == last["fingerprints"]
            and "work_resource_stamps" in last["hotRelations"]
            and "work_resources" not in last["hotRelations"]
        )
except Exception as e:
    report["failure"] = traceback.format_exc()
    raise
finally:
    (out / "results.json").write_text(json.dumps(report, indent=2) + "\n")
sys.exit(not report["passed"])
