# Bulk v2 capacity — feasibility only

Status: **proposal for ROOT review, no v2 code/tests/SQL execution or service connection**. V1 remains frozen and local-only. Its [21/21 result](../RESULTS.md) does not qualify the approximately 478,547 scalar rows in the real core. Keep the same 32 MiB ownership metadata / 16 MiB buffers, 1,000-row / 1-MiB chunks, sequence ceilings, ordinary roles, source/acceptance bindings, exact phase oracle, native generation guards and eight-second statement deadline.

## Proposed change in representation

Replace the per-row client ownership/FK dictionaries with a small **per-relation SQL ownership expression** derived from the approved model. Keep only model metadata, at most 64 generation/snapshot/run mappings, bounded receipts and the three bounded self-reference graphs in client RAM. Source stays frozen under the same read-only repeatable-read snapshot and cooperative lease. No staging table, universal row registry, FDW, extra database object or raw body is required by this proposal.

| Relation family | Ownership/cohort expression to qualify |
|---|---|
| 45 interval relations and append roots | Native recorded generation, exact accepted phase membership, closed history still refused |
| Six atomic children | Set join to the exact parent version and its generation; pass-network edges retain their exact node/network bindings |
| Append-only descendants | Fixed joins along the model's declared append ancestry, rather than an in-memory map of every PK |
| Documents/records/lineage/fetches/issues | Same v1 attribution policy expressed by exact joins; fetches/issues still need their explicit accepted run, and ambiguous attribution is rejected |
| Stable anchors/contracts | Existing explicit first-phase/bootstrap rules plus set-based checks that no dependency belongs to a later phase |
| Snapshot memberships | The small source/destination snapshot map; football standing/ranking IDs remain explicit business IDs |

For each FK component, a set-based anti-join checks missing, ambiguous or forward ownership; inherited generation/snapshot references use the same transitive model analysis proven in v1. Native FK/UQ/CHECK constraints remain the authority for insertion. A SQL expression is a relational calculation, not a copied universal registry. Avoid an all-table UNION of row IDs or a materialized generic JSON relation.

## Streaming transport and exact oracle

Use one source COPY query per relation/phase to produce ordered native columns with only the declared generation/snapshot substitutions. Relay its text COPY stream through bounded RAM into destination COPY chunks; keep matching encoding, NULL marker, DateStyle and timezone. This can remove per-row source FETCH requests as well as destination per-row INSERT/RETURNING. No file or PROGRAM target is permitted. PostgreSQL supports COPY of a SELECT over the client connection and keeps COPY FROM triggers/CHECKs active; this is protocol feasibility, not measured throughput. [PostgreSQL COPY](https://www.postgresql.org/docs/18/sql-copy.html)

Preserve the exact SQL-native oracle rather than an adapter round trip: stream deterministic native row text from both databases, with bounded framing and real native-PK order. Decode transport framing only, never JSON numbers or source bodies. If the digest framing changes from v1, give it a new explicit oracle version and prove equivalence; do not reuse a v1 hash as v2 evidence. Prefix/resume still verifies all copied facts and regenerated controls before deciding to skip. Avoid unordered string aggregation, giant client arrays, per-row WAN lookups and unbounded database-side digest aggregation.

Self-reference source/metric/stage graphs remain separately bounded. Count their nodes/key bytes before fetching, enforce their share of the same 32 MiB budget and reject cycles/dangling parents. A huge self-reference catalogue remains a refusal; the large scalar relation itself has no reason to create an in-memory graph. The current 0.5M objective must not silently expand into a universal arbitrary-graph loader.

SQL joins may trade client memory for server CPU, sort/hash memory or temporary workfiles. CTE materialization/inlining must be inspected in actual query plans, not assumed from syntax. Existing indexes may suffice, but that is unverified; no migration014 or work_mem increase is proposed. Internal PostgreSQL work memory/spill is separate from the client bounds and must be measured and bounded in the next approved local study. [CTE evaluation](https://www.postgresql.org/docs/18/queries-with.html), [server work memory](https://www.postgresql.org/docs/18/runtime-config-resource.html)

## Blocking gates before any v2 implementation

1. ROOT approves this representation and exact failure matrix. Then E2Es precede code, on two owned local databases with approximately 0.5M native scalar rows and the same strict limits; no source collectors or remote reads. Use realistic distinct canonical match/participant/metric grains (including the 15,437 × 31 = 478,547 shape), not hundreds of thousands of alternative variants on one participant. Preserve the 500,000-row table cap. Sparse ID maxima, total rows or phase/control bounds may still refuse a real candidate even if streaming fixes metadata growth.
2. Prove full native oracle equality, precise technical JSONB, FK/provider/cohort membership, distinct generation/snapshot maps, source drift/old-transform refusal, corruption rollback, sequence gaps, prefix retry and no-op; include bounded self graphs and unknown ownership failures.
3. Measure client buffer/metadata peaks, source/target statement counts, query-plan behavior, server memory/workfile effects, COPY, seal and commit separately. No performance or real-candidate capacity claim follows from these unexecuted requirements.
4. One source generation still maps to one destination generation. Copy chunks are transport boundaries, not knowledge phases. If the existing guards cannot seal/commit the 0.5M phase in 8 s, stop: a producer-native repartition of the candidate needs a new reviewed source/acceptance contract. Do not split rows ad hoc, map one source generation to several destination generations, weaken guards or increase timeouts.
5. Real candidate fidelity and RDS application remain later independent gates. The same old serving publication stays active until full acceptance; no publication/cutover/purge is part of this proposal.

UX preserves the current publication during partial imports. DX replaces a capacity-limited row map with inspectable per-family joins, but requires careful plan/performance review. AX gains bounded client state and deterministic streams while retaining explicit refusal and resume contracts. The tradeoff is additional server work and a seal-time risk that is not solved merely by moving data efficiently.

Suggested commit: `docs: outline bounded streaming bulk capacity follow-up`.
