# Proposed append018: exact overlap fast path on the approved 017 target

Preparation only. No production migration file, live apply, new role, restart, capture or query is authorized by this proposal. 012–017 and all existing source/target policies stay byte exact. ROOT owns adoption and the separate real source-P1 to target98 transport compatibility.

## Why this is the next candidate

Real V4 failed on the variant overlap at the unchanged8s seal after 553,545 copies. The native context is exact: 016 retains the two 015 metric overlap lines byte for byte at lines1434–1435. 017 does not replace the parent validate_generation function; its native107 call and all six core-field checks remain required. The prior two actual attempts both rolled back all business rows. Actual P2 B0 after the second attempt has 711,753,728 allocated bytes for the metric relation and indexes; this is physical storage, not committed business data.

The owned P2 planner experiment passed10/10, including 478,547 metric rows twice, dense scope seal2.066s and deferred commit1.906s. But default and disable-nestloop plans had the same Merge Join shape with temp spill. This is not evidence that a planner setting alone repairs RDS. Do not retry solely on that basis.

## Exact proof

Let an eligible pair mean the exact original predicates at 016:1434/1435. The original variant check requires equality on match/player/period/family/metric/variant. The original canonical check requires equality on match/player/period/family/metric and both rows is_canonical. Both require distinct rows, half-open interval overlap and a boundary touched at g. If both rows are open, the exact native immediate partial unique index for the respective key already forbids such a pair. The tested nullable metric value/numerator/denominator are irrelevant to these keys; in this approved table the keys are NOT NULL. Even if a key were NULL, the existing SQL equality would not match it in the predicate. Keeping the original expression retains SQL NULL logic, MAX bigint sentinel, touched-generation qualification and exact errors.

Therefore the only safe skip is: both immediate uniqueness proofs are exact and there is no visible row with recorded_to_gen IS NOT NULL. If either uniqueness index is missing, altered, not ready/live/valid/unique/immediate or on a different table, do not skip. If any closed row exists, keep both original EXISTS statements, unchanged and in the original order. This also detects bad open pairs if an owned negative test removes a supporting index. No branch uses a writer assertion, estimated reltuples or an assumed sequence/generation.

### Proposed SQL shape

Use a single index-proof CASE before both original checks. Bind expected names and exact canonical definitions from ROOT's actual P2 rollback native readback (both indexes unchanged by016/017); use a schema-qualified to_regclass and exact pg_index.indrelid. Require all expected pg_index rows, exact pg_get_indexdef, validity/readiness/liveness and the immediate unique flags on both supporting unique indexes. Missing rows must make the check false (count of nonnull matching OIDs, no bool_and NULL shortcut). The guard, pseudo SQL:

    IF CASE WHEN <both immediate current unique indexes exact
                      and named closed-probe index exact if selected>
            THEN (
                SELECT recorded_to_gen
                FROM football.player_match_metric_values
                WHERE recorded_to_gen IS NOT NULL
                ORDER BY recorded_to_gen
                LIMIT 1
            ) IS NOT NULL
            ELSE true
       END THEN
      <original 016:1434 statement, byte exact>
      <original 016:1435 statement, byte exact>
    END IF;

Use this scalar ORDER BY LIMIT rather than assume the planner retains ORDER BY in an EXISTS. Its truth is the existence of a visible nonnull close; it does not change with index usage. For the optional search index, exact DDL proposal:

    CREATE INDEX football_player_match_metric_values_sv_closed_probe_idx
      ON football.player_match_metric_values USING btree (recorded_to_gen)
      WHERE recorded_to_gen IS NOT NULL;

No new constraint, column, relation, grant, trigger or planner override. Index empty for all-open imports; MVCC still decides visibility of rolled-back closed entries. The candidate should require actual Index (Only) Scan on the closed-probe index in the cold all-open trial, with no metric heap scan in that branch. If the no-index scalar probe meets the same matched evidence and enough headroom, prefer no new index. If retained dead storage makes it expensive, the small partial index is useful. Prove construction under the actual 8s bound on a B0 heap with two aborted full metric loads; CREATE INDEX must read physical pages even if the new index is empty. Do not silently extend deadline, use CONCURRENTLY inside the transactional journal, or run manual VACUUM/ANALYZE. If creation cannot qualify, report that separately.

