"""Package completed local traces without changing their original bytes."""
import datetime as dt
import hashlib
import json
from pathlib import Path
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
UI = HERE.parent / "orion-pro-ui-20261104"
archives = HERE / "traces"
archives.mkdir(exist_ok=True)
records = []
for directory in sorted((UI / "output/playwright").iterdir()):
    trace = directory / "traces"
    receipt = UI / "runs" / directory.name / "result.json"
    if not trace.is_dir() or not receipt.is_file():
        continue
    result = json.loads(receipt.read_text())
    if not result.get("finishedAt"):
        continue
    files = sorted(p for p in trace.rglob("*") if p.is_file())
    manifest = [{"path": p.relative_to(trace).as_posix(), "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "bytes": p.stat().st_size} for p in files]
    archive = archives / (directory.name + ".zip")
    if not archive.exists():
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as packed:
            for path in files:
                packed.write(path, path.relative_to(trace).as_posix())
            packed.writestr("SOURCE_MANIFEST.json", json.dumps(manifest, indent=2) + "\n")
    with zipfile.ZipFile(archive) as packed:
        assert json.loads(packed.read("SOURCE_MANIFEST.json")) == manifest
        assert packed.testzip() is None
        for entry in manifest:
            assert hashlib.sha256(packed.read(entry["path"])).hexdigest() == entry["sha256"]
    records.append({
        "run": directory.name,
        "originalTraceDirectory": trace.relative_to(ROOT).as_posix(),
        "archive": archive.relative_to(ROOT).as_posix(),
        "archiveSha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "receiptSha256": hashlib.sha256(receipt.read_bytes()).hexdigest(),
        "files": len(files), "originalBytes": sum(p.stat().st_size for p in files),
        "archiveBytes": archive.stat().st_size, "allEntryHashesVerified": True,
    })
report = {
    "atUtc": dt.datetime.now(dt.timezone.utc).isoformat(),
    "command": "python3 docs/verification/orion-pro-react-integration-20261104/package_traces.py",
    "purpose": "Public self-contained ZIP copies avoid committing expanded development bundles repeatedly. Original traces/receipts remain unchanged locally; screenshots, DOM, network, SQL and relevant source snapshots remain separately inspectable.",
    "expected": "Each completed trace is packaged losslessly with exact entry hashes; no application or original diagnostic byte changes.",
    "actual": records,
    "originalBytes": sum(r["originalBytes"] for r in records),
    "archiveBytes": sum(r["archiveBytes"] for r in records),
    "limits": "Evidence packaging only; no application/network/storage performance gain inferred. Unzip an archive to inspect its original Playwright trace and resources.",
    "suggestedCommit": "feat: integrate frozen SQL match pages in React",
}
(HERE / "TRACE_ARCHIVES.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({"archives": len(records), "originalBytes": report["originalBytes"], "archiveBytes": report["archiveBytes"]}))
