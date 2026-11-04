# Frozen SQL match details — proposal before E2E and implementation

**Current direction:** AMENDMENT_REVIEW.md, FIELD_MATRIX.json and PROPOSED_MODEL.patch.json now take priority: review native field fidelity and a proposed minimal model amendment first. The partial SQL adapter below is retained as an earlier proposal only; it is neither authorized for implementation nor a functional route. No model/SQL/service has been changed.

Suggested commit: `docs: specify frozen Pro match detail readers and fidelity gaps`.

This is the initial **protocol/read-only contract review**, not an implementation or acceptance receipt. Only this new directory is owned. No backend/frontend/normalizer/model/migration/CI/worklog is changed; no source service, cloud, existing database, commit or deploy is used. The next phase requires ROOT's explicit scope decision, then a complete owned-PG18.6 HTTP E2E written and run RED **before** reader code. Production remains flagOFF; complete data/backend acceptance remains a separate gate.

## Four routes and current feasibility

All proposed routes keep the existing path family, accept only `v`, support GET/HEAD, and are dispatched exclusively inside the Pro flag. With `v` they resolve one actually published ready build. Without `v` they resolve the current accepted publication and reject ambiguous match membership; no legacy router/source fallthrough is allowed for a recognized Pro detail path.

| Route | Existing consumer contract | Approved typed destinations | Proposed scope and gaps |
|---|---|---|---|
| `/api/pitchapi/matches/{id}/events` | MatchSections.Events and MatchEventHighlights expect `data.events[]`: ID, event_type, team/player, sub_in_player, minute/minute_added, is_penalty/is_own_goal, score_home/away | `ingest.match_coverage(feature_code='events')` + parent-bound `football.match_events`; aliases/profiles | SQL core is feasible: preserve exact parent list order, source_event_id, text/bool/NULL/0 and both actors. Generic related_player does not prove sub_in_player. Native per-field absent-vs-null and original nontext ID types are not recorded. No invented actor role or event ID |
| `/api/pitchapi/matches/{id}/lineups` | `data.home_team/away_team`, `home/away.{formation,confirmed,starters[],subs[]}`; player_id/name/shirt_number/is_captain/pitch_x/y | `football.match_lineups`, `match_players`, selected match_teams; source_records metadata; typed shirt/position states | Only a reconciled canonical observation is readable. No destination for native `lineup.standard`; no member ordinal or FK to a lineup version; no side/list presence-state columns. Native order needs explicit per-player source-record ordinal/locator proof. Unknown coordinate frame is not projected onto the formation pitch |
| `/api/pitchapi/matches/{id}/stats` | MatchStatistics and TeamStats expect `data.periods[].{period,groups[].items[]}`; items use key/title/format_type/home/away; `periodStats` also retains homeRaw/awayRaw | `football.team_match_metric_values` + exact metric/period definitions and source_metric_mappings; optional common `team_match_stats` consistency check | Native scalar number/string/boolean/null/absent is representable. Registered raw keys can be mapped only uniquely. Per-observation group title/item title/format_type and all empty nested-container states are not stored. Source order can be used only when explicit source-record coordinates prove it; otherwise full native grouped payload is blocked, not reconstructed alphabetically |
| `/api/pitchapi/matches/{id}/h2h` | MatchSections uses `data.recent_matches[]`; MatchContext separately computes pre-match form/H2H from season/history downloads | Parent-bound `football.match_h2h_entries` + resolved canonical matches/sides/scores; aliases/profiles | Ordered entries are feasible. Native H2H totals and native finished bool have no destination and must not be inferred from the list/scores/status. This route does not replace MatchContext's full season form, averages, rest days or player cohorts. Cross-edition link tokens require a separate proven frozen binding |

These are **partial typed SQL projections**, not proof that the current importer supplies complete readable observations or that every legacy native field is reconstructible. A reduced projection must be accepted as a new public contract; otherwise the corresponding native route stays unavailable. No014, opaque JSON payload, quality_flags/parse_rule escape, provider retry or file fallback is proposed.

## Representation and compatibility decision proposed

Use a distinct persisted build/publication `representation_version`:

`summary-v1-shots-v1-details-sql-v1`

The existing `summary-v1-shots-v1` adapter remains registered and byte-compatible. The `pro1.<build>.<digest>` token already binds representation_version/code/dependency contracts, so a new build/version gets a new token without changing token grammar. Do not relabel existing builds/publications or silently start promising details under old v1. New detail routes requested with an old token return404 `UNSUPPORTED_REPRESENTATION`, `no-store`, with no family materialization or fallthrough.

