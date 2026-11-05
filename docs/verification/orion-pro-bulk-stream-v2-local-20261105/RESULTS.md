# Stream v2 preparation — implementation exists, SQL campaign not released

The new writer and complete E2E are prepared for ROOT review. **No PostgreSQL server, SQL transport, dense campaign, source/RAM access or remote action was executed in this lot.** Native transport, timing, restart and capacity conclusions remain unverified. Full acceptance is false.

The actual missing-implementation RED is retained at `runs/20261105T023316177502Z-complete-e2e-missing-writer-red/result.json`, SHA `7e5b668066b0d10eccb35b1f001a9ae40e673aa0197f398e2e96e9267d19e32c`:0pass/1expected failure/28unverified,0PG. It captures the complete original29-case E2E before the product existed. The earlier draft RED remains intact as well. ROOT subsequently required a stronger compact cross-batch self-DAG proof; `SELF_DAG_FIXTURE_AMENDMENT.md` and `precode-to-current-e2e.diff` record this explicitly. The RED is not silently attributed to the later E2E bytes. The added assertions preceded the new product witness/window contract.

Actual current-byte verification is limited to the default CLI (`offline-cli-final.json`:0connections/0COPY/0nextval) and14static checks (`static-preparation.json`). The static inspector reads source AST, frozen artifacts and model metadata; it neither starts PG nor treats SQL strings as executed checks. Rerun:

```sh
python3 dashboard/scripts/orion_pro_bulk_stream_v2.py
python3 docs/verification/orion-pro-bulk-stream-v2-local-20261105/inspect_preparation.py
```

## Exact pair and fixture, not a real-source acceptance

- Model18da43 remains103tables/1791columns/450FK total,94active/1709columns/431FK.012/013/014function, oldv1/scaffold/design, guard policy/helper/runner and every old receipt stay unchanged.
- The new closed binding reads guard-v2 P1 manifest6ecdf33f… and oracle6305017e…, helper354d2857…/runner3fe82b36…. Source is an exact local P1 function overlay with journal012/013; target is the separately bound P1 journal012/013/014 descriptor. Function properties, full security catalogue, native bootstrap and journal clocks are bound per endpoint. Historical5250 is not the current qualification; old `qualifiedImportPairs` arrays remain empty.
- The source producer SHA is computed from the actual frozen native fixture code, current E2E bytes, explicit version and actual fixture shape. No real normalizer/real RAM receipt stands in for this source-free fixture. The acceptance/pair files containing actual SQL digests will only be created by the authorized owned campaign.
- Compact:40appearances×31=1240canonical scalars,4matches/40players,1010stages. Parent revision2000 lies beyond the first raw PK window; child revision2 depends on it, alongside1008flat roots. Actual successful COPY commands must place parent in an earlier rank window than child, preserve strict window progress and pass the independent native94 oracle. There are1043self vertices/4edges overall, below4096/8192. Dense remains15437×31=478547canonical scalars,612matches/800players, one variant and only2stages;35self vertices/4edges. Minimum2compact stage COPY commands is a cap arithmetic fact; observed command order is still unverified.

## Product decisions to be exercised by the E2E

Ownership is evaluated through source SQL joins and full physical FK dependencies, preserving MATCH SIMPLE null behavior and refusing missing/future owners. Only the three bounded self DAGs retain keys, ranks and witnesses. There is no per-fact ownership/index dictionary, TEMP relation, permanent registry, new index, grant or policy bypass.

The106generation/dataset-snapshot components follow the physical FK closure. Business, revision and import-run IDs remain explicit and unchanged. Generation and dataset-snapshot maps are separate; standing_rows.snapshot_id remains a business ID.74native COPY relations,3regenerated controls and17forced-empty relations account for all94active tables. The native oracle independently compares91source-coordinate relation states; bootstrap/journal/import receipts have3explicit control contracts. Fact timestamps and native JSONB/numeric states have no global tolerance or float adapter.

The source uses a fresh RR transaction per phase and validates the accepted94-table digest plus expected prefix before target BEGIN. Raw COPY bytes use bounded PK/rank windows, at most1000rows/1MiB, and deliberately arbitrary4093-byte protocol fragments. The source RO transaction closes before the target oracle/seal/deferred commit. One successful source generation becomes one target generation; no ad-hoc phase split is allowed. Controls refer to the actual target generation/snapshot and new writer/pair, rather than copied source technical JSON.

The writer reuses only the frozen v1 bounded sequence-inspection/reservation methods and pure utilities. It never constructs v1's full Candidate ownership/index maps or uses its old connection/policy code. Monotone nextval reservations preserve gaps, without setval or sequence reduction. Closed intervals, foreign/partial targets, corrupt/noncontiguous prefixes, stale producer/source/policy and over-bound metadata are refusals. New-process exact-prefix/no-op and simulated lost acknowledgement workflows are written but not executed.

Metadata32MiB and buffers16MiB remain separate hard gates. Self vertices4096/edges8192/graph8MiB/rank input1MiB;64phases/2Mrows/500k per relation; nextval1M per sequence/5M overall in10000blocks. The policy bundle is released before model/graph allocation; a read-only feasibility calculation found7,538,358bytes in its existing accountant and15,926,966bytes with an additional8MiB transient reserve, before the small caller metadata. These are container estimates, not RSS or dense capacity measurements. Live COPY accounting includes both protocol buffers, a previous yielded consumer payload and UTF8/framing allocation; every actual peak remains to be measured. Native statement/seal/commit8s and lock1s stay unchanged; seal and deferred commit are separate timings, not an8s combined promise.

## Proposed campaign, not authorization

`CAMPAIGN_REQUEST.json` binds the current writer/E2E/binding/static hashes for ROOT. It is **not** `ROOT_CAMPAIGN_AUTHORIZATION.json`; no authorization or PG ledger exists. A future release must bind these exact final hashes. Intended command after release:

```sh
python3 tests/orion_pro_bulk_stream_v2_local.py --run-compact-and-dense --label root-authorized-compact-then-single-dense
```

One owned PG/two DB/20min, compact workflows followed by one dense source construction/core transfer;8GiB PG soft stop7GiB,512MiB server temp/backend,64MiB proofs. The first unexpected setup, guard, semantic, ownership, deadline or resource failure stops and preserves its receipt/cleanup for ROOT. No second PG/dense attempt is implicitly granted. Earlier native candidate9/9 and guard14/14 are separate historical proofs, not v2 streamer results. The former v1>32MiB result remains a static lower bound, not a new measured refusal.

Real source SQL acceptance, future RDS policy deployment/readback, RDS micro capacity, backend/readers/builds/publication/cutover/provider fidelity and purge remain outside this lot. Legacy/publication sentinels are part of the future local E2E; no live publication or source copy changes here.

UX: default offline and explicit bounded local acceptance. DX: one closed policy pair, native COPY and inspectable errors. AX: exact source hashes, fixed endpoints and independent native/control oracles. Tradeoff: only this source-free pair/open-history/bootstrap-or-exact-prefix scope is supported; neither a universal clone nor a demonstrated real-candidate import capacity is claimed.

Suggested commit: `perf: stream typed native phases within bounded memory`.
