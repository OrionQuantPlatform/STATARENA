# Local nullable-aware validator — final result

The [final E2E](runs/20261104T235918721381Z-nullable-candidate-final-authorized-load/result.json) passed **9/9 workflows**, with0failed/unverified. The local candidate accepted478,547canonical scalar rows in one core generation, with both native seal and deferred commit below the existing **8-second per-statement** limit. No streamer, migration014, RDS/source/API connection, production function update or deployment was performed. `fullAcceptance=false`.

## Narrow change and proof

[candidate.py](candidate.py) produces only a local replacement of `ingest.validate_generation`. Across81membership clauses,139comparisons become `=` only where the approved model **and all1,709actual catalogue declarations** prove both physical operands NOTNULL. All46nullable comparisons remain `IS NOT DISTINCT FROM`, including match_players.position_code. All other function text, at-generation/canonical/deleted conditions, physical anchors and cohort keys are unchanged. Reversing only those139substitutions reproduces the original function exactly.

The global `_equal`, default compiler,012/013, model, normalizer, readers and runtime source files were not edited. The pure default compiler still emits sealed013 byte-for-byte. The627frozen artifacts from the two earlier lots remain byte-identical. Candidate function owner/OID/ACL/security-definer/search_path/arguments and table/index object inventory stayed unchanged; the **one function body** is an explicitly hashed local overlay, not an applied014 or unchanged013 database.

## Measured outcomes

| Item | Observation |
|---|---|
| Dense native input |15437appearances ×31metrics =478547distinct canonical scalar grains;612draft matches; one primary variant |
| Positive native rows |513790rows across39populated relations;55empty relations are structural checks, not value coverage |
| Comparator |Unchanged013 in the second owned database, compact40×31=1240canonical scalars; no routine repeat of the old dense8sRED |
| Original standalone plan |Non-ANALYZE estimated Nested Loop Anti; estimated-plan request1.411ms; actual baseline query timing unavailable |
| Candidate standalone plan |Actual Hash Anti Join on match/player/team; nullable position remains a join filter;0returned rows;30.072ms execution /31.379ms wall |
| Candidate query workfiles |EXPLAIN reports0temporary read/write blocks; pg_stat temp samples0→0 may lag and are not whole-campaign spill proof |
| Native core seal |5578.437ms |
| Native core deferred commit |5667.145ms |
| Later family-phase seal / commit |5560.734ms /5532.907ms, with the full core still selected |
| Client retained metadata |Selected-object accounting peak5422705bytes, below32MiB; not process RSS |
| Native oracle buffers |Conservative peak1504882bytes, below16MiB; no streaming transport was tested |
| Observed settings |work_mem4096kB; hash_mem_multiplier2; temp_file_limit524288kB/backend |
| Final-run resource use |91.840s; peak observed owned PG directory1528786944bytes |
| Cleanup |All connections closed, owned PG stopped and its directory removed |

Seal and commit are separate statements and each satisfies8s. Their combined times are **11.246s core /11.094s families**; this is not an eight-second whole-phase or HTTP acceptance. The standalone query plan is not the internal PL/pgSQL execution plan, which was not captured. No isolated baseline speedup ratio or RDS/WAN capacity is claimed.

Both original compact and dense candidate reject the same seven native counterexamples. Closed, wrong-team, NULL→nonnull-position, noncanonical and deleted parents fail23514 naming the exact metric→participant membership FK. Earlier pinned generations remain valid in the focused predicates. Separate wrong-physical-anchor and wrong-provider clones fail the intended23503FKs; those failures do not mask the semantic cases. Negative transactions restore all native table digests; consumed sequence gaps are not reset.

Independent SQL-native digests cover all94relations before/after diagnostic SELECTs and negative rollbacks. Precision JSONB/numerics, SQL NULL/JSON null/missing/array/text, empty/Unicode/control text, false/zero and timestamps remain unchanged. Runtime function/sequence/write attempts return42501, with no extra privileges, trigger bypass, new table or index.

## Preserved chronology and budget

The [missing-generator RED](runs/20261104T234957906428Z-precode-missing-candidate-red/result.json) preceded candidate code and started no database. The [static-only preflight](runs/20261104T235100231994Z-scope-proof-before-load/result.json) checked scope without PG. The [first authorized start](runs/20261104T235414111175Z-nullable-candidate-first-load/result.json) stopped during a compact negative fixture: position_mappings has neither variant_key nor is_canonical. Those unsupported inputs were removed after a complete column/default/FK audit, without modifying the candidate. ROOT's [explicit continuation](root-run2-authorization.json) bound the unique second start to the corrected test/candidate hashes.

Both starts remain in [campaign.json](campaign.json); the two-start budget is exhausted. The first failed receipt was not overwritten, and there was no third run. The earlier streaming campaign's dense seal57014 remains the historical baseline at [its immutable receipt](../orion-pro-bulk-stream-20261105/runs/20261104T232206790496Z-native-canonical-seal-gate-complete-inputs/result.json).

## Reproduction and remaining gates

```sh
python3 docs/verification/orion-validator-membership-20261105/e2e.py --label nullable-candidate-final-authorized-load
```

The current ledger deliberately refuses another full load. Reproduction requires a separately authorized fresh campaign/evidence namespace; preserve this campaign's receipts and budget. Exact inputs/commands, candidate SQL, nullability proof, original/candidate plans, native digests, expected errors, timing/settings/resources and cleanup are saved in the final run. [summary.json](summary.json), [candidate.sql](candidate.sql), [changes.patch](changes.patch) and [final-hashes.json](final-hashes.json) are the review entry points.

This candidate is pinned to model18da43…/sealed013. ROOT must coordinate/revalidate a future014+ against the approved target after pending user107. Real-source completeness, typed streaming transfer, source/destination parity, real RDS latency/capacity, public cutover and purge remain unverified. No production reader or serving publication changed in this lot.

Suggested commit: `perf: optimize non-null membership validation without changing semantics`.
