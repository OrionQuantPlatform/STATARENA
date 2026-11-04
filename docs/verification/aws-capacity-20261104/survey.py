"""Design-based sample of effective match representations under the current worker."""

import gzip, hashlib, json, math, random, re, sys, time
from pathlib import Path
from collections import Counter, defaultdict
from statistics import mean, variance

folder = Path(__file__).resolve().parent
root = folder.parents[2]
sys.path[:0] = [
    str(root / "dashboard/scripts"),
    str(folder.parent / "aws-source-preflight-20261104"),
]
from db import connection
from relational_match import prepare, _resource_address

source = Path("/tmp/statarena-prepare-meta-20261104")


def rows(name):
    with gzip.open(source / (name + ".tsv.gz"), "rt") as f:
        for line in f:
            yield line.rstrip("\n").split("\t")


def make_population():
    shards = {s: json.loads(r) for s, r in rows("shards")}
    records = {}
    for mid, s, ordinal in rows("observations"):
        shard = shards[s]
        for f, ref in shard["tables"].items():
            records[(mid, f, "{}", "")] = (
                "archive",
                ref["path"],
                shard["document"]["path"],
                int(ordinal),
                None,
                None,
            )
    for ep, params, status, p, o, doc, *_ in rows("resources"):
        a = _resource_address(ep)
        if not a:
            continue
        mid, f, subject = a
        records[(mid, f, params, subject)] = (
            "saved",
            p,
            None,
            int(o) if o != "\\N" else None,
            doc if doc != "\\N" else None,
            int(status),
        )
    groups = defaultdict(list)
    for k, r in records.items():
        groups[
            (k[1], r[0], "error" if r[-1] is not None and r[-1] != 200 else "body")
        ].append((k, r))
    return groups


SQL = """WITH req AS MATERIALIZED(SELECT * FROM jsonb_to_recordset(%s::jsonb) r(id int,path text,docpath text,ord int,docid text)),
src AS MATERIALIZED(SELECT p.path,d.document FROM (SELECT path FROM req UNION SELECT docpath FROM req WHERE docpath IS NOT NULL) p LEFT JOIN LATERAL
(SELECT document FROM statarena.current_file_documents WHERE document_path=p.path AND source_path=p.path OFFSET 0) d ON true),
selected AS (SELECT r.id,s.document,coalesce(r.docid,(ds.document->r.ord)->>'id') AS docid,r.docpath,r.ord FROM req r JOIN src s ON s.path=r.path LEFT JOIN src ds ON ds.path=r.docpath)
SELECT id, CASE WHEN docid IS NOT NULL THEN (SELECT val FROM jsonb_array_elements(s.document) val WHERE val->>'documentId'=s.docid LIMIT 1)
WHEN ord IS NOT NULL THEN document->ord ELSE document END FROM selected s"""


def run():
    groups = make_population()
    report = {
        "setup": "PROTOCOL.md; exact effective keys from source-metadata.json, server selects only deterministic requested RDS envelopes, production writer counts typed rows locally",
        "command": "PYTHONPATH=/tmp/statarena-publication-test-python python3 docs/verification/aws-capacity-20261104/survey.py",
        "strata": {},
        "sample": [],
    }
    samp = []
    rng = random.Random(41372)
    for (f, src, cls), group in sorted(groups.items()):
        label = "/".join((f, src, cls))
        N = len(group)
        report["strata"][label] = N
        if cls == "error":
            continue
        n = (
            100
            if f in ("players", "player_halves", "single_player", "single_halves")
            else 28
        )
        for k, r in rng.sample(group, min(n, N)):
            samp.append((label, k, r))
    wire = 0
    start = time.monotonic()
    with connection() as d:
        for b in range(0, len(samp), 8):
            batch = samp[b : b + 8]
            req = [
                dict(id=i, path=r[1], docpath=r[2], ord=r[3], docid=r[4])
                for i, (_, k, r) in enumerate(batch)
            ]
            records = d.execute(SQL, (json.dumps(req),)).fetchall()
            for i, doc in records:
                label, k, r = batch[i]
                f = k[1]
                row = {"s": label, "id": k}
                report["sample"].append(row)
                if not isinstance(doc, dict):
                    row["error"] = "unresolved source or selector"
                    continue
                body = doc.get("observation", doc.get("response", doc))
                body = body.get("response", body)
                env = {
                    "status": r[-1] if r[-1] is not None else body.get("status"),
                    "error": body.get("error"),
                    "data": body.get("data"),
                }
                wire += len(
                    json.dumps(doc, separators=(",", ":"), ensure_ascii=False).encode()
                )
                try:
                    head, children = prepare(f, env)
                    row["rows"] = {s.table: len(entries) for s, entries in children}
                    row["status"] = env["status"]
                except Exception as e:
                    row["error"] = str(e)
            if b % 128 == 0:
                print(b, len(samp), wire, flush=True)
            report.update(
                sampled=len(report["sample"]),
                responseJsonBytes=wire,
                elapsedSeconds=round(time.monotonic() - start, 1),
            )
            (folder / "effective-sample.json").write_text(
                json.dumps(report, separators=(",", ":")) + "\n"
            )
            if wire > 35_000_000:
                (folder / "source-byte-stop.json").write_text(
                    json.dumps(report, separators=(",", ":")) + "\n"
                )
                print(
                    "Body transfer checkpoint reached at the end of this eight-key batch; continue with count_remaining.py.",
                    flush=True,
                )
                return


if __name__ == "__main__":
    run()
