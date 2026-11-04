"""Read current imported shapes, verifying the exact inputs used by the app publisher."""

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import gzip
import json
from pathlib import Path
import sys

from db import connection, ROOT

folder = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "dashboard/scripts"))
from relational_catalog import models, normalize, rows_for
from relational_catalog_keys import records
from relational_materialize import CATALOG_PATHS, PROFILE
from relational_support import FAMILIES, _encode


def compact(x):
    return json.dumps(x, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def digest(x):
    return sha256(compact(x).encode()).hexdigest()


def catalog(d):
    orig = {
        r["path"]: r
        for r in json.loads(
            (folder.parent / "aws-catalog-20261104/source-audit-after.json").read_text()
        )
    }
    b = json.loads(
        (
            folder.parent / "aws-catalog-20261104/full-postgres-roundtrip.json"
        ).read_text()
    )
    proven = {r["path"] for r in b["sources"] if not r.get("error")}
    stats = Counter()
    anomalies = []
    max_changed_bytes = 0
    active = d.execute(
        "SELECT path,encode(sha256,'hex') FROM statarena.objects WHERE path~%s OR path='raw/supplemental-index.json' ORDER BY path",
        (CATALOG_PATHS,),
    ).fetchall()
    for p, h in active:
        old = orig.get(p, {})
        if old.get("sha256") == h and "error" not in old and p in proven:
            stats["same_validated_version"] += 1
            continue
        row = d.execute(
            "SELECT d.document FROM statarena.current_file_documents d JOIN statarena.objects o ON o.path=d.source_path WHERE d.source_path=%s AND d.document_path=%s AND o.sha256=decode(%s,'hex')",
            (p, p, h),
        ).fetchone()
        if not row:
            stats["current_document_missing"] += 1
            anomalies.append([p, "no current indexed document"])
            continue
        max_changed_bytes += len(compact(row[0]).encode())
        try:
            mapped = list(records(p, row[0]))
            if not mapped:
                raise ValueError("No mapped records")
            for model, _, _, _, body in mapped:
                rows_for(models[model], normalize(model, body))
            stats["changed_validated"] += 1
        except (ValueError, TypeError, KeyError) as e:
            stats["invalid"] += 1
            anomalies.append([p, str(e)])
    return dict(
        universe=len(active),
        counts=stats,
        anomalies=anomalies,
        inputVersionFingerprint=digest(active),
        changedBodyJsonBytes=max_changed_bytes,
    )


def support(d):
    source = json.loads(
        gzip.decompress(
            (folder.parent / "aws-support-20261104/projections.json.gz").read_bytes()
        )
    )
    baseline = {(k, p): v for k, p, v in source}
    actual = d.execute(
        "SELECT name,params,body FROM statarena.projections WHERE name=ANY(%s) ORDER BY 1,2",
        (list(FAMILIES),),
    ).fetchall()
    errors = []
    same = 0
    for family, param, v in actual:
        if v == baseline.get((family, param)):
            same += 1
        try:
            _encode(FAMILIES[family], v, (), defaultdict(list))
        except (TypeError, ValueError, KeyError) as e:
            errors.append([family, param, str(e)])
    return dict(
        universe=len(actual),
        identicalPriorHTTPFixtures=same,
        actualSha256=digest(actual),
        invalid=errors,
        jsonBytes=len(compact(actual).encode()),
    )


# Each requested source path joins a version-pinned document only once per batch.
# Expand ordinal archives once and emit only the retained profiles from each shard.
# Only grouped path/type counts and representative endpoint identities cross the network.
PROFILE_SQL = """
WITH RECURSIVE requests AS MATERIALIZED (
 SELECT * FROM jsonb_to_recordset(%s::jsonb) AS x(endpoint text,kind text,status int,error jsonb,path text,ordinal int,expected text)
), latest AS MATERIALIZED (
 SELECT p.path,o.sha256,f.document FROM (SELECT DISTINCT path FROM requests) p
 LEFT JOIN statarena.objects o ON o.path=p.path
 LEFT JOIN statarena.current_file_documents f ON f.source_path=p.path AND f.document_path=p.path
), ordinals AS MATERIALIZED (
 SELECT l.path,a.ordinality-1 AS ordinal,a.value AS doc
 FROM latest l CROSS JOIN LATERAL jsonb_array_elements(CASE WHEN jsonb_typeof(l.document)='array' THEN l.document ELSE '[]' END) WITH ORDINALITY a
), resolved AS MATERIALIZED (
 SELECT q.*,CASE WHEN q.ordinal IS NULL THEN l.document ELSE a.doc END doc,
 CASE WHEN q.path IS NULL THEN NULL WHEN l.document IS NULL THEN 'document_missing'
 WHEN q.expected IS NOT NULL AND q.expected<>encode(l.sha256,'hex') THEN 'version_mismatch'
 WHEN q.ordinal IS NOT NULL AND a.doc IS NULL THEN 'ordinal_missing' END gap
 FROM requests q LEFT JOIN latest l USING(path) LEFT JOIN ordinals a ON a.path=q.path AND a.ordinal=q.ordinal
), raw AS (
 SELECT *,COALESCE(doc->'observation',doc->'response',doc) rawdoc FROM resolved
), env AS (
 SELECT *,COALESCE(rawdoc->'response',rawdoc) wrap FROM raw
), tree(kind,endpoint,p,v) AS (
 SELECT kind,endpoint,'{}'::text[],jsonb_build_object('status',status,'data',wrap->'data','error',coalesce(nullif(error,'null'),wrap->'error')) FROM env WHERE gap IS NULL
 UNION ALL SELECT t.kind,t.endpoint,t.p||x.k,x.v FROM tree t
 CROSS JOIN LATERAL(
 SELECT key AS k,value AS v FROM jsonb_each(CASE WHEN jsonb_typeof(t.v)='object' THEN t.v ELSE '{}' END)
 UNION ALL SELECT '[]',value FROM jsonb_array_elements(CASE WHEN jsonb_typeof(t.v)='array' THEN t.v ELSE '[]' END)
 )x
), shapes AS (
 SELECT kind,p, CASE WHEN jsonb_typeof(v)='number' THEN CASE
 WHEN v::text~'^-?[0-9]+$' AND v::text::numeric BETWEEN -2147483648 AND 2147483647 THEN 'int32'
 WHEN v::text~'^-?[0-9]+$' THEN 'large-int' ELSE 'numeric' END ELSE jsonb_typeof(v) END typ,endpoint FROM tree
)
SELECT kind,p,typ,count(*)::int,min(endpoint) FROM shapes GROUP BY 1,2,3
UNION ALL SELECT kind,ARRAY['@gap'],gap,count(*)::int,min(endpoint) FROM resolved WHERE gap IS NOT NULL GROUP BY kind,gap
UNION ALL SELECT kind,ARRAY['@gap'],'nonobject-envelope',count(*)::int,min(endpoint) FROM env WHERE gap IS NULL AND path IS NOT NULL AND jsonb_typeof(wrap) IS DISTINCT FROM 'object' GROUP BY kind
"""


def expected_walk(spec, p=()):
    if isinstance(spec, str):
        if spec.endswith("[]"):
            yield p, {"array", "null"}
            yield from expected_walk(spec[:-2], p + ("[]",))
            return
        yield (
            p,
            {
                "text": {"string"},
                "integer": {"int32"},
                "boolean": {"boolean"},
                "double precision": {"int32", "large-int", "numeric"},
            }[spec]
            | {"null"},
        )
    elif "@rows" in spec:
        yield p, {"array", "null"}
        yield from expected_walk(spec["fields"], p + ("[]",))
    else:
        yield p, {"object", "null"}
        for k, v in spec.items():
            yield from expected_walk(v, p + (k,))


def profiles(d):
    from relational_catalog import spec

    allrows = d.execute(
        """SELECT endpoint,status,error,ref FROM statarena.resources WHERE params='{}' AND endpoint~%s ORDER BY endpoint""",
        (PROFILE,),
    ).fetchall()
    by_path = defaultdict(list)
    errors = []
    actual = Counter()
    examples = {}
    wire = 0
    groups = 0
    for end, status, error, ref in allrows:
        r = ref or {}
        bits = end.strip("/").split("/")
        kind = "profile_" + (bits[0] if len(bits) == 2 else "catalog")
        if "documentId" in r:
            errors.append([end, "unhandled-documentId-selector"])
            continue
        by_path[r.get("path")].append(
            dict(
                endpoint=end,
                kind=kind,
                status=status,
                error=error,
                path=r.get("path"),
                ordinal=r.get("ordinal"),
                expected=r.get("sha256"),
            )
        )
    shape_schema = {
        k: dict(expected_walk(v)) for k, v in spec.items() if k.startswith("profile_")
    }
    paths = list(by_path)
    versions = digest(allrows)
    for start in range(0, len(paths), 32):
        selected = [row for p in paths[start : start + 32] for row in by_path[p]]
        rows = d.execute(PROFILE_SQL, (compact(selected),)).fetchall()
        groups += 1
        wire += len(compact(rows).encode())
        for kind, p, typ, n, example in rows:
            k = (kind, tuple(p), typ)
            actual[k] += n
            examples.setdefault(k, example)
        if groups % 16 == 0:
            print("profile metadata batches", groups, flush=True)
    for (kind, p, typ), n in sorted(actual.items()):
        if typ not in shape_schema[kind].get(p, set()):
            errors.append(
                dict(
                    model=kind,
                    field=list(p),
                    actual=typ,
                    count=n,
                    example=examples[kind, p, typ],
                )
            )
    counts = Counter(r["kind"] for rows in by_path.values() for r in rows)
    valid = sum(n for (_, p, _), n in actual.items() if not p)
    return dict(
        universe=len(allrows),
        profileCounts=counts,
        resolvedRoots=valid,
        sourcePaths=len(paths),
        batchCount=groups,
        sourceRefFingerprint=versions,
        shapeResponseJsonBytes=wire,
        violations=errors,
        shapes=[
            dict(model=k, field=list(p), type=t, count=n)
            for (k, p, t), n in sorted(actual.items())
        ],
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("family", choices=("profiles", "catalog", "support"))
    arg = parser.parse_args()
    report = dict(
        command="PYTHONPATH=/tmp/statarena-publication-test-python python3 docs/verification/aws-source-preflight-20261104/audit.py "
        + arg.family,
        expected="Every source resolved and valid, or exact violations and gaps enumerated",
        setup="PROTOCOL.md",
    )
    try:
        with connection() as d, d.transaction():
            d.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            report["snapshot"] = str(d.execute("SELECT now()").fetchone()[0])
            report.update(globals()[arg.family](d))
    except Exception as e:
        report["failure"] = str(e)
        raise
    finally:
        (folder / (arg.family + ".json")).write_text(
            json.dumps(report, indent=2) + "\n"
        )
        print(
            {
                k: v
                for k, v in report.items()
                if k not in ("shapes", "sourceRefFingerprint", "anomalies", "setup")
            },
            flush=True,
        )
