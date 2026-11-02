# Match standings and country-ordered competition selectors

Baseline: local HEAD af77c868, including the previous verified directory, player-average, home-picker and focus-style changes. Preserve these edits, raw JSON, branding and palette. No unit tests. Commit/push was subsequently authorized after verification.

Expected before implementation:

- Match detail has a real Classement tab in the existing accessible tablist. Mouse, keyboard, URL `view=standings` and reload work; other match tabs still work.
- The table uses the match's competition ID and native season, independent of global search/competition/season filters. It reuses the existing competition table, remains full width, shows known teams and links, and can distinguish the match teams visually when identities match. Current provider tables retain existing availability rules; historical matches use their own result data. Cups with no available table show a clear empty state; no invented table.
- Data is loaded on demand when opening Classement. If the requested season was not loaded with the page, the relevant local season/league snapshot supplies the fallback; no second copy of raw data.
- Shared Matches/Players competition dropdowns always show `League · Country`, sorted by French country label A-Z and then league name. All/Top 7 scopes, underlying IDs and persisted selection are unchanged. Duplicate league names are distinguishable.
- Home multi-select, supplemental competition dropdown, historical archive dropdown and competition directory use the same country ordering/names. Home preset/checkbox/apply/cancel behavior remains intact. Country searching still works.
- Desktop and 390px mobile: no document overflow, standings scroll internally, no restored blue focus halo on selectors, selected competition borders remain.

Refinement before Clubs implementation:

- Clubs gains a Competition selector using the same country suffixes/order. Country Germany offers only competitions belonging to Germany; France only French competitions. With all countries selected, all competitions represented in the loaded club sample remain available, including UEFA.
- Club membership tracks every competition in the season, not only the first match. Selecting a league returns each participating club once; its card's match count and competition label reflect that league. International/European participation must not exclude a domestic participant.
- Country changes clear the competition; selecting a new league, changing country, season or search returns to page 1. Reset clears country, league and search. Season changes also explicitly clear all three filters, consistently for cached and uncached data; the existing full-page data load already reset local controls on an uncached season. No-results remains actionable. A season/scope that lacks the selected league must not leave an invisible active filter.
- Verify Germany/Bundesliga and France/Ligue 1 against club ID/count sets computed directly from raw matches, including all pagination pages. Verify a European competition with no country constraint. Desktop and mobile toolbar/pager fit; focus halo removal, profiles and themes remain intact.

Rerun from dashboard:

```sh
PATH=/Users/lemonnierhugo/.bun/bin:$PATH bun run build
PATH=/Users/lemonnierhugo/.bun/bin:$PATH PORT=3016 API_PORT=8776 PITCHAPI_API_KEY= bun scripts/dev.mjs --production
```

Use real current and historical local matches; compare the current match table with the same competition page. Inspect the actual native select options, choose a competition and verify its ID/data. Save URLs, expected/actual observations, console output, logs and screenshots under this folder with RESULTS.md and exact rerun steps.

Integration: synced through e235adbc before publication, preserving the country-grouped catalogue, enriched club profiles and expanded historical archives. Repeat the affected browser cases on the integrated build. Build log: build-integrated.log. The user subsequently authorized focused commits and push after completion.

Final synchronization: preserve the additional upstream changes through eccc4c0d (competition highlights/aligned results, historical goals and stadium details). Resolve the competition-card wrapper conflict with both the new layout and country label. Apply the same country ordering to the newly arrived historical-goals selector. Rebuild and smoke-test competition overview/highlights, its Matchs switch, historical-goals selector, current/historical match detail and Clubs filters. Keep all upstream data/tests intact; do not add unit tests.
