# Existing aggregate/comparison contracts for the next backend lot

Suggested commit for this inventory: `docs: preserve existing aggregate and comparison semantics`.

Read-only source inventory; no new aggregate, formula, endpoint or model is
implemented here. This supplements the frozen57-route map without editing its
first-lot evidence. The existing behavior is required to survive the typed backend.

* `season-player.js` aggregateSeason/aggregateSeasonPlayers deduplicate a player
  by match. Unknown minutes are tracked separately, and zero/negative minutes do
  not count as played matches. Stat sums retain their observed match count and
  observed minutes. Per90 uses those observed minutes; partial statistics cannot
  silently become a complete zero or complete cohort feature.
* Player ratings are the arithmetic mean of the known positive-minute appearance
  ratings, using ratingSum/ratingCount. The typed aggregate column named
  provider_rating_weighted must not be substituted without proving the same
  averaging contract; its name alone is insufficient.
* Starter counts distinguish unknown starter status; positions/role are selected
  by observed minutes, and latest identity is selected by strict date comparison.
  Input ordering resolves equal-date/equal-minute ties in the current algorithm.
  A server implementation must preserve or explicitly version those tie rules.
* `scouting.js` buildCohorts includes role-group players with at least450minutes
  by default. A rankable metric enters the distribution only when its observed
  count equals all player matches and its observed minutes equal all minutes.
  RankMetric requires at least30valid peers. SimilarPlayers needs max(5,75% of
  target's available style indicators) in common, uses100minus mean absolute
  percentile distance, and returns up to8 with a player-ID tie-break.
* `club-analysis.js` also has an existing similarClubs feature. ClubSummary counts
  finished, scored matches and explicitly tracks unscored matches and unreliable
  team-stat exclusions. ClubStyleCohort uses at least3matches and at least80%
  observed metric coverage; centiles additionally need at least10peers. Club
  similarity needs max(5,75% available target style metrics), uses the same mean
  absolute percentile-distance pattern, and returns up to6 with club-ID ties.
* `season_data.js` readPages already rejects mixed generations, duplicate/reused
  cursors and malformed pages; it restarts once after409 and halves a413page
  limit. Its complete-cohort loading and packed-table missing-property contract
  cannot be replaced with an arbitrary first page or an implicitly complete cap.

Existing103 typed participants/stats/native metric states, profiles/positions,
match scores/periods/team stats and publication generations can feed these
products. Exact normalized field mappings, complete cohort denominators,
membership, causal before-match filters and deterministic numeric ordering still
need their own pre-code E2E. The9deferred model tables are not automatically
required to preserve these already implemented algorithms. Ballon d’Or remains
the separate currently-null stub; no new score is authorized by this inventory.
