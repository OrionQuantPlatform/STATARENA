# StatArena → Neon data migration

User direction: stop every StatArena GitHub Action immediately, then move all collected data into Neon. Target: Orion / Orion Tech Sport, project sweet-queen-11955006, production branch br-mute-bonus-be23014e, private bucket statarena-data. All five workflows are disabled and both formerly active runs are cancelled.

Authoritative source: every tracked file under data/ in the final published GitHub snapshot 579b47107e0cd4fa4f9a12a5a95dd6a1be274ed9. Keep GitHub and local source copies intact. Cancellation can discard runner work not pushed to GitHub; do not claim unpublished runner files were recovered. Unrelated local UI work and duplicate/iCloud copies are preserved in place.

Storage format: immutable gzip tar parts, a per-file manifest mapping original paths to parts and SHA-256/Git blob hashes, and a snapshot receipt. Packing avoids hundreds of thousands of individual S3 requests. Tradeoff: individual archived files must be extracted from their part before use; this delivery is a complete raw-data snapshot, not a SQL import or an app read-path cutover.

Expected E2E outcomes and failure handling, recorded before implementation:

- GitHub workflows remain disabled; no queued/running StatArena jobs remain.
- Pin source commit; compare the source archive's complete file set and each Git blob hash against git ls-tree. Missing/extra/duplicate paths, unsafe paths, unsupported modes or content mismatches abort packaging.
- Preserve every file byte and original data/ path, including empty and binary files. Reopen all output parts and compare every file's SHA-256/length against the manifest before upload.
- Sum stored object bytes before upload and abort above the 5 GB free object-storage allowance. Keep at least 3 GiB local free while packing. Existing bucket objects must not be overwritten accidentally.
- Use purpose-built Neon presigned PUT/GET URLs, without creating or printing reusable credentials. Keep temporary URL material outside Git with mode 0600; delete after verification.
- Upload each object, download it again, and compare byte length and SHA-256. Retry transient transport/5xx/429 failures with backoff; do not retry authorization failures blindly. No success receipt until every source file and every remote object verifies.
- Persist the exact rerun commands, snapshot/file/object counts, storage totals, runtime logs and verification receipt. Report any omitted source or unresolved failure accurately.

Suggested commit: feat: archive StatArena data in Neon with verified manifests.