Preserve the old pinned manifest's fields, ordering, body, ETag and four capability fields exactly. A new representation may add a versioned per-edition detail capability descriptor **only for that representation**, e.g. `details:{contract:'match-details-sql-v1',events:true,lineups:true,teamStats:true,h2hEntries:true,nativePayload:false}`. The old edition's serialized entry stays unchanged. A mixed mutable manifest must not imply a detail capability for every edition. Existing summary/shots DTOs and profile policy remain v1 under both adapters; changing either would require its own representation decision.

Proposed new success envelope: `{data:{detailVersion:1,contract:'match-details-sql-v1',representationToken,collectionState,...familyFields}}`. Family core keys remain events/home+away/periods/recent_matches where representable; source/projection state fields distinguish retained typed values from public/catalogue labels. The capability descriptor explicitly refuses a native-payload completeness claim. Exact native fields lacking destinations are absent from this contract and listed as unsupported in the contract documentation; they are never synthesized as false/0/empty. ROOT must accept this reduced contract before code.

The current ProFootballDataClient refuses unsupported endpoints, while MatchSections/MatchStatistics/MatchEventHighlights use legacy caches and MatchContext loads season/history files. Merely adding routes will not connect these React views. Future frontend integration must use token-aware bounded clients/hooks and a Pro context adapter; that is outside this backend protocol phase. Current consumer conversions (shirt_number `||`, minute_added truthiness, `periodStats` parseFloat and Timeline's presentation sort) are not source-fidelity guarantees and need their own browser evidence later.

## Explicit observation and identity selection

1. Resolve the published ready build and sealed snapshots using metadata only. Dataset generation `dg` controls sporting facts, match membership, periods/metric/mapping versions and coverage. Catalogue generation `cg` controls public aliases and selected profile versions. Never use a `*_current` view or a later build's dimensions in a response pinned by `v`.
2. Every interval test is `recorded_from_gen<=g AND (recorded_to_gen IS NULL OR g<recorded_to_gen)`. Inline facts require `is_canonical AND NOT is_deleted`. Source, logical parent match/team/actor and selected membership must agree. A physical revision FK proves an anchor, not its current selection at `dg`; join selected logical parents as well.
3. Select **one canonical coverage observation** for `(match_id,feature_code)` at `dg`. More than one is503 ambiguity. No row means unknown, not an empty collection. A noncanonical provider observation is not promoted because its timestamp/ID is larger or because canonical values are missing.
4. Events/H2H children join the entire parent key `(match_id,source_id,feature_code,variant_key,recorded_from_gen)` exactly. Order events by source_ordinal and H2H by entry_ordinal; event_seq is the recorded within-parent key, not permission to repair a missing/duplicated source ordinal. Reject invalid order bindings rather than sorting by minutes, timestamps or actors. An ordinal is not an inter-version identity; event ID remains source_event_id, including empty string/NULL, rather than a fabricated stable sequence ID.
5. For lineups/stats, select canonical inline facts at `dg` from the accepted coverage source/variant and explicit registered observation-membership rule. Both sides must belong to selected match_teams. No mixture of a normalized canonical cohort with unrelated archived noncanonical players/metrics. If metadata cannot bind a complete observation or native ordering, fail closed. Repeated source stat items must not be silently deduplicated by metric key; a canonical scalar projection cannot be labelled a lossless duplicate-preserving native list.
6. Public names use the existing explicit ranks, at `cg`: same-source canonical provider_global with variant provider:exact; then same-source legacy_normalized_global; then global with manual provenance and NULL source. Ties at the best priority reject503; ID/timestamp/observed_at never breaks ties. A selected NULL display_name stays NULL, not a fallback name. An existing physical profile reference proves actor membership but is not permission to serve mutable/later catalogue data.
7. Public aliases are selected at `cg`; use the existing v1 public-alias policy when multiple valid aliases exist, not an observation's row ID. Preserve native source IDs in their typed source fields; an unresolved actor or native match ID is not assigned a guessed public route ID. Source-native ID types not recorded by the model cannot be claimed recovered.
8. Family facts use the coverage source for actor profile selection. Resolved H2H canonical previous-match facts use that selected match's source; retain the H2H row's observed labels/time/status/scores as separate typed observation fields. No resolved value overwrites the stored native observation silently.

## Collection and scalar rules

- Present and proven empty collections return200; empty means `collection_state='empty'` and count0, not merely a query returning no rows. Unknown/absent/null/unavailable return404 `NOT_COLLECTED`, `no-store`, retaining the exact collection-state marker. SQL NULL parent/count/field and source explicit null/absent are not conflated. Count/shape inconsistencies reject503 rather than returning a truncated/empty result.
- A missing scalar metric row means unknown. A metric row's value_kind distinguishes number, string, boolean, null and absent. Never parse strings (`''`, `'09'`, `'4/7'`, `'0'`), convert false to0, infer a denominator, or infer absent from a missing row. Preserve numerator/denominator/source_display only when stored; metric and period definitions are the exact versions anchored by the fact and valid at `dg`.
- PostgreSQL numeric defaults to a JavaScript string through pg. JSONB decoding can instead lose numeric precision. The proposed details adapter must serialize exact SQL-generated JSON text without an IEEE Number round-trip, keep number tokens numeric, and have an independent Decimal HTTP-body oracle. Existing summary/shots serialization remains unchanged. Native lexical spelling beyond the stored numeric value is not claimed.
- Native shirt/position types are restored from their explicit *_state and *_source_number columns, not from their text projection. Most other nullable columns lack such states: those cannot establish native absent-vs-null. Frame/role/field-presence uncertainty stays explicit or unsupported.
- Lineup coordinates are raw placement coordinates, not shot metres. Only a separately proved declared fractional frame may populate legacy pitch_x/y; unsupported frames retain raw coordinates and an explicit unprojectable state. No arbitrary division, rotation or role inference.

## Concrete gaps and existing producer/consumer limits

| Gap | Required disposition before a fidelity claim |
|---|---|
| Native H2H totals/finished | No approved destination: refuse these fields. Do not repurpose analytics.metric_totals, infer totals from a possibly partial list, or infer a native bool from scores/canonical status |
| Native lineup.standard | No field; lineup_type's enum is confirmed/predicted/observed/unknown and is not a destination for standard |
| Native lineup member order and lineup-version membership | match_players has neither ordinal nor lineup FK. Existing family-root source_record_id alone cannot prove member order. Require registered per-member ordinal/locator metadata or decline native ordered output |
| Null/absent/empty home/away/starters/subs/periods/groups | One family coverage state does not encode every nested container state; no default `{}`/`[]` may be claimed an exact reconstruction |
| Native stat group/name/title/format and duplicates | Numeric/value-state storage is not a source-group serialization. Only proved metadata order/registered labels can be used; normalized labels/order must be named as such in the new adapter |
| Generic event related_player versus sub_in_player | No role discriminator proves equivalence; retain related_player, refuse the sub-in alias unless an accepted source contract explicitly proves the role |
| Nullable event fields and native ID type | Nullable columns lack per-field absence/type-state for these fields. Do not invent a source absence marker or original numeric ID from stored text |
| Current family mapper | It uses `event_type = row.get(...) or 'unknown'`, losing an observed empty event type; lineup/metric observations can be noncanonical; stats/lineups do not currently create a complete canonical coverage parent. Readers cannot repair lost/uncurated observations. This is a static code finding, not a real-source audit or permission to modify the mapper |
| H2H links to another edition | A token pins one edition. A public alias alone does not supply a frozen representation for a previous match in another edition. Preserve identity/observation but make no navigable link unless membership/token binding is proved; never look up today's publication for an old response |
| MatchContext | H2H entries alone do not supply complete before-kickoff season form, averages, rest or player usage. The existing file/season algorithm must remain unavailable in Pro until separately designed; no implicit season download |

## Metadata, bounds and HTTP behavior proposed

Recognized paths never return null to the legacy router. Validate method/path/public match ID/token, allowed/duplicate query parameters and version before family access; invalid syntax performs0 SQL. Keep no-store on404/400/409/413/422/503 errors. Missing capability/unknown collection is404, ambiguous membership409, invalid/ambiguous typed state503, and encoded-size excess413.

Proposed budgets to prove, not measured results: at most4 SELECTs for an uncached successful GET (build metadata, match+coverage metadata, one bounded family/identity query and at most one bounded companion query); at most2 SELECTs and **zero family/profile/DTO materialization** for HEAD and matching304. Cold validators include `v`, route and representation adapter in the ETag. A304 is permitted only for a supported published representation and accepted present/empty coverage; unknown/unavailable always returns no-store404. No wall-clock sorting, implicit latest observation, N+1 query or unbounded season materialization.

Proposed hard caps:1000 events;500 H2H entries;2 lineup headers and80 players;16 periods and1000 retained team-metric rows. Fetch cap+1 when a body is needed, verify counts and reject excess; never return a silently truncated list. Maximum encoded body1MiB. Precise count semantics for lineup headers/members and stat rows must be registered by the accepted producer contract; present coverage without that binding is not proof of completeness. The publisher must validate the new contract before exposing a new ready details build. HEAD metadata readiness is not an independent full payload-validation proof.

## E2E failure matrix — to write and run RED before reader code

Use one owned PG18.6 cluster, exact sealed012/013/bootstrap/grants, complete synthetic source-free fixtures, the real Bun HTTP handler and actual statarena_runtime role. No source service, normalizer execution, frontend, remote database or schema amendment. The fixture must include representable canonical facts **and** separately labelled noncanonical/unsupported/partial producer states so success does not hide these gaps.

| Complete workflow/failure | Expected observable result |
|---|---|
| Before adding the four routes | Real HTTP RED through the current flagged router, saved before implementation; no mocked handler success |
| A/B/C published under old v1 | Exact old manifest/list/summary/shots bodies+ETags remain unchanged; new detail path with old token404 unsupported/no-store/no fallthrough |
| New details build for A/B and independent C | New version/token, explicit per-edition capabilities; old tokens stay readable via the old adapter |
| Every new route, present and accepted empty | Known typed values and order exact; zero distinct from NULL/unknown, explicit empty distinct from uncollected |
| Unknown, absent, explicit null, unavailable family | Separate state markers and no-store404; no child scan and no fabricated empty list |
| Two sources, noncanonical/latest-ID/timestamp decoys | Only declared selected observation served; ambiguity fails; later source/row ID never wins implicitly |
| Events reorder/correction, duplicate minutes and empty type | Parent-bound order and native IDs/empty event_type/bool false/score0 preserved; ordinal not promoted to stable ID |
| Lineup source order, shirt0/'09'/NULL/absent, captain false | Exact supported state transport; missing order/frame/standard proof explicitly refused; no guessed starter/coordinate |
| Stat repeated keys/groups, mixed scalar kinds and large exact numbers | No dedup/coercion; independent Decimal/raw JSON oracle; unrepresentable source-group metadata refused, no fake native layout |
| Related actor/sub-in ambiguity | Generic actor retained without inventing role; unsupported native field refusal visible |
| Resolved/unresolved H2H, blank time/status, score0 | Canonical facts at dg and observed typed fields both preserved; no invented route ID/totals/finished; unsafe cross-edition link unavailable |
| Cold HEAD and If-None-Match for four routes | Correct headers/status and <=2 metadata SELECTs; no events/lineup/metric/H2H/profile materialization |
| Caps and contradictory counts | Bounded queries, explicit no-store error, no partial body accepted as complete |
| Data correction then later shared catalogue correction | New A/B tokens/typed values/labels; old A's bodies/ETags remain exact; unchanged C retains body/token/304 |
| Same input/no-op republication | No new accepted version/build/publication or token; retain the existing publisher's labelled no-op limitations |
| Runtime permissions | Actual role/access mode recorded; INSERT/UPDATE/generation helpers rejected even with session read-only mode disabled |
| FlagOFF, invalid params and unsupported path | Legacy flagOFF baseline preserved; recognized Pro errors never reach legacy/files/provider; all failures visible |
| Cleanup and exact sources | Stop owned PG/API, remove owned temporary data, pin exact tracked/explicit source export and source/model/SQL hashes; save setup/commands/request bodies/headers/SQL counts/logs/results |

No row in this matrix has been executed for these new routes. After scope approval, the first deliverable is the real HTTP E2E RED and its fixture/input manifest, then implementation, then independent green evidence. Synthetic fixture success will not certify ingestion of genuine event/lineup/stat/H2H data, the production publisher, Vercel/CDN, frontend feature parity or full backend/data acceptance.

UX tradeoff: unsupported native/context fields remain unavailable rather than displaying guessed data. DX/AX tradeoff: the explicit version registry, typed-state serializer and failure contracts add maintenance work, while making source/version decisions inspectable and reproducible. This is not an unconditional improvement in every dimension.
