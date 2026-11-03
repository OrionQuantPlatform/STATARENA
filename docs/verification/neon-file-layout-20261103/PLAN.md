# Restore the original data layout in Neon

User correction: archive parts do not preserve the directly browsable source structure. Replace our archive representation with one private object per original file, using its exact repository-relative key: data/raw/..., data/computed/..., data/sources/..., data/README.md, etc. Keep the existing statarena-data bucket; no extra buckets or public access.

Preserve the previously verified local archive parts and GitHub source snapshot 579b47107e0cd4fa4f9a12a5a95dd6a1be274ed9. Both full cloud representations together would exceed the 5 GB free limit. Replace incrementally: upload and verify every file in one archive part, then remove only that redundant cloud archive part. Remove remaining archive metadata after full object-set verification. Never delete original source files or unrelated objects.

Failure modes and E2E expectations, before implementation:

- Every original path becomes the exact object key; no generated filenames or archive prefixes remain in the final bucket.
- Validate source SHA-256 and length against the existing manifest before uploading. Invalid/missing/duplicate source records stop the run.
- Send Content-MD5 and check the server-returned ETag against the local MD5 for every single-part PUT. If ETags are opaque, download and compare SHA-256 instead. Independently download selected files from every part and verify SHA-256.
- Persist per-file progress in local SQLite so interrupted work can resume. Do not remove a cloud archive before all of its members pass upload integrity checks and download samples.
- Respect server throttling with bounded adaptive SDK retries; stop on persistent authentication/authorization failures.
- Before metadata cleanup, independently paginate the entire data/ object listing and compare every path, size and ETag against the complete manifest/progress database. No missing/extra objects permitted.
- After cleanup, bucket root must show only the original data/ structure, with exactly 250,748 source files and 2,692,640,453 bytes. All five GitHub workflows stay disabled.
- Keep credentials out of code/logs. Use one named, scoped migration credential and a mode-0600 local file; remove temporary credential material at completion.

The live first-part run is the preflight E2E, followed by the complete live migration and independent inventory verification. Save exact commands, expected and actual outcomes, logs, sample hashes and the final listing summary. No post-implementation unit tests.

Suggested commit: fix: preserve original data paths in Neon storage.
