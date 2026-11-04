# AWS source scope for the approved Pro pilot

Read-only reconnaissance, **4 November 2026, 18:59–19:04 Europe/Paris**. Target model SHA-256: `028c221d4cd45ad809a2340e62f34ab9df191c593b23c0c45d5f44587eb35a8c`. The model has 103 tables, 94 active; this file proposes input and mapping scope. It does not implement or accept the typed import.

## Decision

**Ligue 1 `l_3FJFUl`, 2025/2026 and 2026/2027 is viable for a real local typed pilot from sources already on AWS.** Read the existing indexed legacy documents temporarily and transform them in memory. The friend continues to own the initial Neon→AWS physical transfer. No second transfer, collection, provider call, S3 payload download, new raw copy, RDS write or process change occurred.

The two selected partitions have no `statarena_app.partitions` row and zero serving matches/fixtures at the first snapshot. Their absence in serving is not source absence. The current AWS manifest resolves both source partitions.

## Exact selected inputs

| Season | Source fixtures | Finished normalized matches | Performance rows | Shots | Player profile variant rows | Teams | Normalized fixtures |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2025/2026 |306|306|12200|7618|665|18|306|
| 2026/2027 |306|81|3237|2177|486|18|306|

These are exact scoped row counts, not whole-AWS totals. The current 2026/2027 source inventory has 81 finished and 225 upcoming fixtures. All 387 finished fixture IDs occur in the selected normalized matches; all 612 source fixture IDs occur in normalized fixtures; no normalized match ID lacks a source fixture. Those checks establish key coverage only, not field equality or participation fidelity.

| Season | Current source path | Physical gzip SHA-256 |
|---|---|---|
| 2025/2026 | `computed/dashboard/2025-2026/l_3FJFUl-1f2cbed49d570024ea3a0ee7.json.gz` | `08ca2af5bbc78703da76839a7d332a7a40f4dd18486972b363af49bd17ffeaa6` |
| 2026/2027 | `computed/dashboard/2026-2027/l_3FJFUl-3403d71ab77e5287be09e9c2.json.gz` | `b49ea464a213c008cbe9af600e37e90048d5936f5df6db9b7b0061ea4a754ec3` |

Manifest: `computed/dashboard/index.json`, SHA-256 `4295ab0eedcaf225cb2c04ac8e4cc56e1531a31221e76fcd161b4890621c3ff2`. Two other 2026/2027 computed versions exist; choose the current manifest pointer, not the lexicographically first or largest object.

The selected decoded partition documents measured 5,962,225 B and 3,389,852 B. They were decoded only in memory and summarized as counts, identifiers, types and hashes; no source body was saved. Normalized partition rows are a comparison oracle, not a substitute for the 13 original match families.

## Archive, resource and profile availability

- All 612 source fixtures have an exact `statarena.observations`→`statarena.shards` relation. The 512 distinct referenced source paths all have a current object/index SHA match, status `ready`, one current error-free indexed document and zero indexing errors. This does not establish that all responses inside every document contain data.
- The 2025/2026 archive advertises 13 families for all 306 fixtures. The 2026/2027 archive advertises all 13 families for 80 fixtures and only `match`, `lineups`, `h2h` for 226 fixtures (225 upcoming plus `m_0xOQtL`). The latter finished match has all 13 latest resource families separately, with exact current indexed source versions inspected. Do not accept the archive family count as a missing-data total.
- Selected original members `m_0anhgc`/2025/2026 and `m_2SY7ro`/2026/2027 each resolve 13/13 families uniquely, status 200, non-null data. Source paths, actual document IDs, physical and decoded hashes and field/type/state matrices are in `resolvedArchiveFamilyShapes` of the JSON receipt.
- The scoped normalized player identities deduplicate to 839 players; teams deduplicate to 20. Exact resource lookup finds 777/839 player profiles and 20/20 team profiles with status 200, current index versions and no indexing error. Seven explicitly selected member profiles resolve their source ordinal and return the expected provider ID. Whole profile shards were also shape-sampled earlier; those earlier shapes include other observations and must not be read as per-player success.
- 62 players lack an exact `/players/{id}`,`{}` resource row. They still have observed normalized/profile identity fields; do not invent a full provider profile, delete the player, or label the profile absent from every AWS legacy source. The importer must retain the observed variant, record this lookup gap and independently resolve other existing AWS paths if a full profile is required. No new provider request is authorized by this gap.
- One existing standings projection is keyed by `{"competition":"l_3FJFUl"}`. Historical 2025/2026 standings and full ranking, honours, association, stadium/coach and media inventories were not proved in this bounded run.

