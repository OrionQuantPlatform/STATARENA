# Player and advanced match statistics: eleven existing forms

Suggested commit: feat: serve typed match and player shot details.

All paths below start at /api/pitchapi/matches/{match}. This category owns
orion-pro-player-statistics.js and separate owned HTTP verification. ROOT owns
the router, schema, common publication contracts, deployment and live data.
The four original readers and native match-detail reader are frozen inputs.

The legacy shape comes from dashboard/backend/migrations/004_match_details.sql,
detail_response, and dashboard/scripts/relational_match_model.py. Its five
nested forms are independent resources. A normalized view over a parent's
facts uses an explicit representation, and does not certify an independent
original source request.

| Form | Existing response data | Typed route plan | Exact source gate |
|---|---|---|---|
| /shots/{shot} | One shot object | Pinned normalized V1 cohort, exact external s_ ID and side. No global shot lookup. | Keeper/name/image/position and raw spatial fields need exact observation/field states. The original mapper did not retain all spatial leaves. |
| /players/{player}/shots | Player object and shots array | Pinned complete normalized cohort, exact actor membership and unknown shooter check. | Independently captured subject coverage is not implied by the match list. |
| /players | Array of player rows with keyed metric groups | Existing native scalars and proved memberships in a separately versioned product projection. Use existing metric labels/formulas and require exact coverage. | Group key/title and order, stat.type, total presence, 17 empty lists and 63 empty metric keys in the retained scope are not established by native31. |
| /players/{player} | One player row | Same qualified cohort narrowed by exact public alias and captured member. | Independent source response, occurrence profile and group states need proof. |
| /players/halves | Match ID and player rows with ordered periods | Exact typed period/metric cohort; no inferred halves or sums from full-match values. | The retained scope has 105 periods and 420 group headers. Missing halves/empty groups cannot be inferred from absent scalars. |
| /players/{player}/halves | Match ID and one player's periods | Exact player and period membership in that qualified cohort. | Independent source response and full period order remain distinct. |
| /advanced | Match ID and team totals | Exact per-side/period typed advanced values under a qualified normalized DTO. | Actions, passes, pass accuracy, many passing/carrying/creation/defending fields and source labels need observed binding. A matching column name is not semantic proof. |
| /advanced/players | Match ID, sorted_by, and player rows | Exact member/period and approved typed fields; no invented provider sort. | Actions/minutes/passing/defending, goalkeeping states, sparse breakdowns, sorted_by and captured shirt/profile need reconciliation. |
| /advanced/players/{player} | One advanced player row | Scope the qualified advanced cohort to an exact member. | Independent subject and same field/layout gaps remain. |
| /advanced/network | Match ID and networks/nodes/edges | Use directed typed edges, nodes, centralization and declared window unchanged. | Occurrence names/shirts and source order are not persisted on nodes/edges. The old transform uses pitchapi_native_unverified; the viewer assumes 105×68 metre axes. |
| /heatmaps | Match ID, grid and team/player sparse maps | Separate teams/players coverage in one document and requested frame; exact cell order and independent actions. | Prior local proof compared 0/1344 real triplets. Exact captured names/shirts, a grid with no maps, absent actions and alternate frames cannot be inferred. |

SOURCE_SHAPES.json counts field paths and native kinds from the retained
two-match diagnostic. It contains no business values. The original-family
normalizer records the seven relevant families as partial. Its noncanonical
original rows do not establish complete match-scoped coverage for players,
halves, advanced teams/players or networks.

The existing V1 build binds selected shots, participation and relevant aliases/
profiles. The two normalized shot views can use its pinned DG/CG. The V1
publisher selects only shots coverage; it does not publish the other
sporting families. Their readers need an approved closure at the same pair,
or an equivalent owner-approved binding. This category does not change DDL,
introduce a score, read a source or fall back to a provider.

PlayerData.jsx and MatchSections.jsx use player ID/name, period labels and
ordered metric groups. PlayerMetrics.jsx displays typed value, total and type.
Heatmap uses explicit grid/frame/cells and actor labels. PassNetworks uses
directed endpoints, coordinates, weights and window. The route guard can only
mark a form supported for its qualified representation and data prerequisites.
