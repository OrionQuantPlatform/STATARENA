#!/usr/bin/env python3
"""Run the exact copied workflow with one absolute owned-process deadline.

Only ledger location, tempfile location and subprocess supervision adapt. Every
case, fixture, admission expectation and independent oracle remains byte-exact.
This wrapper must only be started during ROOT's explicitly allocated PG slot.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[3]
sys.path[:0] = [str(BASE), str(ROOT / "tests")]
from orion_e2e_process import ChildStopped, run_bounded
import publisher_workflow as workflow


def file_sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def preservation():
    qualified = BASE.parent / "qualified-precode"
    manifest = qualified / "FINAL_CHECKSUMS.json"
    expected = "98620e160cbb6bb60862013ecbc415c4f5d326566fc807f4188d002aab2f090c"
    assert file_sha(manifest) == expected
    entries = json.loads(manifest.read_text())["sha256"]
    assert len(entries) == 101
    assert all(file_sha(qualified / name) == value for name, value in entries.items())
    copies = json.loads((BASE / "COPIED_CONTRACTS.json").read_text())["copies"]
    assert all(file_sha(BASE / name) == value == file_sha(qualified / name.replace(".precode.", ".")) for name, value in copies.items())
    original = (BASE / "publisher_http_server.precode.mjs").read_bytes()
    adapted = original.replace(b"/orion-pro-publisher-20261105/qualified-precode/runs/",
                               b"/orion-pro-publisher-20261105/product-campaign/runs/")
    assert (BASE / "publisher_http_server.mjs").read_bytes() == adapted
    for name, old, new in [("workflow_budget.py", b"'sql':1500", b"'sql':4000"),
                           ("publisher_workflow.py", b"actual_operational>1500", b"actual_operational>4000")]:
        archived = BASE / name.replace(".py", ".precode.py")
        original = archived.read_bytes()
        assert original.count(old) == 1
        assert (BASE / name).read_bytes() == original.replace(old, new)
    return {"qualifiedManifestSha256": expected, "qualifiedArtifacts": 101,
            "exactCopiedContractFiles": len(copies), "predecessors": workflow.preserved(), "unchanged": True}


def main():
    start = time.monotonic()
    deadline = start + 600
    deadline_epoch = time.time() + 600
    receipt = BASE / "campaign-supervision.json"
    assert not receipt.exists(), "This allocated campaign already has a supervisor receipt; no implicit PG retry"
    before = preservation()
    tempfile.tempdir = "/tmp"
    # All main and worker reservations consult this one epoch, initialized by
    # the supervisor before setup. It cannot be extended by starting a child.
    original_budget = workflow.SharedBudget

    class CampaignBudget(original_budget):
        def __init__(self, path, *, create=False):
            super().__init__(path, create=create)
            if create:
                data = self.read()
                data["deadlineEpoch"] = deadline_epoch
                self.path.write_text(json.dumps(data) + "\n")

    workflow.SharedBudget = CampaignBudget
    operations = []

    def bounded_run(args, **kwargs):
        assert kwargs.get("capture_output") and kwargs.get("text"), "Copied workflow must retain captured text subprocesses"
        assert not any(k in kwargs for k in ["shell", "input", "stdin", "stdout", "stderr"])
        cleanup = Path(str(args[0])).name == "pg_ctl" and "stop" in args
        operation_deadline = min(time.monotonic() + kwargs.get("timeout", 30),
                                 deadline + 20 if cleanup else deadline)
        observed = {"program": Path(str(args[0])).name, "cleanup": cleanup,
                    "remainingCampaignSeconds": round(deadline - time.monotonic(), 3)}
        operations.append(observed)
        try:
            result = run_bounded(args, deadline=operation_deadline, cwd=kwargs.get("cwd"), env=kwargs.get("env"),
                                 term_seconds=1, drain_seconds=1)
            observed.update(exitCode=result.returncode, status="completed")
        except ChildStopped as error:
            observed.update(status="stopped", reason=error.reason, pid=error.pid, returncode=error.returncode)
            raise
        if kwargs.get("check") and result.returncode:
            raise subprocess.CalledProcessError(result.returncode, args, result.stdout, result.stderr)
        return result

    workflow.subprocess.run = bounded_run
    report = {"kind": "OWNED_LOCAL_PRODUCT_CAMPAIGN_SUPERVISION", "startedAt": datetime.now(timezone.utc).isoformat(),
              "absoluteCampaignSeconds": 600, "freshChild600SecondBudgets": False,
              "operationalSqlAllocation": 4000, "priorAllocation": 1500,
              "priorAllocationStaticLowerBound": 1521,
              "subprocessSupervisor": "tests/orion_e2e_process.py", "supervisorSha256": file_sha(ROOT / "tests/orion_e2e_process.py"),
              "tempfileRoot": "/tmp", "preservationBefore": before, "subprocesses": operations,
              "oracleAndCaseExpectationsChanged": False, "remoteActions": []}
    receipt.write_text(json.dumps(report, indent=2) + "\n")
    code = 1
    try:
        code = int(workflow.main())
        return code
    finally:
        report.update(exitCode=code, elapsedSeconds=round(time.monotonic() - start, 3),
                      finishedAt=datetime.now(timezone.utc).isoformat(), preservationAfter=preservation())
        receipt.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
