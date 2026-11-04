"""Read-only cloud metadata and bounded public probes; never persist credentials."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import subprocess
import urllib.error
import urllib.request
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
PROJECT = "prj_DhaqrVkH3Gi4uysT7IRsm9fB2bjR"
TEAM = "team_IYt7KqupdSTtMuQuMvNa9wiJ"
OLD_ID = "dpl_5WKUEwBpNkr3hUEk9Fk8qF8EVFBe"
OLD_HOST = "statarena-analytics-jumo9il0b-hlemonniers-projects.vercel.app"
PUBLIC_HOST = "statarena-analytics.vercel.app"
AWS_HOST = "d317dq37z1tacb.cloudfront.net"
DENSE = "/api/seasons/partition?season=2026%2F2027&league=l_0ALvwF&limit=100&format=columns"


def cli_json(args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=40)
    if result.returncode:
        # Do not print raw CLI responses, which may contain credentials.
        return None, {"kind": "command_failed", "exitCode": result.returncode}
    try:
        return json.loads(result.stdout), None
    except json.JSONDecodeError:
        return None, {"kind": "invalid_json"}


def vercel(path):
    return cli_json(["npx", "--yes", "vercel@65.11.0", "api", path])


def deployment(d):
    if not d:
        return None
    meta = d.get("meta") or {}
    return {
        "id": d.get("id") or d.get("uid"),
        "url": d.get("url"),
        "readyState": d.get("readyState"),
        "target": d.get("target"),
        "createdAt": d.get("createdAt"),
        "commit": meta.get("githubCommitSha"),
        "branch": meta.get("githubCommitRef"),
        "source": d.get("source"),
    }


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def probe(host, path):
    url = "https://" + host + path
    request = urllib.request.Request(url, headers={"User-Agent": "StatArena-availability-audit/1.0", "Accept-Encoding": "identity"})
    item = {"url": url, "method": "GET"}
    start = dt.datetime.now(dt.timezone.utc)
    try:
        response = urllib.request.build_opener(NoRedirect).open(request, timeout=30)
    except urllib.error.HTTPError as error:
        response = error
    except Exception as error:
        item["error"] = type(error).__name__
        return item
    with response:
        body = response.read()
        item.update({"status": response.status, "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(),
                     "elapsedMs": round((dt.datetime.now(dt.timezone.utc) - start).total_seconds() * 1000, 2),
                     "headers": {k: v for k, v in response.headers.items() if k.lower() in
                                 {"age", "cache-control", "content-type", "etag", "location", "x-cache", "x-data-source", "x-vercel-cache", "x-vercel-error"}}})
        try:
            value = json.loads(body)
        except (ValueError, UnicodeDecodeError):
            return item
        if path == "/api/health":
            item["health"] = {k: value.get(k) for k in ("status", "source", "revision")}
        elif response.status == 200 and path == "/api/dashboard/manifest" and isinstance(value, dict) and isinstance(value.get("seasons"), list):
            seasons = value.get("seasons") or []
            chunks = [c for s in seasons if isinstance(s, dict) for c in (s.get("chunks") or [])]
            item["manifest"] = {"schemaVersion": value.get("schemaVersion"), "storage": value.get("storage"),
                                "seasonCount": len(seasons), "chunkCount": len(chunks),
                                "competitionCount": len(value.get("competitions") or [])}
        elif path.startswith("/api/seasons/partition") and isinstance(value, dict):
            item["pagination"] = {k: (value.get("pagination") or {}).get(k) for k in ("limit", "generation")}
            item["errorCode"] = (value.get("error") or {}).get("code") if isinstance(value.get("error"), dict) else None
    return item


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dense-aws", action="store_true", help="one additional dense 100-match AWS HTTP GET")
    args = parser.parse_args()
    now = dt.datetime.now(dt.timezone.utc)
    stamp = now.strftime("%Y%m%dT%H%M%S%fZ")
    command = "python3 docs/verification/orion-availability-20261104/capture_readback.py" + (" --dense-aws" if args.dense_aws else "")
    report = {"atUtc": now.isoformat(), "atParis": now.astimezone(ZoneInfo("Europe/Paris")).isoformat(), "command": command,
              "setup": "Existing authenticated Vercel CLI and AWS profile; read-only control-plane GETs and bounded public HTTP GETs. No football-provider calls or cloud/DB mutations. Environment variable values are never saved.",
              "expected": "Identify the canonical alias and deployments, report environment names/targets and actual route status; health alone does not prove data coverage.", "errors": {}}
    project, err = vercel("/v9/projects/" + PROJECT + "?teamId=" + TEAM)
    if err:
        report["errors"]["project"] = err
    else:
        report["project"] = {"name": project.get("name"), "rootDirectory": project.get("rootDirectory"),
                             "production": deployment((project.get("targets") or {}).get("production"))}
    env, err = vercel("/v10/projects/" + PROJECT + "/env?teamId=" + TEAM)
    if err:
        report["errors"]["environment"] = err
    else:
        report["environment"] = [{"name": e.get("key"), "targets": e.get("target"), "branch": e.get("gitBranch")} for e in env.get("envs", [])]
    alias, err = vercel("/v4/aliases/" + PUBLIC_HOST + "?teamId=" + TEAM)
    if err:
        report["errors"]["alias"] = err
    else:
        report["alias"] = {"alias": alias.get("alias"), "deploymentId": alias.get("deploymentId")}
    ids = [OLD_ID]
    if project:
        current = ((project.get("targets") or {}).get("production") or {}).get("id")
        if current and current not in ids:
            ids.append(current)
    report["deployments"] = []
    for dep_id in ids:
        dep, err = vercel("/v13/deployments/" + dep_id + "?teamId=" + TEAM)
        if err:
            report["errors"]["deployment_" + dep_id] = err
        else:
            report["deployments"].append(deployment(dep))
    config, err = cli_json(["aws", "--profile", "statarena", "--region", "us-east-2", "lambda", "get-function-configuration", "--function-name", "statarena-backend", "--query", "{CodeSha256:CodeSha256,MemorySize:MemorySize,State:State,LastUpdateStatus:LastUpdateStatus}", "--output", "json"])
    if err:
        report["errors"]["lambda"] = err
    else:
        report["lambda"] = config
    routes = [
        (PUBLIC_HOST, "/"), (PUBLIC_HOST, "/api/health"), (PUBLIC_HOST, "/api/dashboard/manifest"),
        (OLD_HOST, "/"), (OLD_HOST, "/api/health"), (OLD_HOST, "/api/dashboard/manifest"),
        (AWS_HOST, "/api/health"), (AWS_HOST, "/api/dashboard/manifest"),
        (AWS_HOST, "/api/seasons/partition?season=2026%2F2027&league=l_0ALvwF&limit=1&format=columns"),
    ]
    if args.dense_aws:
        routes.append((AWS_HOST, DENSE))
    report["probes"] = [probe(host, path) for host, path in routes]
    report["limits"] = ["One HTTP observation per route; timings are observations, not latency percentiles.",
                        "Direct deployment access may be protected and differs from canonical alias access.",
                        "Manifest counts are not row-level completeness or semantic parity evidence."]
    out = HERE / ("readback-" + stamp + ".json")
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"artifact": str(out.relative_to(HERE.parent.parent.parent)), "errors": report["errors"],
                      "production": report.get("project", {}).get("production"), "alias": report.get("alias"),
                      "statuses": [{"url": p["url"], "status": p.get("status"), "error": p.get("error")} for p in report["probes"]]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
