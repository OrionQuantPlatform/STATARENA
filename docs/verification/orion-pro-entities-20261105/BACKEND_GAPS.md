# Full backend requirement map and first product boundary

Suggested commit: `feat: add typed edition-bound entity profile readers`.

Local source/schema review only. `ALL_ROUTE_MATRIX.json/.md` reconciles every
one of the57 existing AWS path forms:4 original native readers,3 existing
operational/media exceptions,8 entity forms in this lot,42 other forms requiring
readers/contracts. An implemented route and an accepted real-data import are
separate statuses. Nothing here asserts backend completeness or a cutover.

## Player, club, competition and season products

The coherent first boundary uses existing profile/catalogue/routing URLs at an
explicit edition token. Profiles follow the documented provider/legacy/manual
policy at catalogue generation; scope follows published selected facts at
dataset generation. It does not add an endpoint, a new scoring formula or a
generic version/history mechanism. Publication code and the existing V1
summary/shots DTOs stay exact.

Existing player directory/profile/evolution/club-roster/club-analysis/home
screens still compute from complete normalized appearances and season facts.
Restoring those products needs typed projections of match_players,
player_match_stats/player_match_metric_values, positions/profiles, teams,
memberships and match/competition aggregates. Page/cohort/coverage/minutes
contracts must be admitted before those screens can claim parity. The existing
`/api/seasons/partition` path is the compatibility seam; bounded SQL-backed
product aggregates can later avoid downloading entire seasons. Unknown facts
must stay unknown, and a requested full cohort must never be silently truncated.

Global navigation/history is distinct from one-edition profile routing. The
internal proset digest supports mutable ETag/cursor conflict detection; it is
not a round-trippable frozen multi-edition URL. The new helper retains the
original reader's2048published-build metadata ceiling and fails503 above it.
That ceiling and catalogue batching/pagination across large universes need
further production work; it is not an accepted final global limit.

## Existing comparisons and scoring

`frontend/src/services/scouting.js` already implements buildCohorts,
customIndex, roleAssessments and similarPlayers. Similarity compares existing
role peers using mean absolute percentile distance, requires at least5 shared
style metrics and75% of the target's available style metrics, and returns up
to8 peers with a stable player-ID tie-break. These are existing features to
preserve. They can be recalculated from complete typed appearance/metric,
position/profile and cohort/minutes facts; the nine deferred model tables are
not a blanket prerequisite. SQL/product implementation and parity proof remain.

`frontend/src/services/ballon-dor.js` currently returns null unconditionally.
The page/home do not have existing computed season scores to migrate. Preserve
that availability state; a new Orion/Ballon d’Or scoring formula remains outside
this implementation. Observed external FIFA/UEFA rankings are separate products.

## Precise103 gaps versus missing adapters/data

The approved103 model already has matches/participants/scores, native metric
values and fractions, shots, spatial grids/cells, momentum, advanced facts,
networks, standing/ranking snapshots and children, venues/coaches/honours and
source identities. Their existence establishes neither populated facts nor
exact provider envelopes. Each remaining route needs a field/type/state/order
mapping, source-qualified facts, selected generation and bounded read contract.

The separate pending107 proposal identifies narrower native fidelity gaps:

* Events: a distinct sub_in player and physical observed-profile links, native
  period text, scalar/object/ID presence states and root observed-team context.
  Existing typed event facts can support a normalized event product without
  pretending that they reconstruct the complete original native response.
* Lineups: native `standard` type text, coach-name-only header object, explicit
  property/object/list states, and physical ordered member-to-lineup occurrence
  binding. Existing side/member/formation/placement facts remain reusable.
* Team stats: the scalar values/states/fractions exist. Exact per-observation
  period/group/item labels, formats, empty containers and ordered membership
  do not; the proposal adds three structural children, not duplicate scalars.
* H2H: entries/labels/scores exist. Native header totals when recent is empty
  and original finished boolean/state do not; the proposal adds one summary
  child plus targeted fields. A derived historical match context is a separate
  product and need not wait on an exact native H2H envelope.
* Profiles: current versioned fields preserve position/shirt states. Native
  name/image/identifier presence and immutable observed image URL are not fully
  captured. The normalized resource projection here cannot certify those states.
* Heatmaps: the prior repeated-actor occurrence/profile failure needs its own
  accepted grain/normalization proof. This entity reader neither changes it nor
  establishes that the four-table107 proposal automatically resolves it.

No amendment is applied. Additional native player/momentum/advanced/network,
support, archive sourceFields, cup/standing and ranking shapes remain explicit
qualification work; they are not declared impossible under103 by association.
The existing normalizer also reports profile identity/selected-version gaps
and unverified useful fields (including image properties); those are data and
mapping gates, not permission to invent placeholders.

## Integration and review gates

Actual aws-app Pro dispatch now calls the entity helper after the four existing
readers. Frontend ProFootballDataClient still rejects generic request calls;
it needs deliberate profile/routing integration with v and versioned bounded
cache keys. Current local player-identity cache keys omit the token and must be
fixed before cross-publication profile reuse. No frontend redesign is needed.

The E2E evidence is source-free and backend-only. Essential-media non-NULL
branches, mixed-case catalogue IDs, maximal page/load performance, full global
discovery, ProOFF regression, exhaustive real facts and deployed browser flows
remain additional verification gates unless a later artifact explicitly proves
them. Catalogues currently issue per-row metadata reads, a known efficiency gap
to batch before a broad production directory is accepted. Profile responses
revalidate even with v because the media table is mutable.

Next coherent lots: normalized appearances + complete cohort projections;
home/player/club aggregates and preserved comparisons; observed competitions,
standings/rankings/archives/support; qualified detailed families. Collector
leases/retries/manual schedules, actual RDS facts/publication and hosted runtime
independence are separately required. Exhaustive source transfer continues in
parallel and source deletion still requires reconciliation.
