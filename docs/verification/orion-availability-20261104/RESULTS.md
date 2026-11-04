# Availability and dense-reader results — 4 November 2026

## Released state after owner review

The exact production-target Vercel build `dpl_2YjDXsva7FBr4yDnzRShmZ776MbA`
(main `f65036cdb9273654614354cc083039d2a200a491`) was staged without domains,
built successfully on Vercel in23s, then passed12 real desktop/mobile browser
workflows using its actual server-side Neon credentials. No relay or shim was
used in this acceptance. Root reviewed all seven product paths and promoted
that same immutable build; both canonicalaliases now resolve to it.

Before/after canonicalhealth and manifest: **503→200**, with six seasons and
230 partitions. The actual archive2020/21 endpoint now returns200 and the
original238,411 gzip bytes (2,677,442 decodedJSON), retaining ETag/HEAD/304 and
coding negotiation. Source-backed404 gaps remain404; no data completeness or
all-player coverage claim follows from this recovery.

Evidence: [stagedHTTP](vercel-stage-initial-http.json),
[real12-workflow browser](vercel-browser-20261104T173656163590Z.json),
[promotion/alias readback](vercel-production-readback.json),
[canonicaldesktop/mobile](canonical-browser.json) and their screenshots/logs.
The connector error/fatal-log query returned no records for the specified
10-minute window; this is a bounded log observation, not a monitoring/SLA claim.
Reproduce with `python3 docs/verification/orion-availability-20261104/run_deployed_browser.py https://statarena-analytics-hkt6tq5ke-hlemonniers-projects.vercel.app`
and `python3 docs/verification/orion-availability-20261104/run_canonical_browser.py`.

The stage helper initially failed to unpack the CLIJSON envelope and recorded
null deployment fields after successful upload; direct authenticated API
readback established the actual build identity. The helper was corrected; no
second upload or rebuild was performed. All acceptance tested the same build.

**This restores complete saved-Neon access temporarily.** The explicitAWS
preview origin still takes priority. New typedRDS ingestion, comprehensive data
parity, finalAWScutover and sourcecleanup are separate unfinished work; collectors
remain disabled and no schema/source data were changed by this recovery.

The AWS dense-reader lot is also deployed, with identical response values and
bounded actualHTTP/validators accepted. Its exact release, same-snapshot
**2,605.772→2,019.623ms (−22.49%, one ordered pair)**, threepostdeploy reads
**4,008.62/3,575.56/3,034.98ms** and limits are in
[DENSE_QUERY_RESULTS.md](DENSE_QUERY_RESULTS.md). Dense partitionGETs remain
no-store; stablematch public-cache smoke passed10/10. No p95, storage or dollar
saving is claimed. Both source commits passed their complete GitHubCI runs;
`github-ci-readback.json` records the final successful results.

The following sections preserve investigation chronology and local evidence.
Statements about no deployment describe the named agent's historical scope,
not the released state above.


## Current service and restoration candidates

At 17:27 Paris the canonical alias `statarena-analytics.vercel.app` pointed to
READY deployment `dpl_H1BPDyH7ppFrBA1KjwZMGT1U8kPv`, commit `b2ec973d2d`.
Its home returned 200; `/api/health` and `/api/dashboard/manifest` each
returned 503 with an empty body. The only `NEXT_PUBLIC_API_ORIGIN` environment
entry targeted the historical `codex/aws-backend-20261104` preview branch.
That commit's `bun-proxy.js` explicitly returns an empty 503 on Vercel when the
origin is missing. The AWS endpoint remained on revision 43 and returned health
200. Its manifest exposed one season and 38 chunks; this is not proof that it
has the same coverage as the old service. See
[readback](readback-20261104T162706525702Z.json).

The immutable previous production deployment
`dpl_5WKUEwBpNkr3hUEk9Fk8qF8EVFBe`, commit `0aaf316e0a`, still returned
Neon revision 18 on health. Its actual `/data/dashboard-manifest.json` had six
seasons and 230 chunks. Both sampled Ligue 1 chunks, 2026/27 and 2025/26,
were fetched and decompressed, and its stored league endpoint returned 77
leagues. [Read-only sample](restore-probe-20261104T164354208484Z.json).
The first sample's `competitionCount: 0` meant the old manifest had no
top-level `competitions` array, not that its chunks lacked competitions; the
corrected receipt records this field as null and 230 nested references. The
first generic probe similarly attempted to interpret a 404 error as a manifest;
the 404 is correct and the parsing condition has been fixed.

