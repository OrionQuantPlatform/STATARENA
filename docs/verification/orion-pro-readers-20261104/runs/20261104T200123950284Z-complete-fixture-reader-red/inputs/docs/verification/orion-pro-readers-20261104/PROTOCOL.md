# Frozen typed-reader E2E, before implementation

Suggested commit: `feat: serve frozen Pro match summaries and lazy details`.

Start implementation after the schema/bootstrap RDS readback passes. This next lot uses an owned PostgreSQL 18.6 fixture and local HTTP/browser servers first. It does not publish incomplete real pilot data or switch the canonical frontend. The existing 94-table model is sufficient; no new business table is proposed.

The smallest positive flow is one edition, three matches on two pages (`limit=2`), opening one summary, then requesting its “Tirs & xG” tab. Keep these existing contracts:

- `GET /api/dashboard/manifest` exposes editions and each immutable representation token.
- `GET /api/fixtures?league=…&season=…&limit=2&cursor=…` returns `{data:{matches},pagination:{limit,nextCursor,generation}}`.
- `GET /api/matches/{id}/summary` returns `{data:{version:1,state,match}}` with `summaryVersion=1`.
- The historical `/api/pitchapi/matches/{id}/shots` route serves the accepted typed observation; it performs no provider or document/object read.

A representation token pins a ready `analytics.aggregation_builds` row, dataset snapshot/generation, catalogue snapshot/generation and representation version. An explicit `v` must be accepted by route validators and included in frontend, API, cursor and CDN cache identities. Frozen reads select facts at the dataset generation and aliases/profiles at the catalogue generation; current views cannot supply mutable attributes to a frozen response. Mutable reads resolve the latest accepted publication. Old immutable builds remain readable after correction.

| Failure/input written before code | Expected complete-workflow outcome |
|---|---|
| Missing/unready build or unsealed data/catalogue | 503, `no-store`, explicit unavailable state; no source/Neon fallback |
| Three matches with tied and unknown dates | Stable total order; exactly three unique public IDs over two pages |
| Invalid limit/cursor/token; cross-edition cursor | Existing validation semantics, bounded response, no heavy query |
| Correction while navigating | Old pinned token/ETag/body remain unchanged; stale mutable cursor returns 409 |
| Shared catalogue correction affecting A/B | New A/B token and public fields; independent C token/body/304 preserved |
| Identical re-publication | No new fact/build/token; same cache identity |
| List or unopened match tab | No shots, heatmap, network or other heavy observation query |
| HEAD or matching If-None-Match on cold caches | Metadata only; no body/family materialization; correct 200/304 headers |
| Accepted empty shots versus unavailable collection | Empty proven separately from `NOT_COLLECTED`/unknown; no invented zero |
| Same public ID in another edition or different variant | Exact selected membership, period, variant and coverage; no cross-context row leak |
| Web runtime tries a write/helper | Permission rejection; all user reads use the existing read-only role |
| Browser list → page2 → match → active shots tab | Summary renders first; heavy call occurs only on activation; caches include token; desktop/mobile parity |

Use `analytics.match_summary` for the list and summary, with ready build/publication records. Detailed facts come from the typed football tables at the pinned generation, and their explicit coverage. The current real normalizer still creates draft matches and no edition engagements, analytical build or published pointer; it cannot yet supply this positive publication workflow. A complete synthetic fixture is required first, with explicit labels, scores, engagement, accepted coverage and two immutable builds.

The E2E must save exact setup/inputs/commands, model/runtime hashes, actual HTTP requests/headers/bodies, semantic SQL readbacks, SQL operation counts and timings, browser traces/screenshots, original failures and owned-process cleanup. Source/API/S3 access must fail the local workflow. Report local measurements as local; comparable real RDS latency/transfer gains need accepted representative data and a separate before/after run.

UX: lightweight pages, immediate summary, detailed data requested by the selected tab and explicit unavailable states. DX: existing routes plus one shared typed DTO adapter. AX: inspectable tokens, deterministic replay and bounded validation errors. The added cache-key/version complexity is a deliberate maintenance cost, not an unqualified improvement to every dimension.

## Local backend contract fixed before reader code

`STATARENA_PRO_API=1` selects only these four Pro routes inside `aws-app.js`; any other value preserves the existing router. No frontend or production flag is changed in this backend lot.

