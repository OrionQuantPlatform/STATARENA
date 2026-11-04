"""Run paired local HTTP readers against verified Ohio RDS and retained Ohio S3."""

import hashlib
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import quote, urlencode

from choose_fixture import cfg, choose, stamp

folder = Path(__file__).resolve().parent
root = folder.parents[2]
LIMIT = 64 * 1024 * 1024


def s3_runtime():
    return json.loads(
        subprocess.check_output(
            [
                "aws",
                "--profile",
                "statarena",
                "--region",
                "us-east-2",
                "ssm",
                "get-parameter",
                "--with-decryption",
                "--name",
                "/statarena/app/s3-runtime",
                "--query",
                "Parameter.Value",
                "--output",
                "text",
            ]
        )
    )


def first_differences(a, b, p="$", out=None):
    if out is None:
        out = []
    if len(out) >= 8:
        return out
    if type(a) != type(b):
        out.append(
            {
                "path": p,
                "legacyType": type(a).__name__,
                "relationalType": type(b).__name__,
            }
        )
    elif isinstance(a, dict):
        for k in sorted(a.keys() | b.keys()):
            if len(out) >= 8:
                break
            if k not in a or k not in b:
                out.append(
                    {
                        "path": p + "." + k,
                        "onlyIn": "legacy" if k in a else "relational",
                    }
                )
            else:
                first_differences(a[k], b[k], p + "." + k, out)
    elif isinstance(a, list):
        if len(a) != len(b):
            out.append({"path": p, "legacyLength": len(a), "relationalLength": len(b)})
        for i, (u, v) in enumerate(zip(a, b)):
            if len(out) >= 8:
                break
            first_differences(u, v, f"{p}[{i}]", out)
    elif a != b:
        out.append({"path": p, "legacy": str(a)[:120], "relational": str(b)[:120]})
    return out


def current_versions(selection):
    import psycopg
    from choose_fixture import opts

    with psycopg.connect(**opts) as db:
        results = {
            "match": db.execute(
                "select version from statarena_app.match_detail_versions where match_id=%s",
                (selection["match"],),
            ).fetchone()
        }
        if selection.get("profile"):
            results["profile"] = db.execute(
                "select source_digest from statarena_app.catalog_editions where catalog='profile' and scope='players' and edition=%s",
                (selection["profile"],),
            ).fetchone()
        # Verify every source digest and the saved-reference index before and after trials.
        paths = [v[0] for v in selection["objectDigests"]]
        results["objects"] = db.execute(
            "select path,encode(sha256,'hex') from statarena.objects where path=any(%s) order by path",
            (paths,),
        ).fetchall()
        m = "/matches/" + selection["match"]
        refs = db.execute(
            "select endpoint,params,status,ref,error from statarena.resources where (endpoint>=%s and endpoint<%s) or endpoint=%s order by endpoint,params",
            (m, m + "~", "/players/" + selection.get("profile", "")),
        ).fetchall()
        results["refs"] = hashlib.sha256(
            json.dumps(refs, sort_keys=True).encode()
        ).hexdigest()
        archive = db.execute(
            "SELECT o.ordinal,s.ref FROM statarena.observations o JOIN statarena.shards s ON s.id=o.shard WHERE o.id=%s",
            (selection["match"],),
        ).fetchone()
        results["archiveIndex"] = hashlib.sha256(
            json.dumps(archive, sort_keys=True).encode()
        ).hexdigest()
        if selection.get("profile"):
            results["profileObject"] = db.execute(
                "SELECT encode(o.sha256,'hex') FROM statarena.resources r JOIN statarena.objects o ON o.path=r.ref->>'path' WHERE r.endpoint=%s AND r.params='{}'",
                ("/players/" + selection["profile"],),
            ).fetchone()
        return results


