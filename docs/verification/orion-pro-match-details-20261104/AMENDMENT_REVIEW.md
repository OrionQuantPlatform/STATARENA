# Native match details — complete proposal for review, not application

Suggested commit: `docs: propose typed native match detail amendments with cohort proofs`.

**No model/SQL/service/database change is applied.** This directory contains a field matrix and proposed RFC6902 patch against model SHA256 `18da43f940870b7a3a3cb49323c847dd5e5174e5eea1f8ff0c8a159cf373cb08`. The current approved model and012/013 stay unchanged. The earlier partial SQL adapter in PROTOCOL.md is retained as a historical proposal; it is **not** the current implementation direction. Priority is a faithful native contract before reader implementation.

The qualified input is the existing `20261104T204329068716Z-final-scoped-restart-and-explicit-checkpoint/normalizer-report.json`, not a new provider/source read. Only its field/type/count diagnostics were copied into QUALIFIED_FIELD_SHAPES.json:18 event paths,43 lineup paths,14 team-stat paths and21 H2H paths,96 total. No source values/rows/bodies are copied. This two-match diagnostic universe is not full real-source acceptance; unseen fields/types remain an explicit gate.

## Review artifacts

- NATIVE_MODEL_REVIEW.html: standalone local SVG,114-column dictionary and searchable107-table candidate catalogue. All controls/content work without network dependencies. The approved103-table plan is linked separately.
- MODEL_DELTA.json and COLUMN_DICTIONARY.json/.md: exact computed counts and complete new-column/key/type/state dictionary, plus four column and two CHECK replacements.
- FIELD_MATRIX.json: every qualified path → destination, SQL type, presence/type state, source cohort and uniqueness proof.
- UNIQUENESS_PROOFS.md: existing keys, missing guarantees, exact locator grammar and direct SQL lookup/order patterns. These queries are documentation and have not been executed.
- AMENDMENT_SPEC.json: exact typed columns/replacements, FK/UQ/index/CHECK definitions, four structural child tables and deferred/publication predicates.
- PROPOSED_MODEL.patch.json: standard JSONPatch, to be considered only with the exact base hash. Nothing applies it to the current file.
- STATIC_PATCH_CHECK.json: in-memory document application/reference checks only. It is not SQL compilation, PostgreSQL constraint validation, E2E or approval.
- HEATMAP_CONTEXT_PROOF.md: the already observed repeated-team UQ collision, precise occurrence-context alternative and its remaining PG-E2E gate. UNCOVERED_AND_GATES.json explicitly lists unaccepted native shapes.

## Reuse decisions before additions

| Need | Existing destination and proof | Minimal proposal |
|---|---|---|
| Observed player/team names and native position/shirt types | Existing profile tables, physical PKs and `(id,actor_id)` UQs; player/position/shirt state columns already exist | Reuse source-record-specific observed profiles. Add explicit name/image/identifier states and immutable native image URL; never substitute a global profile |
| H2H entry names | Existing `home_label/away_label` are immutable children of an exact coverage version | Keep these columns and add presence states; no extra name/profile table |
| IDs | `source_records.external_key` already stores native/natural identifiers; `(document_id,locator)` is UNIQUE and the record is append-only | Reuse it only for identifiers, with explicit typed state on the owning fact/profile. Do not store names, totals, formats or scalar measurements in metadata |
| Lineup member order | Existing `source_records.ordinal/locator` can encode exact array position | Add a version FK and slot uniqueness to match_players; use an exact, checked locator contract, not a new ordinal registry/table |
| Native lineup type `standard` | `lineup_type` is a semantic enum confirmed/predicted/observed/unknown | Add `source_lineup_type` text/state. `standard` is preserved as a source label; no invented `standard` boolean and no semantic enum overload |
| Lineup formation/confirmation, member position/shirt/captain/coordinates | Existing typed facts/refs | Add missing presence states; widen raw placement coordinates to exact numeric rather than assuming double precision can retain every source decimal |
| Lineup coach.name without a coach ID | A coaches identity requires identity resolution; a name alone does not prove one | Store the exact source-only coach name and object/property states in the side header, without guessing a coach identity |
| Team-stat values | Existing team_match_metric_values already preserves number/string/boolean/null/absent, fractions and display values | Reference the exact physical scalar rows; do not copy them into a new value registry or coerce native strings |
| Stat period/group/item names/format/order/empty containers | Metric definitions/mappings are semantic, not per-observation labels or layout; an absent value row cannot represent an empty group | Add three typed structural children: periods, groups and items, each bound to the existing collection version. Preserve raw key/title/format and exact membership refs |
| H2H native totals with an empty recent list | Entry rows cannot hold a header when there are no entries; analytics.metric_totals is a derived contract | Add one typed summary child per existing H2H collection version; no new independent history |
| H2H finished | Neither score nor status proves the original boolean | Add a native boolean/state to existing entries |
| Native image URL | media_assets.source_url/legacy_asset_url is mutable and is not the immutable observed property | Preserve source URL text/state in the existing versioned profile or H2H entry; keep asset refs for delivery separately |

