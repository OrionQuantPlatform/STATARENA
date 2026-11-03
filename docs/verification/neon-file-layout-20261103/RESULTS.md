# Original Neon file layout — verified

The user corrected the archive-only migration. The private bucket now holds one object for every original repository-relative data/ path. Our generated snapshot archive objects and metadata have been removed.

## Actual result

Destination: Orion / Orion Tech Sport, project sweet-queen-11955006, production branch br-mute-bonus-be23014e, private bucket statarena-data. Source commit: 579b47107e0cd4fa4f9a12a5a95dd6a1be274ed9.

```text
statarena-data/
└── data/
    ├── README.md
    ├── computed/
    ├── raw/
    └── sources/
```

| Original path | Files | Bytes |
| --- | ---: | ---: |
| data/README.md | 1 | 1,228 |
| data/computed/ | 200 | 127,800,808 |
| data/raw/ | 245,215 | 1,438,727,276 |
| data/sources/ | 5,332 | 1,126,111,141 |
| **Total** | **250,748** | **2,692,640,453** |

No generated snapshots/ objects remain. Original compressed files that already existed inside data/ were preserved as original files. The final whole-bucket listing contains exactly the original source file set and only the top-level data/ prefix. No extra buckets, public access, database changes or app read-path changes were introduced. GitHub/local source copies remain intact. All five StatArena workflows remain disabled, with no active runs.

## E2E evidence actually executed

- Source bodies were checked against the previously Git-verified per-file SHA-256 manifest before PUT.
- Every one of the 250,748 PUTs supplied Content-MD5 and received the matching server MD5 ETag. No opaque-ETag fallback was needed (`cleanup.json`).
- Downloaded 63 selected files across all 21 source parts and checked exact sizes and SHA-256 hashes (`VERIFIED.json`). This is sampled read-back; exhaustive remote verification used the server checksums and full inventory.
- Independently paginated the entire bucket and compared every path, size and ETag with the complete source/progress database. All 250,748 keys and the byte total matched (`bucket-verification.log`, `VERIFIED.json`).
- First-part live preflight passed for 331 files, including three independent downloads (`preflight.log`, `preflight.json`).
- Interrupted/resumed the earlier worker configurations while adjusting transfer parallelism. Completed members were reused from SQLite; the final run resumed without losing data. Archive parts were removed only after all their members and download samples passed verification, keeping cloud storage below the 5 GB free allowance.
- A grouped folder listing returned HTTP 504, and an intermediate audit encountered EndpointConnectionError. The final implementation avoids the grouped listing and completed a flat full-bucket audit without reuploading data. Failed/interrupted logs are retained; they are not represented as passed runs. Browser UI rendering was not tested.
- The named temporary scoped storage credential was revoked and its local mode-0600 file deleted. Credentials were never written into Git/logs. Credential creation/revocation used the connected Neon tools.

Failure modes and expected outcomes were recorded before implementation in PLAN.md. No unit tests were written. The final live E2E completed successfully; unrelated negative branches were not deliberately exercised and are not claimed tested.

## Reproduction and setup

Use Python 3 and the pinned SDK dependencies in requirements.txt. The complete local source archives/manifest came from the earlier Git-verified migration; reproduce them from the immutable Git snapshot with the pack command documented in ../neon-data-migration-20261103/RESULTS.md. Use a new empty output directory when repacking. The old cloud archive objects are intentionally no longer present.

Create a named branch-scoped Neon credential with storage:read and storage:write for the initial migration. Save only accessKeyId (token_id), secretAccessKey (s3_secret_access_key), endpoint and region in a mode-0600 JSON file outside Git. Never print the values. The endpoint is the production branch's S3 endpoint; use path-style SigV4. Revoke the migration credential when finished.

Exact preflight and final commands executed from the repository root:

```sh
python3 -m venv /tmp/statarena-neon-layout-venv
/tmp/statarena-neon-layout-venv/bin/python -m pip install -r docs/verification/neon-file-layout-20261103/requirements.txt
/tmp/statarena-neon-layout-venv/bin/python dashboard/scripts/restore_neon_file_layout.py --archives /tmp/statarena-neon-data-579b4710 --credential-file /tmp/statarena-neon-layout-credential.json --state /tmp/statarena-neon-file-layout --workers 32 --stop-after-parts 1 > docs/verification/neon-file-layout-20261103/preflight.log 2>&1
/tmp/statarena-neon-layout-venv/bin/python dashboard/scripts/restore_neon_file_layout.py --archives /tmp/statarena-neon-data-579b4710 --credential-file /tmp/statarena-neon-layout-credential.json --state /tmp/statarena-neon-file-layout --workers 32 --processes 8 > docs/verification/neon-file-layout-20261103/migration-parallel.log 2>&1
/tmp/statarena-neon-layout-venv/bin/python dashboard/scripts/restore_neon_file_layout.py --archives /tmp/statarena-neon-data-579b4710 --credential-file /tmp/statarena-neon-layout-credential.json --state /tmp/statarena-neon-file-layout --workers 32 --processes 8 > docs/verification/neon-file-layout-20261103/bucket-verification.log 2>&1
```

Resume uses the same local SQLite state; do not start overlapping uploaders. Completed parts are skipped. A final audit with completed state performs reads and removes only our exact known redundant metadata if still present. The supplied credential file has been deleted and must be regenerated for a rerun; no secret is embedded in these commands.

Suggested commit: fix: preserve original data paths in Neon storage.
