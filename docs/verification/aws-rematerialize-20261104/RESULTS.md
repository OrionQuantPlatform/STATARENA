# AWS relational publisher verification

The workflow entry point is `dashboard/scripts/relational_materialize.py`. It uses the AWS ingestion role and the existing writer lease. Source discovery builds a temporary index of saved resources and archive membership. The worker commits one typed partition at a time. It processes recent fixture partitions before orphan detail buckets and interleaves catalog batches between partition batches. The first partition can commit before the support, profile and archive catalogs finish.

Indexed staging documents must match the current object checksum. The existing worker store verifies fallback bytes. Legacy packed partitions seed the first publication. Subsequent partial updates take their base from the committed application tables. Local SQLite scratch groups interleaved archive families and shared source paths on disk. A temporary directory and an explicit connection close bound scratch lifetime to one partition. The web runtime reads the RDS tables.

| Measured local behavior | Result |
|---|---:|
| New workflow checks before the publisher existed | 0/11 |
| Final workflow checks | 16/16 |
| Existing packed materializer workflows after sharing its normalizer | 5/5 |
| Appearance rows in captured match | 40 |
| Archived families published in the same transaction | 13 |
| Nested saved families verified separately from parameter variants | 5 |
| Shots retained after a current failed response | 29 |
| Appearance rows retained after a shots-only refresh | 40/40 |
| Rated players retained after that refresh | 29/29 |
| Interleaved source shards and fixtures | 32 and 64 |
| Reads of 64 required shard files | 64, maximum 1 each |
| Source file fallbacks for indexed bootstrap | 0 |
| Provider jobs created by publisher | 0 |
| Application tables and allocated bytes after fixture bootstrap, including indexes and TOAST | 151 and 5,750,784 bytes |
| Core partitions rewritten in clean repeat | 0 |

The 5,750,784-byte measurement covers the disposable fixture and schema. Production coverage and storage use require the live job receipt. The job applies the 16,000,000,000-byte database ceiling with a 256,000,000-byte reserve by default. It estimates temporary-index and batch growth before writes and checks actual database size before committing each publication. Environment overrides are STATARENA_SQL_LIMIT_BYTES and STATARENA_SQL_RESERVE_BYTES. Growth estimates depend on row and index shape.

The first integrated run exposed a table-name collision between core membership and typed detail players. Core membership now uses match_appearance_members. A later role test reproduced PostgreSQL's database CREATE check for a redundant CREATE SCHEMA IF NOT EXISTS. The publisher applies migrations inside the existing application namespace without that redundant statement. Two final role tests had no database CREATE privilege and only staging SELECT and dirty-marker DELETE privileges. The first worker owned statarena_app. The second matched the production setup: an administrator owned statarena_app and granted the worker USAGE and CREATE within that schema. Both installed and published all four models.

The partial refresh regression initially preserved appearances but changed a known stadium to null, downgraded detailCollected and reduced rated players from 29 to zero. The worker now uses previously published typed families when successful inputs for normalization are missing. New current successes take precedence. The details reader retains the current provider status independently of the successful archive used for core statistics. A second regression proved that a standalone archive observation with no fixture or resource still needs typed detail publication. A third confirmed that fresh match rounds must merge into the calendar returned by the website. Failed runs remain in the before-* directories.

A further partial-refresh workflow showed that SQL text storage alone converted numeric and boolean positionId values to strings. The inverse now reads the source type marker. All six examples (integer, float, string, null, false and true) retain their original type and value after publication.

The advisory lease prevents a second publisher from competing with ingestion. Old and new dirty markers are acknowledged only for the captured timestamps after the corresponding transaction succeeds. An independently committed update left exactly one pending job and the subsequent run consumed it. A failing typed input rolled back the affected partition and preserved its previous generation. Completed earlier partitions remain visible. Unknown typed fields and unrecognized saved match endpoints fail the affected publication so the source can be inspected.

Resume without --all uses durable checkpoint digests for core and catalog inputs. A fresh run scans staging metadata to discover out-of-band changes, which has a cost even when it publishes no partitions. The CLI checks its time budget between atomic batches/partitions. One active transaction can extend beyond that soft budget. A GitHub timeout rolls back an unfinished transaction and releases its database lease when the connection closes. A live receipt with remaining work requires a subsequent resume.

## Rerun

Install the tool-only dependencies described in PROTOCOL.md. The final suite and old-worker regression run against isolated PostgreSQL 18 and write inspection artifacts to this directory.

```sh
node docs/verification/aws-rematerialize-20261104/run.mjs final-native-position
node docs/verification/aws-rematerialize-20261104/run.mjs legacy-regression
```

The final structured report is final-native-position/results.json, with its worker.log and postgres.log beside it. legacy-regression/results.json records all five compatibility cases. PROTOCOL.md records the failure cases before the corresponding changes.

Suggested commit: `feat: publish complete AWS relational read models through rematerialization`