Four proposed tables are **children of existing observations**, not new history tables: `football.match_team_stat_periods`, `match_team_stat_groups`, `match_team_stat_items`, `match_h2h_summaries`. They have no independent validity interval, generation allocator, publication pointer or universal field-code/value storage. Their keys inherit the complete parent coverage key. Values/names already represented in facts/profiles are reused rather than copied into another history system.

## Exact state policy

For a fixed-type source scalar, states are absent/null/value. `value` requires a non-NULL typed value; absent/null require SQL NULL and remain distinct. Empty string, numeric0 and booleanfalse are values. New columns on existing tables additionally default to **unrecorded**, which means legacy source presence was not recorded. It must not become absent/null/value by inference or be advertised as native-complete.

Nested arrays use absent/null/empty/present plus cardinality: NULL for absent/null,0 for empty,positive for present. New typed structures require an explicit state. Nested objects use absent/null/object; an empty object is object with its declared fields absent. A missing SQL row alone is unknown and never proof of source absence. A complete native contract must state every declared slot, including omitted properties, before publication.

Native identifier properties in the qualified universe are strings. Their exact text is retained in the designated immutable source_record.external_key, not a minimum/current public alias. Explicit state distinguishes missing/null/value. Nonstring IDs are an unqualified extension and are not silently converted. The caller's route ID and resolved canonical identity remain separate metadata. Identity resolution may create/reuse an identity from a valid exact source ID; it may not invent one from a name. An object lacking a resolvable actor identity cannot be forced into a required-identity profile: it remains unaccepted/unpurgeable until resolved or separately reviewed, rather than losing its fields.

Numbers are transported with exact typed JSON number tokens, without pg numeric-string leakage or a JavaScript Number round-trip; strings are never parsed. Proposed raw lineup coordinates and native H2H totals are numeric with finite-value checks and no invented scale/frame. No native total is derived from list length, and no equality between reported totals and a possibly partial list is imposed. Existing integer score/time fields retain their approved domain; source values outside that domain must be rejected explicitly, never rounded.

## Cohorts and profile selection

The selected coverage version at dataset generation `dg` fixes the complete `(match_id,source_id,feature_code,variant_key,recorded_from_gen)` observation. Events/H2H and the new layout/summary children use that full key. Lineup headers get an explicit coverage FK; a native member gets a physical lineup-version FK. Canonical selection applies to the **source family observation**. Referenced inline observations need not be promoted to the aggregate's canonical metric/participant: the new native route reads declared physical membership, never an arbitrary noncanonical row.

Native observed profiles are immutable observations in the existing tables, with `profile_context='native_match_observation_v1:' || source_record_id`, stable variant `source:exact`, exact actor ownership and exact source actor-object locator. An explicit physical profile FK identifies one row; the source-specific context prevents a global resource profile from being substituted. It must be valid at the pinned catalogue generation `cg`; the build must include that dependency. Public alias/identity routing also uses `cg`. An FK alone is not enough: deferred admission checks the full source/actor/document/locator/variant/context and selected-parent membership.

For example, an event player object is under the exact event source record plus `/player`; sub_in_player is under `/sub_in_player`, with its own actor/profile columns. `related_player_id` is retained but is not relabelled as a substitution actor. Lineup profile_ref and typed member raw fields must agree when they represent the same source position/shirt property. Root home/away team objects use their exact source-observed profiles, not provider_global/legacy/manual preference ranks.

H2H entry names already have exact per-entry destinations and use those, including unresolved previous matches. Canonical matches/aliases can be supplied separately when resolution is proved; they never overwrite the observed labels, time, score, finished or native IDs. No routable ID/token is invented for a missing/cross-edition reference.

## Structural definitions and SQL enforcement

The JSONPatch is the authoritative list of column types/FK/UQ/index/CHECK definitions. In particular:

- Events add physical observed-profile refs, a distinct sub-in actor/ref, native period label and missing scalar/object/ID states. Source ordinal uniqueness under the full parent key is required. Nullable event_type permits a genuine native null/absence under explicit state; observed empty text stays text, not `unknown`.
- Lineup side headers add coverage binding, object/formation/confirmed/type/coach/list states and exact list counts. `match_players.lineup_revision_id` references the existing `(match_id,team_id,revision_id)` lineup key. A current unique slot index plus a deferred historical non-overlap check on `(lineup_revision_id,source_record_id)` prevents two actors/versions occupying one native member slot. No source ordinal column is added because checked source metadata supplies it.
- New stat periods/groups/items use complete coverage ancestry and exact source-record pointers. Each child FK includes the same source/variant/parent generation. Items point to existing home/away scalar revision PKs. A deferred rule checks same match, source, declared side, period/raw-key mapping and active fact generation, and finite native numeric values; it cannot trust a physical FK as a full cohort proof. Repeated raw keys remain distinct item records. Empty periods/groups survive without scalar rows.
- H2H summary PK is the full coverage parent key. Four native numeric totals have independent states, even when recent_matches is empty. Entries gain native finished, scalar/identity/object/image states; the existing entry ordinal key/order is retained.
- Complete native observation publication requires no unrecorded states, exact typed leaf/shape reconciliation, bounded count/cardinality validation, no foreign actor/source/side/period and immutable parents/children under the existing generation lock. These are explicit deferred/transactional rules in the proposal, **not claims of implemented triggers**.

