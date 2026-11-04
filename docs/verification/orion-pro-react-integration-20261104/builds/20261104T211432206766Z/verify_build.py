"""Compile the candidate UI from inspectable source in an owned local directory."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
run = HERE / "builds" / dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
run.mkdir(parents=True)
report = {
    "command": "python3 docs/verification/orion-pro-react-integration-20261104/verify_build.py",
    "setup": "Owned temporary application copy; exact tracked working source plus three new Pro modules; existing dependencies and pinned local flag-icons7.6.0 cache; VERCEL=1; no credentials or deployment.",
    "expected": "Production Next build exits0; inputs unchanged; owned directory removed.",
    "status": "fail",
    "startedAtUtc": dt.datetime.now(dt.timezone.utc).isoformat(),
}
try:
    tracked = subprocess.check_output([
        "git", "ls-files", "-z", "dashboard/frontend", "dashboard/shared", "dashboard/backend",
    ], cwd=ROOT).decode().split("\0")
    candidates = set(p for p in tracked if p)
    candidates.update([
        "dashboard/frontend/src/hooks/useProResource.js",
        "dashboard/frontend/src/services/pro-football-client.js",
        "dashboard/frontend/src/views/ProMatchesPage.jsx",
        "dashboard/package.json", "dashboard/bun.lock",
    ])
    sources = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in sorted(candidates) if (ROOT / p).is_file()}
    report["sourceSha256"] = sources
    (run / "source-inputs.json").write_text(json.dumps(sources, indent=2) + "\n")
    flag = next(p for p in (Path.home() / ".bun/install/cache").glob("flag-icons@7.6.0*") if (p / "package.json").is_file())
    assert json.loads((flag / "package.json").read_text())["version"] == "7.6.0"
    report["flagPackageVersion"] = "7.6.0"
    report["flagPackageMetadataSha256"] = hashlib.sha256((flag / "package.json").read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory(prefix="orion-pro-build-") as private:
        owned = Path(private)
        report["ownedDirectory"] = str(owned)
        for relative in sources:
            destination = owned / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, destination)
            assert hashlib.sha256(destination.read_bytes()).hexdigest() == sources[relative]
        dashboard = owned / "dashboard"
        os.symlink(ROOT / "dashboard/node_modules", dashboard / "node_modules")
        shutil.copytree(flag, dashboard / "frontend/node_modules/flag-icons")
        env = {key: os.environ[key] for key in ("PATH", "HOME", "TMPDIR", "LANG", "LC_ALL") if key in os.environ}
        env.update(VERCEL="1", NEXT_TELEMETRY_DISABLED="1")
        command = ["node", str(dashboard / "node_modules/next/dist/bin/next"), "build", "frontend", "--webpack"]
        report["buildArgv"] = command
        started = time.monotonic()
        completed = subprocess.run(command, cwd=dashboard, env=env, capture_output=True, text=True, timeout=180)
        report["elapsedMs"] = round((time.monotonic() - started) * 1000, 3)
        (run / "build.stdout.log").write_text(completed.stdout)
        (run / "build.stderr.log").write_text(completed.stderr)
        report["exitCode"] = completed.returncode
        report["sourceDrift"] = [p for p, digest in sources.items() if hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != digest]
        report["status"] = "pass" if completed.returncode == 0 and not report["sourceDrift"] else "fail"
    report["ownedDirectoryRemoved"] = not owned.exists()
except Exception as error:
    report["error"] = {"type": type(error).__name__, "message": str(error)}
finally:
    report["finishedAtUtc"] = dt.datetime.now(dt.timezone.utc).isoformat()
    shutil.copy2(__file__, run / "verify_build.py")
    (run / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "error": report.get("error"), "result": str(run / "result.json")}))
raise SystemExit(report["status"] != "pass")
