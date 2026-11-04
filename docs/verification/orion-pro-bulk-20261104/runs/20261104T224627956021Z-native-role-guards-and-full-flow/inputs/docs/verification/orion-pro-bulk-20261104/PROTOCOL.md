# Pre-code local E2E protocol — typed phase bulk bootstrap

Written before `tests/orion_pro_bulk_local.py` or `dashboard/scripts/orion_pro_bulk.py` is created. This protocol is an execution contract, **not a passed test receipt**. ROOT approved [PLAN.md](PLAN.md) for two owned local databases only, with the explicit baseline/JSONB clauses below added before tests.

## Setup and immutable inputs

- One harness-owned local PG 18.6 cluster, two distinct source/destination DBs. Loopback literal host, owned process/directory marker, verified port/start time and distinct database identities. No AWS/Neon/Pitch credential discovery, service connection or source-body capture.
- Existing sealed model 18da43… and 012/013 bytes are read/applied to the owned local fixture only, never regenerated/replaced. The harness owner performs setup/cleanup separately; source reader and destination ingest login actors have no superuser/role/database/replication/bypass privileges or admin memberships. Runtime actor has only the installed reader capabilities.
- Destination exact bootstrap: 10 seeds, two relation contracts, sealed g1 snapshot and 012/013 journal. An independent baseline oracle covers 94 tables and 67 sequences. Earlier legacy-schema sentinels are checked by the harness owner and are never read/written by the application. Create deliberate target generation/snapshot gaps through a normal writer `begin_generation` transaction followed by rollback, never through setval or sequence resets; the subsequent row baseline remains the bootstrap.
- Source fixture uses native typed rows only, at least two sealed phases and dependent entity/profile/match/participant/metric/atomic-parent children, with 0, false, empty text, SQL NULL, exact numeric/fraction values and explicit collection states. No raw sports JSON, source dump or demo correction in the positive candidate. Include at least 10,001 generated native metric rows in one phase, with the approved 1,000-row/1-MiB chunk limits, to prove destination command growth follows chunks/tables rather than rows. This does not claim real-candidate or WAN capacity. Record populated and empty tables separately; an empty allowlisted table is not proof of its value coverage.
- Freeze expected typed rows/relationships and phase membership independently of the future importer, plus model/SQL/producer/writer/acceptance hashes. Pre-code source fixture creation may use existing local setup helpers but must not edit any shared helper/migration/normalizer.

## Exact baseline comparison and JSONB oracle

The tolerance allowlist is exhaustive. In `ingest.schema_migrations`, only `applied_at` may differ between installations; `version`, SQL `content_sha256` and the accepted `code_commit` remain exact. In the bootstrap `ingest.dataset_snapshots` row, only `created_at`/`sealed_at` may differ as installation clocks; `id`/`generation` use the explicit bootstrap map. Snapshot key/status/manifest/transform/source-priority/knowledge cutoff remain exact. Seed rows in `football.periods` and `football.positions` compare every column exactly, except `recorded_from_gen` follows that bootstrap map. The two bootstrap relation-contract rows compare every column exactly. Sequence positions may be ahead because of legitimate gaps and are handled separately; they are never reset. `xmin`/transaction IDs are physical metadata, not copied business columns and not a reason to tolerate any fact difference. The harness records the actual source/destination installation metadata separately.

No blanket timestamp tolerance applies to transported facts, identity anchors, documents, observations, or source retention metadata. Only the enumerated regenerated bulk run/snapshot control fields from PLAN may change; the oracle compares every other native column and type exactly.

New phase snapshots preserve the source `source_priority_version` and `knowledge_cutoff_at` exactly while using new IDs/generations and bulk transform/execution clocks. The fixture uses two distinct priority versions and a non-NULL cutoff so the oracle can detect a substituted producer version or default NULL. A mismatched journal fixture is installed in a newly owned destination database; the append-only journal is never updated or bypassed to manufacture the negative case.

Technical JSONB must include a 29-digit integer, a long decimal fraction, JSON null, a nested array, empty text, the text `"null"`, false and zero within an allowed technical object. Compare `jsonb::text` as PostgreSQL canonical text and use SQL `IS NULL` / `jsonb_typeof` / presence operators to distinguish SQL NULL, JSON null, missing key, array and text. Also retain a nullable technical JSONB column as SQL NULL; top-level JSON null/array remains rejected wherever the installed CHECK requires an object. The source reader/COPY path must transport JSONB as SQL `jsonb::text`, never `json.loads` through float and back into Jsonb. Regenerate only the enumerated destination control references/receipts; exact source technical parameters must either be preserved unchanged in their allowed field or bound by their full canonical digest when that entire control field is explicitly regenerated. The independent oracle uses SQL-native values/canonical text, not the importer's serializer or the source producer's adapter.

