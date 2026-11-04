#!/usr/bin/env python3
"""Before-code E2E contract: existing AWS sources -> real typed local PostgreSQL."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import traceback

REPO = Path(__file__).resolve().parents[1]
EVIDENCE = REPO / "docs/verification/orion-pro-pilot-20261104"
MODEL = REPO / "docs/architecture/orion-plan-20261104/target-schema.proposed.json"
NORMALIZER = REPO / "dashboard/scripts/orion_pro_normalize.py"
EXPECTED = {"fixtures": 612, "matches": 387, "performances": 15437, "shots": 9795,
            "players": 839, "teams": 20, "player_profile_lookup_gaps": 62}
CASES = ["importer_available", "real_source_import", "exact_typed_key_counts",
         "source_oracle_metrics_aliases", "native_shapes_quality", "noop_reimport",
         "source_correction_retains_snapshot", "local_sql_reads", "mapping_acceptance_boundary"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pg-bin", type=Path, default=Path("/tmp/statarena-cache-test-tools/node_modules/@embedded-postgres/darwin-arm64/native/bin"))
    parser.add_argument("--label", default="real-source")
    parser.add_argument("--phase", choices=["core", "families"], default="core")
    parser.add_argument("--source-scope", type=Path, default=EVIDENCE / "source_scope.json")
    args = parser.parse_args()
    run = EVIDENCE / "real-source-runs" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-" + args.label)
    run.mkdir(parents=True)
    inputs = run / "inputs"
    inputs.mkdir()
    # Code/spec metadata only. Never copy AWS documents or a PostgreSQL dump.
    for source in [Path(__file__), EVIDENCE / "REAL_SOURCE_PROTOCOL.md", EVIDENCE / "harness.py", MODEL, NORMALIZER]:
        if source.exists():
            shutil.copy2(source, inputs / source.name)
    sys.path.insert(0, str(EVIDENCE))
    sys.path.insert(0, str(REPO / "dashboard/scripts"))
    from harness import LocalPostgres
    import psycopg
    pg = LocalPostgres(args.pg_bin, run)
    report = {"startedAt": datetime.now(timezone.utc).isoformat(), "environment": "owned disposable LOCAL PostgreSQL18.6",
              "command": f"PYTHONPATH=/tmp/statarena-publication-test-python python3 tests/orion_pro_real_pilot.py --label {args.label} --phase {args.phase}",
              "modelSha256": sha(MODEL), "sourceScopeSha256": sha(args.source_scope), "expected": EXPECTED,
              "limits": {"awsIndexedQueries":100,"awsDecodedBytes":256*1024*1024,"awsStatementMs":8000,"awsLockMs":1000},
              "cases": [], "remoteWrites": [], "rawSourceCopies": [], "phase": args.phase}
    conn = None
    pilot = None
    blocked = None
    try:
        pg.start()
        pg.migration(REPO)
        conn = psycopg.connect(pg.dsn, autocommit=True)
        for case in CASES:
            if blocked:
                report["cases"].append({"case":case,"status":"unverified","reason":blocked})
                continue
            try:
                if case == "importer_available":
                    assert NORMALIZER.is_file(), "real-source normalizer does not exist (expected initial RED)"
                    spec = importlib.util.spec_from_file_location("orion_pro_normalize", NORMALIZER)
                    normalizer = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(normalizer)
                    assert callable(getattr(normalizer, "run_real_pilot", None)), "normalizer interface missing"
                    actual = {"normalizerSha256":sha(NORMALIZER)}
                elif case == "real_source_import":
                    pilot = normalizer.run_real_pilot(conn, run, args.source_scope, args.phase)
                    assert pilot["sourceBudget"]["queries"] <= 100
                    assert pilot["sourceBudget"]["decodedBytes"] <= 256*1024*1024
                    assert pilot["role"] == "orion_pro_ingest"
                    actual = pilot["import"]
                elif case == "exact_typed_key_counts":
                    sqls = {
                        "fixtures":"SELECT count(*) FROM football.matches_current",
                        "matches":"SELECT count(*) FROM football.matches_current WHERE status='finished'",
                        "performances":"SELECT count(*) FROM football.match_players_current",
                        "shots":"SELECT count(*) FROM football.shots_current",
                        "players":"SELECT count(*) FROM football.players",
                        "teams":"SELECT count(*) FROM football.teams",
                    }
                    actual = {k:conn.execute(sql).fetchone()[0] for k,sql in sqls.items()}
                    assert actual == {k:EXPECTED[k] for k in actual}, actual
                elif case == "source_oracle_metrics_aliases":
                    actual = pilot["oracleComparisons"]
                    assert actual and all(x["sourceSha256"]==x["typedSha256"] and x["sourceRows"]==x["typedRows"] for x in actual), actual
                    assert {x["kind"] for x in actual} >= {"fixtures","performances","shots","public_aliases"}
                elif case == "native_shapes_quality":
                    actual = pilot["nativeShapes"]
                    assert actual["missingProfileResourceCount"] == 62
                    assert actual["missingToZeroCoercions"] == 0
                    assert actual["opaqueSourceBodiesStored"] == 0
                    assert actual["numericRoundingCoercions"] == 0
                elif case == "noop_reimport":
                    actual = pilot["noop"]
                    assert actual["duplicateRows"] == 0 and actual["newFactRevisions"] == 0
                elif case == "source_correction_retains_snapshot":
                    actual = pilot["correction"]
                    assert actual["throughActualNormalizer"] and actual["newValue"] != actual["oldValue"]
                    assert actual["oldSnapshotValue"] == actual["oldValue"]
                    assert actual["newSnapshotValue"] == actual["newValue"]
                elif case == "local_sql_reads":
                    actual = pilot["reads"]
                    assert {x["kind"] for x in actual} >= {"list","player","club","match"}
                    assert all(x["rows"] > 0 and x["environment"] == "local" for x in actual)
                elif case == "mapping_acceptance_boundary":
                    actual = pilot["mapping"]
                    assert actual["dispositions"] and actual["unknownUsefulFieldsSilentlyDropped"] == 0
                    if actual["rejected"] or actual["unverified"]:
                        assert not pilot["fullAcceptance"]
                        actual = {**actual,"fullAcceptance":False,"scope":"Explicit mapping gaps remain; this is not global migration acceptance"}
                report["cases"].append({"case":case,"status":"pass","actual":actual})
                print("PASS " + case, flush=True)
            except Exception as error:
                # Never dump a row/source body or connection detail into evidence.
                safe = str(error) if isinstance(error, AssertionError) and not getattr(error, "sqlstate", None) else type(error).__name__
                report["cases"].append({"case":case,"status":"fail","error":safe,"sqlstate":getattr(error,"sqlstate",None)})
                print("FAIL " + case + ": " + safe, flush=True)
                if case in {"importer_available","real_source_import"}:
                    blocked = "prerequisite " + case + " failed"
    except Exception as error:
        report["setupError"] = {"type":type(error).__name__,"reason":str(error) if isinstance(error, RuntimeError) else None}
    finally:
        if conn is not None:
            conn.close()
        report["cleanup"] = pg.cleanup()
        report["finishedAt"] = datetime.now(timezone.utc).isoformat()
        report["counts"] = {status:sum(c["status"]==status for c in report["cases"]) for status in ("pass","fail","unverified")}
        report["status"] = "pass" if report["counts"]["pass"]==len(CASES) and not report.get("setupError") else "fail"
        (run / "result.json").write_text(json.dumps(report, indent=2, default=str)+"\n")
        print(json.dumps({"status":report["status"],"counts":report["counts"],"evidence":str(run)}),flush=True)
    return 0 if report["status"]=="pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
