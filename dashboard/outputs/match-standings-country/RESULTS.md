# Match standings and dependent club filters

Verified locally on 2026-11-02 with Bun 1.4.4 / Next.js 16.4.3 and real JSON data. Initial baseline af77c868; GitHub integrated through e235adbc before final verification. Existing neutral/blue themes, green branding, player aggregation and enriched club profiles are preserved. No raw data was changed or scraped.

## Reproduce

From `dashboard`, regenerate the independent expected values and build:

```sh
python3 outputs/match-standings-country/reference_clubs.py
python3 outputs/match-standings-country/reference_standings.py
PATH=/Users/lemonnierhugo/.bun/bin:$PATH bun run build
PATH=/Users/lemonnierhugo/.bun/bin:$PATH PORT=3016 API_PORT=8776 bun scripts/dev.mjs --production
```

The normal backend uses the existing server configuration. Setting an empty environment key does not disable its `.env` fallback. For the separate offline E2E, run the following two commands in separate terminals:

```sh
PATH=/Users/lemonnierhugo/.bun/bin:$PATH bun outputs/match-standings-country/offline-backend.mjs
PATH=/Users/lemonnierhugo/.bun/bin:$PATH NEXT_TELEMETRY_DISABLED=1 ORION_API_ORIGIN=http://127.0.0.1:8777 bun node_modules/next/dist/bin/next start frontend --hostname 127.0.0.1 --port 3017
```

The offline backend reports `configured: false`, refuses external-provider requests, and serves the real local data through the existing handlers. No credentials appear in the evidence. Temporary offline servers were stopped after the run; normal previews remain on 3015 and 3016.

Use browser controls for the steps in PLAN.md and the exact URLs, inputs, expected values and observations in `browser-checks.json`. Tests were performed through the Codex in-app browser. Desktop used the default viewport and 1440×650; mobile used 390×844. Reset viewport overrides after testing.

## Observed outcomes

- Match detail: Classement is the second of seven accessible tabs. Right/left arrows change and focus tabs; `view=standings` survives reload. Current Ligue 1 has the same 18 rows and ten fields as the competition page. The table fills its card; exact known club identities are highlighted. SportScore names without an exact identity match are left unlinked/unhighlighted. Existing source timing and calculation limits remain visible.
- Historical match: open `m_3Sg5Uh` with global season 2026/2027 and `sourceSeason=2024/2025`. The standings use 2024/2025, not the global season. Every field of all 18 rows equals the independent calculation from 306 raw fixtures. The same check passes with the provider disabled, showing Archive PitchAPI. PSG has 84 points, Marseille 65. This is a season table, not a reconstruction as of the match date.
- Upcoming/cup cases: Lorient–Brest opens the same Classement tab and 18-team table. The 2024/2025 Champions League final `m_1higPV` has a clear unavailable-season state and no invented table.
- Competition selectors: Players/Matches, the home multi-select, supplemental and historical selectors show country labels and sort by French country names. All 45 local competition options are distinguishable. The Top 7 + UEFA scope retains its ten IDs, with UEFA shown as Europe. Home country search, single-league apply and reload persistence work; Performances remains the player directory title.
- Integrated competition directory: the upstream grouped catalogue is retained, with 77 cards in country groups sorted A–Z. Europe and International are distinct. Selecting Europe returns exactly the three UEFA competitions. Existing league-pyramid ordering within each country is preserved.
- Clubs: Germany offers only Bundesliga, 2. Bundesliga and 3. Liga after the full progressive dataset loads. All 56 German clubs appear exactly once across four short-desktop pages. Selecting Bundesliga gives the exact 18 raw-reference IDs and league-only match counts. A country change to France clears Bundesliga and offers only Ligue 1/2. Ligue 1 yields the correct 18 IDs/counts; adding Paris returns PSG and Paris FC.
- League memberships: selecting Champions League without a country restriction visits all 36 participating clubs once across three pages, each with three collected competition matches. A club's domestic and European memberships both remain usable. Its card count follows the selected competition.
- Reset/season: empty search has a visible empty state; reset clears country, league and search. League changes return to page 1. Season changes explicitly clear the three local filters and paging, consistently with the existing cold-season page reload. A 2024/2025 → 2026/2027 transition was exercised on the final build.
- Mobile/themes: all four Clubs controls fit at 390px with no document overflow. The pager bottom is 808.59px within an 844px viewport. All 18 Bundesliga IDs are visited once across five mobile pages. Match tables scroll internally at 760px inside a 332px region. Both themes remain readable; filter outlines/shadows stay removed. Viewport reset and dark theme restored for the final preview.
- Upstream profile smoke: PSG still has Le club en bref, UEFA ranking, grouped roster and club matches. This confirms integration, not independent validation of every external club fact.

## Failures and corrections retained

`browser-checks.json` contains 46 observations, including four initial failures and their resolving checks:

| Initial observation | Resolution |
| --- | --- |
| Shared competition table sampled before asynchronous load completed | Waited for the visible table; all rows matched the match table. |
| Germany initially offered only Bundesliga | The page first renders the Top 7 dataset, then adds other leagues. Waiting for the full scope produced exactly the three German leagues and 56 clubs. |
| Season-transition check expected Germany to persist | Existing cold-season loading remounts local controls. The contract is now explicit: season changes clear country, league and search for cached and uncached data. Final reset check passes. |
| Compétitions failed after upstream integration: missing useMemo import | Restored the import needed by the upstream country-reference lookup. Rebuilt and verified grouped directory, Europe filter, match table, Players and Clubs. |

The original integration console error is saved in `console-before-correction.json`; the fresh final browser session has no error/warning in `console-final.json`. Harness-only issues included a search input's role (`searchbox`), unavailable `parseInt` in read-only page scope, and a helper retaining a closed tab. Correct locators, host-side parsing and a fresh helper resolved these without product changes. One early final-match observation used stale tab URL metadata; the following DOM URL read confirmed the actual match URL, and later observations read `document.URL` directly.

Production builds are logged in `build.log`, `build-clubs.log`, `build-integrated.log`, `build-final.log` and `build-verified.log`. These checks cover the requested workflows; they do not claim every external provider endpoint or all historical seasons were retested. No unit tests were added.

Feature commits: `bc93403d` — `ui: sort competition selectors by country`; `1445be50` — `feat: add standings to match details`; `d4352508` — `feat: filter clubs by country and competition`. This evidence accompanies `docs: record match standings and club filter verification`. All commit bodies contain clear bullet-point descriptions.
