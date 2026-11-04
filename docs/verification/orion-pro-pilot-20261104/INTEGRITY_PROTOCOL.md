# Typed Pro pilot: integrity contract

Written before implementing the integrity SQL. The approved input is `target-schema.proposed.json`, SHA-256 `028c221d4cd45ad809a2340e62f34ab9df191c593b23c0c45d5f44587eb35a8c`. This protocol concerns the 94 active typed tables in the 103-table model. It does not restore sister history tables, a universal row registry, document payloads, or independent cell revisions.

## Failure cases and expected outcomes

| Area | Failure or edge case | Expected observable outcome |
|---|---|---|
| Generation order | Two transactions allocate concurrently; first transaction pauses before commit | Second allocation waits on transaction advisory lock `(20261104,1)` through first commit/rollback. Committed generations increase. A rollback may leave a sequence gap. |
| Generation ownership | Write to an older draft or sealed receipt, including with forged session settings | Reject. A writable receipt must have been created in this transaction and remain draft. No application-writable bypass flag exists. |
| Receipt lifecycle | Commit an unsealed receipt; mutate/delete a sealed receipt | Reject at the deferred commit gate / immutable receipt trigger. |
| Versions | Change a typed value, reopen/reclose an interval, delete a version, backdate an insertion, or insert a preclosed version | Reject. Only an open interval may close once in the new transaction's generation. |
| Selection | Historical overlap, two current variants/canonical choices, or nullable family-grain duplicate | Reject using the exact model selection keys and NULL semantics, including historical intervals and tombstones. Adjacent half-open intervals are accepted. |
| Physical anchors | Anchor exists for another match/team/player/stage/edition | Reject through physical composite FK; no partial unique index substitutes for a FK target. |
| Selected membership | Old anchor exists, but parent selected at the new generation has changed membership or is deleted | Reject sealing unless affected children are corrected/retired in the same transaction. An old anchor remains acceptable when the selected parent's logical membership still matches. |
| Participants | Published match has one side, duplicate known teams, or an unknown participant in a played status | Reject sealing. Upcoming/postponed/canceled/unknown participants may be labeled and unresolved. Both teams must be known before accepted stats/shots. |
| Collections | Child feature differs, parent tuple differs, declared count differs, or absent/null/empty/unavailable has children | Reject. Present collection count equals its complete typed child set; a genuine empty version has zero children and preserves old children. Failed/partial fetches cannot replace an accepted collection. |
| Reimport | Identical typed content/order/state/selection is submitted as another version | Reject redundant version; ingestion should reuse its retained version and generation. An HTTP attempt may still be recorded. |
| Spatial families | Heatmap index exceeds actual parent grid, empty grid has cells, duplicate coordinate; pass edge uses another network's node | Reject. Zero-based indices are bounded by grid dimensions; accepted grid shape and cells agree; endpoint FKs include network identity. |
| Append-only | Mutate old parent/children, duplicate a grain's generation, decrease/reuse its normalization revision, or backdate correction | Reject. Exact same-grain correction has strictly higher generation and revision; prior typed values and children remain queryable. |
| Aliases/profiles | Profile route references another player's profile, or a selected alias resolves to an absent/deleted typed identity | Reject. Stable identity and exact profile/physical anchor FKs are preserved; historical resolution remains available. |
| Builds | Create build with draft dataset/catalog, change ready build or its output, publish wrong edition/catalog/representation, or publish nonready build | Reject. Snapshots are sealed, build selected edition is valid, published pointer matches the build and outputs remain immutable once ready. |
| Hierarchies/context | Source/document/stage cycle, team honour is individual, edition disagrees with honour competition, ranking entry lacks declared document lineage | Reject in the applicable write/seal gate. |
| Source contract | Persist response payload, wrong native scalar/state, unresolved type or mapping, nonfinite numeric | Model row CHECKs and ingestion mapping gate reject; the pilot must report any unexercised source-contract rule as unverified. |
| Source receipt retention | Alter a receipt hash/request/identity or record locator; delete a receipt; move legacy retention backwards or without accepted reconciliation/cleanup evidence | Reject. Receipt contents and locator/provenance stay immutable; only a one-time verification timestamp and audited forward legacy retention transitions are allowed. No source body or source deletion action is generated. |
| Edition engagement | Build at a sealed snapshot has a known selected match team with no selected `competition_teams` engagement | Reject ready/publication. There is no fallback that infers an engagement from a match side. |
| Permissions | Runtime inserts/updates facts, ingestion writes receipt directly, unauthorized execution of write helpers | Reject by explicit grants/revokes. Helpers use fixed identifiers and a trusted `search_path`; session settings are not authorization. |

