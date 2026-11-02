# Four-page filter and layout verification

Setup: actual STATARENA checkout at 441b4e6e, installed Bun/Next, real JSON database. Keep palette/fonts/logo files unchanged. Use the local production server with an empty PitchAPI key; existing SportScore standings may be fetched through the server route. Do not write isolated unit tests after implementation.

Expected workflows and failure modes, documented before implementation:

1. Clubs: country options come from the available season clubs; national-league country membership takes precedence over UEFA labels. Reviewed ranking links can supply countries for clubs without domestic records. Unknown remains selectable, never assigned to Europe as a country. Search and country intersect; clear/reset and no-results work. A long list has Previous/Next with distinct pages, no lost clubs, proper first/last disabled buttons. Search, country, season and viewport capacity reset/clamp pagination. At desktop and mobile sizes, reserve room for paging and show whole rows fitting the viewport where the controls plus at least one row can fit. A short list has no pager. Club links and return navigation still work.
2. Players (updated before aggregate implementation): one row per stable player ID, including transfers across clubs/competitions. Average only known values; retain missing values and per-stat observation counts. Notes are arithmetic means; per-90 uses totals divided by the minutes of the observed metric. Numeric minutes/rating/stat conditions run after aggregation, never remove a player's weak individual matches to inflate their average. Date/competition/venue/result/starter criteria define the sample first. Position uses the dominant playing-time position. Verify a real repeated player has one row and its means match raw JSON, including partial xA observations. Compare rating and goal filters with independently computed all-match means, CSV and the opened season profile. Keep individual match details and performance comparison accessible on the profile. Test player comparison and both display modes. Refresh preserves position/numeric thresholds, other advanced filters and reset/empty states. No position filter includes unknown positions; include-bench retains players with no played matches without inventing averages.
3. Home: one competition control replaces the dropdown plus separate personalization strip. Open from keyboard; search by league/country, choose custom competitions, apply, cancel and reset to all. Top 7 + UEFA is available in the same picker. Current selection is clear on the trigger. All homepage sections follow the same scope; an old `league` deep link is reflected and is cleared when applying a new custom/all selection. Saved selection survives refresh; choosing leagues outside a previous Europe focus expands the source scope appropriately. Modal closes with Escape and restores focus. No onboarding popup is forced.
4. Competitions: standings card/table spans the content width on a large viewport. The exact removed sentence and duplicate SportScore header link are absent. Existing accurate columns, groups, club links, season and match tabs remain; global attribution persists. On mobile, horizontal scrolling stays inside the table and the team identity remains readable. No invented statistics or source/season merging.
5. Responsive/theme: test 1440x900 and 390x844, with a shorter viewport for the club paginator; no document overflow. Verify both themes and keyboard-visible focus with existing tokens. Check browser console errors and retain screenshots/DOM measurements.

Final comparison review: selecting a player, searching for another and selecting that player must retain both averages. Existing match-performance comparison selections must remain available on the player profile without overlapping the directory's player-comparison tray. Verify that navigation switches the visible comparison context without deleting the existing match selection.

Latest user correction, before styling changes: focusing a filter search, select, numeric input or competition trigger must not add a blue border, outline or halo. Selected competition cards retain their blue selection border. Verify pointer focus and keyboard navigation; a neutral background can indicate keyboard focus without a border.

Exact local commands, from dashboard:

```sh
PATH=/Users/lemonnierhugo/.bun/bin:$PATH bun run build
PATH=/Users/lemonnierhugo/.bun/bin:$PATH PORT=3016 API_PORT=8776 PITCHAPI_API_KEY= bun scripts/dev.mjs --production
```

Data generation, from the repository root:

```sh
python3 dashboard/scripts/build_dashboard_views.py
```

Record actual checks and any corrections in RESULTS.md with screenshot/JSON/build logs. Verification remains local unless publication is requested.
