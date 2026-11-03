"""Bounded overview read models built from an already loaded partition."""
import gzip
import hashlib
from neon_store import canonical

OVERVIEW_STATS = {"expected_goals", "total_shots", "ShotsOnTarget", "BallPossesion", "big_chance", "corners"}
SHOT_FIELDS = {"id", "teamId", "playerId", "playerName", "minute", "minuteAdded", "period", "xg", "isGoal", "isOwnGoal"}
LEADER_FIELDS = {"id", "playerId", "matchId", "teamId", "team", "name", "imageUrl", "minutes", "rating", "goals", "assists"}
SQL_BUDGET_BYTES = 900_000_000


def put_content_json(store, prefix, value, hot=False):
    """The public filename hashes final gzip bytes, not semantic source rows."""
    body = gzip.compress(canonical(value).encode(), mtime=0)
    digest = hashlib.sha256(body).hexdigest()
    path = prefix + digest + ".json.gz"
    store.put(path, body, "application/gzip", hot=hot)
    return {"path": path, "sha256": digest}


def fixture_match(fixture):
    def team(side):
        value = dict(fixture.get(side + "_team") or {})
        return dict(value, imageUrl=value.get("image_url"), score=fixture.get("score_" + side))
    return {"id": fixture["id"], "leagueId": (fixture.get("league") or {}).get("id"), "league": (fixture.get("league") or {}).get("name"), "season": fixture.get("season"), "date": fixture.get("date"), "timeUtc": fixture.get("time_utc"), "status": fixture.get("status"), "home": team("home"), "away": team("away"), "coverage": {}, "shots": [], "stats": [], "warnings": []}


def publish_summaries(store, tables, source_digest, marked):
    """SQL commit/rollback is owned by materialize(); no extra archive reads."""
    fixtures = tables["fixtures"]
    ids = [f["id"] for f in fixtures]
    if not ids:
        return 0
    matches = {m["id"]: m for m in tables["matches"]}
    stats = {s["matchId"]: s.get("values", []) for s in tables["team_statistics"]}
    shots, appearances = {}, {}
    for shot in tables["shots"]:
        shots.setdefault(shot["matchId"], []).append({k:v for k,v in shot.items() if k in SHOT_FIELDS})
    identities = {p["id"]: p for p in tables["players"]}
    for p in tables["performances"]:
        identity = identities.get(p.get("playerRef"), {})
        row = dict(p, name=identity.get("name"), imageUrl=identity.get("imageUrl"))
        appearances.setdefault(p["matchId"], []).append({k:v for k,v in row.items() if k in LEADER_FIELDS})
    rows = []
    for fixture in fixtures:
        mid = fixture["id"]
        match = dict(matches.get(mid) or fixture_match(fixture))
        match["summaryVersion"] = 1
        match["shots"] = shots.get(mid, [])
        match["stats"] = [s for s in stats.get(mid, []) if s.get("key") in OVERVIEW_STATS]
        match["leadingPlayers"] = sorted((p for p in appearances.get(mid, []) if (p.get("minutes") or 0)>0 and isinstance(p.get("rating"), (int,float))), key=lambda p: (-p["rating"], p.get("id", "")))[:5]
        # Do not expose lists of all player IDs or heavy normalized extensions.
        match.pop("players", None)
        payload = {"data": {"version": 1, "state": "ready", "match": match}}
        body = canonical(payload).encode()
        if len(body)>262144:
            raise ValueError("Match summary exceeds 256 KiB: " + mid)
        rows.append((mid, body, hashlib.sha256(body).digest(), len(body), source_digest))
    previous = {mid:(bytes(digest),source) for mid,digest,source in store.db.execute("select match_id,sha256,source_digest from statarena.match_summaries where match_id=any(%s)", (ids,)).fetchall()}
    updates = [r for r in rows if previous.get(r[0]) != (r[2],r[4])]
    if updates:
        database_bytes = store.db.execute("select pg_database_size(current_database())").fetchone()[0]
        # Reserve payload copies and row/index overhead conservatively, including
        # update/MVCC space. This is an admission budget, not a heap-size measure.
        growth = sum(2*r[3]+1024 for r in updates)
        if database_bytes+growth>SQL_BUDGET_BYTES:
            raise RuntimeError("SQL capacity budget would be exceeded by match summaries")
    with store.db.cursor() as cursor:
        cursor.executemany("insert into statarena.match_summaries(match_id,body,sha256,size,source_digest) values(%s,%s,%s,%s,%s) on conflict(match_id) do update set body=excluded.body,sha256=excluded.sha256,size=excluded.size,source_digest=excluded.source_digest,updated_at=now() where statarena.match_summaries.sha256 is distinct from excluded.sha256 or statarena.match_summaries.source_digest is distinct from excluded.source_digest", updates)
        cursor.executemany("delete from statarena.dirty_match_summaries where match_id=%s and changed_at=%s", list(marked.items()))
    return len(rows)
