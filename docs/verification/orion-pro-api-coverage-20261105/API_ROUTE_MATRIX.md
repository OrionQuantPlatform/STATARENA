# Canonical AWS routes — exact path forms

Suggested commit: `docs: map Pro API coverage and define publication rollout`.

57 path forms /114 GET+HEAD combinations:4 Pro readers,3 operational/media exceptions,50 closed under ProON. This is code inventory, not a runtime result. Query names describe allowed names; requiredness/value constraints remain the canonical validators. Catalogue named params are all required; support params are optional at the router. IDs follow the existing six-character public patterns. No new table is assumed.

| Path | Query names | ProON policy | Existing103 targets |
|---|---|---|---|
| `/api/health` | — | allow_operational_or_media |  |
| `/api/status` | — | allow_operational_or_media |  |
| `/api/settings` | — | 501_before_legacy_dispatch |  |
| `/api/dashboard/manifest` | v | native_pro_reader | analytics.aggregation_builds, analytics.publication_versions, analytics.competition_summary |
| `/api/seasons/partition` | season, league, limit, cursor, format | 501_before_legacy_dispatch | analytics.match_summary, football.player_match_stats, football.player_match_metric_values |
| `/api/fixtures` | league, leagues, season, seasons, status, from, to, q, limit, cursor, v | native_pro_reader | analytics.match_summary |
| `/api/scouting/routes` | player, team | 501_before_legacy_dispatch | football.match_players, football.competition_seasons, football.competition_teams |
| `/api/matches/{match}/summary` | v | native_pro_reader | analytics.match_summary |
| `/api/assets` | url | allow_operational_or_media | ingest.media_assets |
| `/api/standings` | competition, season | 501_before_legacy_dispatch | football.standing_snapshots, football.standing_rows |
| `/api/open-cups` | competition, season | 501_before_legacy_dispatch | football.competition_stages, football.matches, football.match_scores |
| `/api/openligadb` | competition, season | 501_before_legacy_dispatch | football.matches, football.match_scores |
| `/api/nations-results` | season | 501_before_legacy_dispatch | football.matches, football.match_scores |
| `/api/club-wikidata` | uefa, name, country | 501_before_legacy_dispatch | football.team_profile_versions, football.team_source_ids, football.team_coach_tenures, football.venues |
| `/api/coach-portrait` | name | 501_before_legacy_dispatch | football.coaches, ingest.media_assets |
| `/api/stadium` | id | 501_before_legacy_dispatch | football.venues, ingest.media_assets |
| `/api/player-honours` | id | 501_before_legacy_dispatch | football.player_honours, football.honour_definitions |
| `/api/archives/index` | kind | 501_before_legacy_dispatch | football.competitions, football.competition_seasons |
| `/api/archives/season` | kind, season | 501_before_legacy_dispatch | football.match_observation_details, football.matches, football.match_scores, football.match_events |
| `/api/rankings/index` | — | 501_before_legacy_dispatch | football.ranking_systems, football.ranking_snapshots |
| `/api/rankings/edition` | kind, edition | 501_before_legacy_dispatch | football.ranking_snapshots, football.team_ranking_entries, football.association_ranking_entries |
| `/api/rankings/associations` | year | 501_before_legacy_dispatch | football.association_ranking_entries, football.association_ranking_components |
| `/api/rankings/club` | club | 501_before_legacy_dispatch | football.team_ranking_entries, football.team_ranking_components |
| `/api/club-links` | club | 501_before_legacy_dispatch | football.team_source_ids |
| `/api/cup-index` | kind | 501_before_legacy_dispatch | football.competitions, football.competition_seasons |
| `/api/cup-table` | competition, season, kind | 501_before_legacy_dispatch | football.matches, football.match_scores, football.competition_stages |
| `/api/cup-snapshot` | competition, season, kind | 501_before_legacy_dispatch | football.matches, football.match_scores, football.standing_snapshots |
| `/api/matchdays` | competition, season | 501_before_legacy_dispatch | football.matches, football.competition_stages |
| `/api/supplemental` | — | 501_before_legacy_dispatch | football.matches, football.match_observation_details |
| `/api/archive/matches/{match}` | — | 501_before_legacy_dispatch | football.match_observation_details, football.matches |
| `/api/archive/profiles/leagues/{league}` | — | 501_before_legacy_dispatch | football.competitions |
| `/api/archive/profiles/teams/{team}` | — | 501_before_legacy_dispatch | football.team_profile_versions |
| `/api/archive/profiles/players/{player}` | — | 501_before_legacy_dispatch | football.player_profile_versions |
| `/api/pitchapi/date/{date}` | status | 501_before_legacy_dispatch | analytics.match_summary |
| `/api/pitchapi/leagues/{league}/matches` | season, status | 501_before_legacy_dispatch | analytics.match_summary |
| `/api/pitchapi/leagues` | — | 501_before_legacy_dispatch | football.competitions |
| `/api/pitchapi/leagues/{league}` | — | 501_before_legacy_dispatch | football.competitions |
| `/api/pitchapi/teams/{team}` | — | 501_before_legacy_dispatch | football.team_profile_versions |
| `/api/pitchapi/players/{player}` | — | 501_before_legacy_dispatch | football.player_profile_versions |
| `/api/pitchapi/matches/{match}` | — | 501_before_legacy_dispatch | football.matches, football.match_observation_details |
| `/api/pitchapi/matches/{match}/shots` | — | native_pro_reader | football.shots, ingest.match_coverage |
| `/api/pitchapi/matches/{match}/momentum` | — | 501_before_legacy_dispatch | football.match_momentum, ingest.match_coverage |
| `/api/pitchapi/matches/{match}/events` | — | 501_before_legacy_dispatch | football.match_events, ingest.match_coverage |
| `/api/pitchapi/matches/{match}/players` | — | 501_before_legacy_dispatch | football.match_players, football.player_match_stats, football.player_match_metric_values |
| `/api/pitchapi/matches/{match}/players/halves` | — | 501_before_legacy_dispatch | football.player_match_stats, football.player_match_metric_values, football.periods |
| `/api/pitchapi/matches/{match}/lineups` | — | 501_before_legacy_dispatch | football.match_lineups, football.match_players |
| `/api/pitchapi/matches/{match}/h2h` | — | 501_before_legacy_dispatch | football.match_h2h_entries, ingest.match_coverage |
| `/api/pitchapi/matches/{match}/stats` | — | 501_before_legacy_dispatch | football.team_match_stats, football.team_match_metric_values, football.periods |
| `/api/pitchapi/matches/{match}/advanced` | — | 501_before_legacy_dispatch | football.team_match_advanced |
| `/api/pitchapi/matches/{match}/advanced/players` | — | 501_before_legacy_dispatch | football.player_match_advanced |
| `/api/pitchapi/matches/{match}/advanced/network` | — | 501_before_legacy_dispatch | football.pass_networks, football.pass_network_nodes, football.pass_network_edges |
| `/api/pitchapi/matches/{match}/heatmaps` | frame | 501_before_legacy_dispatch | football.match_heatmaps, football.match_heatmap_cells |
| `/api/pitchapi/matches/{match}/shots/{shot}` | — | 501_before_legacy_dispatch | football.shots |
| `/api/pitchapi/matches/{match}/players/{player}` | — | 501_before_legacy_dispatch | football.match_players, football.player_match_stats, football.player_match_metric_values |
| `/api/pitchapi/matches/{match}/players/{player}/halves` | — | 501_before_legacy_dispatch | football.player_match_stats, football.player_match_metric_values |
| `/api/pitchapi/matches/{match}/players/{player}/shots` | — | 501_before_legacy_dispatch | football.shots |
| `/api/pitchapi/matches/{match}/advanced/players/{player}` | — | 501_before_legacy_dispatch | football.player_match_advanced |

Source dispatch: aws-app.js lines18–67,126–169,174–326; relational-match.js lines3–28; orion-pro.js lines638–684. The proposed closed default also catches future/unknown API paths. Next catch-all forwards GET/HEAD/POST/PUT/DELETE; AWS returns405 for the latter three. Specific Next proxies exposeGET/HEAD; visitor-country is localGET metadata. `/data/…` is removed410 in the AWS/public-origin branch.

Existing targets do not settle native shape gaps: events/lineups/team-stat layout/H2H remain gated by the pending107 proposal; other support/profile/archive/advanced contracts need source-qualified field/type/order mapping before native claims.
