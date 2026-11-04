# Handoff — final local frontend bridge acceptance, 4 November 2026

Repository: `/Users/lemonnierhugo/Desktop/Coding Project/Football_ranking`,
branch `main`. Root owns releases, backend, configuration, WORKLOG and
independent review. No frontend commit, deployment, alias/environment change,
remote SQL/data write, provider collection or duplicate RDS pair was performed
by this continuation. Product source and evidence/docs are now write-quiescent. The original backend dense-reader evidence remains in
`RESULTS.md`; root owns its later release status.

## Final frontend product hashes

These seven files comprise the bridge. This continuation changed only
`legacy-compat.js`: fail closed on malformed fixture identities, then serve
saved archive gzip transparently to preserve the existing archive JSON URL.
The six other product hashes remain from the previous handoff. The manifest is
[bridge-final-source-manifest.json](bridge-final-source-manifest.json).

| Product path | SHA-256 |
|---|---|
| `dashboard/frontend/app/data/[...path]/route.js` | `d33ed98f008638c4589c9b7fd287dd3df9d43ae93e375290568a93dcf8e9ca29` |
| `dashboard/frontend/src/data-url.js` | `cb1d8f3b3ce19d87e1f30b0ba7b3e4c3ab59793ca36e14da6a626080e12548b2` |
| `dashboard/frontend/src/season_data.js` | `928b8d38f1d4842ed3e8eae5ea0203a15f6f0daaa8e6b7cc6bd908f3287e62ea` |
| `dashboard/frontend/src/server/bun-proxy.js` | `1ffded949a830e2f5264550c0fe2bbfe741c45023df520db4f0287927fce8309` |
| `dashboard/frontend/src/server/legacy-compat.js` | `e3fe3671af2b5e457c2199916607b7ee3ab28fc43bc1d590ee2d42d3bcbf1b2d` |
| `dashboard/frontend/src/services/football-client.js` | `17234cd4db775e469a74c550a4df3c674ef05da0b43f3de97965788aa3e14384` |
| `dashboard/frontend/src/views/CompetitionsPage.jsx` | `e42fec521f9504d4a66a27cb5292e14f4c293ca319b642391e718d2952c49ba0` |

## Evidence and exact measured results

- [Real saved-data acceptance](bridge-acceptance-20261104T171926084Z.json):
  **32/32 workflows passed** before the isolated archive gzip correction.
  264 unique old-deployment reads, 10,463,575 response bytes, maximum concurrency
  four. Duplicate source requests were cached in memory; these are not
  uncached Neon runtime/load measurements.
- Six Ligue 1 season partitions loaded: 81/306/306/306/380/380 matches and
  3,237/12,200/12,215/12,225/15,057/15,092 appearances. Manifest contains six
  seasons and 230 references; all 230 partitions were not downloaded.
- Full historical league fixture union: **1,985 matches in 20 pages**, exact
  source semantic hash `9daf822cd5c32532ce54a1ac2efe2b442b75df527ff22e9d9032b7e3a11623f5`.
  Played=1,759, upcoming=225, with one other-status fixture retained in `all`.
  `historicalFixtures` returned the exact six-season union. Day/status and
  player/team route/history filters passed.
- **All 65 real supplemental competitions / 195 saved tables** expanded through
  the actual `json-packed` client using 196 individual saved-object requests:
  5,575 results, 8,618 fixtures, 2,036 goals. All table values and declared row
  counts matched. Expanded JSON is 3,806,859 bytes, semantic SHA-256
  `30b2a3d49e49906a29c294f3a9b5dfa907c3555080e6e453647ca0445b69716e`.
  Whole `/api/supplemental` explicitly returns 413 at its 2 MiB cap; current
  legacy UI succeeds through bounded individual objects instead.
- Fixture integrity: [first red](fixture-integrity-20261104T171605182Z.json)
  proved null, absent-ID, numeric-ID and empty-ID inputs returned partial 200
  pages. The [17-workflow green](fixture-integrity-20261104T171617076Z.json)
  verifies fail-closed validation, legitimate values/deduplication, status/
  calendar/history scopes, changed generation, 20,000-row limit, source errors,
  invalid queries and HEAD. Fault inputs are synthetic HTTP workflows.
- Honours `/api/player-honours?id=p_3chd12` is **source 404**, identical 54-byte
  body/hash/cache headers to the bridge. The actual client returns
  `{ groups: [], partial: true }`, preserving its existing contract. This is
  unavailable saved data, not a bridge regression or a fabricated success.
