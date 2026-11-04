"""Continue at the sample's byte cap with aggregate-only SQL, reproducing typed row cardinalities."""

from survey import *
from relational_match_model import Children, families, nested_families


def paths(f):
    obj = families[nested_families.get(f, f)]
    out = {obj.table: "strict $"}

    def visit(tree, pre):
        for k, c in tree.items():
            q = pre + '."' + k + '"'
            if isinstance(c, Children):
                q += ".keyvalue().value" if c.keyed else "[*]"
                out[c.table] = q
                visit(c.fields, q)
            elif isinstance(c, dict):
                visit(c, q)

    visit(obj.fields, "strict $")
    return out


def counter_sql(f):
    ending = SQL.index("SELECT id, CASE WHEN docid")
    sql = (
        SQL[:ending]
        + ", envelope AS ("
        + SQL[ending:]
        + "), raw(id,body) AS (SELECT id,coalesce(doc->'observation',doc->'response',doc) FROM envelope e(id,doc)), parsed(id,wrapped) AS (SELECT id,coalesce(body->'response',body) FROM raw), payload AS (SELECT id,wrapped->'data' AS data,wrapped->'status' AS status,wrapped IS NULL AS absent FROM parsed), canonical AS (SELECT id,status,absent,CASE WHEN data IS NULL OR data='null' THEN NULL ELSE "
    )
    value = {
        "players": "jsonb_build_object('players',data)",
        "single_player": "jsonb_build_object('players',jsonb_build_array(data))",
        "single_advanced": "jsonb_build_object('players',jsonb_build_array(data))",
        "single_halves": "jsonb_build_object('players',jsonb_build_array(data-'match_id'))",
        "single_shot": "jsonb_build_object('periods',jsonb_build_array(jsonb_build_object('shots',jsonb_build_array(data))))",
    }.get(f, "data")
    sql += (
        value
        + " END AS original FROM payload) SELECT id,status,absent,(SELECT jsonb_object_agg(k,n) FROM (SELECT k,jsonb_array_length(jsonb_path_query_array(original,pat::jsonpath,'{}',true)) AS n FROM jsonb_each_text(%s) spec(k,pat)) c WHERE n>0) FROM canonical"
    )
    return sql


def main():
    report = json.loads((folder / "source-byte-stop.json").read_text())
    olds = {tuple(r["id"]): r for r in report["sample"]}
    rng = random.Random(41372)
    pending = []
    cross = Counter()
    for (f, src, cls), g in sorted(make_population().items()):
        if cls == "error":
            continue
        label = "/".join((f, src, cls))
        n = (
            100
            if f in ("players", "player_halves", "single_player", "single_halves")
            else 28
        )
        for i, (k, r) in enumerate(rng.sample(g, min(n, len(g)))):
            if k not in olds or i < 3:
                pending.append((label, k, r))
    from itertools import groupby

    size = 0
    with connection() as d:
        for label, grp in groupby(pending, key=lambda x: x[0]):
            group = list(grp)
            f = label.split("/")[0]
            for i in range(0, len(group), 8):
                batch = group[i : i + 8]
                req = [
                    dict(id=j, path=r[1], docpath=r[2], ord=r[3], docid=r[4])
                    for j, (_, k, r) in enumerate(batch)
                ]
                for j, status, absent, counts in d.execute(
                    counter_sql(f), (json.dumps(req), json.dumps(paths(f)))
                ):
                    _, k, r = batch[j]
                    counts = counts or {}
                    status = r[-1] if r[-1] is not None else status
                    if absent:
                        raise ValueError("Missing selected source: " + str(k))
                    if k in olds:
                        assert olds[k]["rows"] == counts, (k, olds[k]["rows"], counts)
                        cross[label] += 1
                    else:
                        report["sample"].append(
                            {"s": label, "id": k, "rows": counts, "status": status}
                        )
                    size += len(json.dumps(counts).encode())
    report.update(
        sampled=len(report["sample"]),
        sqlCountParity=dict(cross),
        rowCountResponseJSONBytes=size,
    )
    (folder / "effective-sample.json").write_text(
        json.dumps(report, separators=(",", ":")) + "\n"
    )
    print(
        "complete",
        report["sampled"],
        "parity",
        sum(cross.values()),
        "count JSON bytes",
        size,
    )


if __name__ == "__main__":
    main()
