#!/usr/bin/env python3
"""Source-free real-CLI pre-code gate, not a substitute for future PG/HTTP E2E."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time

sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[3]
sys.path.insert(0, str(ROOT / "tests"))
from orion_e2e_process import run_bounded


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    started = time.monotonic()
    deadline = started + 10
    target = ROOT / "dashboard/scripts/orion_pro_publish_real.py"
    matrix = json.loads((BASE / "FAILURE_MATRIX.json").read_text())
    pins = json.loads((BASE / "PINS.json").read_text())
    require_missing = not target.exists()
    # Stop instead of accidentally promoting this limited pre-code gate into
    # acceptance of an implementation that needs the future complete harness.
    if not require_missing:
        raise RuntimeError("Real adapter now exists; this pre-code gate does not qualify its runtime. Use the separately reviewed full E2E harness.")
    run = BASE / "precode-runs" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    (run / "inputs").mkdir(parents=True)
    own = [BASE / n for n in ["CONTRACT.md", "ADMISSION.schema.json", "SOURCE_FIELD_MATRIX.json", "READBACK_REQUEST.json", "FAILURE_MATRIX.json", "PINS.json", "e2e.py"]]
    for path in own:
        (run / "inputs" / path.name).write_bytes(path.read_bytes())
    checks = {name: digest(ROOT / name) == value for name, value in pins["sha256"].items()}
    if not all(checks.values()):
        raise RuntimeError("A pinned source/metadata input changed before pre-code execution")
    env = {k: os.environ[k] for k in ["PATH", "HOME", "USER", "LANG", "LC_ALL"] if k in os.environ}
    command = [sys.executable, "-I", str(target), "--help"]
    child = run_bounded(command, deadline=min(deadline, time.monotonic() + 5), cwd=BASE, env=env,
                        term_seconds=1, drain_seconds=1)
    (run / "publisher-help.stdout.log").write_text(child.stdout)
    (run / "publisher-help.stderr.log").write_text(child.stderr)
    expected_missing = child.returncode == 2 and "No such file or directory" in child.stderr and not target.exists()
    cases = [{"id": c["id"], "status": "unverified", "blockedBy": "real-adapter-cli-absent"} for c in matrix["cases"]]
    cases[0] = {"id": "R00", "status": "fail", "expectedPreCodeRed": expected_missing,
                "expected": {"exitCode": 0, "usableRealAdmissionCli": True},
                "actual": {"exitCode": child.returncode, "targetExists": target.exists()}}
    receipt = {"kind": "REAL_PUBLICATION_PRECODE_CLI_RED_NOT_RUNTIME_ACCEPTANCE",
               "status": "expected_precode_red" if expected_missing else "unexpected_failure",
               "command": command, "rerunCommand": "python3 docs/verification/orion-pro-publisher-20261105/real-boundary-precode/e2e.py",
               "setup": {"frozenInputHashesMatched": checks, "environmentKeys": sorted(env)},
               "inputs": {p.name: digest(p) for p in own}, "expectedProtocol": "CONTRACT.md and FAILURE_MATRIX.json",
               "cases": cases, "counts": {s: sum(c["status"] == s for c in cases) for s in ["pass", "fail", "unverified"]},
               "runtimeHarnessImplemented": False, "realAdapterImplemented": False,
               "postgresStarts": 0, "driverConnections": 0, "ramReads": 0, "remoteActions": [],
               "elapsedSeconds": round(time.monotonic() - started, 3), "suggestedCommit": "test: specify real SQL publication admission before adapter code"}
    (run / "result.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": receipt["status"], "counts": receipt["counts"], "postgresStarts": 0,
                      "receipt": str((run / "result.json").relative_to(ROOT))}))
    # The actual CLI failure is RED. Its expected nature does not make a
    # software or runtime test pass.
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
