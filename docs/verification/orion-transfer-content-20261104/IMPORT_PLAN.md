# Typed-import delta prepared from the exact content scope

This is a plan for a later reviewed importer. **No row was imported, no canonical version selected, no014 proposed or generated.** The approved model remains `18da43f9…`;012/013 remain sealed. Physical/selector/ID qualification is separate from complete field mapping and remote acceptance.

## Positive observations and native collection states

| Source observation | Qualified content delta | Existing typed destinations | Gate before import |
|---|---|---|---|
| League `l_3FJFUl`,2026/2027 | Both versions contain306matching match-ID sets. Neon has81finished/scored and225not-started/null-score rows; old AWS has80/226. The exact changed row/value pairing is not retained by this bounded summary. | `football.competitions`, `competition_seasons`, `matches.match_date/kickoff_at/status`, `match_teams`, `match_scores.goals`, `match_observation_details.source_time_text`, public/source aliases | Pair records by exact provider ID; retain both observations. Verify score scope/basis, time precision and all fields before writing. No additional match identity is demonstrated, and no overwrite follows an aggregate count or import clock. |
| Match `m_2vsKSO` | Positive detailed response for an already catalogued identity; status, season, teams, round/date/time; referee/stadium/scores explicitlynull | `matches`, `match_teams`, `match_scores`, `match_observation_details.source_*`, source/alias tables | Preserve null instead of zero. Referee and has_playoff have no direct typed destination demonstrated. Do not hide them in quality JSON/notes or infer stages/referee identities. |
| Events, momentum, team-stat periods for `m_2vsKSO` | Three explicit empty lists: `events=[]`, `points=[]`, `periods=[]` | `ingest.match_coverage(collection_state='empty',observed_row_count=0)` with a reviewed coverage policy; corresponding fact tables get no invented child rows | This records the provider observation at its knowledge generation, not a final lifetime zero. No numeric player/team metric is inferred from an empty family. |
| Shots for `m_2vsKSO` | `periods=null`, not an empty list | `ingest.match_coverage(collection_state='null',observed_row_count=NULL)`; availability remains distinct from HTTP200 | No zero shots, no empty-success substitution. Existing null/empty/unavailable states suffice for this collection distinction. |
| H2H `m_0xOQtL` | Neon33ordered recent entries,32finished/1not-finished; old AWS explicitempty list. One entry has null scores. | `match_h2h_entries` with exact source ordinal, source/provider/parent version, labels/teams/scores/native time; `match_coverage` retains present33 versus oldempty0 | Preserve both versions without unproved source recency. No previous-match ID is invented from names or a date. Provider totals home_wins/away_wins/draws/total_matches and native finished boolean need an exact destination/mapping; `status_source` is text. |
| Lineups `m_0xOQtL` | Neon2confirmed team lineups and40listed players versus AWS2unconfirmed lineups and39players. Source lineup_type is `standard` versus `predicted`. Membership/role ID differences are listed below. | `match_lineups.formation/confirmed/lineup_type`, `match_players.squad_status/is_starter/is_captain/raw_pitch_x/raw_pitch_y`, native position/shirt companions, scoped `player_profile_versions` and source IDs | Model lineup_type admits confirmed/predicted/observed/unknown, notstandard. Freeze a meaning-preserving mapping before insertion. A listed/substitute player is not automatically played. Keep original source/period/parent cohorts and both lineup variants. Coach names do not prove identity or a tenure. |
| Heatmap `m_0xOQtL`, frame `home_ltr` |30player and2team collections:1344rows each containing3integers,4032numeric elements, varying collection lengths. | `match_heatmaps` and atomic `match_heatmap_cells(column_index,row_index,action_count)` once the format is qualified | Three-element rows alone do not establish a dense grid or the meanings of positions. Qualify coordinate/count order, dimensions, origin, bounds, duplicate cells, units and missing-cell semantics first. Never fill unobserved cells with zero. |

