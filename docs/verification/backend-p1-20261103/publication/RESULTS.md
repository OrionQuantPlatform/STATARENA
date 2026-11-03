# Immutable publication results

Local verification on 2026-11-03: **18/18 passing SQL/S3 workflows**, using PostgreSQL 18.6, Python 3.14.6, psycopg 3.3.7 and boto3 1.43.123. These are disposable local services and stored fixtures; no production migration, upload, workflow change or deployment was performed. The original 15-workflow comparison is preserved below; the later admission regressions have a separate before/after section. Latest evidence: `final-sql-admission/results.json` and its SQL/Python logs.

The preimplementation baseline failed the publication requirements. Its original failures remain in `before/` and `before-complete/`. The final test harness was also replayed against frozen P0 source `6bea1b950abf647c58cf9895761132191261e70f`; see `baseline-ledger-growth/results.json`. The ACL-specific restricted-role failure was recorded before its fix in `before-acl/results.json`. A later review caught legacy-writer size growth hidden by an overlapping ledger record; `before-ledger-growth/` preserves that failing regression before its fix. Final evidence: `final-ledger-growth/results.json`, `final-ledger-growth/postgres.log`, `final-ledger-growth/python.log`.

## Numerical comparison

| Observation | P0 baseline | Immutable publication |
| --- | ---: | ---: |
| Passing original publication workflows | 4/15 | 15/15 |
| Attempts to replace an existing physical key with different bytes | 7 | 0 |
| Old version readable through actual S3 GET while a replacement transaction is open | No | Yes |
| Old version readable after the publication callback rolls back | No | Yes |
| PUTs for first publication, identical repeat, then another alias with identical bytes | 2 | 1 |
| GETs for that deduplication sequence | 0 | 0 |
| PUTs for first cold alias publication plus a changed version | 2 | 2 |
| Physical versions retained for that two-version publication | 1 overwritten key | 2 immutable keys |

The seven baseline replacement attempts include one HTTP 403 rejected by the fixture; six actually changed the fixture's bytes. The implementation made zero different-byte replacement attempts. Deduplication removes one of two PUTs (50%) for the identical-byte two-alias scenario. New immutable uploads are verified with the existing Content-MD5/returned ETag check; read SHA-256 and byte-length checks remain enforced.

Whole-run totals are recorded, but **are not a comparable performance benchmark**: baseline assertions terminate failed scenarios before their later verification GETs and role/ledger checks. Baseline: 13 PUT / 4 GET. Final: 10 PUT / 17 GET. Do not describe the extra final verification GETs as runtime regression or the lower total PUT count as a general production saving.

## Costs and limits

- Two versions of a 13-byte cold object retain 26 bytes rather than overwriting one 13-byte object. Preserving history consumes storage; identical-byte aliases share one physical key.
- Immutable publication initially added three ledger SQL statements (reserve, inspect reservation, mark verified), one reusable connection per Store, and two schema checks at Store startup. The admission guard below increases the new-unique-upload ledger path to six SQL statements plus transaction boundaries. Identical same-path publication still returns without upload. No production latency measurement is claimed.
- The final fixture contained 1,245 physical bytes. Capacity accounting reported 1,292 bytes: a conservative 47-byte overcount covering failed/uncertain physical reservations. The ledger includes a uniquely uploaded version whose publication transaction rolled back. The legacy-growth regression initially reported only 293 bytes after a legacy key grew by 999 bytes; the corrected query counts the positive difference between the current legacy catalog size and its older ledger record immediately.
- Existing mutable legacy keys are never overwritten by the new Store. Their prior bytes are preserved under immutable keys and catalog recovery paths. Existing public hash URLs reject different bytes before PUT.
- Migration 002 is idempotent, preserves populated legacy rows, resets stale pointers on old-writer updates, and copies only existing non-PUBLIC SELECT/INSERT/UPDATE role capabilities. A restricted login role successfully published and read an object and queried capacity.
- Activating writers requires migration, compatible readers, and draining old ingestion/materialization owners under advisory lock 97813003. Old writers remain schema-compatible but retain their old non-atomic S3 behavior. P0 readers are not a supported rollback after newly keyed cold objects are published. Writer rollback must retain ledger-aware capacity checks; the P0 catalog-only sum is insufficient once retained/orphan versions exist.
- Historical unknown orphans predating this ledger are not reconstructed by SQL. Bucket reconciliation and deletion are outside this lot. Existing quota thresholds must remain, with ingestion switched to `Store.storage_bytes()`.

Rerun commands and failure contracts are in `PROTOCOL.md`. Suggested commit: `feat: publish object aliases through immutable storage keys`.

## Reservation admission follow-up

Standalone materialization did not necessarily run the ingestion loop's periodic capacity check. The added preimplementation regressions demonstrated this gap without a large allocation: `before-admission/results.json` passed 15/17 workflows, but accepted a new upload with a full known ledger and admitted two concurrent writers into room for only one object. That source/schema is frozen alongside the failed results and can be replayed with the `admission-baseline` phase prefix.

`final-admission/results.json` passes **17/17**. At the 4,750,000,000-byte known-storage threshold, the new unique publication makes **0 PUTs**, preserves the old alias, and leaves **no refused reservation**. A second alias of verified existing bytes also makes 0 PUTs. Removing the synthetic fill allows the rejected publication to retry with exactly 1 PUT. With 19 bytes remaining, two concurrent unique 19-byte publications produce **1 accepted writer, 1 capacity refusal and 1 PUT**, reaching the threshold exactly. The main connection held advisory lock 97813003 during the refusal test; admission uses distinct transaction lock 97813004 and does not deadlock it.

The new unique-upload ledger path executes six SQL statements (advisory lock, database-size read, existing-key lookup, known-storage sum, reservation insert, verification update), plus BEGIN/COMMIT. Before this guard it used three statements. This is additional database work for correct admission; no latency improvement is claimed. The existing thresholds remain 4,750,000,000 object bytes and 900,000,000 SQL bytes.

Latest whole-run counters are 12 PUT / 19 GET / 0 different-byte overwrite attempts. These include verification and quota-recovery requests, so they are not comparable to earlier shorter suites as a performance benchmark. Suggested focused follow-up commit: `fix: enforce storage capacity before immutable uploads`.

### SQL quota for verified-key reuse

The 17-case artifacts above are retained. One additional regression exposed that verified physical keys could bypass the SQL-size check while publishing a new alias. `before-sql-dedup/results.json` passed 17/18; its frozen source/schema can be replayed using the `sql-dedup-baseline` prefix. The actual PostgreSQL test adds a public size-reporting function and sets only the disposable ledger connection's search_path to exercise a reported size of 900,000,001 bytes. The real small database size is also recorded. This is explicit SQL dependency fault injection, not a claim that a 900MB database was allocated.

`final-sql-admission/results.json` passes **18/18**. All three SQL-full operations—new alias reusing verified bytes, changed alias reusing verified bytes, and a unique object—are refused with **0 PUTs, 0 new catalog/recovery rows and 0 newly reserved bytes**. The existing alias remains unchanged. An identical existing path/digest still returns without writes. Recovery catalog rows are now inserted only after admission passes.

Verified-key reuse now executes three ledger reads/checks (lock, database size, key lookup) plus transaction boundaries, rather than two; it still consumes no additional object-storage reservation. The six-statement new-unique-upload path is unchanged from the preceding admission guard. Final whole-run counters: **13 PUT / 19 GET / 0 different-byte overwrite attempts**; their extra PUT initializes the SQL-quota fixture and is not a production cost comparison.