**Exact 62 missing profile resource keys:**

`p_0ARucX`, `p_0S8MLK`, `p_0U63Ok`, `p_0UQxff`, `p_0g7MVs`, `p_0h4Kt6`, `p_0ifA8o`, `p_0lsEQF`, `p_10Yk58`, `p_15HAij`, `p_1CP0m6`, `p_1DRkpy`, `p_1DeM1A`, `p_1IVs0U`, `p_1ZzTV7`, `p_1aVfCd`, `p_1dhlmT`, `p_1hu4Ln`, `p_1msJkW`, `p_1nTyR7`, `p_1pNtUs`, `p_1s7jj1`, `p_1wmmuD`, `p_1yFMlv`, `p_21cwbG`, `p_2Cb2iM`, `p_2Izuyz`, `p_2VRj6w`, `p_2aYMcc`, `p_2di7x3`, `p_2egHmI`, `p_2gMHUC`, `p_2j00Om`, `p_2j8f6K`, `p_2jSxQk`, `p_2t73Kf`, `p_2vnoib`, `p_2zmGFX`, `p_325ea7`, `p_349pGE`, `p_35JgBD`, `p_360I2f`, `p_37cWNi`, `p_38kFuy`, `p_3A16ai`, `p_3CEay1`, `p_3EnNpy`, `p_3PTXv2`, `p_3Q9cqn`, `p_3lWKKg`, `p_3qKNVr`, `p_3qeS7E`, `p_3td9w5`, `p_3xlD33`, `p_40SVrw`, `p_49qpTs`, `p_4JNbto`, `p_4QjICI`, `p_4UwC2K`, `p_4Z0dhF`, `p_4afgS0`, `p_4ffAc0`.

## Small representative real import first

1. Bootstrap the approved 103-table model locally, with the 94 active tables eligible for scope and the 9 model tables reserved. Record the model SHA and deterministic approved reference definitions; do not deploy DDL on RDS in this pilot.
2. Use both exact current partition pointers as the comparison baseline. Import stable league/team/player/match identities for the scoped 612 fixtures, preserving provider IDs and normalized public/profile aliases; do not treat 1151 season profile rows as 1151 distinct people or 1151 distinct profile revisions.
3. Start full fact normalization with the two real archived matches `m_0anhgc` and `m_2SY7ro`. Read their 13 family documents by exact current SHA, select the unique member by `matchId`, retain its actual `documentId`, and map every selected value to typed columns/children. Read direct latest sources for `m_0xOQtL` as the mixed archive/current-resource case. Include upcoming `m_2vsKSO` for missing/not-yet-played semantics.
4. Resolve selected profiles by resource reference path plus exact ordinal/document member, then verify the data ID equals the requested provider ID. A shard filename or status 200 on the resource row alone is insufficient. Keep match-level player IDs, player/profile revisions, team membership, provider and period dependencies exact.
5. Run the previously frozen SQL/application E2 E contract: real import, lossless typed readback, correction and old-snapshot recalculation, source-normalizer variants, retries/idempotence, interruption and competing writers, atomic networks/grids, native state distinctions and shared-dimension A/B/C behavior. Synthetic correction values must be labelled; never alter AWS originals to create a case.
6. Expand the same importer to all 387 finished match identities plus 225 upcoming fixtures only after the representative cases pass. Measure the same corpus and selections before/after. The 94 table matrix below marks deliberate gaps; no claim that every active table can be populated from these two seasons alone.

## Field and variant contract required before acceptance

The JSON receipt provides observed source paths/types/state counts for 26 resolved archive members, 20 initial sampled documents, 12 profile shards, 7 exact selected profiles, 5 fixture examples and all rows of the two normalized comparison partitions. This is a draft input matrix. A complete per-column mapping with explicit accepted/unavailable/rejected outcomes remains required; no purge or fidelity acceptance follows from this inventory.

