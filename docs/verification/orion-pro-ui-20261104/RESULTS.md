# Local React Pro browser acceptance

Suggested commit: `test: verify paginated Pro React workflows in a real browser`.

Suggested commit for the source-export correction: `test: isolate Pro UI E2E source exports from local copies`.

**Current clean-export acceptance:15/15 executed cases pass**,0 fail,0 unverified, in `runs/20261104T214821149806Z-react-clean-tracked-export-final/result.json`. SHA256: `ca038f755bb5d96d3ad76021144be8414c916a72800ed5808608a3d5ce832a9a`.

The new setup exports396 named inputs, including392 runtime sources, from read-only `git ls-files -z`, the three explicitly authorized new Pro modules, fixed harness/helper/model inputs and four explicit SDK dependency files. The isolated Python fixture/helpers, Bun backend and Next frontend all use this export. It includes complete tracked assets/fonts and excludes every unrelated untracked product file and dotenv. The source-export manifest SHA256 is `69b9f81f916cc81a4d6c3e27542d978e4a1b4eb8ede7e9ab60fd43ac86a47298`. It proves the real browser flow works without the unrelated local copies; it does not claim a fresh dependency installation or a separately executed clean-clone CI.

The earlier behavior-green receipt `runs/20261104T212916400593Z-react-final-geometry-and-cache/result.json` remains historical: its recursive export included seven unrelated untracked local `… 2.js` files, as did the other five earlier runs. All six receipt SHA256 values are unchanged. None of the42 historical input copies or seven originals was deleted or modified by this harness owner. The parent owns their separate public/private omission manifest. The new clean-export acceptance supersedes that export claim without rewriting the old evidence.

The actual Next frontend reads the real Bun Pro API and owned PG18.6 publication through its existing proxy. The fixture publishes61 A matches plus independent B/C editions. No football response, page or application module is mocked. The only simulated responses are the two inert telemetry scripts explicitly documented and authorized in PROTOCOL.md. The original application RED, mobile geometry RED, preparation failure and harness-oracle failure remain unchanged in their separate runs; RED_NOTES.md explains each one.

| Observable outcome | Actual result |
|---|---|
| Product pagination |30/30/1 visible rows,61 unique IDs, exactly3 uncached fixture GETs with limit30, returned cursors and correct v; returning to visited pages adds0 fixture GET |
| Lightweight A overview |1 summary GET,0 shots GET, no heavy-table query before opening the tab |
| Explicit Tirs tab |1 shots GET; raw xG0/xGOT0/is_goal=true/event_type="" and52.5m/34m preserved; actual SVG point cx330/cy219/r6 with goal label; tab return adds0 GET |
| Null selected B club profile |API name stays null; row/scoreboard show `Équipe non renseignée`; no page exception |
| Mobile390×844 |List/pager and shots operate without horizontal page overflow. Selected Tirs rectangle[293.0625,367.96875] lies inside tablist clip[14,376]; scrollLeft188; document scroll remains(0,0) |
| New publication |Latest A has corrected score/profile and xG0.67; its token and ETag differ from old A |
| Old A and independent C |Same JS document across16 recorded phases. Old A retains its score/name/xG0 with total1 summary/1 shots GET; C token/summary unchanged with total1 summary/0 shots GET |
| Network/SQL |22 browser API GETs;24 traced backend requests all200;43 traced API SQL queries;0 unexpected failures/current-view reads/provider/file fallthrough |
| Explicit isolation accounting |2 SDK attempts neutralized by exact-URL telemetry shims;0 effective external HTTP transactions;3 strict RSC navigation cancellations retained with URL/error/main-frame navigation/completed phase |
| Cleanup |Owned PG/API/Next/browser stopped; both HTTP ports closed; owned database and frontend-copy directories removed; source hashes unchanged during execution |

Exact rerun from the repository root:

```sh
python3 tests/orion_pro_ui_local.py --label react-clean-tracked-export-final
```

The independently bounded geometry command is:

```sh
python3 tests/orion_pro_ui_local.py --label mobile-selected-tab-red --mobile-tab-only
```

This command now tests the corrected current frontend; the pre-correction RED is preserved at `runs/20261104T212611163860Z-mobile-selected-tab-red`. Replaying historical code requires its saved inputs rather than the corrected current frontend.

Evidence: final `result.json`, `source-export-manifest.json`, `browser-commands.json`, `browser-final.json`,16 phase JSON files, exact source/model/SQL/SDK inputs and hashes, all ordered network responses/bodies, SQL traces, Next/Bun/PG logs, desktop/mobile screenshots, settled DOM snapshots and browser trace. `CLEAN_EXPORT_CHECKSUMS.json` pins the current receipt/export/harness and confirms the six historical receipt hashes remain unchanged. `CHECKSUMS.json` remains the earlier historical index. The current receipt contains all396 source input hashes.

Tools observed: Python3.14.6, PG18.6, Node26.4.0, Bun1.4.4, Playwright CLI0.1.23 and cached Chrome for Testing149.0.7827.55. The exact declared flag-icons7.6.0 package came from the existing local Bun cache only in the temporary copy; shared dependencies were not changed.

This is a synthetic local responsive-browser acceptance. The fixture itself constructs ready builds/publications; real source normalization, production publisher/data availability, AWS/Neon transfer, Vercel/CDN behavior, physical phones and other site features are not certified. No cloud action, shared schema/data mutation, commit or deploy was performed by this harness owner.
