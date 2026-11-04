"""Production read-only evidence. --run requires the deployed stack and actual typed rows."""

import argparse, collections, datetime as dt, gzip, hashlib, http.client, json, os
import re, subprocess, sys, time
from pathlib import Path
from urllib.parse import urlencode, urlsplit, parse_qsl
from http.client import HTTPSConnection
import psycopg
from psycopg.rows import dict_row

HERE = Path(__file__).resolve().parent
ACCOUNT = "361769570630"
REGION = "us-east-2"
parser = argparse.ArgumentParser()
parser.add_argument(
    "--run",
    action="store_true",
    help="run public HTTP workload; default only checks readiness",
)
parser.add_argument("--credentials", default="/tmp/statarena-aws-runtime-20261104.json")
parser.add_argument("--ca", default="/tmp/statarena-rds-us-east-2-20261104.pem")
parser.add_argument("--out", type=Path)
args = parser.parse_args()
now = dt.datetime.now(dt.timezone.utc)
out = args.out or HERE / ("api-" + now.strftime("%Y%m%dT%H%M%S%fZ") + ".json")
report = dict(
    start=now.isoformat(),
    mode="production" if args.run else "preflight",
    command=sys.argv,
    state="running",
    checks=[],
    requests=[],
    missing=[],
    failures=[],
)


def save():
    out.parent.mkdir(exist_ok=True, parents=True)
    temp = out.with_suffix(".tmp")
    temp.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str, allow_nan=False)
        + "\n"
    )
    temp.replace(out)


def check(label, condition, details=None):
    row = {"label": label, "pass": bool(condition)}
    if details is not None:
        row["details"] = details
    report["checks"].append(row)
    if not condition:
        report["failures"].append(label)


def missing(family):
    if family not in report["missing"]:
        report["missing"].append(family)


def aws(*cmd):
    p = subprocess.run(
        [
            "aws",
            "--profile",
            "statarena",
            "--region",
            REGION,
            "--no-cli-pager",
            "--output",
            "json",
            *cmd,
        ],
        capture_output=True,
        text=True,
    )
    if p.returncode:
        raise RuntimeError("AWS discovery failed: " + cmd[0] + "/" + cmd[1])
    return json.loads(p.stdout)


def connection():
    c = json.loads(Path(args.credentials).read_text())
    if (
        c["database"] != "statarena_prod"
        or c["host"] != "statarena-postgres.clcy2iqyajbl.us-east-2.rds.amazonaws.com"
    ):
        raise ValueError("unexpected RDS target")
    return psycopg.connect(
        host=c["host"],
        dbname=c["database"],
        user=c["username"],
        password=c["password"],
        sslmode="verify-full",
        sslrootcert=args.ca,
        connect_timeout=5,
        autocommit=True,
        row_factory=dict_row,
        application_name="statarena-public-acceptance",
        options="-c default_transaction_read_only=on -c statement_timeout=7000 -c lock_timeout=1000",
    )


def fingerprint(value):
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            default=str,
        ).encode()
    ).hexdigest()


def route(path, **params):
    return "/api/" + path + ("?" + urlencode(params) if params else "")


def http(origin, path, method="GET", headers=None, codec="gzip"):
    idx = len(report["requests"])
    h = {
        "Accept-Encoding": codec,
        "Origin": "https://statarena-analytics.vercel.app",
        **(headers or {}),
    }
    conn = HTTPSConnection(urlsplit(origin).hostname, timeout=35)
    start = time.monotonic()
    m = {"route": path, "method": method, "origin": origin}
    try:
        conn.request(method, path, headers=h)
        res = conn.getresponse()
        m["ttfbMs"] = round(1000 * (time.monotonic() - start), 1)
        raw = res.read()
        meta = {k.lower(): v for k, v in res.getheaders()}
        body = (
            gzip.decompress(raw)
            if raw and meta.get("content-encoding") == "gzip"
            else raw
        )
        m.update(
            status=res.status,
            ms=round(1000 * (time.monotonic() - start), 1),
            encodedBytes=len(raw),
            decodedBytes=len(body),
            sha256=hashlib.sha256(body).hexdigest(),
            headers={
                k: meta[k]
                for k in [
                    "x-cache",
                    "age",
                    "x-amz-cf-id",
                    "x-amz-cf-pop",
                    "etag",
                    "content-type",
                    "content-encoding",
                    "cache-control",
                    "location",
                    "access-control-allow-origin",
                    "access-control-allow-methods",
                    "server-timing",
                    "x-data-source",
                ]
                if k in meta
            },
        )
        try:
            value = json.loads(body) if body else None
        except (ValueError, UnicodeDecodeError):
            value = None
        return m, value
    except Exception as error:
        m["exception"] = type(error).__name__
        return m, None
    finally:
        conn.close()
        report["requests"].insert(idx, m)
        save()