| Family | Observed forms | Required typed treatment |
|---|---|---|
| Envelope and identity | Direct `{data:...}`, profile shard `{observation:...}`, archive member `{matchId,documentId,response}`; ordinal and member selectors | Resolve the correct member, provider and physical version before parsing; store metadata/locators, never the response body |
| Match/fixture |612 fixture IDs; status strings, dates, native season; older/current field sets differ | Match identity plus selected match/team/score revisions; preserve missing versus explicit null, upcoming scores and source timing |
| Players/lineups | `position_id` null in player stats and numeric in lineups; lineup shirt numbers are strings while network/profile numbers can be numeric; starter/captain booleans | Selected player profile and match-team membership; keep native value/state/type through an explicit representability contract; never use a display name as a provider identity |
| Player metrics | Nested metric groups; scalar numeric `stat.value`; xGOT and was-fouled values can be null; empty metric keys occur | Typed common statistics plus approved metric-definition extension rows, period and source mapping; key labels/units, zero/null/missing/empty state remain distinct |
| Team statistics | period→groups→items; home/away values are strings, format types can be empty | Parse accepted count/decimal/percent/ratio forms explicitly; retain source text/type/format in the bounded typed contract and reject unrepresentable new variants |
| Shots | Period-specific shot IDs, numeric xG/coordinates, optional keeper/added minute, booleans | Typed shot/coordinate fields with exact selected match-player/profile dependencies; preserve order and optional-state differences |
| Advanced teams/players | Typed subgroups for carrying/passing/etc; numbers, zeros and nulls | Map to the advanced business columns; do not place an opaque source subgroup in JSONB |
| Events and momentum | Ordered arrays, period and added minute; event fields may be empty strings/null | Version the useful fact/collection grain, preserve ordinals/timing and actor identity |
| Passing network | Complete family with networks/nodes/edges; numeric positions and pass counts | New atomic network parent version; typed nodes/edges share that parent and selected participating identities |
| Heatmaps | Grid/frame/dimensions; team/player 2Dnumeric cell arrays including zero | Typed parent plus cells with coordinates/ordinal; enforce dimensions/uniqueness/bounds and atomic replacement |
| H2H | Observed aggregate plus match entries, some references outside the pilot seasons | Preserve rows and same-provider identity; link canonical matches only when resolved, keep observed snapshots without fabricating dependencies |
| Profiles/references | Normalized display/profile variants, country/position/image fields;62 missing full-profile lookups | Stable identity and immutable observed profile versions; explicit selected dependencies and source provenance; do not collapse a normalized profile into the newest full profile |
| Standings/rankings/honours/media | Only the competition standings projection and image URLs inspected here | Treat unverified families as open. No synthetic historical snapshots, new formula or media existence claim |

For every accepted source leaf, the importer matrix must name: exact source family/path/locator and version; target table/column or typed child; canonical/provider grain; native type/unit; absent/null/zero/empty/unavailable handling; variant and selection rule; source-record link; selected dependency revision; reconciliation assertion. Unknown or unrepresentable leaves block acceptance with a diagnostic rather than silent truncation.

## Numeric representability remains unverified

No maximum decimal scale, lexical precision, maximum magnitude or integer range was collected. Source bodies were disposed after their in-memory shape census; the saved `number`/state counts and hashes cannot recover that information. The 20-query budget is exhausted. A fresh precision inventory requires a separately authorized bounded read before importer implementation.

The exact approved model does **not** declare `football.shots.xg` as fixed-scale numeric: it is `double precision`, as are shot xGOT and many other metrics. `football.player_match_stats.xg` is unconstrained `numeric`. Eighteen active columns have fixed scale: `football.standing_rows.points` and `points_adjustment` are `numeric(12,3)`; sixteen team/association ranking entry/component value, points and coefficient columns are `numeric(16,6)`. The JSON receipt enumerates them. Ranking source values were not sampled and standing scalar values were not retained.

Neither fixed-scale numeric nor `double precision` is certified lossless by the observed `number` type. Before code, freeze real decimal/range/state cases and define accepted representations. Use decimal-aware in-memory decoding, compare exact values and reject unrepresentable values explicitly instead of relying on implicit rounding. The reconnaissance canonical hashes describe Python-decoded values; they do not prove original lexical decimal precision or source byte identity. Catalogue/index SHA agreement also does not replace an independent S3 byte checksum.

## Disposition of all 94 active tables

`SOURCE` means a representative source family was observed; `PARTIAL` means fields/definitions/coverage still need explicit mapping; `OPEN` means the required source or operational behavior was not established here; `GENERATED` is local run metadata; `DERIVED` must reproduce an existing accepted aggregation contract. None means implemented. The JSON includes each table grain, write mode and every target column/type/nullability.

