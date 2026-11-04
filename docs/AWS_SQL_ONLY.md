# PostgreSQL-only data migration

The requested destination is PostgreSQL on AWS. S3 is a temporary source during migration; do not remove an object merely because its name appears in the catalog.

## What lives in SQL

- JSON documents are available as `jsonb` through `statarena.current_file_documents`, with the source SHA-256 tied to the current catalog row. The normalized `statarena_app` tables are built from these documents and are not complete until their publication queue has been processed and checked.
- Images and other files whose exact bytes are needed are stored in `statarena.file_payloads`; larger originals use ordered `statarena.file_payload_chunks`. Each payload is checked against the source and against PostgreSQL before it is marked verified.
- `statarena.neon_delta_documents` stages later Neon JSON versions without overwriting the AWS catalog. Changed manifests must be reconciled with AWS writes before they are published.
- SQL-only collectors read indexed JSON directly and write new JSON, image bytes and metadata transactionally. A malformed JSON file retains its original bytes instead of being silently discarded.

`STATARENA_SQL_ONLY=1` enables the SQL-only paths for the AWS backend and GitHub ingestion workflows. Keep it disabled until the required payloads, current JSON versions, database privileges and end-to-end flows have been verified. The SQL image route retains checksum validation and immutable cache headers.

CloudFront can cache images returned by the AWS Lambda/PostgreSQL backend instead of an S3 origin. Configure and test the existing flat-rate distribution and its Lambda origin access control before switching image traffic. Database-to-Lambda traffic, requests and any Vercel traffic remain subject to their respective pricing.

## Removal conditions

1. Reconcile the latest Neon and AWS data, including competing manifest versions and the current collection run.
2. Check all JSON, CSV, SQLite and archive contents needed by the application. An archive being indexed does not by itself prove that every binary member was imported.
3. Verify all required images and other irreducible files in PostgreSQL by size and SHA-256. Keep auxiliary backups and release artifacts until their contents and deployment replacement are verified.
4. Deploy the SQL-only readers and writers, switch the CDN origin, then test site pages, match data, logos and an actual new collection without S3.
5. Only then remove individually verified S3 objects, and verify the resulting inventory. A report or preview alone does not authorize assuming that all remaining objects are redundant.
