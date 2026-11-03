# Neon runtime migration — acceptance plan (before implementation)

## Setup and constraints
- Source snapshot 579b47107e0cd4fa4f9a12a5a95dd6a1be274ed9, 250,748 verified original objects / 2,692,640,453 bytes, private statarena-data bucket.
- Preserve existing routes, compressed packed tables, archives, attribution, UI edits and unavailable-data semantics. Runtime has no Pitch credential or local data directory.
- Test additive SQL on a separate Neon branch. Runtime uses pooled read-only SQL and branch-scoped read-only S3 credentials. Ingestion uses separate write credentials in GitHub Actions.

## Failure modes and expected outcomes
1. Missing configuration, unavailable Neon or missing resource: explicit 503/404, no provider/GitHub/disk fallback and no leaked secret.
2. Path traversal, unsupported parameters/methods: rejected; no arbitrary object or external URL fetch.
3. Existing gzip files, archive references and profiles: bytes/hash and response contracts match the verified source. All catalog entries match the backup inventory.
4. Concurrent requests: bounded pool/cache and one in-flight load per key; revision changes invalidate mutable cache. HTTP HEAD/ETag/304 preserve byte semantics.
5. Daily refresh and historical retries: durable unique endpoint/parameter key, idempotent upsert, no duplicate records or objects on identical retry; 403/404 recorded and skipped, 401 fails the run, 429/5xx bounded retry. Interrupted leases resume.
6. New successful observations appear in API routes and derived dashboard files without a data commit. Supplemental endpoints and display images read Neon, never fetch their original providers during a page request.
7. All pages and features: browser navigation with request/error evidence, no Pitch/GitHub data calls; preserve available match/player/team/cup/standings/stadium functionality. Record unavailable sources honestly.
8. Performance: cold/warm API timing, SQL EXPLAIN ANALYZE for point lookups and queue claims, measured database size below Free limit. Optimize observed slow paths.
9. Production: correct Vercel project/commit/env, deployed health and representative pages, exactly two workflows after successful validation.
10. Cleanup: compare canonical local file hashes to backed-up objects; save small receipts, remove only verified redundant migration artifacts/data; preserve unique local work and history.

## Evidence requirements
Each E2E result records setup/inputs, exact rerun command, expected and observed outcomes, timings and relevant machine-readable logs. Unexecuted checks remain unverified. No post-implementation unit tests.

Suggested commit: feat: centralize StatArena runtime and ingestion on Neon.
