# Exact-key Neon/AWS content reconciliation — bounded RAM-only phase

Owner: ROOT, under Hugo's corrected transfer scope. This is a new budget and evidence folder. The pushed metadata inventory at `eab371a87c` and all its receipts/budgets remain unchanged. No remote import, DML/DDL, provider request, deployment, schema014 or normalizer/frontend/backend change is authorized here.

## Preconditions recorded before source reads

- Frozen metadata inventory SHA `03efac383d4c9bfdaedb483f13b2b1159636d657327fe9d15ba8a1e99d1fe4b3`; approved model SHA `18da43f940870b7a3a3cb49323c847dd5e5174e5eea1f8ff0c8a159cf373cb08`.
- Only14exact object versions: nine positive missing-AWS objects on Neon, the two sides of three differing resource pointers (the Neon sides overlap those nine), and the two manifest versions. Total advertised physical size347557bytes, largest161009bytes. The prepared scope records every path/SHA/size and exact endpoint/params/ordinal selector.
- Existing authenticated PostgreSQL clients are used to keep payloads inside the reader process RAM and apply size gates before transfer. Existing Neon project/branch/host and RDS database/CA are reused. TLS client `verify-full` is required; the previous server-side TLS-flag instrumentation error is not repeated. No credentials or DSNs are printed or saved.
- One sequential RR/RO connection per source; startup options set transaction read-only, repeatable read, statement timeout8s, lock timeout1s. SQL controls count toward the new cap. Nominal8instructions: each source uses implicit BEGIN, one preflight metadata SELECT, one admitted-body SELECT, ROLLBACK. Maximum18instructions, with no implicit budget reset or automatic scope expansion.
- MAX2MiB physical bytes per object,8MiB decoded bytes per object,32MiB decoded bytes cumulatively. Preflight reads stored size, actual `octet_length(body)`, gzip magic/ISIZE and current selector metadata. A changed expected fingerprint/selector, missing key, announced size beyond remaining budget or invalid size blocks that portion before body fetch. Body SQL repeats size/fingerprint predicates in the same snapshot.
- Decode with bounded streaming gzip in RAM; reject trailing/concatenated members, invalid UTF8/JSON, duplicate JSON keys and nonfinite numbers. Decimal decoding preserves exact numeric values and distinguishes strings/numbers/null/bool. Physical SHA is recomputed over fetched bytes and compared with the frozen expected SHA before parsing or qualification.

## Expected outcomes and failure matrix

1. Every fetched object has verified physical size/SHA and an explicit source snapshot. Missing/mutated metadata is retained as a failure, never replaced with a new unapproved key/version.
2. Each observation resolves its exact frozen selector and expected match/league context. Archive selection requires a unique matching member or the exact recorded ordinal, plus response-ID checks. Missing response IDs, duplicate candidates or contradictory IDs remain unverified/blocking. No first-member selection or inferred global identity.
3. Explicit empty collections are distinguished from absent/null properties and failed HTTP outcomes. Field/type/native-state maps, collection lengths, duplicate-ID checks and ID qualification are retained; a missing SQL/JSON row is not proof of source absence.
4. Paired observations/manifests retain both versions. Compare exact typed content and field differences; record wrapper/retrieval clocks separately from provider revisions or qualified provider clocks. Migration/index timestamps do not order provider freshness. Preserve AWS-only data and ambiguous versions.
5. Persist only metadata, digests, field/type/state counts, qualifying IDs, bounded useful differences and typed-destination decisions. Never save source bodies, raw response fragments, archives or replay payloads to disk/RDS/S3. No fetch follows manifest pointers into new objects.
6. The import plan reuses existing approved tables/columns and names unresolved destinations without creating014. Content qualification alone does not accept a remote import, full coverage, public cutover or purge.
7. Keep exact sanitized errors, SQL statements and counters, setup/rerun commands, input/source-code hashes and absence-of-credential checks. If auth/quota/deadline/size blocks work, retain that outcome and stop that portion without paid changes or invented results.

## Execution and evidence

`scope-and-budget.json` and `query-plan.json` are written before connecting. The reader fetches admitted bytes in RAM, closes each RO transaction with ROLLBACK and writes only summaries. Later analysis may use the same captured RAM without another source read; no raw-disk replay is created. An executed pass is not silently rerun under the same budget.

Planned rerun, requiring a fresh authorized live budget and preserved prior receipts:

```sh
python3 -B docs/verification/orion-transfer-content-20261104/prepare_content.py
PYTHONPATH=/tmp/statarena-publication-test-python python3 -B docs/verification/orion-transfer-content-20261104/read_content.py
```

The final result will state actual counters, accepted/blocked selectors, exact limits and whether all14versions were examined. Inspectable conclusions must remain reproducible from the recorded exact keys, frozen expected hashes and explicit selection/decoding rules; raw bodies are deliberately not retained.

Suggested commit: `docs: qualify exact Neon AWS content differences for typed import`.

## External-object transport extension, authorized before reads

The first8SQLinstructions verified both manifests and found the12sport payloads external (`objects.body IS NULL`), while their stored fingerprints/selectors still matched. The initial SQL-size guard blocked those payloads before fetch and its receipts remain intact. Existing `dashboard/scripts/neon_store.py:47` resolves such payloads with S3 `GetObject` at `data/<exact path>`, using the configured branch-scoped Neon bucket; the AWS copy uses the already inventoried AWS bucket and the same prefix. The Store constructor is not invoked because it has unrelated SQL/queue capabilities.

ROOT explicitly authorized this extension: maximum36object HTTP requests for12external bodies (HEAD, four-byte Range GET, bounded GET for each), zero additional SQL if possible, same32MiB decoded budget, TLS-verified SDK transport, no bucket listing or provider call. The two old AWS archive versions are an explicit exception within the three changed-pointer pairs; no scan/re-read of the512equal archive copies is performed. The two manifests are not fetched again.

Before full GET, require HEAD length to equal the frozen advertised size and be at most2MiB, retrieve only gzip ISIZE from the last four bytes, and compare its announcement to per-object/global decode caps. Use the HEAD ETag with IfMatch for Range/full GET; validate physical size and recomputed expected SHA before bounded decompression. ISIZE is an indication only: the real output bound in the decoder remains authoritative. The actual request hook counts every SDK object request, with automatic retries disabled and a hard stop at36. Downloaded physical and actually decoded bytes are counted separately; no source body is written anywhere.

Source identities: existing Neon endpoint `br-mute-bonus-be23014e.storage.c-9.us-east-2.aws.neon.tech`, bucket `statarena-data`; AWS bucket `statarena-football-333rosky-70db6e5f`, existing `statarena` profile/us-east-2 and expected bucket owner. Credentials stay in memory. The external reader records HEAD/Range/version metadata, SHA/size verification, selectors, ID/native-state qualification and pair differences; no opaque report payload or replay snapshot is created.
