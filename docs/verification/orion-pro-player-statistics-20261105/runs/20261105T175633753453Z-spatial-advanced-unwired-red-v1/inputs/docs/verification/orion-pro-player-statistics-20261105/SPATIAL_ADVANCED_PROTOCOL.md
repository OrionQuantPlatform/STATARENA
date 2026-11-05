# Five spatial and advanced match forms: protocol before code

Suggested commit: feat: serve typed spatial and advanced match statistics.

This lot adds /advanced, /advanced/players, /advanced/players/{player},
/advanced/network and /heatmaps under /api/pitchapi/matches/{match}.
It keeps the two shot and four player period forms intact. The new reader
lives in orion-pro-spatial-advanced.js. The router, common publication
writer, schema and any acceptance of a new environment in the older
period reader belong to ROOT.

All five forms require representation=match-statistics-v1 and an exact
published v from the unchanged 017 pair and the exact superset environment
in FULL_STATISTICS_PUBLICATION.json. Same DG/CG, V1, native017 and statistics
components, no new data type or schema. The prior four period forms must
work under either environment, with their original DTO and validators.
The old environment does not admit these five additional forms.

## Heatmaps: two collections, one document and one requested frame

Use heatmaps.teams and heatmaps.players coverage under the exact requested
frame variant. A pair must share the same match revision, source,
document and coverage generation. The default normalized frame is acting_ltr;
a requested home_ltr uses its separately retained typed observation. No
rotation or fallback between variants. Absence of either qualified coverage
does not become an empty map. Preserve declared outer absent/null/empty/
present, where known. If both collections have no maps, no grid can be
derived from map rows; the normalized response omits it. This does not
claim fidelity of an independent source grid on an empty raw response.

Each map has an exact physical team-side binding, source slot ordinal and
grid descriptors. Every selected map must agree on grid/frame. Dimensions
and metre values are direct typed fields, with no default. Player and team
objects use pinned public aliases and the captured typed profile at the
exact actor locator, with the context match_statistics_observation_v1:
plus the physical actor record ID. A team appearing in both collections
does not share a global display profile. Each player must have its
selected match-side membership. No role is inferred.

Sparse cells are ordered by cell_ordinal and keep the exact three integers,
including observed zeros. Missing cell coordinates are never filled. Actions
remain independent, including explicit null when the source contract
declares that field present. The stored cells_state distinguishes
absent/null/empty/available, and exact coordinates/counts must fit the grid.

## Pass network: admitted metre frame and same-network endpoints

Use one complete pass_networks coverage. Parent source order and side are
exact. The only admitted visual frame in this version is the declared
metric_105x68_acting_ltr with a first_substitution window; no value is
rescaled or inferred from the current unverified old frame. The UI uses
105×68 metre axes and a first substitution caption, so other frames/
windows fail closed. The synthetic fixture proves this declared format.
The retained diagnostic does not prove that real network source axes
already satisfy it.

Nodes carry exact finite values and selected captured player identities.
Endpoints of edges refer to those same typed nodes in the same network.
Normalize endpoint display to the selected node profile; do not claim
the raw per-edge observation's profile layout. Nodes and edges use a
stable public-ID order; provider list ordering remains separate. Each
weight, coordinate, centralization and window value is stored and copied.

## Advanced values: declared typed subset and registered scalar paths

Team and player cohorts are selected independently under advanced_teams and
advanced_players. A physical full-match advanced row ties each item to
the exact side or player membership, source document and declared slot.
The nested team/player envelopes preserve the existing container structure.
The normalized list declares its actual stable normalized sort; it does
not replay the original provider sorted_by label or ordering.

Expose a reviewed allowlist of already represented numeric columns and
additional observed metrics in typed player/team_match_metric_values with
family_code advanced, exact physical membership, same source/family
and registered raw path. No unknown field gets a fabricated value.
A numeric field kept in both forms must agree; neither silently wins a
conflict. Omitted unrecorded direct cells stay omitted. An explicit
typed null generic cell remains null. Advanced grouped labels and
source object's empty-state layout are a separate fidelity boundary.
No ratio, xT/VAEP/PV, action count, role or score is calculated.

## Publication, bounds and before-code E2E

The exact stats component is the union of the prior player/period closure
and the admitted advanced/graph/spatial typed closures. Include precise
coverage, physical source records/documents, participating identities/
profiles/aliases, grid, cells, graph parent/node/edge rows, advanced parent
and exact scalar/mapping/definition rows, and any used typed periods.
Use the same snapshot pair for all components and retain physical
identity with no volatile interval ends or write clocks. Old pins stay
usable; a spatial/advanced-only correction changes the composite joint.

At most 2 metadata SELECTs for HEAD/304 with no sporting values. At most
5 GET SELECTs, 80 maps/8,192 cells, 4 networks/160 nodes/1,600 edges,
120 advanced players/2 teams/3,000 scalar cells, 1 MiB encoded body.
Caps are refusal thresholds, not truncation. GET projects only these
selected typed facts. No external provider, source, Neon, RDS or S3.

| Case | Workflow | Required outcome |
|---|---|---|
| X01 | Actual installed 017 app, prior composite release | Four old player/period forms available; five new forms unavailable with old environment |
| X02 | New independently digested composite before dispatch | Actual 501 RED, no-store, zero SQL for the unimplemented route |
| X03 | Sparse heatmaps, multiple exact occurrences and grid | Ordinal, observed 0, action null and grid exact; no filled cells or global profile |
| X04 | Two explicit frames plus unavailable variant | Separately pinned raw frame data; no rotation; invalid parameter 400 and absent variant 503 |
| X05 | Cells and outer collection states | Null/absent/empty/present distinct, grid only from admitted map rows |
| X06 | Directed network plus distinct actor names | Exact metre coordinates, first substitution window, nonzero weights and correct endpoints |
| X07 | Unknown frame or foreign endpoint | Native typed/producer constraint refuses; no fallback to current/global actors |
| X08 | Team advanced typed + generic numeric metric | Direct and generic fields exact, zero/long decimal preserved, missing fields omitted |
| X09 | Advanced player collection and subject | Normalized ordered actors, exact individual scope and profile; no foreign-match fallback |
| X10 | Typed generic nulls and conflict | Null present; mismatch of two typed values rejects rather than silently selecting one |
| X11 | HEAD/304, conditional nonmatch | Same scoped validators; only metadata for HEAD/304, body exact on mismatch |
| X12 | Spatial/advanced correction, earlier period response | New joint/v/tag; old body/tag and independent edition stable; periods accept both environments |
| X13 | Bad params, incomplete and known empty coverage | Status/no-store exact; no fabricated list |
| X14 | Role, budget, cleanup and existing reader coexistence | 42501 write denied, no raw/current/source path, typed rows and bytes bounded, all pins exact |

Proposed one owned PG18.6, 120 s, at most 5,000 typed rows, 4,000 external
SQL calls, 200 actual loopback HTTP including traces, 64 MiB evidence,
1 GiB owned disk, 5 connections. Only on ROOT allocation. Keep the
actual app tests and exact input/output/log/cleanup. No hosted, source
coverage, production publisher or latency acceptance is implied.