The current normalizer at `dashboard/scripts/orion_pro_normalize.py:1069` uses `rows,columns=len(cells),len(cells[0])`, then visits every scalar at1077. On this newly observed representation it would treat1344triples as4032dense numeric cells. Its previous green source run does not qualify this format. A source-driven oracle and failure cases must precede any importer change; no such change is made here.

Lineup ID qualifications, preserving each side/role:

- Away substitutes: Neon-only `p_0Rtil2`; AWS-only `p_1xOSBK`.
- Home starters: Neon-only `p_3JNLfM`; AWS-only `p_0oBqIG`.
- Home substitutes: Neon-only `p_0oBqIG`, `p_1GVseZ`; AWS-only `p_3h0f7v`.

These identify changed source observations, not globally new players or identity errors. Resolve provider IDs through approved identity/source bindings; preserve match-scoped profile names/types without inventing a global biography or participation.

## Negative, changed-pointer and rejected observations

The prior inventory's six HTTP404keys are **metadata-only in this phase**; their bodies were outside this positive-content scope and were not read. Preserve negative status/provenance and distinguish unavailable from empty/null. `resource_fetches` may describe only a real documented attempt: a cached resource row/import timestamp does not justify fabricating a past HTTP request. No sports fact or zero is created from404.

The three changed pointers have different selected typed digests. The bodies establish additional finished/scored information, H2H entries and lineup differences; they do **not** establish a supplier revision order. Storage LastModified, catalogue updated_at, SQL indexing and import clocks are not provider clocks. Keep both variants/values and leave canonical promotion to a separately accepted policy. The two manifest versions select identical Ligue1paths/SHA/sourceDigest for2025/2026 and2026/2027; they authorize no new partition download or dataset rewrite. Array positions changed, so the791positional manifest differences are not791business updates.

All twelve observation contexts have matching expected response IDs and exact frozen resource selectors. The old AWS H2H/lineup archives each have16members; only the unique `m_0xOQtL` member, ordinal2, is qualified here. A selector collision, contradictory ID, changed fingerprint, unrepresentable value or unknown useful field must block the future import and emit bounded diagnostics without a raw response. No such ID contradiction was observed in this scope; global identity completeness remains unverified.

## Provenance, versions and acceptance order

1. Freeze a complete field→typed destination/type/state/unit/variant matrix for these selected observations, including all gaps above. Reuse `sources`, `source_datasets`, `import_runs`, metadata-only `source_documents`, exact `source_records` locators and versioned relation/field contracts. No opaque body, field-state registry or hidden sports JSON.
2. Prove local import idempotence and exact old/new selection using the approved generation/seal mechanism. Bind changing parents, participants and definitions to the same selected dataset cohort. A correction creates retained values; equal content/dependencies reuse their selected versions.
3. Before an RDS import, qualify source numeric ranges/precision, collection formats and identity dependencies, then run an independent source→typed oracle over every useful selected field and both retained variants. No silently dropped field and no source-cache timestamp used as supplier authority.
4. Publish/read/cache through one accepted dataset/catalogue/representation token only after data and backend acceptance. This content audit does not approve public cutover, collectors or cleanup.

## Conditional future removal of old bodies

No body is removable now. The old AWS league blob `raw/pitchapi-world/blobs/9c207f8df81b41a60136a6e56a707efeff2e1550d1a17b0a3c82e2c072dfe3a0.json.gz` could become eligible only after all306records, native states/values, retained source variants, identity/media dependencies and frozen consumers have a complete typed oracle and non-dependency proof.

The old AWS H2H and lineup files ending `5d38e74a477b667b00375b1a.json.gz` each contain16members. Qualifying one member cannot authorize deletion of either whole archive. All16members and dependent builds/consumers require reconciliation first. The512archive metadata agreements alone remain insufficient.

The two old manifest versions cover6seasons/230references; matching two Ligue1pointers cannot authorize retiring those catalogues or their legacy consumers. Neon-only positive bodies likewise remain until every useful field—including the unresolved nulls, totals, lineup category and heatmap contract—is represented and jointly accepted. Essential media and referenced retained versions are preserved. No deletion/overwrite is proposed by this evidence.

Suggested commit: `docs: qualify exact Neon AWS content differences for typed import`.
