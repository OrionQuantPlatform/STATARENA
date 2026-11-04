import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import psycopg

folder = Path(__file__).resolve().parent
cfg = json.loads(Path(os.environ["STATARENA_PROBE_CONFIG"]).read_text())
opts = {
    "host": cfg["host"],
    "user": cfg["username"],
    "password": cfg["password"],
    "dbname": "statarena_prod",
    "connect_timeout": 4,
    "sslmode": "verify-full",
    "sslrootcert": os.environ["STATARENA_PROBE_CA"],
    "options": "-c default_transaction_read_only=on -c statement_timeout=4500",
}


def stamp():
    return datetime.now(UTC).isoformat()


def choose():
    result = {"at": stamp(), "routes": []}
    with psycopg.connect(**opts) as db:
        info = db.execute(
            """SELECT current_database(),current_setting('server_version'),current_setting('transaction_read_only'),(select ssl from pg_stat_ssl where pid=pg_backend_pid()),(select count(*) from statarena_app.partitions),(select generation from statarena_app.publications where singleton)"""
        ).fetchone()
        result.update(
            dict(
                zip(
                    [
                        "database",
                        "postgres",
                        "readOnly",
                        "tls",
                        "partitions",
                        "generation",
                    ],
                    info,
                )
            )
        )
        assert (
            result["readOnly"] == "on"
            and result["tls"]
            and result["database"] == "statarena_prod"
        )
        if not info[4]:
            return result
        parts = db.execute(
            "select season,league_id,published_at::text from statarena_app.partitions order by published_at,season,league_id limit 32"
        ).fetchall()
        for season, league, published in parts:
            matches = db.execute(
                """select m.id,count(*)::int,array_agg(f.family order by f.family)
              from statarena_app.matches m join statarena_app.match_families f on f.match_id=m.id and f.params='{}' and f.subject_id=''
              where m.season=%s and m.league_id=%s and f.status=200
              group by m.id having bool_or(f.family='match') and bool_or(f.family in ('shots','stats','events'))
              order by count(*) desc,m.id limit 12""",
                (season, league),
            ).fetchall()
            for mid, n, families in matches:
                ref = db.execute(
                    "SELECT s.ref FROM statarena.observations o JOIN statarena.shards s ON s.id=o.shard WHERE o.id=%s",
                    (mid,),
                ).fetchone()
                saved = db.execute(
                    """select endpoint,ref,status from statarena.resources where endpoint=any(%s) and params='{}'""",
                    (
                        [
                            "/matches/" + mid + suffix
                            for suffix in (
                                "",
                                "/shots",
                                "/stats",
                                "/events",
                                "/players",
                                "/players/halves",
                                "/lineups",
                                "/momentum",
                                "/h2h",
                                "/advanced",
                                "/advanced/players",
                                "/advanced/network",
                                "/heatmaps",
                            )
                        ],
                    ),
                ).fetchall()
                if not ref and not saved:
                    continue
                paths = {r[1]["path"] for r in saved if r[1] and "path" in r[1]}
                if ref:
                    paths.update(
                        x["path"]
                        for x in [ref[0]["document"], *ref[0]["tables"].values()]
                        if "path" in x
                    )
                if not paths:
                    continue
                objects = db.execute(
                    "select path,size,encode(sha256,'hex') from statarena.objects where path=any(%s) order by path",
                    (list(paths),),
                ).fetchall()
                size = sum(x[1] for x in objects)
                if len(objects) != len(paths) or size > 8 * 1024 * 1024:
                    continue
                family = next(f for f in ("shots", "stats", "events") if f in families)
                version = db.execute(
                    "select version from statarena_app.match_detail_versions where match_id=%s",
                    (mid,),
                ).fetchone()[0]
                result.update(
                    {
                        "match": mid,
                        "league": league,
                        "season": season,
                        "publishedAt": published,
                        "families": families,
                        "sourceBytesBound": size,
                        "objectDigests": [(a, int(b), c) for a, b, c in objects],
                        "matchVersion": version,
                        "routes": [
                            "/api/archive/matches/" + mid,
                            "/api/pitchapi/matches/" + mid + "/" + family,
                        ],
                    }
                )
                profiles = db.execute(
                    """SELECT c.scope,c.edition,c.source_digest FROM statarena_app.catalog_editions c WHERE catalog='profile' AND scope='players' AND response_status=200 ORDER BY edition LIMIT 12"""
                ).fetchall()
                for kind, pid, digest in profiles:
                    p = db.execute(
                        """SELECT o.size,encode(o.sha256,'hex') FROM statarena.resources r JOIN statarena.objects o ON o.path=r.ref->>'path' WHERE r.endpoint=%s AND r.params='{}' AND r.status=200""",
                        ("/players/" + pid,),
                    ).fetchone()
                    if p and p[0] <= 2 * 1024 * 1024:
                        result.update(
                            {
                                "profile": pid,
                                "profileVersion": digest,
                                "profileSourceSha": p[1],
                            }
                        )
                        result["routes"].append("/api/archive/profiles/players/" + pid)
                        break
                return result
    result["reason"] = (
        "No eligible match with budgeted archived/S3 sources in bounded partition/ID scan"
    )
    return result


if __name__ == "__main__":
    d = choose()
    (folder / (sys.argv[1] + ".json")).write_text(json.dumps(d, indent=2) + "\n")
    print(
        {
            k: v
            for k, v in d.items()
            if k
            in (
                "at",
                "partitions",
                "generation",
                "match",
                "sourceBytesBound",
                "routes",
                "reason",
            )
        }
    )