| Target | Columns | Input status | Input group |
|---|---:|---|---|
| `ingest.sources` |6|GENERATED|Run metadata|
| `ingest.source_datasets` |8|GENERATED|Run metadata|
| `ingest.import_runs` |11|GENERATED|Run metadata|
| `ingest.source_documents` |22|GENERATED|Run metadata|
| `ingest.source_records` |8|GENERATED|Run metadata|
| `ingest.document_lineage` |4|GENERATED|Run metadata|
| `ingest.resource_fetches` |14|GENERATED|Run metadata|
| `ingest.media_assets` |11|OPEN|Media and jobs|
| `ingest.dataset_snapshots` |10|GENERATED|Run metadata|
| `ingest.dataset_snapshot_documents` |2|GENERATED|Run metadata|
| `ingest.quality_issues` |10|GENERATED|Run metadata|
| `ingest.identity_candidates` |11|GENERATED|Run metadata|
| `ingest.match_coverage` |23|GENERATED|Run metadata|
| `ingest.relation_contracts` |4|GENERATED|Run metadata|
| `ingest.field_contracts` |5|GENERATED|Run metadata|
| `ingest.reconciliation_runs` |9|GENERATED|Run metadata|
| `ingest.document_reconciliations` |8|GENERATED|Run metadata|
| `ingest.cleanup_items` |11|OPEN|Media and jobs|
| `ingest.collection_jobs` |9|OPEN|Media and jobs|
| `ingest.asset_jobs` |4|OPEN|Media and jobs|
| `ingest.dirty_editions` |5|GENERATED|Run metadata|
| `ingest.schema_migrations` |4|GENERATED|Run metadata|
| `ingest.public_aliases` |24|PARTIAL|Public identity|
| `football.countries` |17|PARTIAL|Reference definitions|
| `football.associations` |6|OPEN|Association and honours|
| `football.positions` |14|PARTIAL|Reference definitions|
| `football.periods` |15|PARTIAL|Reference definitions|
| `football.venues` |23|PARTIAL|Venue and coach|
| `football.coaches` |20|PARTIAL|Venue and coach|
| `football.competitions` |23|SOURCE|Competition scope|
| `football.competition_seasons` |21|SOURCE|Competition scope|
| `football.competition_stages` |22|PARTIAL|Competition layout|
| `football.competition_groups` |19|PARTIAL|Competition layout|
| `football.teams` |12|PARTIAL|Public identity|
| `football.competition_teams` |19|SOURCE|Competition scope|
| `football.players` |10|PARTIAL|Public identity|
| `football.player_profile_versions` |39|PARTIAL|Profiles and membership|
| `football.position_mappings` |15|PARTIAL|Reference definitions|
| `football.player_team_memberships` |27|PARTIAL|Profiles and membership|
| `football.team_aliases` |19|PARTIAL|Profiles and membership|
| `football.competition_source_ids` |14|PARTIAL|Public identity|
| `football.team_source_ids` |13|PARTIAL|Public identity|
| `football.player_source_ids` |13|PARTIAL|Public identity|
| `football.association_source_ids` |13|OPEN|Association and honours|
| `football.venue_source_ids` |14|PARTIAL|Venue and coach|
| `football.coach_source_ids` |14|PARTIAL|Venue and coach|
| `football.matches` |37|SOURCE|Match and lineups|
| `football.match_source_ids` |14|PARTIAL|Public identity|
| `football.match_teams` |24|SOURCE|Match and lineups|
| `football.match_scores` |23|SOURCE|Match and lineups|
| `football.match_lineups` |24|SOURCE|Match and lineups|
| `football.match_players` |39|SOURCE|Match and lineups|
| `football.metric_definitions` |23|PARTIAL|Metrics|
| `football.source_metric_mappings` |17|PARTIAL|Metrics|
| `football.player_match_stats` |54|PARTIAL|Metrics|
| `football.team_match_stats` |45|PARTIAL|Metrics|
| `football.shots` |53|SOURCE|Shots|
| `football.player_match_advanced` |60|SOURCE|Advanced|
| `football.team_match_advanced` |51|SOURCE|Advanced|
| `football.match_events` |28|SOURCE|Events|
| `football.match_momentum` |17|SOURCE|Events|
| `football.pass_networks` |24|SOURCE|Atomic spatial collections|
| `football.pass_network_nodes` |10|SOURCE|Atomic spatial collections|
| `football.pass_network_edges` |4|SOURCE|Atomic spatial collections|
| `football.match_heatmaps` |30|SOURCE|Atomic spatial collections|
| `football.team_coach_tenures` |26|PARTIAL|Venue and coach|
| `football.honour_definitions` |19|OPEN|Association and honours|
| `football.player_honours` |27|OPEN|Association and honours|
| `football.team_honours` |26|OPEN|Association and honours|
| `football.standing_snapshots` |18|PARTIAL|Standings|
| `football.standing_rows` |12|PARTIAL|Standings|
| `football.ranking_systems` |7|OPEN|Rankings|
| `football.ranking_snapshots` |16|OPEN|Rankings|
| `football.team_ranking_entries` |8|OPEN|Rankings|
| `football.team_ranking_components` |13|OPEN|Rankings|
| `football.association_ranking_entries` |8|OPEN|Rankings|
| `football.association_ranking_components` |13|OPEN|Rankings|
| `football.player_match_metric_values` |29|PARTIAL|Metrics|
| `football.team_match_metric_values` |28|PARTIAL|Metrics|
| `football.match_heatmap_cells` |5|SOURCE|Atomic spatial collections|
| `football.match_h2h_entries` |22|PARTIAL|H2H|
| `football.match_observation_details` |21|SOURCE|Match and lineups|
| `football.team_profile_versions` |40|PARTIAL|Profiles and membership|
| `football.association_profile_versions` |36|OPEN|Association and honours|
| `analytics.aggregation_builds` |16|GENERATED|Publication metadata|
| `analytics.publication_versions` |14|GENERATED|Publication metadata|
| `analytics.match_summary` |17|DERIVED|Existing aggregates|
| `analytics.player_competition_team_stats` |18|DERIVED|Existing aggregates|
| `analytics.player_competition_stats` |17|DERIVED|Existing aggregates|
| `analytics.team_competition_stats` |13|DERIVED|Existing aggregates|
| `analytics.competition_summary` |8|DERIVED|Existing aggregates|
| `analytics.player_search` |10|DERIVED|Existing aggregates|
| `analytics.metric_totals` |16|DERIVED|Existing aggregates|
| `analytics.catalog_publication` |4|GENERATED|Publication metadata|

