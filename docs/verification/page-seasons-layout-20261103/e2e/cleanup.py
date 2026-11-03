"""Reproducible filesystem E2E for the reviewed, recoverable copy cleanup."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import subprocess
import tarfile
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument("--apply", action="store_true")
parser.add_argument("--root", type=Path, default=Path.cwd())
args = parser.parse_args()
root = args.root.resolve()
folder = Path(__file__).resolve().parent
plan = json.loads((folder / "delete-plan.json").read_text())
report = {
    "setup": "Reviewed versioned copies, resident canonical files, no active references; excludes Git internals and dependencies.",
    "command": "python3 output/playwright/page-seasons-layout-20261103/cleanup.py" + (" --apply" if args.apply else ""),
    "expected": "Archive and hash-check all present reviewed copies before removal; canonical files unchanged; all reviewed copies absent after apply.",
    "git_recovery_commit": plan["git_recovery_commit"],
    "phase": "apply" if args.apply else "audit",
    "status": "failed",
    "files": [],
}

def location(name):
    path = root / name
    if not path.resolve().is_relative_to(root) or path.is_symlink():
        raise RuntimeError("Unsafe path: " + name)
    return path

def sha(path):
    if getattr(path.stat(), "st_flags", 0) & 0x40000000:
        raise RuntimeError("iCloud-only file left untouched: " + str(path))
    return hashlib.sha256(path.read_bytes()).hexdigest()

try:
    before = {}
    present = []
    names = {row["copy"] for row in plan["files"]}
    for row in plan["files"]:
        copy, original = location(row["copy"]), location(row["original"])
        before[row["original"]] = sha(original)
        if not copy.exists():
            continue
        if sha(copy) != row["sha256"]:
            raise RuntimeError("Changed candidate: " + row["copy"])
        if not row.get("archive_only"):
            old = subprocess.check_output(["git", "show", plan["git_recovery_commit"] + ":" + row["copy"]], cwd=root)
            if hashlib.sha256(old).hexdigest() != row["sha256"]:
                raise RuntimeError("Git recovery mismatch: " + row["copy"])
        if row["kind"].startswith("identical") and row["sha256"] != before[row["original"]]:
            raise RuntimeError("Canonical file no longer matches identical copy: " + row["copy"])
        present.append(row)
    active = {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".html", ".css", ".json", ".yml", ".yaml", ".toml", ".py", ".sh"}
    files = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=root).decode().split("\0")
    for name in files:
        path = root / name
        if not name or name in names or path.suffix not in active or name.startswith(("docs/", "dashboard/outputs/", "output/")) or not path.is_file():
            continue
        text = path.read_text(errors="replace")
        for row in present:
            if Path(row["copy"]).name in text:
                raise RuntimeError("Active reference in " + name + ": " + row["copy"])
    report["reviewed"] = len(plan["files"])
    report["present_before"] = len(present)
    if args.apply and present:
        backup = Path(tempfile.mkdtemp(prefix="statarena-duplicate-cleanup-20261103-"))
        archive = backup / "copies.tar.gz"
        (backup / "delete-plan.json").write_text(json.dumps(plan, indent=2) + "\n")
        with tarfile.open(archive, "w:gz") as handle:
            for row in present:
                handle.add(location(row["copy"]), arcname=row["copy"], recursive=False)
        with tarfile.open(archive, "r:gz") as handle:
            for row in present:
                if hashlib.sha256(handle.extractfile(row["copy"]).read()).hexdigest() != row["sha256"]:
                    raise RuntimeError("Archive mismatch: " + row["copy"])
        report["archive"] = str(archive)
        report["archive_sha256"] = sha(archive)
        report["archive_members_verified"] = len(present)
        for row in present:
            copy = location(row["copy"])
            if sha(copy) != row["sha256"]:
                raise RuntimeError("Candidate changed after backup: " + row["copy"])
            copy.unlink()
            report["files"].append({**row, "removed": True})
    after = {name: sha(location(name)) for name in before}
    if before != after:
        raise RuntimeError("A canonical file changed during cleanup")
    report["canonical_hashes_unchanged"] = after
    report["remaining"] = [row["copy"] for row in plan["files"] if location(row["copy"]).exists()]
    if args.apply and report["remaining"]:
        raise RuntimeError("Reviewed copies remain")
    report["status"] = "passed" if args.apply else "ready"
except Exception as error:
    report["error"] = str(error)
finally:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = folder / ("cleanup-" + report["phase"] + "-" + stamp + ".json")
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"report": str(output), "status": report["status"], "reviewed": report.get("reviewed"), "removed": len(report["files"]), "remaining": len(report.get("remaining", [])), "error": report.get("error")}))
if report["status"] == "failed":
    raise SystemExit(1)
