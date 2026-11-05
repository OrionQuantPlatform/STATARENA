# Closed ProON fallback guard — pre-code local E2E

Suggested commit: `fix: close unversioned football fallbacks in Pro mode`.

ROOT reviewed PRO_ON_ROUTE_POLICY.md and authorized this bounded local implementation independently of the pending107-table amendment. API_ROUTE_MATRIX.json freezes57 existing AWS GET/HEAD path forms:4 native Pro,3 operational/media exceptions and50 unimplemented. Its SHA is captured before each run. The closed default must also reject future/unknown API paths; the inventory is not a permissive denylist.

## Setup and authority

Use owned loopback PG18.6 only, an isolated temporary directory and real Bun HTTP servers. Apply exact existing003–013 SQL solely to the owned database; bootstrap012/013 through existing pure helpers. Reuse ReaderFixture unmodified for94 active Pro tables, sealed A/B/C publications and correction. Reuse the synthetic legacy normalizer/publishers to create complete historical serving schemas with actual matches, appearances, a shot, match detail, profiles/catalogue and a nonempty support fact. Real statarena_runtime has read-only startup plus SELECT-only schema access. No saved/source input, provider, S3, Neon, AWS, real image or host/deployment is accessed.

Two isolated runtime exports contain only explicit canonical backend modules/models/package metadata (no dotenv, numbered copies, credentials or data). Both invoke real PostgreSQL readers. Baseline uses the pre-guard aws-app.js retained in the RED receipt; candidate uses current aws-app.js. The only test transformation rewrites its historical-reader import targets to thin observation wrappers which call the original functions, never simulate football responses. Frozen orion-pro.js/common services are exact copies. Golden and candidate share one fixture DB, avoiding generated timestamp/build-ID differences between runs. Each export has an isolated module/cache process.

Instrumentation records actual per-request pg SQL/binds, historical function entries and body-materialization calls. Backend external fetch and JS source-file read abstractions are tripwires after module/DB initialization; calibration attempts must throw before I/O. The runtime's explicit import graph excludes file/data-store/provider/object SDK modules; no hidden object transport is included. Requests, tripwire counters and graph/hash evidence are retained. This does not trace every operating-system read: legitimate code/library initialization is excluded. Refusals must have0 SQL and0 historical entry, body materialization and source-file/provider/object transport access.

Bun runs with `--no-env-file`, minimal allowlisted local environment and loopback-only local DB URL. No production credential is copied or printed. All source exports/hashes are inspectable. The baseline is selected explicitly by a later `--baseline-receipt` argument; a RED does not become a baseline success merely by changing the expected status.

## Failure matrix

| Case | Expected |
|---|---|
| Positive ProOFF baseline controls | HTTP200 with actual nonempty manifest/matches/performances/scouting/profile/detail/support data; compare candidate to retained baseline bytes/ETag/cache headers |
|50 unsupported GET forms |501 stable PRO_ROUTE_NOT_IMPLEMENTED, all cache layers no-store, no ETag,0 SQL/legacy/materialization/source access |
|50 unsupported HEAD forms | Same501/no-store, no body,0 reads; If-None-Match must not produce304 |
|50 unsupported conditional GETs |501 rather than304;0 reads and no ETag |
|Unknown/new API path; unsupported route with syntactically valid/bad v |501 closed default before legacy validation or reads |
|Malformed path, dot-prefixed segment, POST, removed /data | Existing400/403/405 with Allow/410 behavior; no business read |
|Registered immutable PNG/JPEG/WebP image metadata |307 to configured HTTPS CDN/data path; no redirect followed, no binary/object read |
|Registered JSON or JSON.gz path, mutable image, traversal, arbitrary URL path, absent alias |404/no-store; no redirect or source/object read |
|Registered application/json metadata under a valid hashed.png path | ProON404; records current missing-MIME counterexample before correction |
|Warm the same misleading image alias in ProOFF, then enable ProON | ProOFF retains its previous307; ProON still404, proving cache namespace isolation |
|Four frozen/mutable Pro routes on same A/B/C | Baseline/candidate body/status/ETag/cache/representation-header bytes identical; old source policy, empty event type, metre coordinates and states unchanged |
|Cold HEAD/304 on all four native routes | Existing metadata-only reads, no DTO/profile/summary/heavy materialization; responses bodyless |
|Correction data then catalogue A/B | Distinct dg/cg, new A/B token, correct new values; old A pinned manifest/page/summary/shots bytes and ETag unchanged |
|Independent C and stale mutable cursor | C token/body/ETag/cursor unchanged; old current A cursor409/no-store |
|Actual runtime role | current_user=statarena_runtime, transaction_read_only=on; explicit write attempt refused even with readonly mode disabled |
|Run failure/cleanup | Preserve failures/unverified cases, exact sources/commands, SQL/HTTP logs; stop owned servers/PG and remove only owned temporary DB directory |

The image exception validates **registered MIME metadata + allowed matching extension + immutable path**, not the actual binary content. Its historical mapping stores content_type, but the current router selects only path. If the E2E confirms the misleading PNG counterexample, add a ProON-only MIME check and separate alias cache key; keep ProOFF behavior unchanged. No request-time media fetch or new media format is added. Actual asset completeness/content verification remains a future data/purge gate.

## Exact rerun interface

```sh
PYTHONPATH=/tmp/statarena-publication-test-python python3 tests/orion_pro_route_guard_local.py --label pre-guard-red
```

After preserving that receipt and implementing the guard:

```sh
PYTHONPATH=/tmp/statarena-publication-test-python python3 tests/orion_pro_route_guard_local.py --label closed-guard-final --baseline-receipt <RED-result.json>
```

Every run writes a fresh timestamped directory under runs, including expected/actual cases, all HTTP bodies/headers and per-request SQL, input copies, import rewrites, runtime identity, tripwire calibration, source hashes before/after and cleanup. Baseline and candidate responses are compared as bytes; volatile HTTP Date/Server-Timing measurements are excluded from the selected stable-header comparison. No test has run when this protocol is written. Guard closure is a temporary honest capability boundary; full product/data parity remains the objective and is not replaced by501 responses.
