#!/usr/bin/env python3
"""31 actual CLI/native-PG/HTTP cases, implemented before real adapter code.

Default is a source-free inventory. PG mode requires an exact separate ROOT
release; the first unexpected failure stops and preserves the attempted run.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import threading
import time
import traceback

sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[3]
sys.path.insert(0, str(BASE))
from runtime_cases import CASES


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-owned", action="store_true")
    parser.add_argument("--qualify-setup-only", action="store_true")
    parser.add_argument("--release", type=Path)
    parser.add_argument("--release-sha256")
    parser.add_argument("--label", default="real-publication-precode")
    args = parser.parse_args()
    if args.release is not None:
        args.release = args.release.resolve()
    helpers = [ROOT / "dashboard/scripts/orion_pro_admit_real.py", ROOT / "dashboard/scripts/orion_pro_publish_real.py"]
    assert len(CASES) == 31 and [f.__name__ for f in CASES] == [f"R{i:02d}" for i in range(31)]
    if not args.run_owned:
        print(json.dumps({"kind": "REAL_PUBLICATION_E2E_OFFLINE_INVENTORY", "caseFunctions": len(CASES),
            "helpersPresent": {p.name: p.exists() for p in helpers}, "postgresStarts": 0, "ramGets": 0, "cloudCalls": 0,
            "runtimeCasesExecuted": 0, "setupOnlyRequiresSeparateRelease": True,
            "priorCliRed": "precode-runs/20261105T115038829583Z/result.json"}))
        return 0
    from runtime_context import Runtime, BOUNDS
    assert re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9-]{0,70}", args.label)
    assert args.release is not None and sha(args.release) == args.release_sha256
    assert args.release.is_relative_to(BASE), "Owned test releases stay in this evidence namespace"
    release = json.loads(args.release.read_text())
    required = {"kind", "scope", "allocationId", "testSha256", "caseSha256", "contextSha256", "fixtureSha256", "workerSha256",
                "helperSha256", "bounds", "codeCommit", "expiresAt", "setupOnly"}
    assert set(release) == required
    assert release["kind"] == "real_publication_owned_e2e_release_v1" and release["scope"] == "owned_source_free_fixture"
    assert release["bounds"] == BOUNDS and release["setupOnly"] is args.qualify_setup_only
    assert release["testSha256"] == sha(Path(__file__)) and release["caseSha256"] == sha(BASE / "runtime_cases.py")
    assert release["contextSha256"] == sha(BASE / "runtime_context.py") and release["fixtureSha256"] == sha(BASE / "runtime_fixture.py")
    assert release["workerSha256"] == sha(BASE / "runtime_worker.py") and re.fullmatch(r"[a-f0-9]{40}", release["codeCommit"])
    assert datetime.now(timezone.utc) < datetime.fromisoformat(release["expiresAt"])
    assert re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,70}", release["allocationId"])
    # Setup qualification may precede both implementations. It does not execute
    # case functions or label missing helper behavior as passed.
    if not args.qualify_setup_only:
        assert all(p.is_file() for p in helpers), "Keep the genuine pre-code CLI RED; no repeated missing-helper campaign"
        assert release["helperSha256"] == {p.name: sha(p) for p in helpers}
    else:
        assert release["helperSha256"] == {}, "Pre-code setup has no fabricated real helper hashes"
    consumed = BASE / (release["allocationId"] + ".consumed.json")
    assert not consumed.exists(), "Allocation cannot be reused or reset"
    started = time.monotonic()
    deadline = started + BOUNDS["seconds"]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run = BASE / "runtime-runs" / (stamp + "-" + args.label)
    (run / "inputs").mkdir(parents=True)
    release["releaseSha256"] = args.release_sha256
    save(consumed, {"run": str(run.relative_to(ROOT)), "releaseSha256": args.release_sha256, "startedAt": datetime.now(timezone.utc).isoformat()})
    paths = [*sorted(BASE.glob("*.py")), BASE / "CONTRACT.md", BASE / "FAILURE_MATRIX.json", BASE / "SOURCE_FIELD_MATRIX.json", BASE / "ADMISSION.schema.json", args.release]
    if not args.qualify_setup_only: paths += helpers
    sources = {}
    try:
        for path in paths:
            path = path.resolve()
            dest = run / "inputs" / path.relative_to(ROOT)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)
            sources[str(path.relative_to(ROOT))] = sha(path)
    except BaseException as error:
        # Archiving itself belongs to the attempt. Emit its receipt before any
        # Runtime/PG construction, rather than lose a consumed allocation.
        early = {"kind": "REAL_PUBLICATION_SETUP_ARCHIVE_FAILURE", "status": "fail", "setupOnly": args.qualify_setup_only,
            "command": [sys.executable, str(Path(__file__)), *sys.argv[1:]], "sourceSha256": sources,
            "releaseSha256": args.release_sha256, "error": {"type": type(error).__name__, "message": str(error)},
            "runtimeCasesExecuted": 0, "postgresStarts": 0, "ramGets": 0, "cloudCalls": 0,
            "counts": {"pass": 0, "fail": 0, "unverified": 31}, "cleanup": {"pgNeverConstructed": True}}
        (run / "exception.log").write_text(traceback.format_exc())
        save(run / "result.json", early)
        print(json.dumps({"status": "fail", "counts": early["counts"], "receipt": str((run / "result.json").relative_to(ROOT))}))
        return 1
    report = {"kind": "REAL_PUBLICATION_31_CASE_OWNED_NATIVE_HTTP_E2E", "command": [sys.executable, str(Path(__file__)), *sys.argv[1:]],
        "sourceSha256": sources, "bounds": BOUNDS, "releaseSha256": args.release_sha256, "setupOnly": args.qualify_setup_only,
        "cases": [], "status": "running", "runtimeQualified": False, "rdsQualified": False,
        "sourceRamGets": 0, "cloudCalls": 0, "businessRdsWrites": [], "suggestedCommit": "test: exercise real SQL admission and publication before adapters"}
    context = None
    stop = threading.Event()
    timeout = []
    def watchdog():
        while not stop.wait(.1):
            if time.monotonic() >= deadline:
                timeout.append("absolute_deadline")
                if context and context.db and not context.db.closed:
                    try: context.db.cancel_safe(timeout=1)
                    except Exception: pass
                if context:
                    for child in context.children:
                        if child["process"].poll() is None:
                            import signal
                            try: os.killpg(child["process"].pid, signal.SIGKILL)
                            except ProcessLookupError: pass
                    context.stop_api()
                return
    watcher = threading.Thread(target=watchdog, daemon=True)
    watcher.start()
    try:
        context = Runtime(run, release, deadline)
        context.setup()
        report["setup"] = {"catalogue": context.catalogue(), "native31": context.initial_native31,
            "before": context.state(), "sourcePolicy": "real_source_core_v2_native31", "fixtureOrigin": "owned_source_free_fixture"}
        # Preconditions and independent fixture oracles are qualified first.
        assert context.catalogue()["counts"] == context.expected_catalogue_counts
        assert context.selected_count("football.matches", "publication_state='draft'") == 6
        assert context.db.execute("SELECT count(*) FROM analytics.aggregation_builds").fetchone() == (0,)
        assert context.native31()[0] == 31 * len(context.fixture.minute_rows)
        assert context.fixture.expected_played[context.bench_pair] is None
        assert not context.fixture.at("football.competition_teams")
        if args.qualify_setup_only:
            before31 = context.native31()
            streamed = context.fixture.stream_family()
            context.owner_epoch()
            assert streamed["selectedRows"] > 5000
            closures = context.independent_closures()
            assert len(closures) == 3 and context.native31() == before31
            report["setup"]["streamedSportRows"] = streamed["selectedRows"]
            report["setup"]["independentStreamedClosures"] = closures
            with context.connect("statarena_ingest") as writer:
                actor = writer.execute("SELECT current_user,session_user,current_setting('statement_timeout'),current_setting('lock_timeout'),current_setting('idle_in_transaction_session_timeout'),(SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid())").fetchone()
                assert actor == ("statarena_ingest", "statarena_ingest", "8s", "1s", "5s", True)
                report["setup"]["actualOrdinaryWriterTlsIdentity"] = list(actor)
            report["setup"]["after"] = context.state()
            report["status"] = "setup_pass_runtime_unverified"
        else:
            for case in CASES:
                context.check()
                tick = time.monotonic()
                case(context)
                report["cases"].append({"id": case.__name__, "status": "pass", "elapsedSeconds": round(time.monotonic() - tick, 3)})
            report["runtimeQualified"] = True
            report["status"] = "pass"
    except BaseException as error:
        report.update(status="fail", error={"type": type(error).__name__, "message": str(error)[:3000]})
        (run / "exception.log").write_text(traceback.format_exc())
    finally:
        stop.set(); watcher.join(timeout=1)
        if context:
            try: context.close()
            except BaseException as error:
                report.update(status="fail", cleanupError={"type": type(error).__name__, "message": str(error)[:1000]})
            report.update(cleanup=context.cleanup, invocations=context.invocations, httpRequests=context.requests, budget=context.budget.read())
            commands = []
            postgres_log = run / "postgres.log"
            if postgres_log.exists():
                commands = [line for line in postgres_log.read_text().splitlines() if re.search(r"LOG:  (?:statement:|execute [^:]*:)", line)]
            report["sqlAccounting"] = {"reservedCalls": report["budget"]["counts"]["sql"], "serverLoggedClientCommands": len(commands),
                                       "internalTransactionCommandsReserved": True}
            if len(commands) > report["budget"]["counts"]["sql"] or len(commands) > BOUNDS["sql"]:
                report.update(status="fail", accountingError="Unreserved or over-budget native client command")
        recorded = {c["id"] for c in report["cases"]}
        report["cases"] += [{"id": f.__name__, "status": "unverified", "blockedBy": "setup-only" if args.qualify_setup_only else "prior-failure"} for f in CASES if f.__name__ not in recorded]
        report["counts"] = {s: sum(c["status"] == s for c in report["cases"]) for s in ["pass", "fail", "unverified"]}
        report["elapsedSeconds"] = round(time.monotonic() - started, 3)
        report["sourceChanges"] = [name for name, value in sources.items() if sha(ROOT / name) != value]
        if timeout or report["sourceChanges"]:
            report["status"] = "fail"
        save(run / "result.json", report)
        print(json.dumps({"status": report["status"], "counts": report["counts"], "receipt": str((run / "result.json").relative_to(ROOT))}))
    return 0 if report["status"] in ["pass", "setup_pass_runtime_unverified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
