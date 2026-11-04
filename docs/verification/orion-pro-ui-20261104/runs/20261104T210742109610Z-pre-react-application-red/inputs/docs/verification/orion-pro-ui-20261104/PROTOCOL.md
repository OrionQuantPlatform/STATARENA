# React Pro browser workflow — before integration

Suggested commit: `test: verify paginated Pro React workflows in a real browser`.

This protocol precedes both this browser harness and the React integration. ROOT owns application changes; this sub-lot owns only this directory and `tests/orion_pro_ui_local.py`. Existing readers/client/frontend/schema/migrations/normalizer/worklog/CI remain untouched by this harness. The initial RED must be captured from the actual frontend before requesting React changes.

## Local deployment and necessary interface

Run one owned PG18.6 cluster with the exact sealed 012/013 and shared bootstrap/grants, the real Bun Pro API with `STATARENA_PRO_API=1`, then the actual Next.js frontend in an isolated temporary copy. The copy retains identical frontend/shared/backend source bytes and dependency versions while keeping `.next-dev`, generated agent/type files and process artifacts out of shared source directories. `ORION_API_ORIGIN` points only to the owned loopback API; browser reads `/api/...` through the real Next proxy. No public API origin, Vercel, Neon, S3, provider or real football source is used.

The declared, locked `flag-icons@7.6.0` is absent from the current shared dependency install. When absent, the harness adds an isolated `frontend/node_modules/flag-icons` symlink to its existing Bun cache package, recording package/CSS/country-table SHA256. It does not install or modify shared dependencies. A compiler failure is a preparation failure, not the requested React behavior RED.

A local-only subclass of the sealed reader fixture will publish **61 A-edition matches** while retaining B/C. Product pagination stays **30**, yielding 30/30/1; the test does not reduce the UI page size to make a three-row fixture pass. It retains tied/unknown dates and explicit typed observations. The first accepted acting-frame shot has xG=0, xGOT=0 and metre coordinates 52.5/34. A later correction changes A's fact/profile/build while C's original build remains independent. These are synthetic SQL writes only inside the owned cluster.

Application contract needed by ROOT:

- Detect the actual Pro manifest (`storage=aws-orion-pro`, schemaVersion4, frozenRepresentations capability). For this Pro match workflow, skip `loadSeason`, season/partition/source downloads, legacy status/init and archive/provider fallthrough.
- Choose an edition by league/season and pin its opaque `representationToken`. Keep `v` in page/detail navigation and every fixtures/summary/shots cache/request identity. An explicit old `v` must resolve a pinned manifest, not silently become the latest token.
- This first UI scope is one edition. A single available edition may be selected implicitly; multiple editions with an all-competitions filter require an explicit competition choice. No global pagination or aggregate immutable token is inferred from separate edition tokens.
- `/matchs/?tab=results&league=l_000001&season=2024%2F2025&focus=all` uses the real fixture page API with `limit=30` and returned cursors. Display one bounded page, preserving existing match rows and accessible pagination controls `Suivants`/`Précédents`; no complete-season preload/concatenation.
- Opening an existing match link requests the lightweight summary under its token. Reuse the existing scoreboard, tabs and shots renderer; fetching shots starts only when `Tirs & xG` (or the existing explicit analysis action) is activated.
- The renderer preserves numeric zero, native `is_goal=true` even when `event_type=""`, and the legacy metre convention. The retained `circle.shot-point` at 52.5m/34m has SVG cx=330, cy=219 and goal radius6 on the existing 105m/68m plot, with xG zero and a goal label in its accessible label/list. Unsupported frames stay explicit/unplotted; this test does not claim away/home frame parity.
- A resource key/client identity containing only match ID is insufficient. Navigation among initial A and independent C within the same browser application must preserve their cached entries when a new publication is accepted. Browser hard reload/new context is not used to claim a zero-network cache hit.

No particular internal React context property name is required. Existing public routes, 30-row product size, visible control names and accessible roles are the inspection interface. New UI state may expose semantic `data-*` attributes for published token/page only if useful to the product/agent; hidden test-only data injection is not used.

## Failure matrix written before harness and React code

| Complete browser workflow / failure | Expected observable outcome |
|---|---|
| Before React integration, real Pro manifest and fixture API are healthy | Actual rendered-page RED, screenshot, DOM snapshot, console and network failures retained; no success inferred from HTTP client-only tests |
| Open actual results page with Pro manifest | Site renders the selected edition; manifest fetched; no season blob/partition/archive/provider request |
| Traverse A page1/page2/page3 | Exactly 30/30/1 visible `.match-row` links, 61 unique IDs; one bounded fixtures request per uncached page, `limit=30`, matching cursor/token; controls correctly enabled/disabled |
| Return to a visited page | Correct rows, no duplicate materialization; same-token cached page can be reused without a new fixtures body |
| Open m_000001 overview | Scoreboard/summary renders; every summary request contains selected `v`; no shots/heatmap/network request or SQL |
| Activate `Tirs & xG` explicitly | One accepted typed shots request, correct token; numeric zero remains 0, not dash; the actual chart point uses metre coordinates; native goal bool with empty observed event type still renders as a goal |
| Switch away/back to the same detail tab | Shared token-aware client/resource cache reuses success; no provider/archive fallback |
| Mobile 390×844 | List, pager, scoreboard and active shots tab are operable and visible; no horizontal page overflow; screenshots retained |
| Publish corrected A/B while initial A is still open | Existing old-token UI/body stays frozen; explicit latest-edition navigation gets the corrected token/data |
| Revisit old A and independent C within the same browser app | Old content preserved and C token/cache unchanged; no new summary/shots GET when those exact resources are still retained |
| Unexpected network failure/API route/external request | Fail visibly with request/status/error in evidence; never silently filtered into a pass |
| Browser/page/Next/API/PG startup or cleanup fails | Case is failed/unverified with exact logs and owned-process state, never passed |

## Browser and evidence

Use the installed Playwright skill's CLI wrapper and a named isolated browser session. Snapshot before interactive refs; capture actual DOM, screenshots and Playwright trace. Use `run-code` only for required browser instrumentation/assertion or multi-step work grounded in the current snapshot, not to substitute application data. Browser API calls and pg-client SQL traces are independently captured. The Next server serves the real app; there is no mock page or mock API response.

Evidence goes under this owned directory (`runs/...` and `output/playwright/...`). It includes exact setup/rerun/commands, source/model/SQL digests and input copies, the selected publication tokens, ordered browser requests with response status/bodies, console/page errors, assertions, DOM snapshots, desktop/mobile screenshots, trace, and process/owned-directory cleanup. User preference storage may be initialized to an already-onboarded/all-competitions account to keep onboarding outside this bounded match workflow; the exact keys/values are recorded.

This browser run is local development execution, not Vercel deployment, CDN acceptance, a real-source reconciliation, a production latency benchmark, or all-site feature parity. Club/player/standings/analysis workflows beyond the summary and explicit shots tab are not certified. Any preparation fault is retained separately from a genuine application RED. No cloud/source read, shared mutation, commit or deploy is permitted.
