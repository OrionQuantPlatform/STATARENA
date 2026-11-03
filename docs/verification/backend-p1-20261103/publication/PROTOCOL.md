# Immutable publication SQL/S3 E2E

Written before implementation, 2026-11-03. Exercise the actual Python Store, psycopg and boto3 against disposable PostgreSQL 18 and a local HTTP S3 fixture. No production environment is inherited by the child process.

## Failure modes and expected outcomes

- A mutable cold alias changes bytes: the original physical key remains readable and unchanged; new bytes use their full SHA-256 key. The SQL pointer changes only after a verified upload.
- A publication callback raises before SQL commit: an independent SQL reader and Store.bytes still retrieve the old version; uploaded new bytes may remain unreferenced, but cannot corrupt old references.
- A legacy mutable object is replaced for the first time: preserve its old bytes under an immutable version and a catalogued recovery path before publishing the replacement.
- The upload fails or returns the wrong MD5 ETag: no new SQL alias becomes visible; existing data remains readable.
- A content-derived public URL already exists with different bytes: reject the replacement before any upload.
- The same path and bytes are published twice: the second call performs zero PUTs and returns false.
- A new reader sees an old writer update SHA without updating storage_key: a database trigger clears the pointer so legacy inline/key fallback is used. Explicit new pointers survive valid updates.
- Existing legacy rows, inline bodies, cold bodies and fresh schema setup work. Migration 002 applies twice without losing data. New writers fail clearly before an upload if migration 002 has not been applied.
- Hash/size mismatches on reads remain errors. Stored recovery records account for preserved prior versions; retained versions are never deleted here.
- Existing non-owner ingestion roles retain SELECT/INSERT/UPDATE access to the new ledger when they already hold those object-catalog privileges. Copy explicit non-PUBLIC ACL entries only; never grant PUBLIC. Exercise actual publication and capacity reads through a restricted login role.
- After a legacy path has a ledger entry, an old writer may replace its bytes with a larger object and clear storage_key. Capacity must immediately include that growth from the current catalog, before the new Store next republishes the path; an overlapping older ledger entry must not hide the larger current legacy object.
- Before new unique uploads, reserve capacity under a distinct ledger transaction advisory lock (97813004; the main ingestion session may already hold 97813003). Refuse when known physical usage plus new bytes exceeds 4,750,000,000, or actual database size exceeds 900,000,000. A synthetic size-only ledger row exercises the full-storage limit without a large allocation. Refusal must precede PUT, preserve the old alias and leave no refused reservation. Identical verified data remains reusable at the limit. Two concurrent reservations with space for only one object must produce one upload, not two. Removing the synthetic fill allows the refused publication to retry normally.
- SQL capacity also applies when a new/changed alias reuses a verified physical key: it still writes SQL. Refuse before any new alias/recovery catalog row, with no object budget increment or PUT. An identical existing path/digest remains a no-write success. Exercise this through actual SQL function resolution on the disposable ledger connection: a fixture `public.pg_database_size(name)` reports 900,000,001 with an explicit test-only search_path, while the real `pg_catalog.pg_database_size` remains small. This is SQL dependency fault injection, not an actual 900MB allocation or a production change.

## Rerun and evidence

```sh
mkdir -p /tmp/statarena-cache-test-tools
bun add --cwd /tmp/statarena-cache-test-tools embedded-postgres@18.6.0-beta.19
python3 -m pip install --target /tmp/statarena-publication-test-python boto3==1.43.123 'psycopg[binary]==3.3.7'
node docs/verification/backend-p1-20261103/publication/run.mjs baseline-replay
node docs/verification/backend-p1-20261103/publication/run.mjs admission-baseline-replay
node docs/verification/backend-p1-20261103/publication/run.mjs sql-dedup-baseline-replay
node docs/verification/backend-p1-20261103/publication/run.mjs final-rerun
```

Requires `/tmp/statarena-cache-test-tools/node_modules/embedded-postgres@18.6.0-beta.19` and Python 3. Each phase saves inputs, exact rerun, per-scenario expected/actual results, HTTP object operations, SQL log and Python output. The same tests run against the unmodified baseline first and changed code afterward; failures are retained. Report object PUT/GET counts, different-byte overwrite attempts, transaction visibility and old-version readability. These local counts are not production latency or egress claims.

Phases beginning with `baseline` use the frozen P0 source/schema in `baseline-source/`, copied from commit `6bea1b950abf647c58cf9895761132191261e70f`. The original preimplementation runs are `before/` and `before-complete/`; the final identical-scenario replay is `baseline-ledger-growth/`. The ACL failure was captured before its fix in `before-acl/`, and the overlapping legacy-growth undercount before its fix in `before-ledger-growth/`. The final passing implementation run is `final-ledger-growth/`.

The later admission guard has its own preimplementation failure evidence and frozen source/schema in `before-admission/`. Phases beginning with `admission-baseline` replay that source. Its 17-case passing evidence remains in `final-admission/`; `final-ledger-growth/` retains the earlier 15-workflow comparison. The verified-key SQL quota bypass was then captured before its fix in `before-sql-dedup/`, including frozen source/schema replayed by the `sql-dedup-baseline` phase prefix. Latest complete passing evidence is **`final-sql-admission/` (18 workflows)**. Full-storage simulation adds a size-only ledger record, not a multi-gigabyte body. The SQL-limit branch uses the explicitly isolated SQL size-reporting fixture described above; no >900MB database was allocated.

## Publication contract and tradeoff

New immutable physical keys are `data/versions/<SHA-256 of exact stored bytes>`. Catalog aliases remain stable; no new legacy-key dual write is made. Deploy readers that understand storage_key first, apply additive migration 002, and drain old ingestion/materialization jobs under advisory lock 97813003 before activating new writers. A schema-compatible old writer can still use its old behavior; the trigger prevents a stale pointer but cannot make its S3 writes atomic. Old readers are not a supported rollback after new cold objects are published: roll back writer behavior while retaining the compatible reader.

Preserved old versions add storage; no deletion or global purge is authorized. New physical copies and failed-publication orphans must be included in deployment capacity decisions. The current catalog sum alone is not a complete physical bucket inventory.

`Store.storage_bytes()` now sums the durable physical-object ledger plus legacy catalog objects not already represented by a ledger key, including positive size growth where an old writer has enlarged an overlapping legacy key. Reservations are written using a separate autocommit PostgreSQL connection before upload, so a publication rollback cannot erase their accounting. Failed reservations and uncertain legacy keys are deliberately conservative; reconciliation/deletion is a separate operation. Migration 002 copies existing explicit non-PUBLIC catalog-role SELECT/INSERT/UPDATE grants to the ledger. Role capabilities introduced after this migration require rerunning its grant block. Any rollback of writer behavior must retain this ledger-aware capacity check as well as compatible readers.

Reservations take transaction advisory lock 97813004 on the ledger connection and verify current PostgreSQL size <=900,000,000, including verified-key reuse that can still publish SQL aliases. New unique keys additionally require known storage plus incoming bytes <=4,750,000,000, then commit their reservation before PUT. The main publication may retain its separate 97813003 lock. Capacity refusal rolls back the proposed reservation and precedes upload and alias/recovery catalog writes. Legacy bookkeeping is not charged as newly uploaded physical data. Existing verified keys and retries of already-reserved bytes do not allocate a second storage budget; an identical existing path/digest writes nothing and returns before these checks.

Suggested commit: `feat: publish object aliases through immutable storage keys`.
