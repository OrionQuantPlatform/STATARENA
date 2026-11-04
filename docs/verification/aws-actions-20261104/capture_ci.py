"""Replay an existing HTTP suite on checked-in inputs and keep only this run's evidence."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SUITES = {
    "match": ("relational-match-20261104", "after"),
    "support": ("aws-support-20261104", "green"),
    "catalog": ("aws-catalog-20261104", "after"),
}
name = sys.argv[1]
folder, phase = SUITES[name]
out = Path(os.environ.get("STATARENA_CI_EVIDENCE", HERE / "local-replay")).resolve() / name
out.mkdir(parents=True, exist_ok=True)
report = out / "results.json"
report.unlink(missing_ok=True)
started = time.monotonic()
command = ["bun", f"docs/verification/{folder}/verify.mjs", phase]
with tempfile.TemporaryDirectory(prefix="statarena-http-ci-") as scratch:
    work = Path(scratch)
    (work / "dashboard").symlink_to(ROOT / "dashboard", target_is_directory=True)
    (work / "tests").symlink_to(ROOT / "tests", target_is_directory=True)
    fixtures = work / "docs/verification"
    suite = fixtures / folder
    shutil.copytree(ROOT / "docs/verification" / folder, suite)
    (fixtures / "aws-frontend-20261104").symlink_to(
        ROOT / "docs/verification/aws-frontend-20261104", target_is_directory=True
    )
    fresh = suite / f"{phase}.json"
    fresh.unlink(missing_ok=True)
    env = {k: os.environ[k] for k in ("PATH", "HOME", "LANG", "PYTHONPATH", "STATARENA_TEST_TOOLS") if k in os.environ}
    env.update(STATARENA_TEST_DATABASE="1", STATARENA_VERIFY_ROOT=str(ROOT), AWS_EC2_METADATA_DISABLED="true", PYTHONDONTWRITEBYTECODE="1")
    with (out / "workflow.log").open("w") as log:
        result = subprocess.run(command, cwd=work, env=env, stdout=log, stderr=subprocess.STDOUT)
    if fresh.is_file():
        shutil.copyfile(fresh, report)
    code = result.returncode or int(not report.exists())
receipt = {
    "rerun": f"python3 docs/verification/aws-actions-20261104/capture_ci.py {name}",
    "suite_command": command,
    "setup": "Frozen dashboard dependencies; Bun 1.4.4, embedded PostgreSQL 18.6, Python worker dependencies and checked-in captured inputs.",
    "exit_code": code,
    "elapsed_seconds": round(time.monotonic() - started, 2),
    "fresh_report": report.exists(),
}
(out / "run.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt))
if code:
    print((out / "workflow.log").read_text(errors="replace")[-3500:])
sys.exit(code)
