# Client methods, helpers and screens versus Pro coverage

Suggested commit: `docs: map Pro API coverage and define publication rollout`.

This is local-code inventory, not browser/hosted/full-data acceptance. The exact57 AWS path forms and query names are in API_ROUTE_MATRIX.json/.md; all data routes are GET/HEAD. The implemented local guard closes50 forms while preserving4 native readers and3 diagnostics/media exceptions. It does not finish their product parity. Model107 remains pending; only approved103 definitions (94 active) may be assumed.

## Public data client methods

| Client / public method | Actual operation | Pro behavior / remaining work |
|---|---|---|
| FootballDataClient.constructor | Initializes catalogue, status, fixtures/index/payload/shard Maps; no I/O | Inherited setup only |
| checkStatus | GET `/api/status` | Pro override marks known, performs no request; operational endpoint remains allowed |
| init | checkStatus then request(`leagues`) when configured | Pro override only checkStatus; no legacy catalogue request |
| request(path) | GET `/api/pitchapi/${path}`, validates error envelope | Pro override throws NOT_COLLECTED locally; direct helpers can bypass it |
| localFixtures(leagueId,season) | In-memory normalized season lists | Inherited method sees empty Pro season lists; not a SQL directory |
| loadFixtures | Entire completeFixtures scope; cup snapshot/source API/local fallbacks; caches full results | Pro override throws; ProMatchesPage uses bounded page instead |
| loadSupplemental | Packed source index/tables for json-packed, otherwise GET `/api/supplemental` | Pro override throws; no supplemental Pro route |
| loadShard(id) | GET `/api/archive/matches/{id}`, normalize and cache, null on error | Pro override throws; archive route also closed server-side |
| ensureEndpoint(match,section,force) | request match/section; except certain terminal statuses, archive shard fallback | Pro override throws; no native events/lineups/stats/H2H implementation assumed |
| normalizedRemote(match) | In-memory compatibility DTO, heavy arrays initially empty | No I/O, not evidence a native detail was collected |
| ProFootballDataClient.edition(leagueId,season) | Requires exactly one matching manifest edition; constructs ProMatchClient | Explicit competition choice when several match; no immutable aggregate token |
| ProFootballDataClient.summary(id) | Calls edition().summary | Native Pro route supported |
| ProMatchClient.constructor | Validates one edition + pro1 token; binds fetcher/cache | One frozen representation per instance |
| resourceKey(kind,id) | JSON key includes representation token | Used by match page/summary/shots; no request |
| request(path,parameters,validator) | Adds v, sorts params, reads bounded shared Pro cache | Only invoked by the three methods below; no archive/provider fallback |
| page(filters) | GET `/api/fixtures`, edition filters + v, limit default30/max100, cursor/status/from/to/q | Paginated, verifies generation/token, cursor and unique IDs; no total invented |
| summary(id) | GET `/api/matches/{id}/summary?v=…` | Validates representationToken, match ID, version/summaryVersion1 |
| shots(id) | GET `/api/pitchapi/matches/{id}/shots?v=…` | Validates accepted present/empty state and periods; lazy |
| loadProManifest | GET mutable `/api/dashboard/manifest` | Validates Pro shape/tokens; FootballContext separately loads pinned manifest?v |
| isProManifest / createProMatchCache | Shape predicate / bounded successful-response LRU,48 entries and8MiB per fetcher | These are not additional routes; pending requests deduplicate, oversized responses are not retained |

Source: services/football-client.js, pro-football-client.js, pro-match-data.js. Pro overrides also cover init/checkStatus/request/ensureEndpoint/loadShard/loadFixtures/loadSupplemental exactly; constructor/edition/summary are its other methods. No omitted profile/season/search method exists in these classes.

## Independent network helpers

