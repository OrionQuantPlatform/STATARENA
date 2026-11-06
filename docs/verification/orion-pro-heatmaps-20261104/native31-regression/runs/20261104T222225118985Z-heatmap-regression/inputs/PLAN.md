# Native common metric contract plan

Source-free only. New real states verified: **0/416799**. Existing model and012/013/014 remain unchanged.

| Source field | Common column | SQL type | Native scalar destination |
|---|---|---|---|
| `goals` | `goals` | `integer` | `legacy_normalized_goals` / `numeric_value / text_value / boolean_value` |
| `assists` | `assists` | `integer` | `legacy_normalized_assists` / `numeric_value / text_value / boolean_value` |
| `shots` | `shots` | `integer` | `legacy_normalized_shots` / `numeric_value / text_value / boolean_value` |
| `shotsOnTarget` | `shots_on_target` | `integer` | `legacy_normalized_shotsOnTarget` / `numeric_value / text_value / boolean_value` |
| `chancesCreated` | `chances_created` | `integer` | `legacy_normalized_chancesCreated` / `numeric_value / text_value / boolean_value` |
| `bigChancesCreated` | `big_chances_created` | `integer` | `legacy_normalized_bigChancesCreated` / `numeric_value / text_value / boolean_value` |
| `passesAccurate` | `passes_completed` | `integer` | `legacy_normalized_passesAccurate` / `numeric_value / text_value / boolean_value` |
| `passesAttempted` | `passes_attempted` | `integer` | `legacy_normalized_passesAttempted` / `numeric_value / text_value / boolean_value` |
| `passesFinalThird` | `passes_final_third` | `integer` | `legacy_normalized_passesFinalThird` / `numeric_value / text_value / boolean_value` |
| `defensiveActions` | `defensive_actions` | `integer` | `legacy_normalized_defensiveActions` / `numeric_value / text_value / boolean_value` |
| `interceptions` | `interceptions` | `integer` | `legacy_normalized_interceptions` / `numeric_value / text_value / boolean_value` |
| `tackles` | `tackles` | `integer` | `legacy_normalized_tackles` / `numeric_value / text_value / boolean_value` |
| `recoveries` | `recoveries` | `integer` | `legacy_normalized_recoveries` / `numeric_value / text_value / boolean_value` |
| `duelsWon` | `duels_won` | `integer` | `legacy_normalized_duelsWon` / `numeric_value / text_value / boolean_value` |
| `duelsLost` | `duels_lost` | `integer` | `legacy_normalized_duelsLost` / `numeric_value / text_value / boolean_value` |
| `aerialsWon` | `aerial_duels_won` | `integer` | `legacy_normalized_aerialsWon` / `numeric_value / text_value / boolean_value` |
| `aerialDuels` | `aerial_duels_attempted` | `integer` | `legacy_normalized_aerialDuels` / `numeric_value / text_value / boolean_value` |
| `touches` | `touches` | `integer` | `legacy_normalized_touches` / `numeric_value / text_value / boolean_value` |
| `touchesBox` | `touches_box` | `integer` | `legacy_normalized_touchesBox` / `numeric_value / text_value / boolean_value` |
| `clearances` | `clearances` | `integer` | `legacy_normalized_clearances` / `numeric_value / text_value / boolean_value` |
| `blocks` | `blocks` | `integer` | `legacy_normalized_blocks` / `numeric_value / text_value / boolean_value` |
| `dribbles` | `dribbles_completed` | `integer` | `legacy_normalized_dribbles` / `numeric_value / text_value / boolean_value` |
| `dribblesAttempted` | `dribbles_attempted` | `integer` | `legacy_normalized_dribblesAttempted` / `numeric_value / text_value / boolean_value` |
| `saves` | `saves` | `integer` | `legacy_normalized_saves` / `numeric_value / text_value / boolean_value` |
| `npxg` | `non_penalty_xg` | `double precision` | `legacy_normalized_npxg` / `numeric_value / text_value / boolean_value` |
| `rating` | `provider_rating` | `double precision` | `legacy_normalized_rating` / `numeric_value / text_value / boolean_value` |
| `goalsPrevented` | `goals_prevented` | `double precision` | `legacy_normalized_goalsPrevented` / `numeric_value / text_value / boolean_value` |

All 31known slots use only registered metric rows. Native null/absent have all scalar and auxiliary fields NULL. Numbers retain exact numeric_value and an exactly representable common projection; observed 0 stays 0. Strings, including empty/09/fraction-looking text, retain exact text_value with common NULL; booleans retain boolean_value with common NULL. No string parsing, boolean-to-count coercion, unit conversion, guessed rating range, ratio construction or aggregation. All definitions use source_native units and aggregation none. Fractional/overflow count numbers and inexact double projections block that field/observation, with no schema change.

The 24additional integer count fields are nonnegative int32. npxg is nonnegative finite double; rating and goalsPrevented are finite signed double without an invented scale/range. Exact Decimal numeric_value alone is not enough if the common projection cannot represent it. Old four-slot oracle/results remain historical; planned new transform version is real_source_core_v2_native31, and old receipts must reject without rewrite.

Full machine-readable fields, exact model checks, historical metadata and policy are in FIELD_MATRIX.json. The two-match original-family leaf dispositions remain partial evidence for raw families, not a native-state proof for the 27normalized fields.

Suggested commit: `feat: preserve native states for all registered common player metrics`.