@contextmanager
def suspend_local_audit():
    # Pause only our own companion read-only census processes while origin
    # timings run. Check executable and exact script arguments at the OS.
    paused = []
    tasks = subprocess.check_output(["ps", "-Ao", "pid=,command="], text=True)
    try:
        for line in tasks.splitlines():
            parts = line.split()
            if len(parts) not in (3, 4):
                continue
            pid, exe, script, *args = parts
            if Path(exe).name not in ("Python", "python", "python3"):
                continue
            if script not in (
                "docs/verification/aws-match-schema-007-20261104/array_inventory.py",
                "docs/verification/aws-match-schema-007-20261104/saved_inventory.py",
            ):
                continue
            if args not in ([], ["--all"]):
                continue
            try:
                os.kill(int(pid), signal.SIGSTOP)
            except ProcessLookupError:
                continue
            paused.append(int(pid))
        if paused:
            time.sleep(3)
        yield len(paused)
    finally:
        for pid in paused:
            try:
                os.kill(pid, signal.SIGCONT)
            except ProcessLookupError:
                pass


def main():
    selection = choose()
    (folder / "selection.json").write_text(json.dumps(selection, indent=2) + "\n")
    if not selection["routes"]:
        print(
            "NO_ELIGIBLE_SELECTION",
            selection["partitions"],
            selection.get("reason", ""),
        )
        return 3
    secret = s3_runtime()
    dburl = (
        "postgresql://"
        + quote(cfg["username"], safe="")
        + ":"
        + quote(cfg["password"], safe="")
        + "@"
        + cfg["host"]
        + "/statarena_prod?"
        + urlencode(
            {
                "options": "-c default_transaction_read_only=on -c statement_timeout=8000 -c lock_timeout=1000"
            }
        )
    )
    region = "us-east-2"
    ca = Path(os.environ["STATARENA_PROBE_CA"]).read_text()
    env = {
        "PATH": os.environ["PATH"],
        "HOME": os.environ["HOME"],
        "STATARENA_DATA_PROVIDER": "AWS",
        "STATARENA_EXTERNAL_STORAGE": "1",
        "DATABASE_URL": dburl,
        "DATABASE_CA_PEM": ca,
        "STATARENA_DATABASE_CA_PEM": ca,
        "NEON_DATABASE_URL": dburl,
        "NEON_STORAGE_ENDPOINT": "https://s3." + region + ".amazonaws.com",
        "NEON_STORAGE_REGION": region,
        "STATARENA_S3_PATH_STYLE": "0",
        "NEON_STORAGE_BUCKET": "statarena-football-333rosky-70db6e5f",
        "NEON_STORAGE_ACCESS_KEY_ID": secret["access_key_id"],
        "NEON_STORAGE_SECRET_ACCESS_KEY": secret["secret_access_key"],
        "STATARENA_METRICS_SAMPLE_RATE": "1",
        "STATARENA_SERVER_TIMING": "1",
    }
    sha = subprocess.check_output(
        [
            "git",
            "-C",
            root,
            "rev-parse",
            os.environ.get("STATARENA_BENCHMARK_REF", "HEAD"),
        ],
        text=True,
    ).strip()
    results = {
        "started": stamp(),
        "source": sha,
        "bun": subprocess.check_output(["bun", "--version"], text=True).strip(),
        "selection": selection,
        "routes": [],
    }
    path = folder / "measurements.json"

    def persist():
        path.write_text(json.dumps(results, indent=2) + "\n")

    with (
        suspend_local_audit() as paused,
        tempfile.TemporaryDirectory(prefix="statarena-live-readers-") as tmp,
    ):
        results["pausedLocalCensusProcesses"] = paused
        scratch = Path(tmp)
        archive = scratch / "source.tar"
        subprocess.run(
            [
                "git",
                "-C",
                root,
                "archive",
                sha,
                "dashboard/backend",
                "dashboard/package.json",
                "--output=" + str(archive),
            ],
            check=True,
        )
        subprocess.run(["tar", "-xf", archive, "-C", scratch], check=True)
        (scratch / "dashboard/node_modules").symlink_to(
            root / "dashboard/node_modules", target_is_directory=True
        )
        before = current_versions(selection)
        for route in selection["routes"]:
            entry = {"route": route, "trials": [], "paired": False}
            results["routes"].append(entry)
            used = 0
            bound = (
                selection["sourceBytesBound"]
                if "/players/" not in route
                else 2 * 1024 * 1024
            )
            for trial in range(-1, 5):
                tags = {}
                files = {}
                readers = (
                    ["legacy-app", "aws-app"]
                    if trial % 2
                    else ["aws-app", "legacy-app"]
                )
                for reader in readers:
                    if reader == "legacy-app" and used + bound > LIMIT:
                        entry["stop"] = "source read budget"
                        break
                    dump = scratch / (reader + "-body.json") if trial == -1 else None
                    if dump:
                        files[reader] = dump
                    try:
                        run = subprocess.run(
                            [
                                "bun",
                                folder / "reader.mjs",
                                scratch,
                                reader,
                                route,
                                str(10 if trial == 0 else 0),
                                dump or "-",
                                str(LIMIT - used),
                                str(bound),
                            ],
                            env=env,
                            capture_output=True,
                            text=True,
                            timeout=240,
                            check=False,
                        )
                    except subprocess.TimeoutExpired:
                        entry["stop"] = "reader timeout"
                        entry["failedReader"] = reader
                        break
                    if run.returncode:
                        entry["stop"] = "reader subprocess failed"
                        entry["failedReader"] = reader
                        entry["failureClass"] = next(
                            (
                                tag
                                for tag in [
                                    "Database startup guard failed",
                                    "TimeoutError",
                                    "Cannot find module",
                                    "Invalid comparison target",
                                ]
                                if tag in run.stderr
                            ),
                            "subprocess error",
                        )
                        entry["exitCode"] = run.returncode
                        break
                    payload = json.loads(run.stdout)
                    if not payload["requests"]:
                        entry["stop"] = "source budget reached"
                        break
                    if not payload.get("verifiedConnections"):
                        entry["stop"] = "read-only runtime connection not observed"
                    tags[reader] = payload["requests"][0]["canonicalSha256"]
                    for req in payload["requests"]:
                        entry["trials"].append(
                            {
                                "trial": trial,
                                "stage": "screen"
                                if trial == -1
                                else ("cold" if req["n"] == 0 else "warm"),
                                "reader": reader,
                                **req,
                            }
                        )
                        if reader == "legacy-app":
                            used += req["metrics"].get("object_bytes", 0)
                        if req["status"] != 200:
                            entry["stop"] = "non-success HTTP response"
                        if req["canonicalSha256"] != tags[reader]:
                            entry["stop"] = "body changed within trial"
                    if entry.get("stop") and trial != -1:
                        break
                persist()
                if len(tags) == 2 and len(set(tags.values())) != 1:
                    entry["stop"] = "HTTP content differs"
                    if trial == -1 and all(p.exists() for p in files.values()):
                        entry["differences"] = first_differences(
                            *[
                                json.loads(files[k].read_text())
                                for k in ["legacy-app", "aws-app"]
                            ]
                        )
                if entry.get("stop"):
                    break
                if trial == -1:
                    entry["screenDigest"] = next(iter(tags.values()))
                elif any(x != entry["screenDigest"] for x in tags.values()):
                    entry["stop"] = "body changed versus screening"
                    break
                if trial == 4:
                    entry["paired"] = True
            entry["legacySourceBytesRead"] = used
            persist()
        after = current_versions(selection)
        results.update(
            {
                "finished": stamp(),
                "sourcesStable": before == after,
                "beforeVersions": before,
                "afterVersions": after,
            }
        )
    persist()
    print(
        [(x["route"], x["paired"], x.get("stop")) for x in results["routes"]],
        "stable",
        results["sourcesStable"],
    )


if __name__ == "__main__":
    sys.exit(main())