def baseline(path, expected=200, predicate=None, validators=True):
    meta, value = http(api, path)
    check("GET " + path, meta.get("status") == expected)
    if meta.get("status") != expected:
        return None
    hdr = meta["headers"]
    check("CORS " + path, hdr.get("access-control-allow-origin") == "*")
    if predicate:
        try:
            check("SQL/contract " + path, predicate(value))
        except (KeyError, TypeError, IndexError, ValueError, AttributeError):
            check("SQL/contract " + path, False)
    if expected != 200:
        check("error no-store " + path, "no-store" in hdr.get("cache-control", ""))
        return value
    if validators:
        tag = hdr.get("etag")
        check("ETag " + path, bool(tag))
        head, _ = http(api, path, "HEAD")
        check(
            "HEAD " + path,
            head.get("status") == 200
            and head.get("decodedBytes") == 0
            and head["headers"].get("etag") == tag,
        )
        if tag:
            cond, _ = http(api, path, headers={"If-None-Match": tag})
            check(
                "304 " + path,
                cond.get("status") == 304
                and cond.get("decodedBytes") == 0
                and cond["headers"].get("etag") == tag,
            )
    return value


def query(sql, params=()):
    return db.execute(sql, params).fetchall()


def first(sql, params=()):
    rows = query(sql, params)
    return rows[0] if rows else None


def targets():
    report["account"] = aws("sts", "get-caller-identity", "--query", "Account")
    if report["account"] != ACCOUNT:
        raise ValueError("unexpected AWS account")
    stack = aws(
        "cloudformation",
        "describe-stacks",
        "--stack-name",
        "statarena-backend",
        "--query",
        "Stacks[0].{status:StackStatus,outputs:Outputs}",
    )
    values = {x["OutputKey"]: x["OutputValue"] for x in stack.get("outputs") or []}
    report["stack"] = {**values, "status": stack["status"]}
    api = values.get("ApiOrigin", "")
    signed = values.get("SignedOrigin", "").rstrip("/")
    if api and (
        not re.fullmatch(r"https://d[a-z0-9]+\.cloudfront\.net", api)
        or "d2clu0phovomb8" in api
    ):
        raise ValueError("unexpected API origin")
    if api:
        distribution = aws(
            "cloudfront",
            "get-distribution",
            "--id",
            values["DistributionId"],
            "--query",
            "Distribution.{status:Status,domain:DomainName}",
        )
        report["distribution"] = distribution
        check(
            "dedicated distribution deployed",
            distribution["status"] == "Deployed"
            and api == "https://" + distribution["domain"],
        )
    return api, signed


def run_family(name, fn):
    try:
        fn()
    except Exception as error:
        check(
            "completed family " + name,
            False,
            {
                "exception": type(error).__name__,
                "sqlstate": getattr(error, "sqlstate", None),
            },
        )


