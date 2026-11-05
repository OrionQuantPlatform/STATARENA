# Portable pinned Node24 E2E runtime

Suggested commit: `test: verify pinned Node24 archives across macOS and Linux`.

Before changing test setup, the required workflow is: inspect the actual Node platform/architecture/version, verify the retained official SHASUMS file itself, require the exact v24.22.2 archive hash for that platform, and compare the executed binary with the archive member bytes. Archive or binary drift must fail before PG starts. Only qualified darwin-arm64 and linux-x64 are accepted; no path aliasing between them. Existing exact numeric JSON.rawJSON checks and all route expectations remain unchanged.

The original appearance22 runner and all prior receipts/input snapshots remain immutable. The live original22 regression, corrective8 and alias16 runners may use the common portable verifier and archive its code/sum inputs. macOS is verified by actual owned PG/HTTP E2E; Linux remains unverified until the real GitHub job downloads and validates the official archive, then runs the same22/8/16 workflows. No unit test or production change is included.

Evidence must record archive/binary SHA, actual runtime, setup, command, route results, logs and cleanup. A Linux failure must be retained rather than represented by a macOS result.