018 would change only this guard envelope and, if selected, that one index. The function signature, OID, owner, ACL, SECURITY DEFINER, search path, transaction receipt, all other 016 assertions, validate_native107_generation call and 017 functions remain exact. Adoption would preserve native B0, journal012..017 hashes/old clocks, all 67 sequence values, role graph and protected metadata, then add only one canonical validator delta, the explicitly accepted index delta (0 or1), and journal018. A distinct actual postcommit readback is required. No in-place edits to the prior migration chain.

## Matched cold qualification, before migration materialization

One owned PG18.6 cluster, at most three owned databases over its lifetime (baseline dense017, candidate dense018, compact historical), no real source or provider, at most five clients. Proposed global 600s/3GiB disk/96MiB retained proof, normal 8s/1s SQL. Dense databases sequentially if required to stay below disk cap; first unexpected failure stops and retains the failing owned root. Baseline exact 016+017 and candidate exact same setup plus only 018. Both use the already qualified fixture emission/parser and COPY metric ingress with identical 15,437×31 values, 612 matches, bounded batches and payload digests. Both use ROOT's 14 actual planner parameters, default join methods, no stats and no DDL/performance override after installation other than candidate adoption.

For each matched dense trial, the metric heap receives the same two rolled-back 478,547-row COPYs to reproduce the physical prior-abort effect, then one fresh 478,547-row COPY in a genuinely owned draft transaction. Use the frozen fixture to supply exact parents; no prior seal in the session and no fabricated xmin or dataset snapshot. Track any bloat page reuse, relation+index sizes, catalogue/ANALYZE/vacuum counters, wire SHA equality, actual planner choices and RDS-vs-local resource limits. Full native seal AND actual deferred commit are observed, not predicted from EXPLAIN. If baseline times out at either exact original overlap statement, record this as the expected negative comparator; no automatic retry. A different error is unexpected. If baseline passes, retain both measured runs and do not claim local reproduction of the RDS timeout. Set up/index-build cost and seal/commit cost are separate.

Take nonexecuted EXPLAIN estimates separately from EXPLAIN ANALYZE BUFFERS. In baseline capture both original overlap joins; in candidate capture the CASE proof, chosen closed lookup, original subplan loops and heap/index/temp blocks. Record a bounded no-index closed probe on the same dense shape to justify whether the index is necessary; use a separate readonly EXPLAIN/diagnostic scope without altering the live writer or caching its PL/pgSQL plans. Stop if the result is inconclusive. Exact 98-table native oracle must compare the matched business state (account for legitimate per-database clocks and generated controls explicitly), old registry/security and all 67 sequence states independently.

| Before-code cases | Required result |
| --- | --- |
| Missing candidate | Genuine static workflow RED; no PG initialized. |
| Original 016 overlap preimages and post017 validator | Actual V4 context matches the first unchanged 016 expression. Remove the sole new guard wrapper from candidate function and recover the exact old function, including both error messages and native107 call. |
| Open-only with exact indexes | Guard skips both joins; same verdict as old two checks. Native open duplicates remain rejected by the exact immediate unique indexes. |
| Any closed interval, two touching intervals, one overlap, untouched old overlaps, cross-variant canonical, noncanonical, nullable metric slots | Evaluate both old checks unchanged with their original truth, order and error; no weakening, including the MAX bigint sentinel. |
| Supporting index missing or wrong definition, invalid/unfinished flags | No fast path. Owned compact test removes each original current index in a distinct disposable case, creates the formerly prevented open pair in an actual later ordinary-ingest draft and verifies the original exact 23514 overlap refusal. Wrong/absent closed-probe index also falls back. Do not alter a real schema. |
| Real historical correction | Close predecessor, insert changed adjacent successor and verify original and new selected values. The 016/017 seal and deferred commit still pass. Exact no-op successor and unselected parent errors still refuse. |
| Matched cold full COPY/bloat | All writes same ordinary role, no stats collected or changed. Observe candidate and baseline actual seal/commit under8s, or expected baseline overlap timeout; exact metric payload/coverage/canonical membership. |
| Partial index policy, if selected | Probe uses exact valid index and no large heap scan on all-open load; index builds under 8s against B0 with real-size rolled-back allocation; verify separate native catalog/index proof and native commit. |
| Adoption/cleanup | No unapproved DDL or privilege, fresh independent pre/post readback, old journal/B0/67 preserved, candidate policy exact, first unexpected stop and owned-only cleanup. |

The candidate does not solve every future mature history workload: a closed row deliberately retains the prior queries. Full production performance, commit, transport to active98 and public availability remain unproven until separately observed. Suggested commit: test: specify the exact metric history overlap fast path
