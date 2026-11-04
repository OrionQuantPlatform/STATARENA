# Historical baseline for the superseded document-read design

This captures only the original handler and its failed acceptance before the user specified relational domain tables. The implemented and tested replacement is recorded in ../relational-match-20261104/. No document-reader product code was created.

## Original verification plan

Run from the repository root with Bun, dashboard dependencies and embedded-postgres 18.6.0-beta.19 (install outside the checkout with `npm install --prefix /tmp/statarena-cache-test-tools embedded-postgres@18.6.0-beta.19`). The runner creates a throwaway PostgreSQL 18 cluster on loopback with a temporary verified TLS certificate, applies both checked-in migrations and inserts synthetic rows. A loopback object server counts legacy downloads. An actual HTTP listener serves the production request handler. No external network or live database fixtures are used.

`bun docs/verification/aws-sql-reads-20261104/verify.mjs before` before the implementation. Re-run with argument `after` following the change. For an exact source replay from another branch, set STATARENA_VERIFY_ROOT to the checked-out source, with dashboard packages installed. Each run writes requests, expected outcomes, HTTP values, SQL counts, source body bytes, decoded bytes, actual HTTP bytes, and failure messages in its named JSON receipt.

Expected outcomes were established before implementation:
- A cold match aggregate uses one SQL query, reads zero object bytes, and returns metadata, arbitrary archive family, exact archived response, recent status/error/no-ref precedence, plus direct, ordinal and documentId resource shapes. Preserve null, zero, false and empty arrays. Large sibling matches must never enter the application.
- An archived-only compatibility response returns its requested family and match. A saved HTTP error keeps its original status and body. IDs with no data return HTTP 404.
- Unpublished or stale SQL documents and invalid references must cause HTTP 503 when required. An incomplete source must not be treated as ordinary missing data.
- Saved-only match detail works, even without a shard index. A declared archive family missing its indexed row makes the aggregate incomplete. A match whose saved response replaces an archived family still preserves all other families.
- No object downloads, gzip decompression or application parsing of archived objects in AWS mode. The legacy baseline may return correct data through full-object downloads and fail these performance or current-version criteria.

Suggested commit `feat: read saved resources and archive match families from PostgreSQL`.
