# Local typed bulk v1 — frozen result

The bounded local phase writer passed **21/21 end-to-end workflows**, with 0 failed/unverified workflows in the [final receipt](runs/20261104T225232246653Z-final-frozen-self-reference-memory/result.json). Its captured writer, E2E, protocol, model and sealed SQL bytes remained unchanged during that run. This qualifies the tested source-free local workflow only. `fullAcceptance=false`; no real RDS/Neon/Pitch connection, real candidate import, publication, deployment or purge was performed.

ROOT approved the local scope in [PLAN.md](PLAN.md). The [protocol](PROTOCOL.md) preceded the E2E and importer. The [pre-implementation RED](runs/20261104T222638071559Z-final-e2e-before-importer-red/result.json) failed on the genuinely absent writer before starting a database. Earlier design checks live in [design-before-root-review](design-before-root-review/). Every earlier run is historical evidence for its own captured bytes, including earlier green runs; none replaces the final receipt above.

## Observed scope and quantitative limits

| Item | Final observation |
|---|---|
| Engine/catalogue | Owned local PostgreSQL 18.6; two databases; 94 tables / 1,709 columns / 431 immediate FKs |
| Candidate | 10,114 native rows, 39 populated relations; 55 empty relations are structural checks, not value coverage |
| Scalar density | 10,001 generated native metric observations, five native states, one canonical observation and distinct noncanonical variants; no positive corrective phase |
| Transport | 10,095 rows in 47 COPY commands across two phases; two run-control rows regenerated separately; exact bootstrap reused |
| Generation/snapshot maps | Source g2/id2 → destination g5/id6; source g3/id3 → destination g6/id7 |
| Native oracle | 91 relations compared column-for-column through SQL-native row digests; three control relations checked explicitly with enumerated differences |
| Ownership metadata | Conservative peak 6,349,164 bytes; owners/indexes + fixed reserve 6,347,599; retained self references 1,565; temporary graph peak 5,133 at a different instant |
| COPY payload buffers | Conservative complete-batch peak 4,960,613 bytes; these fields do **not** measure total process RAM/RSS |
| Seal time | Core 100.490 ms; families 97.427 ms |
| Commit time | Core 83.407 ms; families 81.781 ms |
| Deadlines | Statement 8 s, lock 1 s; injected timeout produced SQLSTATE 57014 and complete current-phase row rollback |
| Cleanup | Owned server stopped, all connections closed and owned data directory removed |

The hard ceilings remain 64 phases, 2,000,000 source rows including baseline/control checks, 500,000 per table, 1,000 rows / 1 MiB per COPY chunk, 1 MiB encoded row, 16 MiB payload buffers and 32 MiB ownership/self-reference metadata. Legal nextval catch-up stays at 1,000,000 calls per business sequence / 5,000,000 overall. Generation and snapshot identity sequences are allocated by the native phase functions, never reset or confused with each other. No limit, privilege, trigger, FK or CHECK was relaxed to obtain green.

**Real capacity is unmeasured.** The real core's approximately 15,437 × 31 = 478,547 scalar observations, before other facts, are far larger than this fixture. V1 retains ownership and FK indexes in client memory and may refuse that candidate well before the nominal row ceilings. Do not infer that it can import the real candidate, finish a real seal in 8 s, or preserve complete source coverage. A separately reviewed streaming/set-join design is needed before that capacity claim; raising the limits is not the proposed remedy.

## Proven behavior and preserved failures

- Default plan/preflight leaves destination rows, sequences and generations unchanged. Remote endpoints, an unowned marker, identical databases, a privileged actor and runtime apply are refused. Runtime's native COPY, begin/seal and sequence attempts return 42501.
- Model/SQL/writer/producer bindings, source-native digests, exact installation contracts and destination prefix equality are checked before application. A nonbootstrap row, collision, source drift, unknown phase ownership, unsupported history and corrupted control receipt refuse without target mutation.
- A valid typed scalar altered during transport is caught by the independent phase oracle before seal and rolled back. Mid-phase failure preserves committed prefixes and nontransactional sequence gaps. A new process retries/resumes once; a complete matching candidate returns a no-op without nextval or a new generation. A subsequent native identity insert cannot collide with copied IDs.
- COPY uses SQL text values directly, including JSONB canonical text. The oracle preserves exact long integers/fractions, SQL NULL, JSON null, missing keys, arrays, empty strings, false, zero, native type/state distinctions, timestamps and FK provenance. Invalid top-level technical JSON kinds remain blocked by installed CHECKs.
- The [atomic-generation failure](runs/20261104T224117614614Z-ordinary-writer-fixture-cleanup/result.json) exposed inherited child generations that lacked a direct snapshot FK. The fix propagates mapping through FK components without remapping business IDs. The [control-contract failure](runs/20261104T224300017920Z-inherited-atomic-generation/result.json) exposed lost snapshot priority/cutoff; final recreation preserves both exactly.
- Earlier fixture failures exposed native canonical uniqueness, positive pass counts, immutable journals and non-DELETE writer permissions. Fixtures were corrected or recreated under their owner; guards were preserved. Schema/migration/model/shared helpers and older lots were not edited.

## Reproduction and artifacts

```sh
python3 tests/orion_pro_bulk_local.py --label final-frozen-self-reference-memory
```

The runner's defaults name the existing embedded PG binary directory and explicit Python dependency path. Exact commands, role/endpoint checks, native digests, per-invocation receipts, maps, sequence observations, expected negative outcomes, logs, input copies and cleanup are in the final run directory. [environment-postrun.json](environment-postrun.json) is a separately labelled post-run dependency readback, not an in-run capture. [changes.patch](changes.patch) contains the two new runtime/E2E files for review; [final-hashes.json](final-hashes.json) binds the resulting local artifacts.

Serving remains outside this tool. Analytics/build/publication and operational queues stay empty in both fixture databases, and historical publication sentinels remain unchanged. Real-source fidelity, common-xG/source inventory, real candidate capacity, RDS import, public cutover and purge remain separate open acceptance gates. This local result authorizes none of them.

Suggested commit: `feat: add guarded local typed bulk import phases`.