| Helper(s) | Routes / traversal | Boundary under Pro |
|---|---|---|
| FootballContext current/pinned manifest and refreshManifest | `/api/dashboard/manifest`, optional v; explicit refresh removes pinned v | Supported. Pro loadScope resolves empty season data and progressive loading is disabled |
| json / useResource / primeResource | Arbitrary supplied `/api/…` URL; generic resource cache is unbounded by bytes | Generic transport is not Pro-aware. New Pro features must use versioned/bounded keys/cache, as match hooks already do |
| readPages / loadSeason | Repeated `/api/seasons/partition?season&league&format=columns&limit&cursor`; restart on409, halve limit on413 | Season route closed501. FootballContext shortcut does not protect every direct component call |
| completeFixtures | Repeated `/api/fixtures` with league+season or day range, limit100 until complete | Same supported route, but helper requests whole scope and omits v. It is not the Pro page flow |
| playerRoutes | `/api/scouting/routes?player=…&team=…`, up to8 IDs each; WeakMap cache by manifest | Closed501 until a frozen routing contract exists. SourceDigest in manifest.scouting is not route capability |
| loadPlayerSeason / loadPlayerHistory | playerRoutes then loadSeason per edition/season | Closed dependencies; no full player history from current4 routes |
| historicalFixtures | complete readPages(`/api/fixtures`,league,status=all), no season or v | May read multiple current edition builds; not frozen H2H/history. Does not justify bypassing the one-edition client |
| loadRemoteMatch | Summary, then archive then match resource for legacy; early client.pro summary guard | Pro early guard prevents both fallbacks |
| archiveIndex / archiveSeason | `/api/archives/index?kind`, `/api/archives/season?kind&season` | Both closed501 |
| cupIndex / cupTable | `/api/cup-index?kind`, `/api/cup-table?competition&season&kind` | Closed501 |
| associationRanking / clubRanking | `/api/rankings/associations?year`, `/api/rankings/club?club` | Closed501; these are observed external rankings, not Ballon d’Or computed scores |
| cupWorkerSnapshot | `/api/cup-snapshot` in parallel with completeFixtures for native or a validated same-backend fallback URL | Snapshot/support fallback routes closed501. A successful fixtures read is not native snapshot parity |
| loadClubFacts | `/api/club-links`, match root/lineups, optional `/api/club-wikidata`, `/api/coach-portrait` | Direct helper bypasses subclass and catches many failures to null; backend guard now prevents historical data leak |
| player-honours helper / StadiumDialog | `/api/player-honours?id`, `/api/stadium?id` | Closed501; separate from allowed binary-image alias |
| safeImageUrl / mediaImageSource | Approved image hosts routed through `/api/assets?url` | Explicit media exception, metadata/path validated; no binary fetch by API |
| MatchdaySchedule / competition/native brackets | `/api/matchdays`, sometimes client.request match root | Closed501 for direct helper; Pro subclass rejects request |
| PlayerData | Direct `/api/pitchapi/matches/{id}/players` and `/players/halves` | Closed501; cache key currently match ID without token, not reusable for new frozen readers |
| CompetitionsPage hosting-country fetch | Next local GET `/api/visitor-country` | Non-football metadata, private no-store, no location/provider request |

These helpers include all explicit local `/api/` call sites found in src. Many other services compute from f.data or invoke these helpers; they are not additional backend endpoints. Five nested match resource patterns exist in the AWS router without a dedicated current frontend call site. Direct requests to them are nevertheless covered by the closed default.

## Screen and tab coverage