An isolated headless Chromium session opened the old deployment, loaded the
current season, opened a featured match and its team statistics, loaded the
previous season, and fit the 390-pixel viewport. All six checks passed, with no
page exceptions. Browser requests outside the old Vercel host were blocked.
This is sampled behaviour, not exhaustive coverage. The first CLI browser
launch failed because Google Chrome was absent; the successful rerun used the
already installed Chromium configuration. [E2E receipt](browser-e2e-20261104T163549174045Z.json)
and `browser-open.log` preserve both outcomes.

Promoting the old deployment is a directly observed recovery candidate, but it
temporarily loses changes made since `0aaf316e0a`: the diff includes 50 frontend
files, including later player-profile and radar changes. No rollback or
deployment was performed in this investigation.

## Current interface compatibility bridge: local acceptance

The current frontend now has a bridge validated locally to the existing Neon
reader and saved objects. Vercel with no explicit public AWS origin selects
`legacy-app.js`; an explicit `NEXT_PUBLIC_API_ORIGIN` still wins, and local
non-Vercel transport keeps its local upstream. The current `loadSeason`
interface decodes `json-packed` chunks. New fixture, scouting, summary,
archive, ranking, cup and supplemental routes adapt existing saved data.
Unknown paths and source errors remain observable. No layout changed; the
competition-view edit only aliases an import to fix its existing binding
collision. The source and pre-edit failure requirements are in
[BRIDGE_PROTOCOL.md](BRIDGE_PROTOCOL.md) and
[ACCEPTANCE_PROTOCOL.md](ACCEPTANCE_PROTOCOL.md).

The original [bridge HTTP E2E](bridge-http-20261104T170630100Z.json) passed
20 workflows, and [transport E2E](transport-20261104T165815892Z.json) verified
local forwarding, AWS-origin priority, `/data` 410 when AWS is configured, and
missing-Neon failure. Earlier red artifacts remain in this directory. The
new [real acceptance E2E](bridge-acceptance-20261104T171926084Z.json) passed
32 workflows using the actual compatibility HTTP handler and saved data from
the immutable old deployment. It made 264 unique external reads, returned
10,463,575 bytes, and measured at most four concurrent external reads. It
cached duplicate source requests in memory and persisted only metadata/hashes.
Its timings therefore do not measure uncached production Neon request cost.

| Current UI data family and filters | Verified outcome | Limits |
|---|---|---|
| Manifest, `/data/*`, `loadSeason(season, leagueIds)` | Exact six-season manifest, 230 references; one Ligue 1 partition loaded for each season. Matches: 81, 306, 306, 306, 380, 380; appearances: 3,237, 12,200, 12,215, 12,225, 15,057, 15,092. | All 230 partitions were not downloaded or exhaustively checked. |
| `/api/fixtures`: league+season, league across seasons, day, all/played/upcoming, cursor/limit | Six-season league union matched source values and dates: 1,985 fixtures in 20 pages, including 1,759 finished and 225 not started. Day sample: 65 fixtures; `historicalFixtures` returned the exact union. Per-season pagination passed the original HTTP run. | One canceled/other-status fixture remains in `all`; no fixtures were invented. Synthetic fault checks cover changed generations and the legacy row cap. |
| Scouting and player/team history | Exact route indexes: sampled player has four seasons and sampled team two; real player-history loader found 9/32/34/37 appearances in its four indexed seasons. | Representative profiles, not every indexed identity. |
| Summary, archive match/profile and PitchAPI resources | Five summary leaders; saved match, stats, players, halves, lineups, shots, events, momentum, H2H and advanced-resource statuses/bodies/cache headers match source. League/player/team profiles and a saved image asset returned 200. | Sampled heatmap is source 404. Other matches and assets remain sampled. |
| Archives: results/goals, season | Exact indexes: 150 results seasons (2020/21 to 1871/72) and 62 goal seasons (2024/25 to 1963/64). Both boundary seasons of each index returned 200 and exact saved values. The browser additionally exposed a 2020/21 goals object larger than 2 MiB; the focused correction now serves its existing 238,411-byte gzip and exact 2,677,442-byte decoded JSON. | Archive-season gzip responses cap encoded bytes at 2 MiB; identity-only requests retain the generic JSON cap. Other season objects remain sampled. |
| Cups: worker/supplemental indexes; competition+season+table kind; snapshot kind | Catalogs contain 11 worker and 65 supplemental competitions; representative results and fixtures preserve values. World Cup 2022 (64 matches), DFB-Pokal 2025/26 (63), Nations League (48/72) and native Champions League (144) snapshots returned 200. | Historical-edition selection was tested synthetically in the earlier HTTP E2E. The sampled saved standings snapshot is source 404. |
| Supplemental client | **All 65 competitions and all 195 table references** decoded and matched saved values: 5,575 results, 8,618 fixtures and 2,036 goals. Client used 196 individual object requests, at concurrency at most four. | Expanded JSON is 3,806,859 bytes. The combined `/api/supplemental` endpoint returns explicit 413 at its 2 MiB cap; the actual `json-packed` client path succeeds through individual saved objects. |
| Club links/rankings, associations and matchdays | Association ranking has 55 rows; positive club link and four UEFA editions passed the original HTTP run. New acceptance preserves the no-link club shape and reads 144 matchday entries. | No-link/null rank data is not evidence of a positive ranking. All years/club mappings were not checked. |
| Honours, standings, stadium, club facts, coach portrait, status, visitor country | Existing legacy routes retain exact source statuses, bodies and cache headers; browser visitor-country route returns 200 independently. | Exact browser honours `p_3chd12`, sampled historical standings, stadium `Q1`, club lookup `Paris/FRA`, and coach `Test` return source-backed 404s. Positive data availability for every stored projection is not established. |