## Frozen/legacy behavior and costs

Old rows are not relabelled or backfilled from incomplete diagnostics. New state columns default unrecorded; new child tables start empty. The proposed player display-name nullability relaxation and raw-coordinate widening do not recover previously lost values. Current global/source mapper losses require a separately authorized source replay/reconciliation; this review does not perform one.

A future native representation, e.g. `summary-v1-shots-v1-details-native-v1`, would bind the new source/cohort/serializer contract in new ready builds. Existing `summary-v1-shots-v1` tokens, old pinned manifests, summary/shots bodies/ETags and profile policy must retain their old adapter exactly. Do not change existing build/publication versions or claim partial SQL projection as native parity. The new schema/producer/readers need independent E2E approval before any flag/publication/cutover; production remains ProOFF.

The minimal-table choice reuses match_players for lineup occurrences. A changed physical lineup parent can require rebinding/reinserting its member observations even when some displayed values are unchanged; identical accepted input must remain a no-op. This is an explicit write/storage cost. A separate small membership child could reduce that rebinding cost but would add a fifth relation; it is a review alternative, not silently included. Stat layout children can reference retained unchanged scalar rows at the same declared logical cohort, avoiding a second copy of scalar values.

Adding four active typed child relations would take94 active tables to98 (103 to107 including9 deferred model tables); it adds114 columns in total,65 to existing tables and49 in the new children. It replaces four column specifications: nullable player display_name, nullable event_type, and exact numeric raw_pitch_x/y. No role/resource/source-body/history registry is added. Future migration/grant/compiler costs and table rewrites must be reviewed against actual database state later; no remote state is assumed here.

The two existing raw_pitch_x/y finite CHECK definitions explicitly cast to double precision. They are **replaced**, under their existing names and exact JSONPatch test preconditions, by numeric-compatible finite checks; they are not added a second time. The first strict static export rejected that duplicate-name proposal before writing generated output; STATIC_REVIEW_FAILURE.json preserves the counterexample. Four new collection-state CHECKs also require count IS NOT NULL in empty/present branches, since an UNKNOWN CHECK expression alone would not reject a missing count. These are document corrections, not executed PostgreSQL proofs.

Exact materialized candidate counts, computed from the patch (named model definitions, not observed DB objects):

| Scope | Tables | Columns | FK | JSONB columns | CHECK |
|---|---|---|---|---|---|
| All definitions |103 →107|1791 →1905|450 →466|51 →51|889 →1017|
| Active core/enrichment |94 →98|1709 →1823|431 →447|35 →35|846 →974|
| Deferred model phase |9 →9|82 →82|19 →19|16 →16|43 →43|

The delta is4 PKs,1 UQ constraint and1 explicit current-slot index, in addition to16 FK and128 new CHECK definitions; two existing CHECKs are replaced. The96 untouched table definitions are byte-equivalent as JSON values. Existing103 table names/order remain; none is removed. No extra JSONB column or independent historical registry is introduced. No storage/latency/migration-lock benchmark has been run.

The occurrence-context proposal is a producer/cohort contract, not acceptance of the general heatmap mapper. Actor-object source records must be unique exact children, not one coarse record shared by multiple actors. The new player external_profile_version_id value `native-observation:<actor_source_record_id>` is a deterministic observation discriminator for this bounded context, **not a claimed provider profile-version ID or public alias**. Native actor IDs remain separately preserved in exact source-record metadata with explicit state. A newly observed native profile-version field would need its own faithful mapping review rather than being overwritten by that discriminator.

## Validation required after review — not executed

Before any implementation, write the owned-PG18.6 full workflow and retain an old-schema RED for missing native states/standard/totals/layout. Then independently verify: exact actor profiles against wrong/global/source decoys; duplicate/missing/leading-zero source locators and historical slot overlap; lineup0/'09'/NULL/absent/false and exact order; repeated stat keys with empty group/period and empty format; large exact numeric versus string/bool; H2H totals with empty list, finishedfalse/0–0 and unresolved IDs; no-op retry; correction A/B and independent C; old v1 byte/ETag compatibility; metadata-only HEAD/304; real readonly role; source-free tracked export and cleanup. No case in this proposed-amendment matrix has been run.

The patch, static consistency check and diagnostic metadata are review inputs. They do not constitute model approval, SQL validation, complete source coverage, functional reader routes or permission to produce/apply migration014.
