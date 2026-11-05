# Streaming typed phases — bounded v2 design

**Static proposal only. No implementation, PostgreSQL start, source/RDS/SSM/API access or SQL execution.** Only this new namespace is written. M0,012/013/bootstrap, v1, the old streaming scaffold, the policy14/14 lot and ROOT workflows remain frozen. This document grants no run or remote application.

One path is proposed: preserve explicit business IDs, compute row ownership and FK admission with source SQL joins, copy bounded native-text batches in the original knowledge phases, and verify exact native prefix oracles. No staging/business table, permanent registry, new grant/index/model, policy bypass or generation split is required. First source/target pair is **exact approved P1 local overlay → exact separately accepted P1 journalled deployment**, not a general P0/P1 compatibility rule.

## Evidence available and still missing

| Input | What it establishes |
|---|---|
| [Frozen v1](../orion-pro-bulk-20261104/RESULTS.md) | Small-fixture transport/rollback/resume21/21; row ownership and every referenced-key index grow in client RAM. Not real0.5M capacity |
| [V1 owner accounting, lines367–385](../../../dashboard/scripts/orion_pro_bulk.py#L367) | Every row charges at least160bytes before tuple/key/index/graph overhead.478547×160=76567520bytes, already above32MiB. This is a static lower bound on its accounting, not measured RSS or a new executed refusal |
| [Old scaffold RED](../orion-pro-bulk-stream-20261105/RESULTS.md) | Original013 whole seal hit8s on the native canonical shape. Do not replay this known baseline for routine proof |
| [Exact candidate9/9](../orion-validator-membership-20261105/RESULTS.md) | Same model/constraints,139 nonNULL comparisons optimized and46 nullable retained; native478547 scalars sealed/committed locally, each statement about5.6s |
| [Local014 adoption14/14](../orion-validator-adoption-20261105/RESULTS.md) | Closed policy/manifest/journal/roles/properties/rollback/no-op/local099 and native journal clocks. Compact1240 scalars, not a dense transport proof |
| Actual source RAM | ROOT reports its true SQL comparison is still pending at this design checkpoint. This proposal reads no source RAM and grants it no acceptance |
| Real RDS | No current capacity/readback is performed here;014 is not assumed applied there. Source fidelity, global validator cost and real transport remain separate gates |

Current M0 SHA `18da43f940870b7a3a3cb49323c847dd5e5174e5eea1f8ff0c8a159cf373cb08`:103 definitions,94 active relations/1709 columns/431 FK. Current local P1 manifest SHA `5250beb9a8f1bba003e44880eea04fd81029665912c2aa9e586f2d81e15ecdb9`;014 file SHA `e0810f8670b2cb627ade2c76e3c8eb527ab31fd595d5cf939fd63bfc5cf649d6`; exact function-string SHA `30f86fa262fd4cf10307e78431350f25b9d7a5b353d0c76abc0594340edb5d20`. A local manifest is not an RDS deployment receipt or automatic source-overlay acceptance.

## Three separate contracts before copying

**Structure:** compare full active table/column/type/nullability, PK/UQ/FK/CHECK/index/trigger definitions against M0 and the approved PostgreSQL-normalized catalogue. Resolve OIDs to qualified names for cross-database comparison. Keep actual native attributes; never strip whole functions, CHECKs or nullability because endpoints differ.

**Ownership/security:** attest actual owners, ACLs, default ACLs, memberships and effective privileges independently for each endpoint. Local owner names/OIDs differ from RDS; a reviewed role-slot mapping may normalize only those owner/ACL fields. It cannot rewrite SQL bodies, source data or arbitrary text. The source actor must be a nonowner ordinary reader; destination a nonowner ordinary ingest actor with existing COPY/INSERT/close-interval/helper/sequence rights. Runtime must be denied. No new role/grant/TEMP privilege or superuser is requested.

**Provenance/policy:** bind source producer/transform/code, exact sealed phase receipts/document membership, SQL-native94-table acceptance digest and source policy descriptor; bind destination deployment policy manifest/readback, exact journal chain/body/procprops and B0. Keep the original bootstrap bundle379ef1…/manifest215870… derived from model18da+old migrator+012/013. Never recompute it with the new writer,014 or current commit.

| Actual state | Explicit descriptor and first-v2 decision |
|---|---|
| P0 | Journal012/013 plus original function. Recognized historical state; not an accepted dense destination and not an automatically compatible source |
| P1 local overlay | Journal012/013 plus exact P1 body. Must have an independent **source overlay manifest**, including parent P0, function/procprops/source/producer/evidence hashes. It is not relabelled as an applied014 |
| P1 journalled | Journal012/013/014, hashes and actual P1 body/properties exact. Target requires a deployment-specific acceptance/readback, not merely the local oracle |
| LOCAL099, unknown/mixed chain/body | Refuse destination; source policy also unqualified in this delivery |

The first acceptance must name one exact pair of endpoint descriptors and their hashes, writer code, model and source-native acceptance. Neither abstract name P1 nor the function hash alone grants admission. Existing manifests have `qualifiedImportPairs=[]`; keep them immutable. A new v2 acceptance can bind the newly reviewed pair and its evidence without editing old receipts. Any later source/target policy/code/ACL change requires a new reviewed pair/version; no fallback toP0 or arbitrary SQL path/latest.

## Ownership without per-row dictionaries

[OWNERSHIP_MATRIX.json](OWNERSHIP_MATRIX.json) statically inventories all94 relations and the generation/snapshot FK-component closure. It is documentation, not an executable compiler or proof of source coverage. V1's75-name scope includes import_runs: the actual partition is **74 native-copy relations, three regenerated controls and17 forced-empty active relations**. The three classes are disjoint and cover94; do not count import_runs twice.

| Family | Exact source ownership calculation |
|---|---|
| B0 seeds/contracts | Their exact bootstrap key/template gives owner0; later definitions use their recorded generation |
|45 retained interval relations / generation-bearing roots | `recorded_from_gen` from an accepted sealed source phase; any nonNULL interval end is refused in this first delivery |
| Stable sources/datasets/assets/contracts/teams/players in v1 first-phase allowlist | Explicit first-phase rule, not an inferred generation from ID magnitude or a field name |
| Documents, records, lineage | Source document's exact accepted import_run_id→phase; record→document and lineage→derived_document; the parent lineage document must be an admitted nonfuture dependency |
| Fetches/issues | Exact accepted producer run→phase; unknown/unowned runs refuse |
| Snapshot-document membership | Exact dataset_snapshot.id→phase map |
| Six atomic children | Join complete declared parent-version binding; H2H includes match/source/feature/variant/generation, edges resolve the declared network binding through both real node FKs |
| Append-only descendants | Declared standing/ranking root ancestry, with exact composite keys and revision context; do not choose an arbitrary FK at runtime |

Derive a small typed SQL expression per relation. For each real FK, a set-based anti-join checks missing or forward-owned parent rows under PostgreSQL MATCH SIMPLE semantics. Parent owner0 is neutral; otherwise parent phase must not be later than child phase. Fully present owner-ancestry keys are mandatory; no missing-owner→0 fallback. Validate all other FKs even when only one declared ancestor determines ownership. Large child checks use bounded PK windows rather than an unbounded cross product. No all-row ID UNION/JSON registry, client PK→owner index or network lookup for each fact.

For the large scalar table, ownership is its recorded generation; its match/player/team/metric/source dependencies are SQL joins to the actual indexed parent keys. Keep existing nullable membership logic and native FK/check/validator admission unchanged. Plans are measured before accepting a join: moving work into PostgreSQL does not make it bounded automatically. No global work_mem/index/validator modification is part of this plan.

## IDs, cycles and TEMP decision

Preserve business IDs, physical revision IDs and import_run IDs explicitly. Source documents retain their original import_run_id because that same ID is regenerated as the destination execution control row. A collision with unrelated target data refuses; this delivery does not merge or invent identities. Source provider IDs/source_record_id and standing/ranking snapshot IDs are business references, not control snapshots.

Only dataset generation and dataset snapshot IDs are remapped. Maintain at most64 phase pairs plus B0. Start from `ingest.dataset_snapshots.generation` and `.id`; propagate kind to each referenced FK component until a fixed point, including atomic child columns reached transitively. A component marked both kinds is a refusal. For example H2H.recorded_from_gen maps through its coverage parent even without a direct dataset FK; standing_rows.snapshot_id does **not** map. Preserve exact native types. Assert source phase order and both control maps are strictly increasing and one-to-one; never assume generation equals snapshot ID or that rollbacks leave no gaps.

The inter-relation DAG is statically topologically ordered; immediate FKs remain enabled. Three self-FK families require an extra order: ingest.sources upstream id; competition_stages parent id/edition/revision; metric_definitions numerator/denominator composite keys. Fetch only their typed PK/FK/phase metadata once, check missing/forward parents/cycles, and order parents before children. No per-node source query. A single bounded typed VALUES rank map drives their source batch SELECTs.

**Fixed first-delivery bounds:** at most4096 self-reference vertices in total,8192 edges,8MiB charged graph workspace including keys, edges, ready/ordered/rank arrays and serialized VALUES. Rank-map SQL+parameters≤1MiB. All remain inside the same32MiB metadata envelope; pre-count/key-size admission occurs before fetching. The model/expected catalogue is shared once; source and target actual catalogue comparisons stream against it rather than retaining two extra full copies. Exceeding this profile is an explicit refusal, not a generic graph-loader promise.

TEMP ID maps were evaluated and are not indispensable here: business IDs are preserved, control maps have≤65 rows, and the only graph ranks are bounded above. First v2 creates **no TEMP or permanent tables**. This keeps the source transaction genuinely read-only and avoids assuming an existing TEMP grant. PostgreSQL read-only mode disallows CREATE/ALTER/DROP; creating TEMP would require a different reviewed session lifecycle. A future need for a typed per-relation temporary key/rank map would be a separate approval with existing privileges verified, ID metadata only and no opaque facts; there is no automatic fallback. [PG18 transaction access mode](https://www.postgresql.org/docs/18/sql-set-transaction.html).

## Exact phase and transport lifecycle

1. Default offline plan lists exact code/model/policy/acceptance, ownership expressions, dependency order, projection masks, source/target schemas and refusals. No endpoint is opened until explicit preflight/apply mode and its scope-specific authorization. Old v1/default compilers/guards are never modified.
2. Verify owned local identities for the local implementation; later RDS mode is separately gated. Acquire the existing cooperative source/target writer leases, verify no unexpected write-capable activity and inspect the exact bootstrap or committed destination prefix. Source/target roles stay ordinary and all endpoint state/policy checks occur before business DML.
3. **Before each target phase begins**, open source REPEATABLE READ READ ONLY, revalidate its policy/producer/sealed manifests and its full accepted native94-table fingerprint. Precompute the expected complete-prefix native digests in **source coordinates**, filtered by SQL ownership, including this phase. This happens before the target write transaction; no long idle target waits for a source-wide oracle.
4. Begin exactly one target transaction and allocate exactly one generation through ingest.begin_generation; read its separately allocated dataset snapshot ID. Fill the two small control maps. Reserve business/import-run sequences monotonically with permitted nextval blocks≤10000, at most1M per sequence/5M total, no setval/reset/UPDATE sequence grant. Retain original positive-ID/max/cache1/increment1/noncycling bounds. Gaps from any failure are logged and accepted, never undone.
5. Regenerate one execution import_run with the preserved source run ID and new writer/phase/source-policy/target-policy references. Rebuild its technical receipt/checkpoint; do not copy technical JSON containing stale destination generation/snapshot IDs. Preserve original source run native digest and accepted source receipt hashes. No user fact is hidden in these controls.
6. Copy relations in dependency order. Every batch belongs to the same source phase and target transaction; batch/chunk boundaries never create another knowledge generation. Source READ ONLY and target native COPY/guards remain active. Counts/copy digest and PK progress detect missing/duplicate rows before seal.
7. After the final source batch, finish the source RO transaction **before** the target full oracle/seal/deferred commit. Keep the cooperative session lease; the next phase opens a new RO snapshot and must reproduce the same full accepted source fingerprint. This is an explicit per-phase snapshot contract, not a claim of one snapshot lasting the whole campaign.
8. Hash the target native prefix in source coordinates using the inverse declared control maps; compare to step3. Then regenerate/check bounded destination controls, seal through the native helper, and commit. Measure COPY, oracle, seal and deferred commit separately. Journal/properties/policy must still match the accepted endpoint descriptor.

Each row is transported through source COPY SELECT→STDOUT bytes, then destination COPY→STDIN bytes, with all columns explicit and identical encoding/DateStyle/UTC/IntervalStyle. JSONB/numeric tokens are not decoded through Python float or JavaScript Number. PostgreSQL COPY FROM retains its native triggers/checks and accepts explicit identity values; no filename/PROGRAM/FREEZE/ON_ERROR-ignore or disabled trigger mode is allowed. [PG18 COPY](https://www.postgresql.org/docs/18/sql-copy.html).

**Bounded batch selection:** query at most1000 ordered PK+conservative encoded-width metadata rows after the last native PK (no OFFSET). Select the largest nonempty prefix whose COPY bytes have a proven upper bound≤1MiB. Then COPY exactly that key interval/phase in PK order into RAM, close the source COPY, and issue one target COPY. A single row above1MiB encoded refuses. No data body is fetched to choose the size; a conservative width bound may refuse a valid oversized profile rather than exceed memory. The partial PK/width window is bounded metadata, not retained ownership for the dataset.

Use conservative server-side text/escaping bounds, typed integer/map widths and an E2E check of actual encoded length. Do not assume a driver block contains a complete row; bound/framing logic handles arbitrary blocks. At most1MiB complete payload plus bounded live row/parser/driver copies fits the16MiB total transport envelope. Peak accounting includes both connections, byte buffers, metadata window and any transient encoding copies. Source batches finish before opening destination COPY, avoiding one long source COPY stalled by WAN writes. Client prefetch/processing must also stay below the observed idle-transaction deadlines; on timeout/cancellation roll back rather than raise the timeout or add heartbeats.

Psycopg supports block-by-block COPY bytes and parameterized COPY queries; COPY is outside pipeline mode. First delivery uses serialized bounded batches and explicit sync at dependent boundaries. It does not depend on pipeline tricks or per-row INSERT/RETURNING. About479 batches cover478547 scalar rows if the byte cap allows1000 rows; actual batch count is measured, not assumed. Metadata sizing adds a bounded query per window, still not per fact. [Psycopg COPY](https://www.psycopg.org/psycopg3/docs/basic/copy.html), [pipeline limitations](https://www.psycopg.org/psycopg3/docs/advanced/pipeline.html).

## Oracle, crashes and restart

Keep a versioned SQL-native length-framed row oracle in real PK order, independent of the transport adapter. Oracle scans also advance in bounded PK ranges/fetches, not one whole-dataset COPY/statement whose streaming duration could exceed8s. The digest continues across batches independently of transport blocks. The expected digest is computed before target BEGIN in unmodified source coordinates; inverse-map only declared target generation/snapshot components for comparison. Validate monotone maps so ordering is preserved, or refuse the profile. Never silently cast all IDs or compare a digest built from the same decoded objects as the writer.

All94 relations are accounted for:91 noncontrol relations compare native accepted prefix values, while dataset_snapshots/import_runs/schema_migrations have separate exact contracts for regenerated controls/policy-chain differences. Nonempty out-of-scope analytics/operational relations refuse. SQL NULL vs JSON null/missing, precise numeric, strings/arrays, zero/false/empty, Unicode/backslash/control text and all timestamps remain native-exact. No global timestamp tolerance.

Before commit, any failure rolls back the whole phase; sequence gaps remain. After a committed core, a new process verifies source/policies, recovered generation/snapshot maps, regenerated control receipts and the full target prefix before skipping it. Families then copy in one next knowledge phase. Lost commit acknowledgement is resolved by a fresh RO prefix readback, never by blind replay. Exact complete input yields no-op with no nextval, COPY or new clocks. Foreign rows, controls, checksum collisions, changed policy/ACL/producer/source or noncontiguous prefix refuse.

One source generation always maps to one destination generation. Closed intervals remain refused. Replaying knowledge corrections/closures is a later native-phase contract; neither cloning sealed rows nor ad hoc splitting a phase is introduced to pass8s. A failed family phase never unpublishes or rewrites the committed core; the existing serving publication stays active throughout this partial dataset.

## Actual future RDS path

The local streamer version must not contain an enabled remote fallback. After local acceptance and real typed-source SQL parity, a separately reviewed remote adapter/acceptance binds exact target account/instance/database/engine/CA/TLS verify-full, actual nonowner ingest role and existing credentials by indirect approved mechanism. No credential discovery/read or service call happens in this proposal. Default remains offline; remote preflight read-only; apply explicit and hash-bound.

Require an independently accepted **actual RDS P1 deployment** and native readback first; the local14/14/manifest cannot stand in for it. Check owner/ACL role slots, all structure/procprops/journal/B0, capacity/credits/storage/WAL constraints and quiescence against the approved target. The actual ingest session must already have an enforceable temp_file_limit≤512MiB; unset/unlimited refuses this delivery. Do not assume an ordinary writer can SET a privileged GUC or create a grant/helper to obtain it. No parameter/resource change is bundled into import. Neither AWS legacy namespaces/data nor serving functions/publication pointers are imported, reset or changed.

The later capacity gate transports the **accepted typed candidate**, not provider bodies, into bootstrap/exact-prefix target under the same phase transactions,1MiB/1000 batch caps,32/16MiB envelopes,8s statements/1s locks and native seal/commit. It measures WAN RTT/bytes/throughput, server work/buffers/temp/WAL/storage and every COPY/oracle/seal/commit; metadata-only RDS readback is not such a benchmark. Capacity requirements for this deployment must be authorized separately; no resize/grant/index/new model is implied.

The validator is global over selected data and runs at seal and deferred commit. Local0.5M seal≈5.6s and commit≈5.6s are separate statements, about11.2s combined; they do not qualify RDS micro-instance or all seasons. Statement timeout includes server command elapsed time, so slow client/network COPY is a real refusal. If COPY, oracle, seal or commit cannot satisfy existing deadlines, stop with evidence before any retry. No higher timeout, split seal, new index or trigger bypass. [PG18 timeouts](https://www.postgresql.org/docs/18/runtime-config-client.html#GUC-STATEMENT-TIMEOUT).

UX keeps current serving available until a separate full dataset/publication acceptance. DX gains bounded, inspectable per-relation plans instead of large client indexes, at the cost of SQL-plan review and prefix hashing work. AX gains closed endpoint/policy descriptors and deterministic refusal/restart. This improves transport capacity design, not proof of source completeness or permission to purge bodies.

See [PROTOCOL.md](PROTOCOL.md) for E2E-before-code and a **single dense campaign budget proposal**. Suggested commit: `docs: define bounded typed streaming phases and RDS qualification gates`.
