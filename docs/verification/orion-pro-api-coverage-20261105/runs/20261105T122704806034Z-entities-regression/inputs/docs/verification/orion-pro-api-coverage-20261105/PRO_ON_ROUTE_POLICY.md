# Proposed closed route policy for ProON

Suggested commit: `docs: map Pro API coverage and define publication rollout`.

**Review proposal only. No code or test has run.** This guard is independent of publisher work and of the107-table amendment. Production Pro remains OFF. It belongs in `dashboard/backend/aws-app.js` after the existing method/path security checks and before any historical football dispatch. The four current `orionProRoute` handlers run unchanged; a non-match must no longer fall through automatically when the flag is1.

## Exact allowlist for GET/HEAD

| Path | Query contract | ProON behavior |
|---|---|---|
| `/api/dashboard/manifest` | `v` only | Existing Pro V1 reader, unchanged |
| `/api/fixtures` | `league,leagues,season,seasons,status,from,to,q,limit,cursor,v` | Existing Pro V1 reader, unchanged |
| `/api/matches/m_[A-Za-z0-9]{6}/summary` | `v` only | Existing Pro V1 reader, unchanged |
| `/api/pitchapi/matches/m_[A-Za-z0-9]{6}/shots` | `v` only | Existing Pro V1 reader, unchanged |
| `/api/health` | none | Preserve existing operational health check. It currently reports historical serving readiness, **not** completeness/readiness of Pro publications |
| `/api/status` | none | Preserve existing configuration boolean/basePath diagnostic. The Pro client does not require it; allowing it exposes no football facts |
| `/api/assets` | existing `url` validation only | Preserve existing307 lookup to an already registered immutable image path. No source URL fetch, provider request or arbitrary data object response is permitted |

The image redirect remains an explicit operational/media exception; it is not a frozen football JSON route or a guarantee about source media completeness. Binary CDN delivery/static framework assets lie outside this router and stay unchanged. Existing CORS/OPTIONS/transport middleware, if supplied outside the router, stays outside the policy; the AWS router itself currently accepts only GET/HEAD and returns405 with Allow for other methods. Next's local `/api/visitor-country` returns country metadata only and is outside AWS dispatch.

## Closed default for all other data paths

Every other normalized `/api/…` path returns **501**, `available:false`, a stable error code such as `PRO_ROUTE_NOT_IMPLEMENTED`, and a short actionable message. This includes known historical routes and any future route not yet explicitly added to the Pro allowlist. No historical router/reader/cache/data-store/file/object/provider function may be entered first. Error body shape should remain the existing `ok:false,available:false,error` envelope. Use `Cache-Control:no-store` and the corresponding existing CDN no-store headers; no ETag/Last-Modified, no immutable/shared cache and no304 for this refusal. HEAD has the same501/no-store headers and no body. Do not claim an unimplemented route is an accepted empty collection or a source404.

Use501 for deliberately unimplemented capability. Existing Pro readers retain503 for unavailable/unready publication and404 for accepted-route resource/coverage absence; syntax errors on those routes remain400 before SQL. Generic bad path encoding/control/traversal checks and `/data/…`410 still precede the flag branch. Methods other than GET/HEAD retain405 before all Pro dispatch. No new network fallback or optional legacy query is part of the refusal.

Known blocked families are: settings; season partitions; scouting routes; archive match/profile/season/index; catalogue rankings/club links/cups/matchdays/supplemental; support standings/open-cups/openligadb/nations-results/club-Wikidata/coach portrait/stadium/player honours; compatibility date/league schedules and league/team/player resources; match root and every match section/nested player/shot route except the exact shots collection above. The full parameter/path inventory belongs in API_ROUTE_MATRIX.json. A `v` parameter does not turn a historical route into a Pro route.

ProOFF follows the original control flow byte-for-byte; neither validators nor historical fallback behavior is changed by this proposed guard. The guard does not remove UI controls or implement those capabilities. The UI may show explicit unavailable states until its own supported route is implemented.

## Future E2E matrix — write and execute before guard code

| Case / injected condition | Expected observable outcome |
|---|---|
| Direct helper GET to every known unsupported path family, including a correct-looking old `v` |501/no-store/stable error, no ETag, no source/file/object/provider/historical-reader access |
| Unsupported HEAD or If-None-Match request |501 with no body, never304, no football SQL/materialization |
| Unknown `/api/…` route added after inventory | Closed default501, no historical dispatch |
| Invalid generic path, method or removed `/data/…` path | Existing400/403/405/410 behavior preserved before the guard |
| Four Pro routes, frozen A and mutable current | Exact pre-guard body/status/ETag/cache/header bytes where stable; no alteration of summary-v1-shots-v1 or its profile/coordinate policy |
| Cold HEAD and matching conditional GET on all four Pro routes | Existing200/304 metadata-only access; zero body/profile/summary/heavy materialization as applicable |
| Accepted shots empty vs unknown/unavailable/missing coverage | Existing distinction and404/no-store retained, no fabricated zero/empty |
| Correct A/B, independent C; old V1 request and stale mutable cursor | Old pinned bytes unchanged; current A/B change only on publication; C token/body/ETag/cursor unchanged; old mutable cursor409 |
| ProOFF fixtures/profile/archive/catalogue/support controls | Existing functional legacy results on a complete owned legacy fixture; previous fallback flow remains reachable only with flagOFF |
| Health/status/media exceptions under ProON | Diagnostics/registered immutable-image redirect preserved; no data-object or arbitrary source redirect/fetch is admitted |
| Next proxy/transport | Unsupported helper routes also reach the closed guard; no Next compatibility fallback is invoked by Pro AWS responses; no source object/provider read |
| Counts, cleanup and failures | Record exact HTTP/headers/body and SQL/source/file/object/provider counters; stop owned processes/DB; preserve RED and all unexpected failures |

Use the existing owned PG18.6 reader fixture for all94 active Pro tables and real read-only runtime role, plus a separate complete owned historical serving fixture for ProOFF functional controls. Do not use the current empty historical router RED as a claimed positive legacy control. Instrument the actual lower-level read functions/files/object/provider transports before execution; zero HTTP calls alone does not prove zero file/object reads. Refusal should be proven before historical function entry, including a source-function tripwire, not only from its status code. No football response may be mocked; synthetic typed fixture values are permitted. Binary media redirect resolution may query its existing asset mapping only.

This is a planned test protocol; no fixture, harness, test, SQL or application change is authorized by this document. ROOT reviews this policy and exact path list before any guard implementation.