The browser's honours 404 is not a bridge regression: the exact
`/api/player-honours?id=p_3chd12` path returns the same 54-byte source response,
SHA-256 `355c74c6e9516430d1447c97d6174688ca9b35de57e49fbadb02e6ed89f86887`,
and `Cache-Control: no-store`. The real existing honours client maps that 404
to `{ groups: [], partial: true }`; no successful projection was fabricated.

Fixture validation originally discarded null, missing-ID and numeric-ID rows,
and accepted an empty identity. The [first red HTTP run](fixture-integrity-20261104T171605182Z.json)
proved all four cases returned successful partial pages. The minimal correction
checks the saved rows before filtering/deduplication and returns
503/`DATA_UNAVAILABLE` on a missing or invalid identity. The same
[17 HTTP workflows passed](fixture-integrity-20261104T171617076Z.json), covering
valid values/deduplication, status filters, calendar/history scopes, changed
publication, 20,000-row truncation guard, source errors, invalid queries and
HEAD. These fault inputs are synthetic; no malformed live rows were claimed.

The expanded browser then exposed an actual archive regression: 2020/21 goals
existed at source but the adapter returned 413. The [browser red](bridge-browser-20261104T172132481647Z.json)
and [focused HTTP red](archive-goals-20261104T172628385Z.json) are retained.
The correction forwards the existing saved gzip as JSON with
`Content-Encoding: gzip`, preserving the original ETag/cache metadata, HEAD
and conditional GET; the encoded body retains the 2 MiB cap. It does not change
client URLs, UI layout, saved bytes or explicit AWS routing. Explicit
identity-only, `br`-only or `gzip;q=0` requests are not sent unsupported gzip;
they retain the uncompressed path and its explicit 413 when oversized.
The [focused HTTP E2E](archive-goals-20261104T172656403Z.json) passed six
workflows: actual catalog-client value equality, metadata/HEAD/304, query/
missing-season handling, coding negotiation, encoded-size rejection and source
503. It read only the saved archive index/object and metadata; fault cases are
labelled synthetic. The earlier 32-workflow run predates this isolated archive
correction; final browser/build and these focused workflows cover the final
archive source hash.

The [first disposable Next production build](bridge-build-20261104T171420028814Z.json)
passed with Next 16.4.3/Webpack and no public AWS origin or production
credentials. The [final production build](bridge-build-20261104T172723051561Z.json) passed at the final
fixture/archive source hash. The [final browser receipt](bridge-browser-20261104T173306252606Z.json)
passed all 12 workflows, including the affected archive filters, oldest archive
and goal-event detail, with no page exceptions. Final exact hashes and cleanup
are recorded in [HANDOFF_SOL.md](HANDOFF_SOL.md).

Local-shim browser checks exercise the current Next UI at desktop and 390px
mobile, including home, match/statistics, player/profile/history, club/ranking,
competition/cup indexes, calendar redirect/week filters, archive season/
competition/search/event detail, ranking season and method routes. The browser
runner temporarily substitutes saved-data relay shims in the copied backend;
it is **not** the real Neon SDK/credential path. It also installs the declared
`flag-icons@7.6.0` only in the disposable checkout because the installed
workspace dependency is absent. These passes do not establish actual Vercel
runtime duration/response limits, production database permissions, CI, or live
availability. Parent owns an actual credentialed preview, independent review,
preview evidence and release. No deployment, alias/environment change,
provider collection, SQL write or source-data copy was performed by this agent.

