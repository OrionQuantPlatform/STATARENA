# Focused metric scalar-state E2E — test-first amendment protocol

This E2E is written before the targeted model/SQL correction. The original approved model remains SHA-256 `028c221d4cd45ad809a2340e62f34ab9df191c593b23c0c45d5f44587eb35a8c`; its approval receipt is not rewritten as if a later candidate had separately received user approval.

Concrete saved-source observations contain null player metrics, including expected-goals-on-target and was-fouled. The two existing typed metric-value tables presently reject null/absent and their `value_kind` descriptions refer to removed field-state machinery. The proposed amendment changes only four CHECK expressions, two `value_kind` descriptions and two table descriptions. It adds no table, column, key, JSON payload, universal row registry or per-cell history structure.

## Setup and exact rerun

```sh
PYTHONPATH=/tmp/statarena-publication-test-python python3 tests/orion_pro_metric_states_postgres.py --run-label metric-states
```

Before any candidate change, this command accepts only the exact original approved model digest and should record RED failures for null/absent. A changed candidate additionally requires `--amendment-receipt PATH`, an inspectable chain from the original digest to the current digest, and an independent model diff restricted to those eight edits. The compiler's own model gate remains in force; this E2E does not implement or bypass it.

Only an owned loopback PostgreSQL 18.6 process is mutated. The test invokes the existing local migration CLI and reuses the unchanged base fixture to create FK-valid matches, teams, participants, source receipts, periods, contracts and engagement rows. The focused metric inserts bind their own test-code digest. Source responses remain synthetic typed inputs in memory; no cloud/provider operation, file transfer, raw-body store or deletion is performed.

## Failure matrix saved before model/SQL changes

| Workflow | Inputs | Expected observable outcome |
|---|---|---|
| Bootstrap and amendment scope | Original model for RED; recorded bounded amendment for candidate | Real local migration succeeds; actual applied SQL digest matches its database journal; original approval and baseline model remain inspectable |
| Player and team metric states | Independently insert number `0`, string `''`, boolean `false`, null, absent in each existing table | All five states persist distinctly; exactly one matching native scalar for the three present kinds and all three scalar columns SQL NULL for null/absent |
| Contradictory state | `value_kind='null'` with `numeric_value=42`, separately for each table | CHECK rejection, without a PK/FK/uniqueness failure masking the scalar-state rule |
| Contradictory absent metadata | Null/absent with numerator zero, denominator one, or non-null source_display including `''`, separately for each table | CHECK rejection; an absent/null metric carries no scalar, fraction or displayed source value |
| Type mismatch | `value_kind='number'` with only `boolean_value=false`, separately for each table | CHECK rejection; false is not coerced to absence or zero |
| Retained correction | Same logical player/team null metric corrected to number `0.67` in one later generation | New current views return number 0.67; physical old null rows remain; old generation still selects explicit null |
| Frozen same-generation read | Ready build pinned to the generation where both player/team metrics are explicit null, then correction | Both families read through that build's one dataset generation still return null, while current reads return number; no mixing of generations |
| Missing row remains unknown | Registered metric definition with no observation row | No fabricated `absent` or `null` row; explicit `absent` fixtures mean the expected source field was established and then absent |

Each run saves exact setup commands, code/model/receipt snapshots and digests, native scalar readbacks, SQLSTATE/constraint diagnostics, applied SQL, PostgreSQL log and owned-process cleanup. Failed null prerequisites leave retained-correction/frozen workflows unverified. Every RED is retained; a post-code test is not used to conceal the pre-change failure.

This targeted change closes representability only for the existing player/team metric-value scalar states. It does not establish a complete source-field mapping, absent/null/empty/string state handling in wide `player_match_stats.xg`, production collector adaptation, full cohort/scoring replay, remote RDS performance, public cache/browser behavior or purge safety.

## Observed outcomes

- Original model `028c221d…`, before the amendment: `metric-state-runs/20261104T182823662466Z-original-approved-null-absent-red/result.json` records **19 passed, four failed, two unverified**. Both tables reject null and absent through their original `*_one_value_ck` constraints. Retained correction/frozen read remain unverified in that baseline because null rows cannot be inserted.
- Recorded candidate `18da43f9…`: `metric-state-runs/20261104T183139777229Z-targeted-native-metric-candidate/result.json` records **25/25 passed**, including ten scalar/metadata/type contradictions rejected. The eight-path amendment reconstructs the candidate exactly from the retained original. Player and team explicit null observations are corrected to number 0.67 in one later generation; the frozen build still selects null from both at one earlier generation. Number zero, empty string and false remain present values, while a missing metric row remains unknown.
- The unchanged 23 base workflows also pass against the recorded candidate in `runs/20261104T183222785812Z-recorded-metric-amendment-regression/result.json`: **23/23, 57 invalid workflows rejected**, catalogue **94 tables / 1,709 columns / 94 PK / 431 FK**. Only its model gate was made chain-aware; the original approval constant and semantic assertions were retained.

All three runs used PostgreSQL 18.6, captured the actually applied SQL against the migration journal, and stopped/removed their owned PostgreSQL process/data. No remote operation was performed. The original approval receipt still contains `028c221d…`; the bounded candidate is documented as an in-scope correction rather than a separate user approval.

Suggested commit: `test: exercise typed metric scalar states and retained null corrections`.
