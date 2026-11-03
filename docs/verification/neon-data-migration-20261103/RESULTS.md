# StatArena data transfer to Neon — completed

## Outcome

- All five StatArena GitHub workflows are disabled (`workflows.json`). Both active runs were cancelled; a final scan of the latest 100 runs found zero non-completed runs (`runs.json`).
- Copied every tracked data/ file from published commit `579b47107e0cd4fa4f9a12a5a95dd6a1be274ed9`: **250,748 files, 2,692,640,453 original bytes**.
- Destination: **Orion → Orion Tech Sport → production → Object Storage → statarena-data** (private).
- Project `sweet-queen-11955006`; branch `br-mute-bonus-be23014e`; AWS Ohio (`us-east-2`).
- Object prefix: `snapshots/579b47107e0cd4fa4f9a12a5a95dd6a1be274ed9/`.
- Stored **25 objects, 2,691,390,896 bytes**: 21 gzip tar parts, compressed per-file manifest, README, snapshot inventory and verification receipt. This is within the 5 GB free Object Storage allowance.

## Verification actually executed

1. Compared every source archive file with the pinned Git tree: exact path coverage, file count and Git blob hash. No missing, extra or duplicate files; all source entries were regular files.
2. Reopened all 21 local archive parts. Checked original path, archive assignment, byte length, SHA-256 and Git blob hash for all 250,748 files.
3. Uploaded every archive/manifest/README/snapshot object using Neon-presigned URLs, then downloaded each object and verified its exact length and SHA-256. Uploaded and downloaded the final verification receipt as well.
4. Independently listed the private Neon prefix through the connector. Its complete key/size map exactly matched all 25 expected objects (`neon-object-list.json`).
5. Rechecked GitHub: five disabled workflows and zero active/queued runs. Deleted the temporary mode-0600 signed-URL file; no reusable storage credential was created or committed.

Actual positive-path E2E completed successfully. Evidence: `pack.log`, `transfer.log`, `snapshot.json`, `VERIFIED.json`, `neon-object-list.json`, `workflows.json`, `runs.json`. Negative transport/authentication/failure branches were not deliberately induced and are not claimed tested. Failure modes and expected outcomes were recorded before implementation in `PLAN.md`.

## Setup, inputs and exact commands

Requirements: Python 3, Git, network access to GitHub and access to this Neon project through the connected plugin. No PitchAPI requests or credentials are used. Snapshot source and full expected tree are pinned, rather than following a changing branch.

Commands executed from the repository root:

```sh
git ls-tree -r -z 579b47107e0cd4fa4f9a12a5a95dd6a1be274ed9 data > /tmp/statarena-neon-source-tree.bin
python3 dashboard/scripts/migrate_data_to_neon.py pack --output /tmp/statarena-neon-data-579b4710 --snapshot 579b47107e0cd4fa4f9a12a5a95dd6a1be274ed9 --tree /tmp/statarena-neon-source-tree.bin --source-url https://codeload.github.com/OrionQuantPlatform/STATARENA/tar.gz/579b47107e0cd4fa4f9a12a5a95dd6a1be274ed9 --part-mib 128 > docs/verification/neon-data-migration-20261103/pack.log 2>&1
python3 dashboard/scripts/migrate_data_to_neon.py objects --output /tmp/statarena-neon-data-579b4710
python3 dashboard/scripts/migrate_data_to_neon.py transfer --output /tmp/statarena-neon-data-579b4710 --urls /tmp/statarena-neon-transfer-urls.json --workers 3 > docs/verification/neon-data-migration-20261103/transfer.log 2>&1
```

The transfer URL file was generated through `presign_storage_object` for each object under the prefix, with separate upload/download operations and a 3,600-second expiry. The file maps local filenames to `{upload:{url,headers},download:{url,headers}}`; upload content type comes from the object inventory. Include VERIFIED.json. To rerun, regenerate fresh URLs in a mode-0600 file outside Git. Do not print or commit signed URLs. Repack into a new empty output directory if the existing snapshot has already been created; `pack` refuses to overwrite a completed snapshot.

## Access and restoration

Open the private bucket above and download README.md, snapshot.json and manifest.jsonl.gz. The manifest maps every original data/ path to its archive part and both content hashes. Download the part(s), verify their SHA-256 against snapshot.json, and extract into an empty directory with `tar -xzf part-NNNN.tar.gz`. Original data/ paths are retained. The connected Neon tool can generate authorized temporary download URLs.

## Scope and tradeoffs

This transfers the complete **published snapshot** into Object Storage. Archives provide efficient transfer and a verifiable recovery copy; accessing one original file requires extracting its manifest-selected part. The existing app read paths, Postgres schema, GitHub data files, local source files and unrelated UI changes were preserved. No SQL-table import, app storage cutover or source deletion was performed. Work downloaded on a cancelled runner but never pushed is not claimed recovered. Local untracked/iCloud duplicate copies remain preserved in place and are outside the authoritative published snapshot.

Suggested commits: `feat: add verified Neon data archive migration`; `docs: record completed Neon transfer and stopped workflows`.