- Archive browser [first red](bridge-browser-20261104T172132481647Z.json)
  exposed 2020/21 goals 413. Existing gzip is **238,411 encoded / 2,677,442
  decoded bytes**. [Focused HTTP red](archive-goals-20261104T172628385Z.json)
  was written before correction; [final six HTTP workflows](archive-goals-20261104T172656403Z.json)
  pass at the final source hash. They prove exact values through the current
  catalog client, source ETag/cache/length, HEAD 200, conditional 304, query/
  missing-season handling, coding negotiation, encoded-size 413 and source 503.
  Explicit identity/br-only or `gzip;q=0` does not receive unsupported gzip;
  those requests use the original capped uncompressed response. The generic
  cap remains; gzip archive-season responses cap encoded bytes at 2 MiB.
- First post-fix browser [harness failure](bridge-browser-20261104T172721922119Z.json)
  retained: the local relay removed raw-object Content-Length and correctly
  triggered the metadata 503 guard. The relay now removes lengths only when
  fetch decoded an HTTP content coding; raw `.gz` lengths survive, matching the
  actual legacy file handler. HTTP runners received the same relay correction.
- [Final production build](bridge-build-20261104T172723051561Z.json) **passed**
  at the final `e3fe3671…` archive/fixture hash. Next 16.4.3, documented Webpack
  mode, disposable copy, VERCEL=1, public AWS origin absent, no production
  credentials. The workspace's missing declared `flag-icons@7.6.0` was supplied
  only in the temporary checkout. Full build output and dependency log exist.
- [Final expanded browser](bridge-browser-20261104T173306252606Z.json):
  **12/12 workflows passed** at the unchanged final product hash. Includes
  home, match/statistics, player/scouting, club/UEFA card, competition/cup
  indexes, 390px historical mobile, calendar redirect/week/query preservation,
  archive 2020/21 season+competition+team search, oldest 1871/72 archive (22
  visible rows), 2024/25 stored goal detail (three events), ranking season and
  method routes. No page exceptions. The second relay/chunked-length failure
  is retained in `bridge-browser-20261104T173010657951Z.json` as well.
- Cleanup readback: no owned bridge Next/adapter/browser/runner processes;
  final adapter/frontend ports 60564/60565 closed; named Playwright session
  closed. Final manifest contains the observation and exact final hashes.

Full route/filter inventory and source-backed data limitations are in
[RESULTS.md](RESULTS.md), with the pre-edit protocols in
[BRIDGE_PROTOCOL.md](BRIDGE_PROTOCOL.md) and
[ACCEPTANCE_PROTOCOL.md](ACCEPTANCE_PROTOCOL.md). Earlier transport and original
20-workflow HTTP receipts remain valid historical observations and are linked
there. They predate final fixture/archive changes; targeted receipts state the
hashes actually tested.

## Remaining release gates and data limits

Actual credentialed Next/Vercel→Neon SDK execution remains parent-owned. Local
browser shims relay to an old immutable public deployment; they do not establish
real database permissions, Vercel runtime duration/response compression,
production error handling or CI. Verify gzip Content-Encoding/Content-Length,
HEAD/ETag/304, desktop/mobile and representative six-season flows on the exact
preview before release. AWS-origin priority is unchanged and had transport E2E
coverage; it must remain intact on the preview branch.

Preserve source-backed missing data: sampled historical Ligue 1 standings and
its standings snapshot, heatmap, stadium `Q1`, club lookup `Paris/FRA`, coach
`Test`, and the exact honours player are 404. Existing client fallback/partial
behaviour is required. Positive availability for every projection, profile,
asset, archive season and all 230 partitions is not claimed. Results/goals
archive catalogs have 150/62 seasons; four boundary objects plus the affected
2020/21 goals were checked, not every archive payload. Historical cup-edition
selection was checked synthetically; sampled real snapshots/tables are listed
in RESULTS. No new provider traffic is a part of the bridge.

## Reproduction

From the actual repository root, using existing Bun/Python/Node and the existing
Playwright CLI/headless config. Every runner writes time-stamped receipts/logs.
No credentials are printed or persisted.

```sh
bun docs/verification/orion-availability-20261104/fixture_integrity_e2e.mjs
bun docs/verification/orion-availability-20261104/bridge_acceptance_e2e.mjs
bun docs/verification/orion-availability-20261104/archive_goals_e2e.mjs
python3 docs/verification/orion-availability-20261104/run_bridge_build.py
python3 docs/verification/orion-availability-20261104/run_bridge_browser.py
```

The real-data acceptance runner enforces 300 unique reads, 64 MiB response
bytes, concurrency four and 30 seconds per request. It persists no football
row payloads. Do not rerun the RDS pair or restart collectors/builders as part
of this frontend acceptance.

Suggested commit: `fix: bridge the current frontend to saved Neon data`.
Suggested evidence commit: `test: record bridge fixture archive and history acceptance`.
