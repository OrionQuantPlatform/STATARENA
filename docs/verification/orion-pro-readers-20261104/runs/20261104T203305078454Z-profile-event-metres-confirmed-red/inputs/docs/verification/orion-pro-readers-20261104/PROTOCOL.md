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

## Exact local rerun and evidence

```sh
PYTHONPATH=/tmp/statarena-publication-test-python python3 tests/orion_pro_readers_local.py --label frozen-readers-final
dashboard/node_modules/.bin/prettier --check dashboard/backend/services/orion-pro.js dashboard/backend/aws-app.js docs/verification/orion-pro-readers-20261104/http_server.mjs
python3 docs/verification/orion-pro-readers-20261104/measurements.py --result docs/verification/orion-pro-readers-20261104/runs/20261104T201705737660Z-frozen-readers-final/result.json
```

`--pg-bin` accepts the equivalent owned local PG18.6 binary directory in CI. No Git, AWS, Neon, source collection, normalizer execution, deploy, model or migration edit is performed. The fixture loads the sealed migration bytes directly and uses the existing bootstrap/grant helpers; only its owned loopback database is mutated. The test HTTP server's trace/control endpoints exist only in this local harness and are never production routes.

Each run retains full request method/path/headers/body/status, actual pg-client SQL text/binds/count/timing, model/runtime/code digests and input copies, runtime role/access-mode identity, server/PostgreSQL logs and owned cleanup. All values are synthetic. The Pro reader supports the explicit `summary-v1-shots-v1` representation contract and fails closed on another representation version. No response uses a current view or legacy/source fallback. Unknown media, full statistical rollups and leaders remain null/empty in this bounded summary DTO; their production publisher and full feature parity are not established here.

## Retained outcomes

- `runs/20261104T200052470951Z-missing-reader-red/result.json`: one passed, one failed, 18 unverified. Initial fixture incorrectly supplied an observed count of zero for unavailable coverage. The sealed SQL correctly requires NULL; this first failure and cleanup are retained.
- `runs/20261104T200123950284Z-complete-fixture-reader-red/result.json`: the corrected fixture creates all 94 tables and three ready/public A/B/C builds. The old router rejects `v`, leaving its dependent cases unverified.
- `runs/20261104T200201787734Z-full-publication-http-red/result.json`: genuine before-code HTTP RED, two passed/two failed/16 unverified. The complete fixture is present, runtime is `statarena_runtime` with read-only startup, but the old manifest returns 503 and its validator rejects the requested representation. No reader service existed yet.
- `runs/20261104T200747322194Z-first-reader-integration/result.json`: 19/20 HTTP workflows passed. The sole failure was a fixture attempt to republish identical build values: existing `ingest.validate_generation` rejects that as an identical typed reimport. The fixture now records the expected SQL rejection and verifies rollback/no change; production publisher code was not altered.
- `runs/20261104T201130872886Z-frozen-readers-acceptance/result.json`: first 20/20. It also verifies a pinned one-edition manifest and CSV validation. Its HTTP timing initially included the trace readback; later runs correct that harness timing boundary.
- `runs/20261104T201337598229Z-reviewed-frozen-readers-final/result.json` and `runs/20261104T201419133241Z-frozen-readers-final-formatted/result.json`: 20/20 retained after narrowing the shot projection to DTO columns, correcting timing, and completing the formatter's second pass.
- **`runs/20261104T201705737660Z-frozen-readers-final/result.json`: final 20/20, 49 actual HTTP requests.** Three initial builds and two corrected A/B builds are immutable; the new dataset and catalogue generations differ. Old pinned manifest/summary/shots retain exact bodies/ETags; mutable stale cursor is 409; C's token/body/304 survive; default-disabled flag preserves legacy validation. Accepted empty, unavailable and missing coverage are distinct. Wrong-edition token and noncanonical/source decoy do not leak. Invalid syntax performs no SQL. The runtime rejects writes and generation helpers with SQLSTATE42501 even with read-only transaction mode disabled. HTTP and owned PG processes stop successfully and the owned data directory is removed. The final source bytes were checked unchanged after the run.