| Existing URL / screen | Current Pro data path | Defined103 destinations for future route | Blocker / next contract |
|---|---|---|---|
| `/matchs` results/upcoming | Manifest + one-edition30-row pages; summary deep link v | analytics.match_summary, publication_versions/builds | Functional fixture-backed subset; production publisher/data gate still missing |
| `/calendrier` | Redirect to `/matchs?tab=upcoming`, preserves existing listed filters | Same | Redirect does not mint/preserve an aggregated frozen token; no extra page implementation |
| Match overview | Light summary; unopened shots/stats/leader arrays are V1 empty placeholders | match_summary, competition_summary, metric_totals | Full xG/ratings/stat cards need new representation/aggregate contract; do not fill old V1 silently |
| Match Tirs & xG | ProSummaryShots → client.shots only on tab selection | football.shots + match_coverage; profiles/aliases at cg | V1 metres/empty type/bool/frame policy retained; no full native-shot parity claim beyond accepted contract |
| Match Temps forts / Chronologie | Goals derives loaded summary shots; timeline ensureEndpoint events | football.match_events | Pro events not implemented; native field/state/order/actor gaps belong to pending107 |
| Match Avant-match | playerRoutes, direct loadSeason, historicalFixtures across shared editions | matches/scores/participants, build aggregates | Needs bounded before-match, history/scope/time and multi-edition representation. Native H2H list alone is not this screen |
| Match Classement | cloned client.loadFixtures then CompetitionStandings/support helpers | standing_snapshots/rows | Client rejects; need observed table scope/time + exact source states. Do not fabricate from team points aggregates |
| Match Statistiques | ensureEndpoint stats; periods/groups/items | team_match_metric_values/team_match_stats/periods | Native labels/layout/states/order missing until pending107 review/implementation |
| Match Compositions | ensureEndpoint lineups | match_lineups, match_players, observed profiles | Native standard/order/parent/object states are pending107; no partial native projection |
| Match Joueurs / player detail drawer | ensureEndpoint players or direct PlayerData full/halves | match_players, player_match_stats/metric_values, periods | Native group/layout/profile/ID contracts not accepted just because scalars exist; direct cache keys need v |
| Match Analyses | events/momentum/heatmaps/network and other selections | match_events/momentum, heatmaps/cells, networks/nodes/edges, advanced facts | Only shots is implemented. Heatmap repeated-actor profile mapping remains a known gate; other families need exact qualified field/state/order checks |
| `/` Vue d’ensemble | Existing cards compute from f.data.matches/appearances; extra matchdays helper; nightly manifest refresh | build aggregates + match_summary | Empty Pro season data cannot supply home metrics/highlights/leaderboards. New bounded home contract needed |
| `/joueurs` + profile/history/similarity | Season appearance model, source profile, routing/history helpers | players/profiles, memberships, metric values, player_competition[_team]_stats | Directory/profile/season/match cohorts and denominators must be frozen; current player_search is mutable, not an immutable result source |
| `/clubs` + profile/roster/fixtures/analysis | Season model; request league schedule; loadClubFacts/support | teams/profiles, competition_teams, memberships, team_competition_stats, matches, coach/venue refs | Missing typed readers and source-qualified profile/support parity; no global/provider fallback |
| `/competitions` + standings/cups/native brackets | Manifest catalogue can list editions; season analysis, support/cup/rankings/matchdays helpers | competitions/seasons/stages/groups/engagements, standings, rankings | Catalogue presence is not detail parity. Freeze source tables/scope/knockout ordering; unrepresented useful fields require review |
| `/archives` results/goals/history | archiveIndex/Season + historical merge logic | match_observation_details, matches/scores, events, source IDs | Existing schema may hold many fields; no exhaustive archive/source shape reconciliation or native archive reader is established |
| `/classement-joueurs` Ballon d’Or | Local formula over season appearances; scoring UI |9 analytics model/scoring tables are deferred, not among94 active | Independent model/cohort/window/normalization/coverage acceptance needed; not supplied by external ranking tables or V1 summary |
| `/methode` | Mostly static explanation/current metadata | Not a new football route | Can render, but no claim its legacy counts describe Pro completeness |
| Navbar search / saved research/comparison controls | Local catalogues/appearance index/browser research state | Typed paginated player/team search possible; current player_search mutable | Saved UI state is not frozen remote data; links/keys must carry appropriate token and actor identity |

All data destinations above are defined in the unchanged103-table model; no assertion is made that they contain accepted real data or encode every native DTO field. The9 deferred model relations are explicitly excluded from the first publisher/routes lot. Full parité remains the goal;501 is a truthful interim boundary, not the final feature scope.

Transport caveat: Next redirects API to NEXT_PUBLIC_API_ORIGIN when configured, proxies a local Bun otherwise, or uses the historical Vercel compatibility branch when that configuration selects it. This audit does not inspect hosted env or prove which branch runs remotely. The guard applies to aws-app.js; a deployment pointing somewhere else does not gain the guard automatically.