The manifest retains `schemaVersion:4`, `seasons/chunks/competitions/defaultSeason/retrievedAt`. It identifies this implementation with `storage:"aws-orion-pro"` and `capabilities:{frozenRepresentations:true,fixturesPagination:true,matchSummary:true,lazyShots:true}`. Each chunk and each added `editions` entry has `representationToken`; edition entries contain `leagueId,season,representationToken,sourceDigest,datasetGeneration,catalogGeneration`. `sourceDigest` is SHA-256 of the token. Tokens match `pro1.<positive bigint build id>.<64 lowercase hexadecimal digest>`, binding the immutable ready build, edition, dataset/catalogue snapshots and generations, representation version and code/dependency contracts. A requested token must also belong to an actually published build.

All four routes accept `v`. `manifest?v=…` returns only the pinned edition. Fixtures keep existing filters `league/leagues/season/seasons/status/from/to/q/limit/cursor`, plus `v`, and their existing DTO. Summary and shots accept only `v`. A single-edition page's `pagination.generation` is its representation token; cursors bind the exact filters, limit and representation identity. Summary adds `data.representationToken` while retaining `data.version/state/match` and `match.summaryVersion=1`. Its unopened heavy arrays remain empty and `coverageStates.shots` explicitly distinguishes `present/empty/unavailable/unknown`. Shots retain native `data.periods[].shots[]` fields and add `data.representationToken/collectionState`; uncollected/unavailable facts return 404 `NOT_COLLECTED`, never a fabricated zero. Known metre coordinates with pitch dimensions are mapped to the native percent DTO; unknown coordinate semantics stay null.

HEAD and matching validators read only ready-build/snapshot/membership/coverage metadata; no profile/summary DTO or heavy family is materialized. Lists/summaries never query shots, heatmaps or networks. Immutable GET/HEAD responses receive immutable cache policy; mutable responses revalidate. `v`, token scope and filters participate in ETags/cursors. All unavailable/errors use `no-store`. No current view, file/provider/Neon fallback is allowed on these four flagged paths.

## Executable backend failure matrix, before implementation

| Local complete workflow | Expected observation |
|---|---|
| Owned PG18.6 bootstrapped with exact sealed 012/013; synthetic A/B/C builds | 94 tables; A has three summaries with tied/unknown dates; selected labels/scores/engagement/coverage are valid; real read-only runtime role |
| Existing router before new reader | Actual HTTP RED retained, not a source-backed success |
| Empty/unpublished or building build; syntactically valid missing token | 503/no-store, no fallback or heavy query |
| Malformed/overflow token, invalid/duplicate query, limit/cursor/cross-filter cursor | 400 before heavy SQL; malformed syntax before all SQL |
| Manifest → A page1(limit2) → page2 | Exactly three distinct public match IDs, stable date/id order including null date |
| Summary before shots activation | Existing small DTO with observed zero/null scores; no shots/heatmap/network SQL |
| Activate shots | One accepted canonical source/variant at dataset generation, native period/player DTO using catalogue-generation profile/aliases |
| Accepted empty A2 versus unavailable A3 and unknown C coverage | Empty 200 is proven; unavailable/unknown are explicit 404 states, without heavy row reads |
| Token for B with A public match id; duplicate shot external id in B/noncanonical A variant | 404 or exact A observation; no cross-edition/source/variant leak |
| Cold HEAD/conditional manifest/list/summary/shots | Correct 200/304/ETag; metadata only; no body/heavy query |
| Dataset correction then later shared catalogue correction | New A/B representations, updated score/xG/profile names; data generation differs from catalogue generation |
| Old pinned A after correction | Identical HTTP body/ETag; old shot xG/profile retained |
| Mutable cursor after correction | 409/no-store before page/heavy materialization |
| Independent C after correction | Same representation, body and ETag; conditional request remains 304 |
| Publish the same build again | No new fact/build/token or cache identity; publication bookkeeping may add its own generation |
| Runtime write/helper attempted with transaction read-only disabled locally | SQL privilege rejection, proving role grants in addition to connection read-only startup |
| Flag absent/zero | Pro token rejected by the existing route validator; no Pro route takeover |

The executable backend acceptance does not include a substitute browser UI. Desktop/mobile activation and actual frontend cache integration belong to the parent frontend lot after this backend contract passes. No source normalization, publisher implementation, remote latency/transfer claim, Vercel verification or live data acceptance is inferred from these synthetic workflows.
