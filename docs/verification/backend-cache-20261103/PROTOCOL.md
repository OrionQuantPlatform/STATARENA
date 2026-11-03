# Backend/cache P0 verification protocol

Written before application changes, 2026-11-03. Source audit: pages 4, 6, 7, 10-12 of `StatArena_Audit_Backend_Cache_Vercel.pdf`. Baseline: bb7812bd1e.

## Setup and exact rerun

From the repository root, with existing dashboard dependencies and Bun installed:

```sh
mkdir -p /tmp/statarena-cache-test-tools
bun add --cwd /tmp/statarena-cache-test-tools embedded-postgres@18.6.0-beta.19
STATARENA_TEST_TOOLS=/tmp/statarena-cache-test-tools STATARENA_TEST_EVIDENCE=docs/verification/backend-cache-20261103/after bun dashboard/scripts/verify_backend_cache.mjs
```

The runner creates a disposable local PostgreSQL 18 cluster, self-signed TLS certificate trusted only by this test connection, the actual runtime schema and deterministic fixture data. It starts the real Bun handler over HTTP and the real AWS S3 SDK against a local HTTP object fixture. It never uses production credentials or mutates Neon. Exact binary/platform versions, inputs, results, SQL/application logs and rerun command are saved even on failure. Network timings describe this local fixture only.

Only the fixture server has clock-advance and telemetry controls. Advancing its clock by 31 seconds expires actual 30-second caches without a wall-clock sleep. Retained-content TTL stays 15 minutes. Cache admission is also exercised through a fixture-only HTTP route with a 1 KiB budget, allowing oversized/failing/concurrent loaders to be tested without allocating 64+ MiB. This is a narrow cache harness, not a deployed product route or a claim about whole-process memory.

## Failure modes and expected outcomes

1. **Metadata/body separation:** cold inline GET reads identical bytes; its extra SQL round trip is recorded. Refresh metadata after 31 seconds while parsed/body entries remain warm: zero SQL body bytes and zero S3 bytes. Cold S3 GET requires one metadata query and one object request, without probing SQL for a known S3 body.
2. **Validators:** strong, weak, comma-separated tags and standalone wildcard yield 304 for an existing object; absent objects stay 404. Mismatches yield exact bytes and the current ETag. After metadata expiry, unchanged validators trigger no body load, gzip or parse. HEAD returns correct ETag/known size, zero bytes and no body read.
3. **Integrity and races:** bad size/hash yields a retryable 503, never bytes under an old ETag. A completed inline update between HEAD and GET must return current bytes/ETag immediately after at most one fresh-metadata retry. Repeated changes during both attempts end in 503 after four SQL queries. Exercise the parsed JSON path too. A failed load must not poison the cache; the next valid load succeeds. Failed S3 operations retain duration/error telemetry.
4. **Status/HEAD contracts:** archive/profile/compatibility GET and HEAD preserve existing envelope/status and fallback ordering. Include saved 404/403/429/5xx, absent profiles, broken references, archive fallback, empty and populated fixtures, `/leagues` fallback, projection presence/absence, settings/health/status, validation and method errors. HEAD has no payload, and never invents a dynamic size or validator. Referenced archive HEAD may still read/parse until projections exist; measure and report this limitation.
5. **Cache policy:** declarations yield CDN TTL 900 (leagues), 3600 (identity), 180/120 (fixture lists), 300 (details), 60 (lineups), with bounded SWR only in CDN headers. Browser TTL remains zero for mutable endpoints without browser SWR. All non-success/error/health/settings/status responses use no-store. Asset aliases remain mutable even when their internal path contains a hash; rebinding the mapping changes the image after lookup expiry. Exposed versioned paths retain immutable caching. Manifest aliases remain bounded. Remove the saved league resource to exercise valid, malformed and missing manifest fallback.
6. **LRU/coalescing:** small A/B entries survive inadmissibly large C, C is retried rather than retained, concurrent loads for one key coalesce, expiration reloads, failed loads retry, cache bytes/evictions/rejections are counted separately.
7. **Concurrency and observability:** isolated request contexts at 1/5/20 concurrent reads; source bytes and cache events are attributable, SQL pool wait is measured separately from execution, and sample-rate zero emits no sampled request log. Labels contain no entity IDs, raw parameters, URLs, credentials or payloads. Byte estimates are labeled; they are not provider wire-egress measurements.

## Acceptance and limits

Require unchanged successful response digests/statuses, preserved failures and unavailable values, no additional source body bytes on the specified warm/304/HEAD paths, and intact integrity checks. Report cold-path extra queries explicitly. No local test establishes Vercel HIT/MISS, global freshness, real users' p95 or production egress. No new unit tests will be written after implementation. P1 summaries/pagination, immutable publication, shared caches and production invalidation remain separate deliveries.

Suggested commit: `test: capture backend cache HTTP failure modes and baseline`.
