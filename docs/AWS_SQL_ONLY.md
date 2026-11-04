# PostgreSQL-only data migration

The requested destination is PostgreSQL on AWS. S3 is a temporary source during migration; do not remove an object merely because its name appears in the catalog.

## What lives in SQL

- JSON documents are available as `jsonb` through `statarena.current_file_documents`, with the source SHA-256 tied to the current catalog row. The normalized `statarena_app` tables are built from these documents and are not complete until their publication queue has been processed and checked.
- Images and other files whose exact bytes are needed are stored in `statarena.file_payloads`; larger originals use ordered `statarena.file_payload_chunks`. Each payload is checked against the source and against PostgreSQL before it is marked verified.
- `statarena.neon_delta_documents` stages later Neon JSON versions without overwriting the AWS catalog. Changed manifests must be reconciled with AWS writes before they are published.
- Neon relational rows can also change after the initial export. `dashboard/scripts/sync_neon_fixtures.py` compares fixture snapshots and copies missing or newer Neon rows directly into AWS while preserving newer AWS rows. Its `verify` mode rolls back a sample, and changed competition/season scopes are queued for publication. Repeat this comparison during the final synchronization; other relational tables still need reconciliation too.
- `dashboard/scripts/stage_neon_resources.py` stores newer Neon resource rows in `statarena.neon_resource_delta` without changing active AWS resource references. Apply them only after each referenced document is available to the SQL-only readers, and repeat the snapshot at cutover.
- `dashboard/scripts/stage_neon_jobs.py` preserves Neon-only collector jobs separately from the live AWS queue. `--include-conflicts` also captures differing shared jobs with the AWS fingerprint observed at capture. Reconcile all staged jobs with current resources and leases at cutover before scheduling; staging does not trigger API requests.
- `dashboard/scripts/stage_neon_assets.py` stages new or changed image URL mappings only after checking their bytes in SQL. Activate them after SQL image serving is deployed and check conflicts with any current AWS mappings.
- `dashboard/scripts/stage_neon_projections.py` stages newer Neon projections while keeping AWS-newer projections untouched. Recheck captured target versions before publishing them.
- `dashboard/scripts/stage_neon_asset_jobs.py` stages Neon-only image collection jobs without starting them; reconcile them with existing images and current source leases before scheduling.
- `dashboard/scripts/stage_neon_state.py` captures later Neon workflow state separately. Reconcile each state key with AWS before use; cursors and revision counters cannot safely be merged by timestamp alone.
- `dashboard/scripts/stage_neon_ingest_failures.py` preserves later Neon ingestion diagnostics separately from AWS diagnostics for reconciliation.
- `dashboard/scripts/stage_neon_dirty_partitions.py` preserves later Neon publication signals separately. Queue them only after the referenced data has been reconciled.
- `dashboard/scripts/audit_s3_archives.py` compares supported members of each archive against the current SQL documents and records checks by source SHA-256. Archives with unknown, nested or special members require further review. A content audit does not preserve original archive bytes or establish that readers have stopped using S3.
- SQL-only collectors read indexed JSON directly and write new JSON, image bytes and metadata transactionally. A malformed JSON file retains its original bytes instead of being silently discarded.

`STATARENA_SQL_ONLY=1` enables the SQL-only paths for the AWS backend and GitHub ingestion workflows. Keep it disabled until the required payloads, current JSON versions, database privileges and end-to-end flows have been verified. The SQL image route retains checksum validation and immutable cache headers.

Before enabling SQL-only mode, run `dashboard/scripts/install_sql_storage.py` with a schema-owner connection in `STATARENA_MIGRATION_DATABASE_URL`; apply the existing runtime and ingestion grants separately. This installer tracks migrations 012 onward in `statarena.sql_storage_schema`. The relational publisher continues to install only `statarena_app` migrations and does not need CREATE privileges in `statarena`.

CloudFront can cache images returned by the AWS Lambda/PostgreSQL backend instead of an S3 origin. Configure and test the existing flat-rate distribution and its Lambda origin access control before switching image traffic. Database-to-Lambda traffic, requests and any Vercel traffic remain subject to their respective pricing.

## Removal conditions

1. Reconcile the latest Neon and AWS data, including competing manifest versions and the current collection run.
2. Check all JSON, CSV, SQLite and archive contents needed by the application. An archive being indexed does not by itself prove that every binary member was imported.
3. Verify all required images and other irreducible files in PostgreSQL by size and SHA-256. Keep auxiliary backups and release artifacts until their contents and deployment replacement are verified.
4. Deploy the SQL-only readers and writers, switch the CDN origin, then test site pages, match data, logos and an actual new collection without S3.
5. Only then remove individually verified S3 objects, and verify the resulting inventory. A report or preview alone does not authorize assuming that all remaining objects are redundant.
