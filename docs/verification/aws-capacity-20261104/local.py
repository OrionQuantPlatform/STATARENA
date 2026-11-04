"""Physical comparison and full relation equality in disposable PG18. No product DDL."""

from pathlib import Path
import gzip, json, os, sys
import psycopg

folder = Path(__file__).resolve().parent
out = folder / sys.argv[1]
raw = Path("/tmp/statarena-metric-values-20261104")
url = os.environ["TEST_DATABASE_URL"]
assert "@127.0.0.1:" in url
r = {
    "command": "node docs/verification/aws-capacity-20261104/run.mjs metric-layout",
    "setup": "PG18, exact 411,416 published rows exported from RDS + original local heap and equivalent unique indexes. Types and values compared, including dynamic names, present-null and ordering.",
}
cols = "resource_id bigint,record_no int,missing text[],null_groups text[],parent_no int,position int,metric_label text,key text,stat_type text,stat_value float8,stat_total float8"
metrics = "metric_label,key,stat_type,stat_value,stat_total,missing,null_groups"
with psycopg.connect(url, autocommit=True) as d:
    for fs in ("p", "h"):
        d.execute(
            "CREATE TABLE "
            + fs
            + " ("
            + cols
            + ",PRIMARY KEY(resource_id,record_no),UNIQUE(resource_id,parent_no,position))"
        )
        file = {"p": "player_stat_metrics", "h": "half_stat_metrics"}[fs]
        with (
            gzip.open(raw / (file + ".tsv.gz"), "rb") as f,
            d.cursor().copy("COPY " + fs + " FROM STDIN") as cp,
        ):
            while b := f.read(1 << 20):
                cp.write(b)
    d.execute(
        "CREATE TEMP VIEW src AS SELECT 0 AS fam,* FROM p UNION ALL SELECT 1 AS fam,* FROM h"
    )
    d.execute(
        "CREATE TEMP TABLE ranked AS SELECT s.*,dense_rank() OVER(ORDER BY "
        + metrics
        + ")::int AS def FROM src s"
    )
    d.execute(
        "CREATE TABLE fact_dictionary AS SELECT DISTINCT def,"
        + metrics
        + " FROM ranked"
    )
    d.execute("ALTER TABLE fact_dictionary ADD PRIMARY KEY(def)")
    d.execute(
        "CREATE UNIQUE INDEX fact_natural ON fact_dictionary("
        + metrics
        + ") NULLS NOT DISTINCT"
    )
    d.execute(
        "CREATE TABLE fact_links AS SELECT resource_id,parent_no,position,def FROM ranked ORDER BY resource_id,parent_no,position"
    )
    d.execute("ALTER TABLE fact_links ADD PRIMARY KEY(resource_id,parent_no,position)")
    d.execute("ALTER TABLE fact_links ADD FOREIGN KEY(def) REFERENCES fact_dictionary")
    d.execute(
        """CREATE TEMP TABLE semantic_groups AS SELECT resource_id,parent_no,array_agg(def ORDER BY position) ids FROM ranked GROUP BY resource_id,parent_no"""
    )
    d.execute(
        "CREATE TEMP TABLE signatures AS SELECT *,dense_rank() OVER(ORDER BY ids)::int AS group_id FROM semantic_groups"
    )
    d.execute(
        "CREATE TABLE group_dictionary AS SELECT group_id,sha256(int4send(cardinality(ids))||array_send(ids)) AS digest FROM (SELECT DISTINCT group_id,ids FROM signatures) u"
    )
    d.execute("ALTER TABLE group_dictionary ADD PRIMARY KEY(group_id)")
    d.execute("CREATE UNIQUE INDEX group_digest ON group_dictionary(digest)")
    d.execute(
        "CREATE TABLE group_members AS SELECT group_id,(position-1)::smallint AS position,def FROM (SELECT DISTINCT group_id,ids FROM signatures) s CROSS JOIN LATERAL unnest(ids) WITH ORDINALITY m(def,position)"
    )
    d.execute("ALTER TABLE group_members ADD PRIMARY KEY(group_id,position)")
    d.execute(
        "ALTER TABLE group_members ADD FOREIGN KEY(def) REFERENCES fact_dictionary"
    )
    d.execute(
        "ALTER TABLE group_members ADD FOREIGN KEY(group_id) REFERENCES group_dictionary"
    )
    d.execute(
        "CREATE TABLE group_links AS SELECT resource_id,parent_no,group_id FROM signatures ORDER BY resource_id,parent_no"
    )
    d.execute("ALTER TABLE group_links ADD PRIMARY KEY(resource_id,parent_no)")
    d.execute(
        "ALTER TABLE group_links ADD FOREIGN KEY(group_id) REFERENCES group_dictionary"
    )
    # Include metric record order, as used in original DDL, even though the API addresses metrics by their key.
    d.execute(
        "CREATE TEMP VIEW reconstructed AS SELECT l.resource_id,(row_number() OVER(PARTITION BY resource_id ORDER BY l.parent_no,m.position)-1)::int AS record_no,f.missing,f.null_groups,l.parent_no,m.position::int,f.metric_label,f.key,f.stat_type,f.stat_value,f.stat_total FROM group_links l JOIN group_members m USING(group_id) JOIN fact_dictionary f USING(def)"
    )
    src = "SELECT " + ",".join(c.split()[0] for c in cols.split(",")) + " FROM src"
    diffs = d.execute(
        "SELECT count(*) FROM (("
        + src
        + " EXCEPT ALL SELECT * FROM reconstructed) UNION ALL (SELECT * FROM reconstructed EXCEPT ALL "
        + src
        + ")) x"
    ).fetchone()[0]
    r["symmetricDifference"] = diffs
    groups = {
        "baseline": ["h", "p"],
        "dictionaryLinks": ["fact_links", "fact_dictionary"],
        "sharedGroups": [
            "fact_dictionary",
            "group_dictionary",
            "group_members",
            "group_links",
        ],
    }
    rel = {}
    for t in set(x for xs in groups.values() for x in xs):
        d.execute("VACUUM ANALYZE " + t)
        rel[t] = dict(
            zip(
                ["rows", "bytes", "indexBytes"],
                d.execute(
                    "SELECT (SELECT count(*) FROM "
                    + t
                    + "),pg_total_relation_size(%s),pg_indexes_size(%s)",
                    (t, t),
                ).fetchone(),
            )
        )
    r["relations"] = rel
    r["layouts"] = {k: sum(rel[t]["bytes"] for t in ts) for k, ts in groups.items()}
    r["rows"] = rel["p"]["rows"] + rel["h"]["rows"]
    r["passed"] = diffs == 0
(out / "results.json").write_text(json.dumps(r, indent=2) + "\n")
print(r)
sys.exit(not r["passed"])