## Reproduction and limits

RDS endpoint/database/user, verified TLS certificate, connection options, exact SQL/parameters, per-query timings and receipt hashes are in `source_scope.py`/`source_scope.json`. Libpq uses the existing pgpass indirectly; its contents were never opened or printed. There was at most one connection at a time, no parallel SQL, an 8 s statement deadline and 1 s lock deadline.20 SELECT queries used indexed metadata/PK/prefix/scoped access, with no full 2.8 Mdocument scan. Aggregate wall time inside query calls:18,279.634 ms; maximum 4,656.865 ms, including client materialization for the partition-shape query. This is not a benchmark or SQL p95.

The audit used three sequential repeatable-read, read-only snapshots. Initial 12 queries, supplemental 6 queries and final 2 queries are independently dated; do not treat the whole run as one atomic snapshot. Snapshot 1 identity/index catalogue was inspected before source reads. Current-document reads require object/index SHA agreement. AWS metadata content is a dated observation, not evidence that the physical transfer is finished.

Query 17 initially found 26 source files but selected zero members because the helper searched an absent shard-level `documentId`. This is a helper failure, preserved in `source_scope.supplement18.json`, not missing source data. Query 19 corrected member selection using exact `matchId`:26/26 unique responses,200/data. The final receipt retains both attempts. Initial whole-shard profile shapes also remain explicitly separate from exact selected-profile verification. No E2 E import was executed.

Commands actually executed, in order:

```sh
PYTHONPATH=/tmp/statarena-publication-test-python python3 docs/verification/orion-pro-pilot-20261104/source_scope.py
PYTHONPATH=/tmp/statarena-publication-test-python python3 docs/verification/orion-pro-pilot-20261104/source_scope.py --supplement
PYTHONPATH=/tmp/statarena-publication-test-python python3 docs/verification/orion-pro-pilot-20261104/source_scope.py --resolve-archive-members
```

For an independently authorized rerun, pass the same fresh `--out-dir /tmp/statarena-source-scope-rerun-YYYYMMDDTHHMMSS` to each command; this preserves the original receipts. Each three-command sequence consumes 20 queries. Expected: two live manifest pointers,612 scoped fixture keys, current source metadata, unique archive member selection and explicit profile lookup gaps. Values may change with the friend's transfer or other legitimate source updates. Review changed IDs/hashes/counts rather than expecting historical byte equality.

Open boundaries: entire per-column/variant transformation, every response inside all 512 source documents, all 839 profile selector identities, historic standings/rankings/honours/association/media sources, typed writes/reader acceptance, correction/concurrency/restart tests, measured gains, final migration and cleanup. None is declared complete by this reconnaissance.

Suggested commit: `docs: bound the Orion Pro pilot to verified AWS source partitions`.
