"""Owned source export from Git's tracked inventory and explicit test inputs only."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess

PRODUCT_PREFIXES = ("dashboard/frontend/", "dashboard/shared/", "dashboard/backend/")
PRODUCT_METADATA = {"dashboard/package.json", "dashboard/bun.lock"}
PRO_MODULES = {
    "dashboard/frontend/src/hooks/useProResource.js",
    "dashboard/frontend/src/services/pro-football-client.js",
    "dashboard/frontend/src/views/ProMatchesPage.jsx",
}
UI = "docs/verification/orion-pro-ui-20261104/"
HARNESS_INPUTS = {"tests/orion_pro_ui_local.py"} | {
    UI + name for name in ("PROTOCOL.md", "MOBILE_TAB_PROTOCOL.md", "ui_fixture.py", "workflow.py", "source_export.py",
                          "browser_setup.js", "browser_initial.js", "browser_state.js", "browser_tab_geometry.js")
}
TRACKED_SUPPORT = {
    "docs/architecture/orion-plan-20261104/target-schema.proposed.json",
    "docs/verification/orion-pro-readers-20261104/fixture.py",
    "docs/verification/orion-pro-readers-20261104/http_server.mjs",
    "docs/verification/orion-pro-pilot-20261104/harness.py",
    "docs/verification/orion-pro-pilot-20261104/fixtures.py",
    "dashboard/scripts/orion_pro_schema.py",
    "dashboard/scripts/orion_pro_migrate.py",
    "dashboard/scripts/orion_pro_integrity.py",
}
SDK_INPUTS = {
    f"dashboard/node_modules/@vercel/{package}/{name}"
    for package in ("analytics", "speed-insights") for name in ("package.json", "dist/next/index.mjs")
}


def excluded(name):
    parts = PurePosixPath(name).parts
    return any(part in (".git", "node_modules", ".next", ".next-dev", "__pycache__") or part.startswith(".env") for part in parts)


def prepare(root, runtime, inputs, env):
    command = ["git", "-C", str(root), "ls-files", "-z"]
    inventory = subprocess.run(command, env=env, check=True, capture_output=True, timeout=15)
    tracked = {os.fsdecode(name) for name in inventory.stdout.split(b"\0") if name}
    product = {name for name in tracked if (name.startswith(PRODUCT_PREFIXES) or name in PRODUCT_METADATA) and not excluded(name)} | PRO_MODULES
    missing_tracked = TRACKED_SUPPORT - tracked
    if missing_tracked:
        raise RuntimeError("Required shared support is not tracked: " + ", ".join(sorted(missing_tracked)))
    source_names = product | TRACKED_SUPPORT | HARNESS_INPUTS
    if any(excluded(name) for name in source_names):
        raise RuntimeError("Excluded source entered the explicit export")
    source_hashes, runtime_hashes = {}, {}
    for name in sorted(source_names | SDK_INPUTS):
        relative = PurePosixPath(name)
        if relative.is_absolute() or ".." in relative.parts or "\\" in name:
            raise RuntimeError("Invalid tracked source path")
        source = root / name
        if not source.is_file() or source.is_symlink():
            raise RuntimeError("Required export file absent or a source symlink: " + name)
        body = source.read_bytes()
        digest = hashlib.sha256(body).hexdigest()
        target = inputs / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
        source_hashes[name] = digest
        if name not in SDK_INPUTS:
            target = runtime / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
            runtime_hashes[name] = digest
    def owned_inventory(directory):
        return {str((Path(current) / name).relative_to(directory)) for current, _, files in os.walk(directory, followlinks=False) for name in files}
    if owned_inventory(runtime) != source_names or owned_inventory(inputs) != source_names | SDK_INPUTS:
        raise RuntimeError("Owned source export inventory differs from explicit allowlist")
    # All source bytes are written from the same read; dependencies are explicit
    # external tool/package inputs and never cause a source-tree directory copy.
    if any(hashlib.sha256((runtime / name).read_bytes()).hexdigest() != digest for name, digest in runtime_hashes.items()):
        raise RuntimeError("Owned runtime differs from pinned source bytes")
    manifest = {
        "kind": "tracked_source_plus_explicit_pro_modules_v1", "inventoryCommand": command,
        "trackedProductPaths": sorted(product & tracked), "explicitProModulePaths": sorted(PRO_MODULES),
        "explicitUntrackedProModulePaths": sorted(PRO_MODULES - tracked),
        "ownedHarnessInputs": sorted(HARNESS_INPUTS), "trackedSupportInputs": sorted(TRACKED_SUPPORT),
        "explicitSdkInputs": sorted(SDK_INPUTS),
        "excludedTrackedPaths": sorted(name for name in tracked if (name.startswith(PRODUCT_PREFIXES) or name in PRODUCT_METADATA) and excluded(name)),
        "policy": "No other untracked product file or dotenv is read/exported; no recursive source copy; exact local dependencies are recorded separately",
        "runtimeSourceSha256": runtime_hashes, "inputSourceSha256": source_hashes,
        "runtimeInventoryExact": True, "inputInventoryExact": True,
        "cleanCloneComparableSource": True, "freshDependencyInstallClaimed": False,
    }
    return manifest