def sample_catalog():
    rows = query(
        "select distinct on(catalog,scope) resource_id,catalog,scope,edition,source_digest from statarena_app.catalog_editions where coalesce(response_status,200)=200 order by catalog,scope,edition desc"
    )
    report["catalogFamilies"] = dict(collections.Counter(r["catalog"] for r in rows))
    calls = {}

    def case(label, path, checkfn):
        calls.setdefault(label, (path, checkfn))

    for r in rows:
        name, scope, edition = r["catalog"], r["scope"], r["edition"]
        if name == "profile":
            if edition and scope in ("teams", "players", "leagues"):
                case(
                    "archive-profile:" + scope,
                    route("archive/profiles/" + scope + "/" + edition),
                    lambda v: "status" in v,
                )
                case(
                    "pitch-profile:" + scope,
                    route("pitchapi/" + scope + "/" + edition),
                    lambda v: v.get("data") is not None,
                )
        elif name == "ranking":
            case(
                "ranking:" + scope,
                route("rankings/edition", kind=scope, edition=edition),
                lambda v: isinstance(v.get("rows"), list) and bool(v["rows"]),
            )
            if scope == "uefa-associations" and re.fullmatch(r"\d{4}\.uefa", edition):
                case(
                    "associations",
                    route("rankings/associations", year=edition[:4]),
                    lambda v: bool(v.get("rows")),
                )
        elif name == "archive-season":
            case(
                "archive:" + scope,
                route("archives/season", kind=scope, season=edition),
                lambda v: isinstance(v, dict) and bool(v),
            )
        elif name == "matchdays":
            case(
                "matchdays",
                route("matchdays", competition=scope, season=edition),
                lambda v: isinstance(v.get("matches"), dict),
            )
        elif name.startswith("cup-") and name != "cup-index":
            kind = name[4:]
            if kind in (
                "native",
                "standings",
                "open-cups",
                "openligadb",
                "nations-results",
            ):
                case(
                    name,
                    route("cup-snapshot", kind=kind, competition=scope, season=edition),
                    lambda v: isinstance(v.get("matches", v.get("tables")), list),
                )
    for kind in ("results", "goals"):
        case(
            "archive-index:" + kind,
            route("archives/index", kind=kind),
            lambda v: bool(v.get("seasons")),
        )
    for kind in ("supplemental", "worker"):
        case(
            "cup-index:" + kind,
            route("cup-index", kind=kind),
            lambda v: bool(v.get("competitions")),
        )
    case("ranking-index", route("rankings/index"), lambda v: bool(v.get("editions")))
    case("leagues", route("pitchapi/leagues"), lambda v: bool(v["data"]["leagues"]))
    case(
        "supplemental",
        route("supplemental"),
        lambda v: bool(v.get("competitions")) and isinstance(v.get("meta"), dict),
    )
    club = first(
        'select metric_label as club,"entityId" as entity from statarena_app.cat_club_links_links order by metric_label limit 1'
    )
    if club:
        case(
            "club-link",
            route("club-links", club=club["club"]),
            lambda v: v["links"][club["club"]]["entityId"] == club["entity"],
        )
        case(
            "ranking-club",
            route("rankings/club", club=club["club"]),
            lambda v: isinstance(v.get("rows"), list),
        )
    for kind in ("results", "fixtures"):
        table = first(
            'select folder,season from statarena_app.cat_cup_worker_index_competitions where "tables_'
            + kind
            + '_rows">0 order by folder limit 1'
        )
        if table:
            case(
                "cup-table:" + kind,
                route(
                    "cup-table",
                    competition=table["folder"],
                    season=table["season"],
                    kind=kind,
                ),
                lambda v: isinstance(v, list) and bool(v),
            )
    required = (
        {"archive-profile:" + k for k in ("teams", "players", "leagues")}
        | {"pitch-profile:" + k for k in ("teams", "players", "leagues")}
        | {"ranking:" + k for k in ("fifa-men", "uefa-associations", "uefa-clubs")}
        | {
            "cup-" + k
            for k in (
                "native",
                "standings",
                "open-cups",
                "openligadb",
                "nations-results",
            )
        }
        | {
            "archive:results",
            "archive:goals",
            "matchdays",
            "associations",
            "club-link",
            "ranking-club",
            "cup-table:results",
            "cup-table:fixtures",
        }
    )
    for k in sorted(required - calls.keys()):
        missing(k)
    refs = {}
    for r in rows:
        n, sc = r["catalog"], r["scope"]
        if n == "archive-season":
            refs.setdefault("archive:" + sc, r)
        elif n == "ranking":
            refs.setdefault("ranking:" + sc, r)
        elif n == "matchdays":
            refs.setdefault("matchdays", r)
        elif n == "profile" and r["edition"]:
            refs.setdefault("archive-profile:" + sc, r)
            refs.setdefault("pitch-profile:" + sc, r)
        elif n in ("cup-standings", "cup-openligadb", "cup-nations-results"):
            refs.setdefault(n, r)
    for k, (p, test) in calls.items():
        result = baseline(p, predicate=test)
        if k in refs and result is not None:
            ref = refs[k]
            row = first(
                "select statarena_app.catalog_response(c) value from statarena_app.catalog_editions c where resource_id=%s and source_digest=%s",
                (ref["resource_id"], ref["source_digest"]),
            )
            if not row:
                check("catalog source revision stayed available " + k, False)
            else:
                expected = row["value"]
                if k.startswith("pitch-profile:"):
                    expected = {"data": expected["data"]}
                check(
                    "typed catalog representation " + k,
                    result == expected,
                    {
                        "sourceDigest": ref["source_digest"],
                        "sqlSha256": fingerprint(expected),
                        "httpSha256": fingerprint(result),
                    },
                )

        if k == "archive:results" and result:
            report["selections"]["archiveSeason"] = dict(
                parse_qsl(urlsplit(p).query)
            ).get("season")
        if k == "cup-index:worker" and result:
            item = next(
                (
                    i
                    for i in result["competitions"]
                    if i.get("folder")
                    and (i.get("tables") or {}).get("results", {}).get("rows")
                ),
                None,
            )
            if item:
                report["selections"]["cup"] = {
                    "id": "open-matchday:" + item["folder"],
                    "season": item.get("season"),
                    "name": item.get("name"),
                }


