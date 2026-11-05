# Closed fallback guard — local result and next proposals

Suggested commits: `fix: close unversioned football fallbacks in Pro mode`; `docs: map Pro API coverage and define publication rollout`.

The only product change is aws-app.js. With STATARENA_PRO_API=1, the four current Pro readers run unchanged; health/status and registered immutable-image redirects remain available; every other API path returns501 PRO_ROUTE_NOT_IMPLEMENTED/no-store before historical data dispatch. ProOFF retains its original route/read/cache behavior. ProON images additionally require registered matching PNG/JPEG/WebP MIME metadata, with a separate cache namespace; no binary is fetched or inspected.

This is a local correction and review package, **not deployment/activation, complete site/data parity, publisher implementation or approval/application of model107**. The guard is an interim explicit unavailable boundary; the broader parity objective remains.

## Evidence retained

| Run | Actual result | Meaning |
|---|---|---|
|20261104T234252158556Z-pre-guard-red|0 pass /0 fail /18 unverified|Setup rejected an extra `ok` in the synthetic legacy publisher envelope; no product RED claimed |
|20261104T234319721638Z-complete-fixture-pre-guard-red|12 pass /6 fail|Genuine pre-code HTTP/PG RED: direct historical fallback, missing MIME check and OFF→ON cache reuse |
|20261104T234428216754Z-media-formats-pre-guard-red|12 pass /6 fail|Expanded accepted image formats and mismatch counterexample specified before product correction |
|20261104T234450895270Z-closed-guard-first|18 pass /0 fail|First full corrected HTTP workflow |
|**20261104T234630404920Z-closed-guard-final**|**19 pass /0 fail /0 unverified**|Final formatted helper/unchanged product bytes, plus explicit health/status GET/HEAD and11 positive legacy controls |

Every run has its original result, exact source inputs/commands, runtime export/observation-wrapper hashes, HTTP headers/bodies, per-request real PostgreSQL SQL/binds and cleanup. Historical runs are unchanged. RED_SUMMARY.json identifies the first genuine RED; it does not relabel the setup failure as a guard failure.

Final: [result.json](runs/20261104T234630404920Z-closed-guard-final/result.json). It used owned PG18.6 with94 active Pro tables and159 complete historical serving-schema tables, unmodified ReaderFixture A/B/C plus synthetic nonempty legacy publications, two isolated real Bun HTTP servers and the actual readonly role. The baseline server uses aws-app.js captured before the correction; the candidate server uses the changed source. Thin import wrappers observe and call the real historical readers; no football response or SQL result is mocked.

-261 actual business HTTP requests, including153 candidate501 responses:50 route forms × GET/HEAD/conditional plus3 unknown/versioned forms.
- All153 refusals:0 SQL,0 historical function entry,0 legacy body materialization, no ETag/Last-Modified, all three cache headers no-store. HEAD body empty; conditional requests remain501.
-11 nonempty ProOFF controls compare actual status/body/ETag/stable cache/representation headers against pre-guard code: manifest, fixtures, partition performances, scouting, league/player profiles, legacy shots/summary, archive match/index and support stadium. No positive control is just404/empty.
- Health/status GET/HEAD match the pre-guard behavior. Health is historical serving readiness, not a new Pro-completeness signal.
- Frozen/current V1 manifest/page/summary/shots body bytes, ETags and selected stable headers match baseline; existing NULL/type/empty event/true goal/metre/frame behavior remains. HEAD/304 use metadata only. Correct A/B, distinct dg/cg, old A pins, C and stale current cursor behavior pass unchanged.
- Registered PNG/JPEG/JPG/WebP paths redirect307; JSON/JSON.gz, mutable/traversal/arbitrary URL paths, missing alias, application/json PNG and MIME-extension mismatch are rejected. OFF-warmed misleading alias cannot pass ON. Redirects are never followed.
-0 source-access tripwire calls across all requests; source-file/provider/object modules are excluded by the explicit runtime graph. Six tripwire calibrations reject before I/O. This is not an OS syscall audit; code/library/DB initialization occurs before source-access instrumentation.
- Runtime is statarena_runtime/read-only; an actual write attempt also fails42501 with transaction readonly disabled. Owned APIs and PostgreSQL stop, owned DB directory is removed, sourceChangesDuringRun is empty. Targeted Prettier check passes.

Exact final rerun from repository root:

```sh
PYTHONPATH=/tmp/statarena-publication-test-python python3 tests/orion_pro_route_guard_local.py --label closed-guard-final --baseline-receipt docs/verification/orion-pro-api-coverage-20261105/runs/20261104T234428216754Z-media-formats-pre-guard-red/result.json
```

The harness creates a fresh timestamped receipt. PostgreSQL binaries default to the existing local embedded18.6 path recorded by the command log; Bun runs with --no-env-file and a minimal local environment. Runtime exports copy explicit canonical modules only, no dotenv/numbered files. Their node_modules symlinks reuse local installed dependencies and are setup artifacts, not dependency source exports to publish. The local DB/server and code inputs suffice to reproduce this backend workflow; no cloud credential/data is required.

## Review documents and limits

- [API_ROUTE_MATRIX.md](API_ROUTE_MATRIX.md) / JSON:57 exact AWS path forms, methods, parameter names,4 Pro readers/3 exceptions/50 closed paths, existing103 destinations.
- [CLIENT_SCREEN_MATRIX.md](CLIENT_SCREEN_MATRIX.md): all public client methods, direct helper bypasses, screens/tabs, token/cache boundaries and parity blockers.
- [PUBLISHER_PLAN.md](PUBLISHER_PLAN.md): missing production publisher, exact edition build/data/catalogue/closure/aggregate/pointer/no-op/retry design, guarantees already in013 and remaining application gates.
- [IMPLEMENTATION_ORDER.md](IMPLEMENTATION_ORDER.md): route/product lots after publisher, pending107 native families, derived products and9 deferred scoring relations.

Publisher plans are unimplemented; no new orion_pro_publish.py, reader, aggregate contract, schema/model change or source reconciliation was made. The code inventory is local, including the normalizer's current draft publication assignment; no real source/hosted state was inspected. Frozen V1 code,012/013 and approved model hashes are unchanged.

Next/browser/Vercel/CDN wiring and actual media content were **not executed** in this direct backend HTTP lot. The earlier policy's planned Next transport row remains a separate integration check; a deployment using the historical Vercel compatibility branch does not automatically gain the AWS guard. Selected stable-header comparison excludes volatile Date/Server-Timing fields. No full-source, full-site, clone/CI, live performance, activation or purge conclusion follows from these fixtures.
