# Real source admission audit

All source inspect stages were reviewed against the frozen producer and the
immutable core checkpoint. No extra source/PG/cloud/RAM read was needed.

| Stage | Actual format and retained guard |
|---|---|
| Source bounds |94relations, native/encoded/key width,500k/table/2Mtotal,1MiBrow;17forced-empty relations and closed intervals refused. Unchanged pure V2 method. Current source553562rows/478547metric slots fits; these remain pilot bounds, not final caps. |
| Snapshot/run set |Current concrete source is exactly B0+one sealed core snapshot and one run1/g2/sid2. Unknown/extra/oversized runs or snapshots refuse. No anonymous latest phase or accepted fixture origin. |
| Producer metadata |run.mode=rebuild/status=partial/transform_version=real_source_core_v2_native31/code_commit=4b98a829.../error SQLNULL. parameters{}; source counters exactly full_acceptance=false,local_only=true,source_document_count=2 with exact JSON types. The source local flag belongs to the frozen local producer; it is not copied to real target counters. |
| Checkpoint closure |Exactly kind/phase/receipt_key/binding/generation/snapshot_id/report/report_sha256. Binding/report match the independent frozen source contract, including selector fingerprint. Unknown fields and bool-as-int counts refuse. |
| Input/report/seal hashes |Use only frozen normalizer canonical_decimal/normalized/hashed pure function ASTs. Input tags count2and hashes to3fd1ff1246e51e73f3aa94cbd2b68a07e875847c632fb5f75a4faf419b9eb479. Exact stored core report hashes to5a063182a3baa80dce33b9dcd7edf525b429ca74fb2cddd434675b38f9c96a04. Final string-only seal hashes tocf7683e637370bdf3b22533c64ae466bc20ac0917c8b103304f6f8578035bc54. No checkpoint value is rewritten. |
| Selector authority |The profile resource metadata preimage is not fully represented in SQL. Expected binding is taken from the separately pinned real fresh producer no-op, which recomputed it using frozen RAM. Exact selector d3470eaff3b62da909deec2b44bbb18b04ad38a968f743cf50f5f05b59db6d9e is mandatory; coherently rehashing a different selector does not change that expected contract. |
| Source documents |Exactly the two frozen AWS2025/2026partition path/SHA pairs, same ordered membership hash a23c66a3c64e23bdf9f77303fa8055a54cce12f6d034ec639f3b79b5f7bfb1b1. SQL reads links only for the exact accepted snapshot. Missing/extra/duplicate/changed memberships refuse. General ownership/FK checks also bind document run ancestry. |
| Native snapshot |Exact key real-source-v2:core:<inputSHA>, sealed status, real transform and source priority version, NULL knowledge cutoff, exact generation/snapshot coordinates, exact seal. |
| Source clocks |Aware run.started_at=finished_at=snapshot.created_at=sealed_at; preserved and compared, never aligned to target clocks. |
| Ownership/dependencies |Unchanged generation ownership for all94tables, source-derived phase row counts excluding12B0, producer transform columns, MATCH SIMPLE FK semantics and no future/unowned parent, bounded EXPLAIN actual work/temp. Source run1is legal. |
| Self graphs |Unchanged three typed self-reference DAGs,4096nodes/8192edges/8MiB workspace/rank bounds and native-cycle refusal. No business ID remap. |
| Sequences |Unchanged metadata-only increment1/noncycle/cache1 checks, source min/max reservation caps and monotone nextval. No sequence value SELECT by target ingest and no setval. |
| Native94 |Unchanged complete native source fingerprint comparison against checkpoint35dba5... /native94220b5d... and553562rows. The independently confirmed native31digest5f9175... is bound in the new dependency/receipt contract. Reopen checks policies/native94again before each target phase. |
| Target controls/data |Unchanged pure COPY/native91inverse/prefix/rollback/resume/no-op and four target transaction clocks. Only new adapter/version/binding identities differ. Source receipts use producer hashes; regenerated target technical receipts keep their existing transport canonical JSON hash. These two formats are explicit, not aliases. |

The real v1preflight error is retained at real-core-operation/preflight.result.json:
2connections closed,0COPY/nextval/business writes. The new structural CLI test has
33corruptions, positive local metadata and routing guards; it does not constitute
real native source/RDS qualification. ROOT must run the separately released real
preflight and own any business-write authority/readback. Source gaps (including
four unresolved actor links), spatial and detailed families remain open.

Suggested commit: `fix: verify complete frozen real source receipt admission`.
