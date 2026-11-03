# P1 contract and verification, before implementation

User scope: preserve Neon + Vercel, publish/verify P0, then deliver match summaries, pagination and immutable publication. P0 code5510ca4bee/evidence6bea1b950a is deployed and its 50 public checks pass. Every lot needs a numerical before/after analysis, including adverse changes and unavailable measurements.

## Bounded read contracts

- Add `GET/HEAD /api/matches/:id/summary`: serialized, SHA-verified precomputed normalized match overview, selected leader rows, goal/highlight data and explicit coverage. Ordinary current-summary GET takes one SQL query; HEAD or matching validators transfer no body, parse no JSON and read no archive/object. Keep exact representation ETag/size. An absent or dirty projection gets a lightweight fixture-only response, explicitly marked pending, or 404 for an absent fixture. No on-demand archive reconstruction for summaries.
- Publish summaries from already loaded materialization tables inside the existing SQL transaction. Dirty-source triggers hide outdated summaries, including old-writer updates; failed refreshes keep work queued. Existing normalized matches/appearances/shot statistics and archive precedence must survive. Avoid inventing missing values or claiming complete detail availability from a partial summary.
- Add `/api/fixtures` with 50 default / 100 maximum and a stable cursor using `(day NULLS LAST, id)`; bind cursor to filter scope and data generation. Invalid/duplicate parameters are400, changed-generation cursors409. Preserve civil/split-year seasons, date bounds, null dates, status semantics, tie IDs and missing statistics. Upcoming means explicitly not_started, preserving the legacy route separately. Bound byte size and select only list fields in SQL.
- Migrate selected detail requests to their endpoint first; no full archive before a requested heatmap/stats/halves section. Use summaries for remote match overview, and targeted player/halves reads. Keep a documented fallback for older/failed services. Existing full-season standings/brackets remain complete by explicitly following paginated pages; never silently cap them at50.
- The interactive calendar already pages40 rows from the shared in-memory research dataset and does not call the unbounded backend list. Preserve it and its filters/compact previews; adding a second server read before changing bootstrap would duplicate work. Migrate backend-list consumers to explicit page traversal, and expose50/100 bounded pages for interactive API callers. The global research bootstrap stays separate; do not claim a200KiB whole-navigation budget merely from a small API response.

## Failure/expected-outcome matrix

1. Complete/partial/missing summaries, unavailable vs zero, archived inputs overridden by newer successful resources, dirty/source update, failed refresh and retry. Summary publication shares commit/rollback with manifest and completion markers. HEAD/304 and weak/list/wildcard tags remain correct.
2. Traverse >100 fixtures across same-day ties and null dates: no duplicate/omission and deterministic order; 50/100 limits, canonical filters, malformed/oversized cursor, filtered cursor reuse, generation change409, empty page and case-sensitive IDs. Legacy full-season route remains unchanged. SQL result payload excludes injected heavy fixture fields.
3. Browser/API workflow: overview has no full archive or advanced payload; selecting one section loads only that section; returning to the same section reuses it; missing stats remain actionable. Calendar filters/week/search and next/previous pages work at desktop/mobile and light/dark, including errors/fallback. Full-season standings remain complete.
4. Immutable publication scenarios are specified and tested separately under `publication/`. Reader follows nullable storage_key with legacy fallback and keeps metadata pinned to old physical bytes across alias changes. Schema migration + new reader rollout and draining the existing advisory-lock owner are prerequisites to new writer activation; do not cancel or replace the active production job.

## Evidence and comparison

Run the same deterministic PostgreSQL/TLS + S3/HTTP fixtures before/after and preserve SQL/application/object logs even on failure. Run the actual Python materializer against a separate disposable PostgreSQL database; no production fixture writes. Browser verification uses a production Next build and inspectable request logs/screenshots. Record exact commands, fixtures, versions, expected/actual outcomes and source hashes.

Quantify match SQL fan-out/body bytes before vs summary; full-season response bytes vs one page and full traversal; initial vs requested heavy endpoints; immutable overwrite attempts, retained-version integrity, transaction failures, physical storage reservations and dedup. Local tests do not establish production p95 or costs. Report consumer compatibility and quota/rollback tradeoffs explicitly.

Suggested commits: `feat: serve bounded match summaries and paginated fixtures`; `feat: publish Neon objects through immutable storage versions`.