## Required workflow cases and expected outcomes

| Workflow | Expected observable outcome |
|---|---|
| Default plan/preflight | ROconnections; zero target row, sequence, generation or publication change; exact scope/order/role/source/target refusals inspectable |
| Initial apply | COPYstream under ingest permissions, realbegin/seal per phase, immediate FKorder and all triggers active; sourceOracle equals destinationOracle under only the declared generation/snapshot/control mappings |
| Explicit phase maps | Source generation/snapshot numbers differ from destination. Every generation FK and snapshot membership uses actual returned destination values; bootstrap matched by meaning, not row number |
| Mid-phase failure | Inject after a COPY chunk and sequence reservation. Current phase rows/snapshot/receipt absent after rollback; committed prefix retained, legacy sentinels unchanged; sequence advancement remains explicit and is never reset |
| Retry after rollback | Fresh generation/snapshot gaps observed; same business IDs/FKvalues imported without collision; sequences monotone and subsequent native default insert cannot reuse a copied ID |
| New-process resume | Exact sealed prefix verified and reused; remaining phase applied once. A second new-process invocation is a no-op across rows **and sequences/generations** |
| Collision/nonempty target | An unrelated row, conflicting ID/seed or divergent committed prefix causes refusal, with no overwrite/upsert/skip-error behavior |
| Corruption | Wrong FK/source/parent, numeric/state contradiction, row-digest/receipt membership or manifest corruption is rejected by preflight/oracle/normal guards; no misleading success receipt |
| Exact technical JSONB | Long integer/fraction canonical SQL text remains identical, SQL NULL differs from JSON null/missing/array/text, and invalid top-level kinds are rejected by native CHECKs; no float intermediary |
| Old transform/source drift | Changed producer/tool/model/SQL/acceptance or source phase bytes/rows is refused. No original normalizer checkpoint is blindly reused as a destination receipt |
| Unsupported history/cycle | Closed source interval, nonbaseline source seed mutation, unknown phase ownership, row self-cycle/unknown parent or forward snapshot reference refused before target writes |
| Privileges | Runtime COPY/begin/seal/nextval attempts denied; destination actor never owns/administers schema or resets sequences; no disable-trigger/replication-role/DDL grant path |
| Chunk and validation deadline | COPYseparated from pipeline, bounded buffers, each statement/lock deadline recorded, actual seal/commit duration measured. Timeout leaves a failed phase/sequence gaps and no accepted data receipt |
| Bound exhaustion | Phase/row/encoded-row/buffer/self-reference metadata/ID-reservation ceilings from PLAN are refused without implicit limit increases; excessive IDs fail RO preflight without consuming nextval |
| No publish/source body | Analytics/queues/collectors/model tables stay empty; no body/file/dump/CSV/opaque report/staging table is emitted; all prior sources/proofs untouched |
| Cleanup | Connections/leases closed, owned local PG stopped, temporary DB/data directory removed even on failure; evidence/logs/hashes contain no credentials or COPYpayloads |

The oracle must compare all transported native values, types, null/empty/false/zero/fraction distinctions, complete PK/UQ/FK/parent bindings and source stamps. It may normalize only declared generation references, snapshot references and regenerated loader receipt fields, with both maps explicit. No row-count-only or same-source-helper-as-oracle proof. Sequence assertions are monotonic/noncolliding, never exact rollback restoration or gapless numbering.

## Evidence saved at each E2E completion

Setup and exact local commands, PG/Psycopg versions, actor privileges, source fixture/acceptance/code/SQL/model hashes, source/destination schema and native-row digest oracles, per-phase source→destination maps, COPYtable/chunk/row/byte/command counts, elapsed deadlines, expected/actual failures and SQLSTATE, transaction outcomes, sequence observations before/after rollback/retry, no-op readbacks, legacy sentinels, credential/no-payload scans and cleanup receipts. Persist metadata/diagnostics only, no typed export/dump or source body snapshot.

No command is currently reported as run. After ROOT approves, the intended rerun interface is the new local E2E runner (final flags to be frozen before its first run), with its owned PG binary path and evidence label. Capture the genuine failure against the absent implementation first; implement only after those E2Es and expected inputs are written in this local worktree. No CI, git commit, deployment or real RDS execution belongs to this task.

## Acceptance limits

Passing local cases may qualify the bounded local bulk writer only. It does not accept the incomplete real normalizer/source inventory, closed-history replay, arbitrary candidate cloning, WAN8sperformance, RDS data import, public cutover or purge. Any need for extra privileges, unbounded ID reservation, blind technical-JSON rewriting or bypassing a guard blocks implementation and returns to ROOT review.

Suggested commit: `docs: plan guarded phase bulk bootstrap for typed PostgreSQL`.
