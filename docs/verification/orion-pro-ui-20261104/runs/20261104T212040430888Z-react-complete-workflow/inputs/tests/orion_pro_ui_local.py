#!/usr/bin/env python3
"""Pre-code real Next -> Bun -> owned PostgreSQL browser E2E. No cloud or source reads."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import select
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "docs/verification/orion-pro-ui-20261104"
READERS = BASE.parent / "orion-pro-readers-20261104"
PILOT = BASE.parent / "orion-pro-pilot-20261104"
MODEL = ROOT / "docs/architecture/orion-plan-20261104/target-schema.proposed.json"
PWCLI = Path("/Users/lemonnierhugo/.codex/skills/playwright/scripts/playwright_cli.sh")
DEFAULT_BROWSER = Path("/Users/lemonnierhugo/Library/Caches/ms-playwright/chromium-1228/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing")
CASES = ["local_published_preconditions", "manifest_renders_results", "cursor_pages_30_30_1", "visited_page_cache", "summary_lightweight", "shots_explicit_zero_meters_goal", "same_detail_cache", "mobile_operable", "nullable_profile_rendering", "published_correction", "old_A_pinned", "independent_C_cache", "network_and_sql_boundaries", "cleanup"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def clean_env():
    return {key: value for key, value in os.environ.items() if key in ("PATH", "HOME", "USER", "SHELL", "LANG", "LC_ALL", "TMPDIR")}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", default="react-baseline")
    parser.add_argument("--pg-bin", type=Path, default=Path("/tmp/statarena-cache-test-tools/node_modules/@embedded-postgres/darwin-arm64/native/bin"))
    parser.add_argument("--browser-executable", type=Path, default=DEFAULT_BROWSER)
    args = parser.parse_args()
    if not re.fullmatch("[A-Za-z0-9][A-Za-z0-9-]{0,70}", args.label):
        parser.error("Use a simple label")
    if not shutil.which("npx"):
        parser.error("The installed Playwright CLI skill requires npx")
    sys.path[:0] = [str(BASE), str(READERS), str(PILOT), str(ROOT / "dashboard/scripts")]
    import psycopg
    from harness import LocalPostgres
    from ui_fixture import BrowserFixture
    from workflow import BrowserWorkflow
    from orion_pro_migrate import bootstrap
    from orion_pro_integrity import role_grants_sql

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run = BASE / "runs" / (stamp + "-" + args.label)
    inputs = run / "inputs"
    inputs.mkdir(parents=True)
    browser_artifacts = BASE / "output/playwright" / (stamp + "-" + args.label)
    browser_artifacts.mkdir(parents=True)
    session = "orion-ui-" + stamp[:15].lower()
    report = {
        "kind": "owned_pg_bun_next_playwright_ui_e2e", "startedAt": datetime.now(timezone.utc).isoformat(),
        "command": ["python3", "tests/orion_pro_ui_local.py", *sys.argv[1:]],
        "setup": "Owned loopback PG18.6, sealed 012/013/bootstrap, synthetic published 61/1/1 matches, real read-only Bun Pro API, actual Next frontend source in temporary isolation, installed Playwright CLI skill and cached Chromium",
        "expected": "PROTOCOL.md matrix prepared before React integration", "sourceSha256": {}, "cases": [], "processes": [],
        "remoteActions": [], "browserSession": session, "browserArtifacts": str(browser_artifacts.relative_to(ROOT)),
        "limits": ["Synthetic local development workflow only; no AWS/Neon/real source/Vercel/CDN or all-site parity claim", "Mono-edition cursor UI; multiple editions need explicit selection, no aggregate token inferred"],
    }
    def save():
        (run / "result.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
    def case(name, status, **details):
        report["cases"].append({"case": name, "status": status, **details})
        if report.get("activeCase") == name: report.pop("activeCase")
        save()
    def copy_input(path):
        relative = path.relative_to(ROOT)
        target = inputs / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        report["sourceSha256"][str(relative)] = sha(path)
    paths = [Path(__file__), MODEL, *[p for p in BASE.iterdir() if p.is_file()], READERS / "fixture.py", READERS / "http_server.mjs", PILOT / "harness.py", PILOT / "fixtures.py", ROOT / "dashboard/scripts/orion_pro_migrate.py", ROOT / "dashboard/scripts/orion_pro_integrity.py", ROOT / "dashboard/package.json", ROOT / "dashboard/bun.lock"]
    for directory in (ROOT / "dashboard/frontend", ROOT / "dashboard/shared", ROOT / "dashboard/backend"):
        for path in directory.rglob("*"):
            relative = path.relative_to(directory)
            if any(part in ("node_modules", ".next", ".next-dev", "__pycache__", ".git") or part.startswith(".env") for part in relative.parts):
                continue
            if path.is_file() and (path.suffix in (".js", ".jsx", ".mjs", ".css", ".json", ".sql", ".md") or directory.name == "shared"):
                paths.append(path)
    for path in dict.fromkeys(paths):
        if path.is_file(): copy_input(path)
    pg = LocalPostgres(args.pg_bin, run)
    admin, api, frontend = None, None, None
    streams, cli_commands = [], []
    owned_frontend = Path(tempfile.mkdtemp(prefix="orion-pro-ui-next-"))
    origin, frontend_origin, browser_opened = None, None, False
    frontend_copy = owned_frontend / "dashboard/frontend"
    def cli(*argv, timeout=60, check=True):
        command = [str(PWCLI), "--session=" + session, *map(str, argv)]
        index = len(cli_commands) + 1
        completed = subprocess.run(command, cwd=BASE, env=clean_env(), text=True, capture_output=True, timeout=timeout)
        name = f"{index:03d}-{argv[0]}"
        (run / (name + ".stdout.log")).write_text(completed.stdout)
        (run / (name + ".stderr.log")).write_text(completed.stderr)
        cli_commands.append({"argv": command, "cwd": str(BASE), "exitCode": completed.returncode, "stdout": name + ".stdout.log", "stderr": name + ".stderr.log"})
        (run / "browser-commands.json").write_text(json.dumps(cli_commands, indent=2) + "\n")
        if check and (completed.returncode or "### Error" in completed.stdout):
            raise RuntimeError(f"Playwright {argv[0]} failed: {completed.stdout[-1500:]} {completed.stderr[-800:]}")
        return completed.stdout
    def result_value(output):
        match = re.search(r"### Result\s*\n(.*?)(?=\n### |\Z)", output, re.S)
        if not match:
            raise RuntimeError("Playwright CLI did not return a result section")
        return json.loads(match.group(1).strip())
    def http_json(path):
        with urlopen(origin + path, timeout=10) as response:
            return json.load(response)
    try:
        report["toolVersions"] = {"python": sys.version}
        for tool, command in (("node", ["node", "--version"]), ("bun", ["bun", "--version"]), ("chromium", [str(args.browser_executable), "--version"])):
            version = subprocess.run(command, env=clean_env(), capture_output=True, text=True, check=True, timeout=10)
            report["toolVersions"][tool] = version.stdout.strip()
        report["toolVersions"]["playwrightCli"] = cli("--version").strip()
        model = json.loads(MODEL.read_text())
        pg.start()
        admin = psycopg.connect(pg.dsn, autocommit=True)
        assert admin.info.server_version == 180006
        artifacts = [(version, ROOT / "dashboard/backend/migrations" / filename, (ROOT / "dashboard/backend/migrations" / filename).read_text()) for version, filename in (("012", "012_orion_pro_domain.sql"), ("013", "013_orion_pro_integrity.sql"))]
        with admin.transaction():
            for version, path, sql in artifacts:
                admin.execute(sql, prepare=False)
                admin.execute("INSERT INTO ingest.schema_migrations(version,content_sha256,applied_at,code_commit) VALUES(%s,%s,CURRENT_TIMESTAMP,%s)", (version, sha(path), "source-free-ui-e2e"))
            report["bootstrap"] = bootstrap(admin, model, artifacts)
            for role in ("statarena_ingest", "statarena_runtime"):
                admin.execute(f"CREATE ROLE {role} LOGIN NOSUPERUSER NOCREATEROLE NOCREATEDB NOREPLICATION NOBYPASSRLS")
            admin.execute(role_grants_sql(model, ingest_role="statarena_ingest", runtime_role="statarena_runtime"), prepare=False)
        fixture = BrowserFixture(admin, pg.dsn, run, psycopg)
        report["fixture"] = fixture.prepare()
        env = clean_env()
        env.update(DATABASE_URL=f"postgresql://statarena_runtime@127.0.0.1:{pg.port}/postgres?sslmode=disable", STATARENA_DATA_PROVIDER="aws", STATARENA_TEST_DATABASE="1", STATARENA_PRO_API="1", AWS_EC2_METADATA_DISABLED="true")
        api_err = (run / "api.stderr.log").open("w"); streams.append(api_err)
        api = subprocess.Popen(["bun", str(READERS / "http_server.mjs")], cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=api_err, text=True, bufsize=1, start_new_session=True)
        report["processes"].append({"name": "Bun Pro API", "pid": api.pid, "argv": ["bun", str(READERS / "http_server.mjs")], "environment": {key: env[key] for key in ("DATABASE_URL", "STATARENA_DATA_PROVIDER", "STATARENA_TEST_DATABASE", "STATARENA_PRO_API", "AWS_EC2_METADATA_DISABLED")}})
        deadline = time.monotonic() + 25
        while time.monotonic() < deadline:
            ready, _, _ = select.select([api.stdout], [], [], 0.2)
            if not ready: continue
            line = api.stdout.readline()
            with (run / "api.stdout.log").open("a") as stream: stream.write(line)
            if not line and api.poll() is not None: raise RuntimeError("Bun API exited")
            try: info = json.loads(line)
            except ValueError: continue
            if info.get("event") == "ready":
                origin = f"http://127.0.0.1:{info['port']}"
                report["runtimeIdentity"] = info["identity"]
                break
        assert origin, "Bun API startup timed out"
        assert report["runtimeIdentity"] == [{"role": "statarena_runtime", "readonly": "on"}]
        manifest = http_json("/api/dashboard/manifest")
        (run / "manifest-before.json").write_text(json.dumps(manifest, indent=2) + "\n")
        assert manifest["storage"] == "aws-orion-pro" and len(manifest["editions"]) == 3
        report["tokensBefore"] = {edition["season"]: edition["representationToken"] for edition in manifest["editions"]}
        chunk = next(season for season in manifest["seasons"] if season["id"] == "2024/2025")["chunks"][0]
        assert chunk["meta"]["matchCount"] == 61
        case("local_published_preconditions", "pass", serverVersion=admin.info.server_version, matchCounts=report["fixture"]["matchCounts"], role=report["runtimeIdentity"])

        ignored = shutil.ignore_patterns("node_modules", ".next", ".next-dev", ".git", ".env", ".env.*", "__pycache__")
        shutil.copytree(ROOT / "dashboard/frontend", frontend_copy, ignore=ignored)
        shutil.copytree(ROOT / "dashboard/shared", owned_frontend / "dashboard/shared", ignore=ignored)
        shutil.copytree(ROOT / "dashboard/backend", owned_frontend / "dashboard/backend", ignore=ignored)
        shutil.copy2(ROOT / "dashboard/package.json", owned_frontend / "dashboard/package.json")
        (owned_frontend / "dashboard/node_modules").symlink_to(ROOT / "dashboard/node_modules", target_is_directory=True)
        # This declared, locked package is absent from the shared install. Supply only
        # its existing cache bytes in the owned copy; never install into shared source.
        cached_flags = Path("/Users/lemonnierhugo/.bun/install/cache/flag-icons@7.6.0@@@1")
        if not (ROOT / "dashboard/node_modules/flag-icons").exists():
            assert json.loads((cached_flags / "package.json").read_text())["version"] == "7.6.0"
            (frontend_copy / "node_modules").mkdir(exist_ok=True)
            (frontend_copy / "node_modules/flag-icons").symlink_to(cached_flags, target_is_directory=True)
            report["isolatedDependencyRepair"] = {"package": "flag-icons", "version": "7.6.0", "source": str(cached_flags), "sha256": {name: sha(cached_flags / name) for name in ("package.json", "country.json", "css/flag-icons.min.css")}, "sharedInstallChanged": False}
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0)); port = probe.getsockname()[1]
        frontend_origin = f"http://127.0.0.1:{port}"
        next_env = clean_env()
        next_env.update(ORION_API_ORIGIN=origin, NEXT_TELEMETRY_DISABLED="1", NODE_ENV="development", STATARENA_PRO_API="1")
        command = ["node", str(ROOT / "dashboard/node_modules/next/dist/bin/next"), "dev", "--webpack", "--hostname", "127.0.0.1", "--port", str(port)]
        next_log = (run / "next.log").open("w"); streams.append(next_log)
        frontend = subprocess.Popen(command, cwd=frontend_copy, env=next_env, stdout=next_log, stderr=subprocess.STDOUT, start_new_session=True)
        report["processes"].append({"name": "Next isolated frontend", "pid": frontend.pid, "argv": command, "cwd": str(frontend_copy), "environment": {key: next_env[key] for key in ("ORION_API_ORIGIN", "NEXT_TELEMETRY_DISABLED", "NODE_ENV", "STATARENA_PRO_API")}})
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            if frontend.poll() is not None: raise RuntimeError("Next exited; inspect next.log")
            if "Ready in" in (run / "next.log").read_text(): break
            time.sleep(0.2)
        else: raise RuntimeError("Next startup timed out")
        report["frontendOrigin"] = frontend_origin
        config = {"browser": {"browserName": "chromium", "isolated": True, "launchOptions": {"headless": True, "executablePath": str(args.browser_executable)}, "contextOptions": {"viewport": {"width": 1440, "height": 1000}, "serviceWorkers": "block"}}, "outputDir": str(browser_artifacts)}
        config_path = run / "playwright.config.json"
        config_path.write_text(json.dumps(config, indent=2) + "\n")
        cli("open", "about:blank", "--config", config_path)
        browser_opened = True
        cli("tracing-start")
        report["browserSetup"] = result_value(cli("run-code", "--filename", BASE / "browser_setup.js"))
        path = "/matchs/?tab=results&season=2024%2F2025&league=l_000001&focus=all"
        cli("goto", frontend_origin + path, timeout=60)
        cli("snapshot", "--filename", browser_artifacts / "initial.snapshot.yml")
        actual = result_value(cli("run-code", "--filename", BASE / "browser_initial.js", timeout=45))
        (run / "browser-initial.json").write_text(json.dumps(actual, indent=2) + "\n")
        cli("snapshot", "--filename", browser_artifacts / "initial-settled.snapshot.yml")
        cli("screenshot", "--filename", browser_artifacts / "initial.png", "--full-page")
        if any(response["status"] >= 500 and response["url"].split("?", 1)[0].rstrip("/").endswith("/matchs") for response in actual["proof"]["responses"]):
            report["classification"] = "frontend_preparation_failure"
            raise RuntimeError("Next document failed before application workflow; inspect retained compiler/browser logs, not an application RED")
        if actual["rows"] != 30:
            report["classification"] = "application_red"
            case("manifest_renders_results", "fail", expected="30 rendered results from healthy published Pro edition", actualRows=actual["rows"], renderedBody=actual["body"][:5000], evidence="browser-initial.json", screenshot=str((browser_artifacts / "initial.png").relative_to(ROOT)))
            raise AssertionError("Actual frontend did not render the first 30 Pro matches (pre-integration browser RED)")
        case("manifest_renders_results", "pass", actualRows=actual["rows"])
        report["classification"] = "executed_application_workflow"
        BrowserWorkflow(cli=cli, result_value=result_value, fixture=fixture, report=report, run=run, artifacts=browser_artifacts, case=case, http_json=http_json, base=BASE).run_all()
    except Exception as error:
        report["error"] = {"type": type(error).__name__, "reason": str(error)}
        active = report.get("activeCase")
        if active and not any(entry["case"] == active and entry["status"] == "fail" for entry in report["cases"]):
            case(active, "fail", reason=str(error))
    finally:
        if origin:
            try: report["httpSqlTraces"] = http_json("/__e2e__/traces")
            except Exception as error: report["traceError"] = str(error)
        if browser_opened:
            try:
                final_state = result_value(cli("run-code", "--filename", BASE / "browser_state.js", check=False))
                (run / "browser-final.json").write_text(json.dumps(final_state, indent=2) + "\n")
                cli("snapshot", "--filename", browser_artifacts / "final.snapshot.yml", check=False)
                cli("screenshot", "--filename", browser_artifacts / "final.png", "--full-page", check=False)
            except Exception as error: report["browserFinalCaptureError"] = str(error)
            for argv in (("tracing-stop",), ("close",)):
                try: cli(*argv, check=False)
                except Exception as error: report.setdefault("browserCleanupErrors", []).append(str(error))
        for process in (frontend, api):
            if process is not None and process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try: process.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL); process.wait(timeout=5)
        for stream in streams: stream.close()
        if admin is not None: admin.close()
        cleanup = pg.cleanup()
        shutil.rmtree(owned_frontend)
        cleanup.update(nextStopped=frontend is None or frontend.poll() is not None, apiStopped=api is None or api.poll() is not None, isolatedFrontendRemoved=not owned_frontend.exists(), browserCloseAttempted=browser_opened)
        def listening(url):
            from urllib.parse import urlsplit
            if not url: return False
            target = urlsplit(url)
            with socket.socket() as probe:
                probe.settimeout(0.3)
                return probe.connect_ex(("127.0.0.1", target.port)) == 0
        cleanup.update(nextPortClosed=not listening(frontend_origin), apiPortClosed=not listening(origin), browserCleanupSucceeded=not report.get("browserCleanupErrors"))
        report["cleanup"] = cleanup
        changed = [path for path, digest in report["sourceSha256"].items() if not (ROOT / path).is_file() or sha(ROOT / path) != digest]
        report["sourceChangesDuringRun"] = changed
        case("cleanup", "pass" if all(value for key, value in cleanup.items() if isinstance(value, bool)) and not changed else "fail", actual=cleanup, changedSources=changed)
        completed = {entry["case"] for entry in report["cases"]}
        for name in CASES:
            if name not in completed:
                case(name, "unverified", reason="Dependent browser workflow not yet executed; retained prerequisite result is not a pass")
        report["counts"] = {status: sum(entry["status"] == status for entry in report["cases"]) for status in ("pass", "fail", "unverified")}
        report["expectedCaseCount"] = len(CASES)
        report["status"] = "pass" if report["counts"]["pass"] == len(CASES) and not report["counts"]["fail"] and not report["counts"]["unverified"] and "error" not in report else "fail"
        report["finishedAt"] = datetime.now(timezone.utc).isoformat()
        save()
        print(json.dumps({"status": report["status"], "counts": report["counts"], "receipt": str((run / "result.json").relative_to(ROOT))}))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