def run_core():
    v = first(
        "select generation::text as g from statarena_app.publications where singleton"
    )
    gen = v["g"]
    report["generationBefore"] = gen
    parts = query(
        "select season,league_id,source_digest from statarena_app.partitions order by season desc,league_id"
    )
    report["publishedPartitions"] = len(parts)
    health = baseline(
        route("health"),
        predicate=lambda v: v["source"] == "AWS" and v["status"] == "ok",
        validators=False,
    )
    baseline(
        route("status"),
        predicate=lambda v: v.get("configured") is True,
        validators=False,
    )
    baseline(
        route("settings"),
        predicate=lambda v: isinstance(v.get("sync"), list),
        validators=False,
    )
    man = baseline(
        route("dashboard/manifest"),
        predicate=lambda v: (
            v["storage"] == "aws-relational"
            and {
                (s["id"], c["leagueId"], c["sourceDigest"])
                for s in v["seasons"]
                for c in s["chunks"]
            }
            == {(r["season"], r["league_id"], r["source_digest"]) for r in parts}
        ),
    )
    # This is a verifier-only read of the migration staging manifest. Public handlers
    # read normalized tables exclusively. Do not equate any one partition with a full release.
    manifest_scopes = query("""select distinct s->>'id' season,c->>'leagueId' league_id
        from statarena.current_file_documents d cross join lateral jsonb_array_elements(d.document->'seasons') s
        cross join lateral jsonb_array_elements(s->'chunks') c
        where d.source_path='computed/dashboard/index.json' and d.document_path=d.source_path""")
    expected_scopes = {(r["season"], r["league_id"]) for r in manifest_scopes}
    actual_scopes = {(r["season"], r["league_id"]) for r in parts}
    coverage = {
        "published": len(actual_scopes),
        "expectedFromIndexedMigrationManifest": len(expected_scopes),
        "missing": sorted(expected_scopes - actual_scopes),
        "additional": sorted(actual_scopes - expected_scopes),
    }
    for owner, table in [
        ("stagingDirty", "statarena.dirty_partitions"),
        ("servingDirty", "statarena_app.publication_jobs"),
    ]:
        coverage[owner] = first("select count(*) n from " + table)["n"]
    report["coreCoverage"] = coverage
    if expected_scopes:
        check(
            "all migration-manifest partitions published",
            not coverage["missing"],
            {"missingCount": len(coverage["missing"])},
        )
    else:
        missing("full coverage baseline: indexed migration manifest absent")
    check(
        "dirty publication queues clear",
        coverage["stagingDirty"] == coverage["servingDirty"] == 0,
    )
    if not parts:
        missing("core:published partitions")
        return
    part = first("""select p.season,p.league_id,p.source_digest,c.name from statarena_app.partitions p
        join statarena_app.competitions c on c.id=p.league_id
        where exists(select 1 from statarena_app.matches m where m.season=p.season and m.league_id=p.league_id)
        order by (p.league_id='l_3FJFUl') desc, p.season desc,p.league_id limit 1""")
    if not part:
        missing("core:matches")
        return
    y, l = part["season"], part["league_id"]
    rows = query(
        "select id,day,home_score,away_score,home_id,away_id,home_name,away_name from statarena_app.matches where season=%s and league_id=%s order by day nulls last,id",
        (y, l),
    )
    fixtures = query(
        "select id,score_home,score_away from statarena_app.fixtures where season=%s and league_id=%s order by day nulls last,id",
        (y, l),
    )
    selected_matches = {r["id"]: r for r in rows}
    selected_fixtures = {r["id"]: r for r in fixtures}
    appearance_count = first(
        "select count(*) n from statarena_app.appearances where season=%s and league_id=%s",
        (y, l),
    )["n"]
    mid = next(
        (
            r
            for r in rows
            if r["home_score"] is not None and r["away_score"] is not None
        ),
        rows[0],
    )
    rich = first(
        """select m.id,m.home_name,m.away_name,m.home_score,m.away_score,m.home_id,m.away_id
       from statarena_app.matches m where m.season=%s and m.league_id=%s
       and exists(select 1 from statarena_app.match_families f where f.match_id=m.id and f.family='shots' and f.status=200)
       and exists(select 1 from statarena_app.match_families f where f.match_id=m.id and f.family='stats' and f.status=200)
       and exists(select 1 from statarena_app.shots s where s.match_id=m.id)
       and exists(select 1 from statarena_app.appearances a where a.match_id=m.id)
       order by m.day desc,m.id limit 1""",
        (y, l),
    )
    if rich:
        mid = rich
    else:
        missing("core:populated match linking summary to typed shot details")
    player = first(
        "select a.player_id,p.name,a.position_id,a.position_id_type,a.id from statarena_app.appearances a join statarena_app.players p on p.id=a.player_ref where match_id=%s order by (a.position_id is not null) desc,a.ordinal,a.id limit 1",
        (mid["id"],),
    )
    shot = first(
        "select id,match_id,goal_crossed_z,goal_crossed_y,blocked_x,blocked_y,xg from statarena_app.shots where match_id=%s order by (goal_crossed_z is not null) desc,ordinal limit 1",
        (mid["id"],),
    )
    report["selections"].update(
        upcoming=first(
            "select id,season,league_id,day,home_name,away_name from statarena_app.fixtures where day>=current_date and status='not_started' order by day,id limit 1"
        ),
        partition=part,
        match=mid,
        player=player,
        shot=shot,
        alternatePartition=next(
            (r for r in parts if r["season"] != y),
            next((r for r in parts if r["league_id"] != l), None),
        ),
    )
    expected_shots = first(
        "select count(*) n from statarena_app.shots s join statarena_app.matches m on m.id=s.match_id where m.season=%s and m.league_id=%s",
        (y, l),
    )["n"]
    for kind, expected in (
        ("seasons/partition", selected_matches),
        ("fixtures", selected_fixtures),
    ):
        page_ids = []
        fixture_ids = []
        seen_cursors = set()
        cursor = None
        apps = 0
        shots = 0
        page_no = 0
        found_player = False
        found_shot = False
        # The first traversal deliberately spans multiple pages on any nontrivial production partition.
        limit = min(25, max(1, len(expected) // 2))
        while True:
            q = {"season": y, "league": l, "limit": limit}
            if cursor:
                q["cursor"] = cursor
            path = route(kind, **q)
            m, test = http(api, path)
            if m.get("status") == 413 and limit > 1:
                limit = max(1, limit // 2)
                page_ids.clear()
                fixture_ids.clear()
                seen_cursors.clear()
                cursor = None
                apps = shots = page_no = 0
                found_player = found_shot = False
                continue
            if m.get("status") != 200 or not isinstance(test, dict):
                check("complete traversal " + path, False, {"http": m.get("status")})
                break
            check("page byte budget " + kind, m["decodedBytes"] <= 2 * 1024 * 1024)
            if page_no == 0:
                head, _ = http(api, path, "HEAD")
                tag = m["headers"].get("etag")
                check(
                    "first page HEAD " + kind,
                    tag
                    and head.get("status") == 200
                    and head.get("decodedBytes") == 0
                    and head["headers"].get("etag") == tag,
                )
                if tag:
                    cond, _ = http(api, path, headers={"If-None-Match": tag})
                    check(
                        "first page 304 " + kind,
                        cond.get("status") == 304 and cond["decodedBytes"] == 0,
                    )
            data = test["data"]
            matches = data["matches"]
            page_ids.extend(r["id"] for r in matches)
            for r in matches:
                sql = expected.get(r["id"], {})
                if kind == "fixtures":
                    if (r.get("score_home"), r.get("score_away")) != (
                        sql.get("score_home"),
                        sql.get("score_away"),
                    ):
                        check("fixture score " + r["id"], False)
                elif (r["home"].get("score"), r["away"].get("score")) != (
                    sql.get("home_score"),
                    sql.get("away_score"),
                ):
                    check("match score " + r["id"], False)
            if kind == "seasons/partition":
                apps += len(data["appearances"])
                fixture_ids.extend(f["id"] for f in data["fixtures"])
                for r in matches:
                    shots += len(r["shots"])
                    for s in r["shots"]:
                        if shot and (r["id"], s["id"]) == (
                            shot["match_id"],
                            shot["id"],
                        ):
                            found_shot = True
                            check(
                                "shot geometry and xG",
                                all(
                                    s.get(k) == shot[c]
                                    for k, c in (
                                        ("goalCrossedZ", "goal_crossed_z"),
                                        ("goalCrossedY", "goal_crossed_y"),
                                        ("blockedX", "blocked_x"),
                                        ("blockedY", "blocked_y"),
                                        ("xg", "xg"),
                                    )
                                ),
                            )
                if player:
                    for a in data["appearances"]:
                        if a["id"] == player["id"]:
                            found_player = True
                            value = player["position_id"]
                            typ = player["position_id_type"]
                            if value is not None:
                                value = (
                                    int(value)
                                    if typ == "int"
                                    else float(value)
                                    if typ == "float"
                                    else value == "True"
                                    if typ == "bool"
                                    else value
                                )
                            check(
                                "native position and identity",
                                a["name"] == player["name"]
                                and a["playerId"] == player["player_id"]
                                and type(a.get("positionId")) is type(value)
                                and a.get("positionId") == value,
                            )
            page_no += 1
            cursor = test["pagination"]["nextCursor"]
            if not cursor:
                break
            if (
                cursor in seen_cursors
                or page_no > len(selected_matches) + len(selected_fixtures) + 1
            ):
                check("advancing cursor " + kind, False)
                break
            seen_cursors.add(cursor)
        check(
            "complete unique IDs " + kind,
            len(page_ids) == len(expected) and set(page_ids) == set(expected),
            {
                "returned": len(page_ids),
                "expected": len(expected),
                "pages": page_no,
                "idsSha256": fingerprint(sorted(page_ids)),
            },
        )
        if len(expected) > 1:
            check("observed multi-page traversal " + kind, page_no >= 2)
        if kind == "seasons/partition":
            check(
                "partition fixture coverage",
                len(fixture_ids) == len(selected_fixtures)
                and set(fixture_ids) == set(selected_fixtures),
            )
            check(
                "appearance and shot counts",
                apps == appearance_count and shots == expected_shots,
                {
                    "appearances": apps,
                    "expectedAppearances": appearance_count,
                    "shots": shots,
                    "expectedShots": expected_shots,
                },
            )
            if player:
                check("appearance sample observed", found_player)
            if shot:
                check("shot sample observed", found_shot)
    baseline(
        route("matches/" + mid["id"] + "/summary"),
        predicate=lambda v: (
            v["data"]["match"]["id"] == mid["id"]
            and [v["data"]["match"][s]["score"] for s in ("home", "away")]
            == [mid["home_score"], mid["away_score"]]
            and len(v["data"]["match"].get("leadingPlayers", [])) <= 5
            and len(v["data"]["match"].get("stats", [])) <= 6
        ),
    )
    if player:
        baseline(
            route("scouting/routes", player=player["player_id"], team=mid["home_id"]),
            predicate=lambda v: (
                l in v["routes"][player["player_id"]][y]
                and l in v["clubRoutes"][mid["home_id"]][y]
            ),
        )
    else:
        missing("scouting/source player")
    baseline(
        route("pitchapi/leagues/" + l + "/matches", season=y, status="all"),
        predicate=lambda v: (
            set(x["id"] for x in v["data"]["matches"]) == set(selected_fixtures)
        ),
    )
    day = next((r["day"] for r in rows if r["day"]), None)
    if day:
        baseline(
            route("pitchapi/date/" + str(day), status="all"),
            predicate=lambda v: (
                bool(v["data"]["matches"])
                and all(x["date"] == str(day) for x in v["data"]["matches"])
            ),
        )
    if man and health:
        report["coreSampleCounts"] = {
            "matches": len(rows),
            "fixtures": len(fixtures),
            "appearances": appearance_count,
            "shots": expected_shots,
        }


def run_support():
    rows = query(
        "select distinct on (name) name,params,digest from statarena_app.support_projection order by name,params"
    )
    counts = query("""select s.name,s.staged,t.typed from
      (select name,count(*) staged from statarena.projections group by name) s
      left join (select name,count(*) typed from statarena_app.support_projection group by name) t using(name) order by s.name""")
    report["projectionCoverage"] = counts
    check(
        "all staged supporting keys represented",
        not first(
            """select 1 from statarena.projections s left join statarena_app.support_projection t using(name,params) where t.id is null limit 1"""
        ),
    )
    for k in (
        "standings",
        "club-wikidata",
        "coach-portrait",
        "nations-results",
        "open-cups",
        "openligadb",
        "player-honours",
        "stadium",
    ):
        r = next((i for i in rows if i["name"] == k), None)
        if not r:
            missing("support:" + k)
            continue
        sample = first(
            "select body from statarena.projections where name=%s and params=%s",
            (k, r["params"]),
        )
        if not sample:
            missing("staging parity:" + k)
        v = baseline(
            route(k, **json.loads(r["params"])), predicate=lambda v: isinstance(v, dict)
        )
        if v is not None and sample:
            original = sample["body"]
            check(
                "full source parity " + k,
                all(v.get(key) == value and key in v for key, value in original.items())
                and set(v) - set(original)
                <= ({"displayGroups"} if k == "player-honours" else set()),
                {
                    "params": r["params"],
                    "stagingSha256": fingerprint(original),
                    "publishedDigest": r["digest"],
                },
            )


def run_detail():
    family_paths = {
        "match": "",
        "advanced_teams": "advanced",
        "advanced_players": "advanced/players",
        "pass_networks": "advanced/network",
        "player_halves": "players/halves",
        "single_shot": "shots/$",
        "single_player": "players/$",
        "single_halves": "players/$/halves",
        "player_shots": "players/$/shots",
        "single_advanced": "advanced/players/$",
    }
    families = set(family_paths) | {
        "shots",
        "lineups",
        "players",
        "momentum",
        "events",
        "h2h",
        "stats",
        "heatmaps",
    }
    groups = query(
        "select distinct on (family) resource_id,match_id,family,subject_id,params,status,source_digest from statarena_app.match_families where status=200 order by family,resource_id"
    )
    for f in sorted(families):
        r = next((row for row in groups if row["family"] == f), None)
        if not r:
            missing("match family:" + f)
            continue
        suffix = family_paths.get(f, f).replace("$", r["subject_id"])
        endpoint = route(
            "pitchapi/matches/" + r["match_id"] + ("/" + suffix if suffix else ""),
            **json.loads(r["params"]),
        )
        # Compare a complete typed SQL response, including explicit nulls and ordered collections.
        reference = first(
            "select statarena_app.detail_response(f) as v from statarena_app.match_families f where resource_id=%s",
            (r["resource_id"],),
        )["v"]
        baseline(endpoint, predicate=lambda v: v == {"data": reference["data"]})
    arch = first(
        "select match_id,fixture_home_team_name,fixture_away_team_name from statarena_app.match_details where has_context order by match_id limit 1"
    )
    if arch:
        baseline(
            route("archive/matches/" + arch["match_id"]),
            predicate=lambda v: (
                v["fixture"]["id"] == arch["match_id"] and len(v["endpoints"]) > 0
            ),
        )
    else:
        missing("match archive")


try:
    api, signed = targets()
    with connection() as db:
        report["sqlTransport"] = first(
            "select current_database() db,current_setting('transaction_read_only') read_only,(select ssl from pg_stat_ssl where pid=pg_backend_pid()) tls"
        )
        check(
            "RDS verify-full TLS and enforced read-only session",
            report["sqlTransport"]["read_only"] == "on"
            and report["sqlTransport"]["tls"] is True,
        )
        names = [
            "publications",
            "partitions",
            "matches",
            "appearances",
            "fixtures",
            "support_projection",
            "catalog_editions",
            "match_families",
            "assets",
        ]
        report["relations"] = {
            s: bool(
                first(
                    "select to_regclass(%s) is not null as ready",
                    ("statarena_app." + s,),
                )["ready"]
            )
            for s in names
        }
        exists = {}
        for s, ok in report["relations"].items():
            exists[s] = (
                bool(
                    first("select exists(select 1 from statarena_app." + s + ") v")["v"]
                )
                if ok
                else False
            )
        report["publishedRowsAvailable"] = exists
        for s, present in exists.items():
            if not present:
                missing("typed rows:" + s)
        if not api or not signed:
            missing("deployed API origin")
        if not args.run:
            report["state"] = "preflight"
        elif not api or not signed:
            report["state"] = "waiting"
        else:
            report["selections"] = {}
            direct, _ = http(signed, "/api/health")
            check("unsigned private origin 403", direct.get("status") == 403)
            for path, status in [
                (route("matches/m_ZZZZZZ/summary"), 404),
                (route("seasons/partition", season="bad", league="l_000001"), 400),
                ("/data/dashboard-manifest.json", 410),
            ]:
                if status == 404 and not exists["partitions"]:
                    missing("missing-match distinction before partition publication")
                    continue
                baseline(path, status, validators=False)
            invalid, _ = http(api, "/api/does-not-exist", "POST")
            check("viewer refuses write method", invalid.get("status") in (403, 405))
            opt, _ = http(
                api,
                "/api/health",
                "OPTIONS",
                headers={
                    "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": "If-None-Match",
                },
            )
            check(
                "CORS preflight",
                opt.get("status") == 204
                and "GET"
                in opt.get("headers", {}).get("access-control-allow-methods", ""),
            )
            if exists["partitions"]:
                run_family("core", run_core)
            else:
                baseline(
                    route("health"),
                    503,
                    predicate=lambda v: (
                        v.get("source") == "AWS" and v.get("status") == "pending"
                    ),
                    validators=False,
                )
                baseline(
                    route("status"),
                    predicate=lambda v: v.get("configured") is True,
                    validators=False,
                )
                baseline(
                    route("settings"),
                    predicate=lambda v: isinstance(v.get("sync"), list),
                    validators=False,
                )
            if exists["support_projection"]:
                run_family("support", run_support)
            if exists["catalog_editions"]:
                run_family("catalog", sample_catalog)
            if exists["match_families"]:
                run_family("match families", run_detail)
            if exists["assets"]:
                a = first(
                    "select url,path from statarena_app.assets where path ~ '\\.(webp|png|jpe?g)$' order by url limit 1"
                )
                if a:
                    m, _ = http(api, route("assets", url=a["url"]))
                    check(
                        "immutable binary redirect",
                        m.get("status") == 307
                        and m["headers"].get("location", "")
                        == "https://d2clu0phovomb8.cloudfront.net/data/" + a["path"],
                    )
                else:
                    missing("binary asset redirect")
            stable = next(
                (
                    r
                    for r in report["requests"]
                    if "/api/standings?" in r["route"]
                    and r.get("status") == 200
                    and r["method"] == "GET"
                ),
                None,
            )
            if stable:
                warm, _ = http(api, stable["route"])
                check(
                    "warm edge hit after successful read",
                    warm.get("status") == 200
                    and "hit" in warm.get("headers", {}).get("x-cache", "").lower()
                    and warm.get("sha256") == stable["sha256"],
                    {
                        "initialCache": stable["headers"].get("x-cache"),
                        "repeatCache": warm.get("headers", {}).get("x-cache"),
                    },
                )
            else:
                missing("cache hit")
            if exists["publications"] and "generationBefore" in report:
                report["generationAfter"] = first(
                    "select generation::text g from statarena_app.publications where singleton"
                )["g"]
                check(
                    "stable release during parity observations",
                    report["generationBefore"] == report["generationAfter"],
                )
            report["state"] = (
                "failed"
                if report["failures"]
                else "partial"
                if report["missing"]
                else "passed"
            )
except Exception as e:
    # Never print DSN, private material, entire AWS responses or connection error text.
    report["state"] = "failed"
    report["exception"] = {
        "type": type(e).__name__,
        "sqlstate": getattr(e, "sqlstate", None),
    }
    import traceback

    report["exception"]["location"] = [
        f"{Path(t.filename).name}:{t.lineno}:{t.name}"
        for t in traceback.extract_tb(e.__traceback__)
    ]
finally:
    report["finished"] = dt.datetime.now(dt.timezone.utc).isoformat()
    save()
print(
    json.dumps(
        {
            "report": str(out),
            "state": report["state"],
            "requests": len(report["requests"]),
            "checks": len(report["checks"]),
            "failures": len(report["failures"]),
            "missing": report["missing"],
        },
        ensure_ascii=False,
    )
)
sys.exit(0 if report["state"] in ("passed", "preflight") else 1)