## Dense page reader

The earlier deployed dense Serie A `limit=100&format=columns` request had
failed with 503 and SQL `57014` under an 8-second deadline. At 17:27 the same
deployed code and route returned 200 once in 5,938.97 ms client wall time with
the same 1,973,314-byte body and SHA as the previous good reference. This single
observation does not erase the original failure or establish reliability.

The earlier uncommitted optimization filtered appearances on their own
`season` and `league_id`. A paired local E2E demonstrated that a row whose
season disagreed with its match was silently omitted: old reader 2 appearances,
candidate 1. The pre-edit [red run](reader-comparison-20261104T163659245Z.json)
and [protocol](FIX_PROTOCOL.md) are preserved. The authorized change now
selects appearances by the page's match IDs, matching the deployed reader, and
still materializes them and aggregates their extra metrics once. The original
patch is preserved in [before-semantic-fix.patch](before-semantic-fix.patch).

The post-fix [paired local HTTP E2E](reader-comparison-20261104T163921235Z.json)
passed eight comparisons: both cursor pages, full page, decoded compact wire,
another league, conditional GET, future schema fallback, and the deliberately
inconsistent appearance. Existing isolated publisher/API checks passed 9
workflows and 10 HTTP checks; the compact-wire/property checks also passed.
These reader E2Es use synthetic data and a disposable local PostgreSQL database.

One production RDS pair then used the exact SQL captured from the baseline and
revised handlers, a single read-only repeatable-read snapshot, the same Serie A
generation, and the existing 8-second statement deadline. Each returned 100
matches and 4,788 appearances with the same canonical semantic result hash.
Client execute-and-fetch times were 2,605.772 ms baseline and 2,019.623 ms
candidate for this ordered pair. [RDS receipt](rds-pair-20261104T164032339102Z.json).
This is a correctness sample, not p95, a load test, or proof that the deployed
HTTP timeout has been eliminated. This pair measured the local candidate before any deployment.

Before publication: confirm the tested source hash is unchanged; run the
project's normal CI and build; deploy the isolated backend change only under
the owner's release decision; then test the actual deployed dense route under
the unchanged timeout with matching generation and semantic content, multiple
representative page sizes and observed load, retaining failures. Verify that
frontend recovery and the separate shared-dimension cache-version issue are not
mistaken for this query fix. No schema migration, RDS write, workflow restart,
provider collection, release, rollback or environment change occurred here.

## Reproduction

Run from the repository root. Cloud probes require existing authorized CLI
credentials; the RDS command uses the existing `.pgpass` without reading or
printing it. The RDS command performs one additional bounded pair if rerun.

```sh
python3 docs/verification/orion-availability-20261104/capture_readback.py --dense-aws
python3 docs/verification/orion-availability-20261104/restore_probe.py
python3 docs/verification/orion-availability-20261104/legacy_contract_probe.py
bun docs/verification/orion-availability-20261104/legacy_loader_probe.mjs
python3 docs/verification/orion-availability-20261104/run_browser.py
STATARENA_TEST_TOOLS=/tmp/statarena-cache-test-tools STATARENA_TEST_PYTHONPATH=/tmp/statarena-publication-test-python bun docs/verification/orion-availability-20261104/compare_readers.mjs
STATARENA_TEST_TOOLS=/tmp/statarena-cache-test-tools STATARENA_TEST_PYTHONPATH=/tmp/statarena-publication-test-python STATARENA_CORE_API=1 STATARENA_CORE_EVIDENCE=docs/verification/orion-availability-20261104/core-rerun bun dashboard/scripts/verify_relational_core.mjs
STATARENA_TEST_TOOLS=/tmp/statarena-cache-test-tools STATARENA_TEST_PYTHONPATH=/tmp/statarena-publication-test-python STATARENA_CI_EVIDENCE=docs/verification/orion-availability-20261104/wire-rerun bun docs/verification/aws-wire-pages/disposable.mjs --ci
PYTHONPATH=/tmp/statarena-publication-test-python python3 docs/verification/orion-availability-20261104/compare_rds.py
```

Suggested commit: `perf: batch appearance metrics while preserving match membership`.
