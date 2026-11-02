# Local verification

Setup: repository base 441b4e6e, Bun 1.4.4 / Next.js 16.4.3, real JSON database. Production build served on `127.0.0.1:3016`, backend `8776`, provider key empty. No raw data was changed. Reference calculations read canonical raw tables directly, without importing application aggregation code.

## Rerun

From the repository root:

```sh
python3 dashboard/scripts/build_dashboard_views.py
python3 dashboard/outputs/navigation-filters/reference_means.py
```

From `dashboard`:

```sh
PATH=/Users/lemonnierhugo/.bun/bin:$PATH bun run build
PATH=/Users/lemonnierhugo/.bun/bin:$PATH PORT=3016 API_PORT=8776 PITCHAPI_API_KEY= bun scripts/dev.mjs --production
```

Repeat the browser cases in PLAN.md at 1440×900, 1440×600 and 390×844. Use native controls; browser verification was run through the Codex in-app browser. JSON observations, exact URLs and screenshots accompany this report in this directory.

## Verified outcomes

- Players: LaLiga directory contains 488 distinct played players. Raphinha appears once: 10 matches, 72.3 average minutes, 8.612 mean rating, 1.5 goals, 1.087 xG and .166 xA. Rating ≥8 returns exactly four independently identified players; ≥9 returns none. Goals ≥.5 returns exactly the 18 raw-reference players. Raphinha is excluded at mean goals ≥2, even though individual games could pass that condition. Per90 goals are 1.8672, xG 1.3531; rating stays 8.612. Refresh retains the basis and thresholds.
- Grouping across competitions: Raphinha's domestic and European performances produce one row with 12 matches and mean rating 8.5258333. Opening his profile under the mean rating ≥8 retains the complete 10-match LaLiga sample and 723 minutes. Numeric filters do not discard his lower-rated matches before averaging.
- Position, comparison and CSV: dominant-position filtering returns the expected keeper; clearing returns all four qualifying players. The player comparison shows the two correct averages. The downloaded CSV contains the same four unique IDs and full-precision means, plus observation counts. Pass-accuracy aggregate is independently 84.232365%; 85 excludes and 84 includes Raphinha. See `csv-check.json`, `players-rating-8.csv`, `reference-means.json`, `reference-extra.json` and `browser-checks.json`.
- Clubs: all 192 current Europe clubs were visited across every desktop page, with 192 unique IDs and no omissions. France filters to 18, Paris to two, no-results and reset work. Unknown countries remain selectable. At 1440×900 capacity is 28 clubs, at 1440×600 it is 12, and at 390×844 it is six. Mobile pager bottom is 816.59px inside an 844px viewport. Final page has the same document pager position (820.20px) as the first page.
- Home: one competition trigger replaces the native dropdown and separate personalization strip. Escape restores trigger focus; cancel preserves selection. Ligue 1 + Ligue 2 selection clears the legacy single-league URL, expands the Europe source restriction, filters upcoming cards correctly and survives refresh. All and Top 7 + UEFA presets apply through the same picker. Mobile dialog is 358×796, inside 390×844, with internal scrolling.
- Competitions: desktop card is 1392px in a 1440px viewport with 24px gutters; table is 1358px with all ten accurate columns and 18 teams. Redundant status/provider header row is removed; global attribution remains. Match tab still opens results. On mobile the 760px table scrolls inside 332px, team identity is sticky, document width stays 390px and keyboard horizontal scrolling works.
- Themes and data: original Inter, neutral/blue theme and green assets remain unchanged. Mobile light background is `rgb(246,248,251)`; dark is retained in final previews. The country index has 761 stable IDs, is regenerated idempotently and reuses all 127 existing data chunks. No new scraping, statistics or raw-data duplication.
- Final comparison workflow: selecting Raphinha, searching for Lamine Yamal and selecting him retains both complete samples (10/11 matches; 8.61/8.60 ratings). Player and match-performance trays never overlap; the prior match selection remains available on the profile. Both workflows were verified through navigation.
- Latest style correction: pointer/keyboard focus on search, competition select and numeric inputs has `outline: none`, `box-shadow: none` and neutral borders. The home selector remains neutral when opened; selected competition cards retain `rgb(59,142,255)` borders with no extra focus outline. Neutral backgrounds indicate keyboard focus. See `players-no-focus-ring.jpg`, `home-picker-no-focus-ring.jpg` and the final two browser checks.

## Corrections and limits

The first club reset test restored an old page when returning to an earlier filter combination. Pagination state now synchronizes with its scope; final desktop/mobile reset checks pass. First and last page heights are reserved consistently. An initial stability check used viewport coordinates even though browser automation scrolls clicked controls into view; final comparison uses document coordinates and preserves the original observation.

Automation notes: a previous-turn tab handle was stale, a segmented control had no group role, and the read-only browser evaluator does not expose localStorage. These were corrected by a fresh test tab, a visible-button locator and reload-based persistence checks. The match-comparison clear control uses the accessible name "Vider la comparaison"; the locator was corrected. No application error was inferred from those harness issues. JSON retains original failed/corrected observations and their resolving checks.

Build logs `build.log`, `build-final.log`, `build-verified.log` and `build-focus.log` capture successful production compilations (terminal carriage returns/trailing spaces normalized). Final `browser-checks.json` contains 42 observations, resolved prior failures, no unresolved failure and no console errors. This is focused local E2E verification of the requested workflows, not a claim that every archive/provider endpoint was retested. No unit tests, commit or push were performed for this iteration.
