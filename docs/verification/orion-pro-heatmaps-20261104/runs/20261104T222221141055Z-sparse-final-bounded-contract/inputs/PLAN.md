# Sparse heatmap plan

Source-free phase only: **0/1344 real triplets compared**. The provider contract
is read from the parent's local primary-source note at
`../orion-pro-react-integration-20261104/PROVIDER_CONTRACTS.md`, citing
https://pitchapi.dev/. No provider/network access is performed here. The old
dense projection is historical partial evidence and cannot validate sparse data.

| Source | Existing typed destination | Contract |
|---|---|---|
| grid.length / width | match_heatmaps.grid_columns / grid_rows | Explicit positive smallint dimensions; never inferred from cells shape |
| grid.cell_length_m / cell_width_m | Corresponding double columns | Explicit metres, positive finite shortest-decimal roundtrip; never inferred |
| grid.frame | coordinate_frame | acting_ltr/home_ltr preserved, including away maps; no second rotation |
| cells triplet ordinal | match_heatmap_cells.cell_ordinal | Native list order, not row-major coordinate order |
| triplet[0] / [1] | column_index / row_index | Exact nonnegative integral coordinates inside declared dimensions |
| triplet[2] | action_count | Exact nonnegative int32; observed zero remains a row |
| cells absent/null/[]/nonempty | cells_state | absent/null/empty/available; no unobserved zero cells |
| row.actions | actions | Exact nonnegative int32 or explicit null. Absent cannot be distinguished in this model and is refused |
| team/player/side | actor IDs + match_team_revision_id | Match-scoped participant/team/side/cohort validation; no played/tenure inference |
| teams/players outer states | match_coverage feature heatmaps.teams / heatmaps.players | Separate absent/null/empty/present collection states and entity counts |

All collections are validated before any parent/cell is inserted. Duplicate
coordinates, repeated logical parent, invalid scalar types, nonfinite numbers,
fractional/overflow counts, invalid descriptors and unknown frames reject the
family atomically. Parent actions are retained independently, never filled from
a computed cell sum. Geometry rows require valid explicit grid metadata even
when cells is null/absent/empty. A family containing no map rows may retain its
outer collection states without inventing a grid.

The native31 VERSION and mapping remain unchanged; the module transform SHA
changes and existing phase bindings therefore reject old code receipts. Replay
uses the real family phase receipt API and a fresh process, preserving later
corrections and variants. The unchanged native31 E2E will run with only its output
directory redirected here, leaving its code/spec/proofs/ledger untouched.

## Observed names and shirts

The existing player/team profile tables have typed name/shirt columns,
source_id/source_record_id, variant/context and generation intervals. A join on
actor + same source/record + same variant + an explicitly declared observation
context + selected cohort can be unique. No global profile is a substitute.
However current uniqueness is actor/context/variant, not heatmap/source-record:
repeated team labels in multiple player heatmaps with one common variant can
collide. A SQL candidate/join/cohort and collision experiment will evaluate this
without a new schema or a hidden generic link. This does not yet prove a general
profile mapping policy. Until it does, name/shirt and other useful unmapped
fields are qualified by path only; values are never hidden in diagnostic JSON.
Full field fidelity remains blocked, while the spatial correction can proceed.

Suggested commit: `fix: preserve sparse heatmap coordinates and native collection states`.
