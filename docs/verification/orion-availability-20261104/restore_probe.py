"""Read the old deployment's own manifest and two saved data chunks."""
import datetime as dt
import gzip
import hashlib
import json
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request

HERE = Path(__file__).resolve().parent
HOST = "https://statarena-analytics-jumo9il0b-hlemonniers-projects.vercel.app"
report = {"atUtc": dt.datetime.now(dt.timezone.utc).isoformat(),
          "command": "python3 docs/verification/orion-availability-20261104/restore_probe.py",
          "setup": "Old immutable Vercel deployment 0aaf316; GETs of its own Neon-backed saved data only. No football-provider calls, mutations, or production alias changes.",
          "expected": "Historical deployment serves its own manifest, selected current and historical packed chunks, and stored league compatibility endpoint.",
          "requests": [], "samples": [], "status": "failed"}


def fetch(path):
    assert path.startswith("/") and ".." not in path
    req = urllib.request.Request(HOST + path, headers={"Accept-Encoding": "identity", "User-Agent": "StatArena-restore-readback/1.0"})
    try:
        response = urllib.request.urlopen(req, timeout=30)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        body = response.read()
        report["requests"].append({"path": path, "status": response.status, "bytes": len(body),
                                   "sha256": hashlib.sha256(body).hexdigest(),
                                   "contentType": response.headers.get("Content-Type"),
                                   "source": response.headers.get("X-Data-Source")})
        if response.status != 200:
            raise RuntimeError(path + " returned HTTP " + str(response.status))
        return body


try:
    health = json.loads(fetch("/api/health"))
    if health.get("source") != "Neon":
        raise RuntimeError("Old deployment is not Neon backed")
    manifest = json.loads(fetch("/data/dashboard-manifest.json"))
    seasons = manifest.get("seasons") or []
    chunks = [c for s in seasons for c in (s.get("chunks") or [])]
    report["manifest"] = {"storage": manifest.get("storage"), "seasons": [s.get("id") for s in seasons],
                          "seasonCount": len(seasons), "chunkCount": len(chunks),
                          "topLevelCompetitionCount": len(manifest["competitions"]) if isinstance(manifest.get("competitions"), list) else None,
                          "chunkCompetitionReferences": sum(len(c.get("competitions") or []) for c in chunks)}
    for season_id in ("2026/2027", "2025/2026"):
        season = next((s for s in seasons if s.get("id") == season_id), None)
        if not season:
            raise RuntimeError("Missing season " + season_id)
        chunk = next((c for c in season.get("chunks", []) if c.get("leagueId") == "l_3FJFUl"), None)
        if not chunk:
            raise RuntimeError("Missing Ligue 1 chunk for " + season_id)
        path = chunk.get("path") or ""
        if not path.startswith("computed/dashboard/") or ".." in path:
            raise RuntimeError("Unexpected chunk path")
        body = fetch("/data/" + urllib.parse.quote(path, safe="/"))
        packed = json.loads(gzip.decompress(body))
        tables = packed.get("tables") or {}
        counts = {name: len((table or {}).get("rows") or []) for name, table in tables.items()}
        if not counts.get("matches") or not counts.get("performances"):
            raise RuntimeError("Selected chunk lacks expected matches or performances")
        report["samples"].append({"season": season_id, "leagueId": "l_3FJFUl", "path": path, "tableCounts": counts})
    leagues = json.loads(fetch("/api/pitchapi/leagues"))
    report["leaguesCount"] = len((leagues.get("data") or {}).get("leagues") or [])
    if not report["leaguesCount"]:
        raise RuntimeError("Stored league list is empty")
    report["status"] = "passed"
except Exception as error:
    report["error"] = type(error).__name__ + ": " + str(error)
finally:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out = HERE / ("restore-probe-" + stamp + ".json")
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"artifact": str(out), "status": report["status"], "error": report.get("error"),
                      "manifest": report.get("manifest"), "samples": report["samples"]}, ensure_ascii=False))
raise SystemExit(report["status"] != "passed")