For the same-build no-op, SQL rejects the attempted equal publication with 23514 and rolls it back. Before/after counts remain five builds, five publication versions, six accepted snapshots and four retained shot rows. The sequence may allocate a skipped number; no accepted generation, fact, build or representation is added. A future production publisher should detect the equal state before attempting that transaction.

## Honest local component measurements

`measurements.json` beside the final result is reproducible from `measurements.py` and pins its result SHA. These are the first successful observations of different workflow components in scripted order, not a paired before/after benchmark. Logical JSON bytes exclude headers/framing. Loopback RTT excludes diagnostic trace retrieval; SQL time starts after leasing a connection. Database/pool warmth is not controlled for latency inference.

| Component in the final synthetic run | JSON bytes | SQL statements | Heavy queries |
|---|---:|---:|---:|
| Manifest | 2,361 | 1 | 0 |
| Fixture page, two matches | 1,250 | 2 | 0 |
| Match summary | 682 | 3 | 0 |
| Activated shots | 521 | 3 | 1 |
| Manifest/list HEAD or 304 | 0 | 1 | 0 |
| Summary/shots HEAD or 304 | 0 | 2 | 0 |

The old-router RED has no populated legacy serving projections and returns errors, so it cannot support a successful semantic latency/transfer baseline or a speedup percentage. The measured result establishes deferred heavy access and metadata-only validators on the fixture. Bun emits `content-length:0` for the harness's bodyless HEAD responses although the application omits that header; no GET representation-size equivalence is claimed. Real data completeness, production publication, hosted/browser/CDN behavior, storage savings and representative remote gains remain separate gates.

These outcome notes are appended after the executed tests; their original pre-code matrix and exact runtime bytes remain in each run's `inputs/`. Suggested commit: `feat: serve frozen Pro match summaries and lazy details`.

## Parent review corrections, tests before guards

The preceding 20-case greens are prototype evidence, superseded for acceptance by this review matrix. The real normalizer creates `provider_global` and `legacy_normalized_global`, while the initial synthetic profiles used only `global`. Its existing code was read locally to identify the contract; it is neither changed nor executed here. The earlier percent-coordinate assumption is superseded: the existing legacy map consumes metres (`x/105`, `y/68`), so v1 preserves metres for `acting_ltr` rather than emitting percent.

For `summary-v1-shots-v1`, selected profiles must be canonical/not deleted at the pinned catalogue generation and match the actor. Priority is: (1) `provider_global`, variant `provider:exact`, exact same source as the dataset match for team names or the accepted source/variant shot for player names; (2) canonical `legacy_normalized_global` from that same source; (3) `global` only with manual provenance and NULL source. Another source is never a fallback. This priority is part of the representation contract; future policy changes require a separately versioned adapter while retaining v1 for old published representations. Equal best-priority candidates fail closed, and observation IDs/timestamps do not decide public values.

| Additional real local-SQL input before guard code | Expected HTTP observation |
|---|---|
| Provider, normalized and manual profiles coexist; provider/legacy names differ | Same-source exact provider wins at pinned catalogue generation |
| Canonical provider profile belongs to another source; same-source normalized exists | Other-source label ignored, normalized label selected |
| Only manually curated global exists | That explicit manual row is allowed; mutable identity fields are not read |
| Noncanonical provider variant has a different label | It cannot alter the response |
| `source_event_type=''` and independently known `is_goal=true` | Preserve both native values; only NULL event type permits derived fallback |
| Acting-frame point 52.5m/34m | Return x=52.5/y=34 and `coordinate_state=available`, not 50/50 percent |
| Same typed point in `home_ltr` without demonstrated orientation | x/y NULL, `coordinate_state=unsupported_frame`; `source_coordinates` retains metre values, frame and pitch dimensions |

The fixture now includes the real profile contexts, a competing-source canonical provider, a noncanonical provider variant, an empty native event type and the unsupported frame. Existing 20 workflows plus three new HTTP workflows run before these guards to retain a concrete RED. No away/home rotational or whole-coordinate-frame parity is inferred from the home acting-frame example.
