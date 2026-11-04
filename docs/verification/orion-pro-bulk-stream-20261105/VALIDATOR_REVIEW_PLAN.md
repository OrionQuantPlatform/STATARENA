# Nullable-aware membership comparison — static review before patch

Status: **no patch, migration, SQL execution or additional run authorized in this lot**. The source capacity campaign stopped at its native seal deadline. ROOT requested this read-only review of the exact query, existing indexes and compiler, followed by an E2E/EXPLAIN proposal.

## Exact expression active at cancellation

This is the existing SELECT from sealed013 line2381, formatted for reading. `g` is the validator's generation argument; this text has not been executed separately or measured in isolation.

```sql
SELECT 1
FROM football.player_match_metric_values child
JOIN football.match_players anchor
  ON anchor.match_id = child.match_id
 AND anchor.player_id = child.player_id
 AND anchor.team_id = child.team_id
 AND anchor.revision_id = child.match_player_revision_id
WHERE ingest.selected_at(g, child.recorded_from_gen, child.recorded_to_gen)
  AND child.is_canonical AND NOT child.is_deleted
  AND child.match_id IS NOT NULL AND child.player_id IS NOT NULL
  AND child.team_id IS NOT NULL AND child.match_player_revision_id IS NOT NULL
  AND NOT EXISTS (
    SELECT 1 FROM football.match_players selected_parent
    WHERE ingest.selected_at(g, selected_parent.recorded_from_gen, selected_parent.recorded_to_gen)
      AND selected_parent.is_canonical AND NOT selected_parent.is_deleted
      AND selected_parent.match_id IS NOT DISTINCT FROM anchor.match_id
      AND selected_parent.player_id IS NOT DISTINCT FROM anchor.player_id
      AND selected_parent.position_code IS NOT DISTINCT FROM anchor.position_code
      AND selected_parent.team_id IS NOT DISTINCT FROM anchor.team_id
  );
```

## Exact equivalence boundary and existing access paths

The parent logical key is(match_id,player_id). `_membership_checks` adds structural membership columns from `_MEMBERSHIP`, giving the four comparisons below. `anchor` and `selected_parent` are physical rows of the same NOTNULL-constrained table, not nullable outer-join projections.

| Parent column | Declared nullable | Existing comparison | Proposed comparison |
|---|---|---|---|
|match_id|false|IS NOT DISTINCT FROM|=|
|player_id|false|IS NOT DISTINCT FROM|=|
|position_code|true|IS NOT DISTINCT FROM|**keep IS NOT DISTINCT FROM**|
|team_id|false|IS NOT DISTINCT FROM|=|

For the three declared NOTNULL columns, both operands cannot be SQLNULL, so equality has the same truth value as the current null-safe comparison. Position remains null-safe; the capacity fixture deliberately has NULL positions. Replacing all four with equality would reject valid NULL/NULL membership and is outside the proposal.

Existing access paths include the nonpartial UQ(match_id,player_id,team_id,revision_id), the revision_id PK, and btree(player_id,match_id). Current partial canonical indexes cover(match_id,player_id) and(match_id,player_id,team_id) with recorded_to_gen IS NULL / is_canonical predicates. Three ordinary equalities may permit an existing prefix index or hash anti-join with nullable-position filtering. **This is a planning hypothesis**: there is no EXPLAIN proving which path the original or proposed query takes, and generic at-generation selection cannot simply be replaced with a current-only predicate.

The generator currently calls `_equal` with its all-null-safe default for every membership column. The pure static enumeration finds81membership checks /185comparisons:139declared-NOTNULL and46nullable. A future implementation should choose the operator from the parent column's actual approved nullable metadata **only in membership generation**. Do not alter `_equal` globally, remove selected-at/canonical/deleted/FK conditions, weaken cohort keys or infer nullability from the sample data.

## Compiler/installation guardrail

Current `integrity_sql` still reproduces sealed013 SHA85525221… exactly. `orion_pro_migrate.compiled_migrations` recomputes012/013 and writes differing generated output. A naive edit of the shared default membership generator would therefore rewrite sealed013 on the next old runner. That is forbidden.

The next diagnostic candidate must live as a new module/SQL artifact in its separately owned proof folder and append a local replacement of the validator function after installing unchanged013. Do not edit the frozen generator, its global `_equal`, sealed013 or the old migration journal for that benchmark. Bind the overlay's code/SQL hash explicitly and describe the database as a local candidate, not an unchanged013 installation. After validation and user107 coordination, ROOT may decide a later014+ delivery with a versioned compiler path whose013 default stays exact. No candidate, migration file or helper change exists here. Existing bootstrap/acceptance fingerprints also need review when a migrator eventually changes; old installation artifacts cannot be reattributed silently.

## Proposed next E2E/EXPLAIN gate, requiring a new ROOT budget

1. Proposed **new budget**, not approved or consumed here: one large local run maximum20minutes, owned disk8GiB/soft stop7GiB, workfiles512MiB/backend and evidence64MiB. Write the diagnostic E2E and expected failures before its candidate generator. Use the same two owned databases, ordinary data actors, exact478,547canonical shape, one source generation,8s/1s and32/16MiB. A fixture owner may append the separately hashed candidate function during owned setup, before ordinary-actor data generation. Preserve the original RED and all sealed bytes. No RDS/source/API access.
2. Prove the three NOTNULL equalities mathematically and verify declared nullability against the actual catalogue; retain all46nullable membership comparisons. Inside the still-open source generation, capture **non-ANALYZE EXPLAIN for the original SELECT**, then bounded EXPLAIN ANALYZE/BUFFERS only for the mixed-operator candidate over the same rows/g. The original whole-seal8sRED is already preserved; do not repeat it by routine. Save estimated baseline costs/paths and actual candidate rows/loops, index/anti-join choices, buffer/temp I/O and query times. Label baseline actual timings as unavailable. Read-only diagnostic savepoints may recover from an expected candidate query timeout without discarding the prebuilt fixture; there is no row dump or opaque aggregation. Do not assert a baseline nested-loop cause or speedup before the available observations justify it.
3. Prove semantic equivalence on full canonical positives and targeted native failure workflows:NULL/NULL position valid, NULL/nonNULL and differing positions invalid, changed team/match/player invalid, unselected/deleted/noncanonical parents excluded, historical at-g selection intact, exact physical FK anchor retained, and nullable columns in other membership families still null-safe. Preserve types, source provenance and old snapshots. New guards must reject every original negative case, without relying on a wrong FK error to mask a membership error.
4. Only after those tests exist, generate the separate local candidate with per-column membership comparisons; keep013/default compiler byte-identical. Test the **entire** native validate/seal and deferred commit under8s, not just the candidate SELECT. Transport remains unqualified until its later94-table/source-destination oracle and rollback/prefix/no-op/sequence/role checks pass; candidate validator success alone cannot claim them.
5. If the mixed query or complete guard still misses8s, retain RED and return to ROOT review. The current membership check scans all selected facts at g, including earlier phases, so merely splitting a producer's initial load cannot be assumed to solve cumulative validation cost. No importer-side generation split, increased timeout, omitted guard, new table/index/privilege or schema change is authorized by this proposal.

UX keeps serving unchanged until complete acceptance. DX preserves the same predicate semantics with a narrow, versioned generator change; AX gets explicit nullable cases, comparable query plans and honest whole-guard timings. Server plan improvement and full-candidate capacity remain unverified.

Suggested next commit only after successful separate validation: `perf: generate nullable-aware membership comparisons`.
