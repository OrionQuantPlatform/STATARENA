# Backend P1 : bounded reads and immutable publication

Status: implemented, verified locally and pushed on `codex/backend-p1-reads-publication`. GitHub ingestion CI is successful; its Vercel preview build is READY on a4ade8c17b. These receipts cover the code before this documentation-only update. P0 is already published. P1 has not changed production schemas, objects, workflows or the active materialization job. Numerical results and exact reruns: [ANALYSE.md](verification/backend-p1-20261103/ANALYSE.md).

## Match overview

`GET /api/matches/m_XXXXXX/summary` returns `{data:{version:1,state,match}}`. A current materialized summary is returned as its exact stored JSON bytes, using one SQL query. SHA-256 and size are verified before GET delivery. HEAD and strong/weak/list/wildcard validators use metadata only; a mismatched conditional request reads version-pinned bytes. If replacement races that read, the handler returns a pending fixture response without an obsolete ETag. Pending HEAD and wildcard requests use fixture existence rather than its body. Absent fixtures remain 404.

The normalized overview contains score/identity/status, the six overview statistic families, compact xG/goal shot points and up to five leaders. Detailed coordinates, all player rows, periods, networks, heatmaps and advanced payloads remain on their existing endpoints. `summaryVersion` tells the UI to fetch complete shots/player sections when selected. Unknown values stay unknown; zero is preserved.

`match_summaries.py` publishes exact bytea/size/SHA/source-digest rows from tables already loaded by `neon_materialize.py`. No extra archive download is needed per summary. Publication happens inside the existing manifest/partition SQL transaction, before the unchanged-partition early exit. Updates with identical bytes and source digest are skipped. Each response is capped at 256 KiB. A conservative SQL admission estimate keeps the existing 900 MB budget for summary-only backfills too.

Fixtures, resource/observation changes and shard-reference changes mark affected summaries/partitions dirty. The publisher snapshots dirty markers before reading sources and acknowledges only those exact markers. Later changes stay queued. Failed publication leaves the old committed manifest, missing/old summaries and pending work intact. A dirty summary is hidden rather than presented as current; the fixture-only fallback is no-store. Current ready summaries use 60 s CDN freshness +30 s SWR; collection/publication and client state are separate freshness layers.

## Fixture pages

`GET /api/fixtures` accepts `league` or comma-separated `leagues` (maximum 100), `season` or `seasons` (maximum 2), `status=all|played|upcoming`, `from`, `to`, `q`, `limit`, `cursor`.

- Default 50 rows, maximum 100; a 2 MiB representation ceiling is enforced. SQL selects list fields and nested identity fields, excluding arbitrary heavy fixture extensions.
- `played` selects finished; `upcoming` selects explicitly not_started. The old compatibility route keeps its previous semantics. Date arguments use valid nonzero Gregorian years; civil/split-year season labels stay intact.
- Sort is `(stored day NULLS LAST, case-sensitive id)` under the database collation, with cursor comparison using the same order. Null dates can span pages. Cursor schema 1 binds scope, limit, generation, date and ID. It is a public traversal position, not an authorization credential.
- One SQL statement reads generation and a bounded page from the same snapshot. Invalid parameters/cursors return 400; a changed generation returns 409 so the client restarts rather than mixing pages. Zero-row writes do not advance generation.
- Pages are initially no-store. This avoids replaying an obsolete cached first-page cursor after a 409. It trades shared-cache reuse for predictable publication/restart semantics; targeted CDN invalidation can be added separately after verification.

Existing full-season routes remain available for compatibility and exports. Full-season standings/cup consumers explicitly traverse 100-row pages, retry a generation restart once and retain legacy fallback for an older/unavailable service. They are not silently truncated to 50. For 123 fixtures this means two page requests instead of one full response. The weekly calendar already pages 40 rows from the shared in-memory research dataset; it keeps its existing Paris-day/kickoff ordering and filters. Adding another network list there would duplicate the bootstrap work. This lot does not claim to reduce all bootstrap data or the whole-navigation byte budget.

## Immutable storage