## SQL interface

`dashboard/scripts/orion_pro_integrity.py` exposes pure `integrity_sql(model, active_tables) -> str`. It reads the model supplied by its caller; it performs no connection, file collection, remote query, DDL application, deployment, or role creation. The migration compiler creates all typed tables/keys first. The returned SQL adds the generation sequence, guarded functions, immediate immutability checks and deferred cross-row validation. Grants are a separate pure helper so the caller binds actual role names.

SQL API planned for the E2E harness:

- `ingest.begin_generation(snapshot_key text, transform_version text, source_priority_version text, knowledge_cutoff_at timestamptz DEFAULT NULL) RETURNS bigint`.
- `ingest.validate_generation(generation bigint) RETURNS void`.
- `ingest.seal_generation(generation bigint, manifest_sha256 text) RETURNS void`.
- `ingest.selected_at(g bigint, from_gen bigint, to_gen bigint) RETURNS boolean` implements the half-open predicate; typed queries select business rows directly.

`begin_generation` takes the global transaction lock before allocating. Fact guards require the draft receipt to belong to the current transaction using PostgreSQL row transaction identity. `seal_generation` validates the final typed state, then seals. A deferred constraint trigger rejects unsealed receipts and validates the committed selection. A sealed generation is never reused for additional facts or children. Direct receipt DML and sequence allocation are not application privileges.

## Verification and evidence

The E2E owner writes the real PostgreSQL 18.6 scenarios before implementation and captures the initial failure. Subsequent runs must retain setup, exact command, expected/actual outcomes, logs and outputs in this directory. The parent owns the disposable local runner and 013 integration; only loopback disposable databases are permitted. No RDS write, workflow change, source requery, raw-payload write, deployment or Git commit is authorized by this subtask.

Acceptance is bounded: passing exercised database invariants does not complete the exhaustive source-field inventory, multi-record provenance, ingestion validation, mathematical aggregation validation, retained code/environment availability, operational capacity, or remote rollout. Reserved model/scoring tables remain outside this pilot.

The initial [21-scenario pass](runs/20261104T181231918635Z-integration-2-jsonb-and-shot-setup/result.json) is retained unchanged. Independent review then identified the source-document metadata and edition-engagement gaps above. Their executable cases produced [21 passes and two genuine failures](runs/20261104T181829854021Z-receipt-and-engagement-red/result.json) before the corresponding guard changes. A preceding masked engagement check is also preserved; its summary counter rejected the input before the missing engagement rule could be tested. The corrected case omits the nullable counter and requires an engagement-specific error.

The [expanded PostgreSQL 18.6 run](runs/20261104T182008595719Z-receipt-and-engagement-fixed/result.json) passes **23/23 scenarios**, including all three noncanonical/closed/tombstone engagement cases and the positive and negative synthetic retention audit transitions. Its owned server was stopped and temporary data directory removed. The synthetic `deleted` receipt transition changed SQL metadata only; no source object was purged. Tested integrity module SHA-256: `32aa1c84cbf3900b28fe2c1e186e4ba56695f83aeea17d5d1336882fec9aae85`.

Exact no-op normalization is currently exercised by the local fixture driver comparing typed inputs before generation allocation, rather than by a production ingestion service. The SQL also rejects equal replacement versions at a closing boundary, but that does not make the production collector implemented. The scenario result explicitly retains the missing xG source-state contract as unverified inside its detailed observations; the 23 case passes do not establish absent/null/empty/numeric-string xG fidelity or exhaustive source coverage.

Suggested commit: `feat: enforce typed Pro generation and selection integrity`.