Migration002 adds nullable `objects.storage_key` and a physical-byte ledger. A null key retains the original `data/<logical path>` lookup. The new Store uploads and verifies final-byte-SHA keys `data/versions/<sha256>` before publishing SQL aliases. Existing legacy bytes are retained and recoverable; a changed logical alias never overwrites the previous physical bytes. New materialized public filenames hash the final encoded gzip bytes rather than a semantic/uncompressed digest. Semantic source digests remain available for unchanged-input detection.

Readers keep the metadata's physical key across alias changes. If its old inline body has disappeared, they can read the old immutable key with the original size/SHA checks. A legacy writer changing SHA without changing the storage pointer resets that pointer to null; it cannot leave a stale pointer behind. Missing-column compatibility is retried on subsequent uncached metadata requests, without a permanent pre-migration latch.

Ledger reservations use a separate autocommit connection because S3 writes survive SQL rollback. Failed/uncertain uploads and unreferenced successful uploads remain counted. Admission is serialized with a distinct transaction lock 97813004, preserving ingestion lock 97813003. Existing 4.75 GB object / 900 MB SQL limits apply before new uploads, including standalone materialization and verified-key/new-alias publication. Identical existing path/digest is a no-write operation. Ingestion capacity uses `storage_bytes()`, including legacy size growth overlapping an old ledger entry.

There is no GC, deletion or global purge. Retained versions consume more storage; failed reservations can overcount; historical unknown orphans predating the ledger still require inventory reconciliation. The extra ledger connection and SQL operations are publication costs, not runtime pool expansion. Reverting to P0 readers or catalog-only capacity after activation is unsafe.

## UX, DX and AX tradeoffs

| Decision | UX | DX / AX | Cost or limit |
| --- | --- | --- | --- |
| Materialized overview and lazy details | Overview loads fewer bytes; detailed tabs remain available | One versioned contract and inspectable ready/pending state | Backfill and freshness must be monitored |
| Generation-bound pages | Complete traversal restarts after publication | Stable cursor scope, explicit 409 recovery | Full-season consumers make more requests; pages initially bypass shared caching |
| Immutable keys and physical ledger | Earlier published content stays readable | Exact byte hashes, atomic aliases and reproducible rollback failures | More retained storage, publication SQL and one ingestion connection |

## Controlled activation

Do not merge/deploy the entire writer change as an undifferentiated release while an old job is active.

1. Publish the version-aware reader/API/frontend commit first. Its old-schema fallbacks preserve the existing service while new projections are unavailable. Verify its Vercel SHA and HTTP behavior.
2. Let the existing old ingestion/materialization owner finish. Use the existing GitHub concurrency group and SQL lock 97813003. Do not cancel/requeue it merely to activate this lot; check for already queued old-version runs too. Avoid DDL waiting behind its long transaction.
3. With the lease drained, apply idempotent migrations002 and003 using the existing ingestion/database migration role, then verify copied reader/writer privileges. Migration001 is only the fresh-database baseline. No PUBLIC grant is introduced. Keep a recorded schema receipt and verify the runtime role can read the new models.
4. Roll/recheck readers after migration, then publish/activate the writer/producer commit. Keep all physical versions. New writers fail early when the immutable schema is absent. They must not run ahead of compatible readers.
5. Backfill summaries from saved responses through the existing serialized materialization mechanism. Requeue published partitions only for an intentional initial backfill; resumptions do not requeue everything. No provider collection is required. Validate ready/pending coverage, queued work, storage/SQL budgets and representative p50/p95/source bytes after activation.
6. Rollback retains version-aware readers and ledger-aware capacity. A P0-reader rollback needs explicit restoration of compatible legacy object paths; changing code alone is insufficient once new cold objects exist.

At the read-only checkpoint for this delivery, run 41723613754 was still in progress on 58acaf1428. P1 activation/backfill is deliberately not claimed. The local tests prove contracts and controlled failures, not real-world Vercel savings.

Suggested commits: `feat: serve bounded match summaries and paginated fixtures`; `feat: publish match overviews through immutable storage`; `test: preserve P1 workflow evidence and quantified results`.
