# DataScout enrichment results

Base: origin/main 72e2da99 (includes the in-progress snapshot 79b94ffd, the concurrent cup competitions, the unified Archives page and the removal of provider profile entries; the club workspace follows the same rules). Coverage by audit function: docs/DATASCOUT_IMPLEMENTATION.md.

## Setup

`cd dashboard && bun install && bun run dev` (port 3000), real local data from data/computed and data/raw, no provider key. Browser checks with Chromium/Playwright.

## Checks

| Check | Expected | Actual |
|---|---|---|
| Production build | `next build` succeeds | Passed |
| Node tests | No new failure | 166 pass, 3 fail. The 3 failures predate this work and test files it does not touch (competition-directory ordering ×2, overview-featured fixture without `filters`). The one failure introduced during the work (navbar search using `useRouter` outside an app router) was fixed by switching results to real links. |
| Python tests | Pass | 42 pass |
| Browser E2E, 1440 px dark and 390 px light | Every tab of player, players, clubs, club profile, matches and match detail renders; no console error; no document overflow | 32/32 states clean in both runs (e2e-1440-dark.json, e2e-390-light.json) |
| Navbar search | Typed text never lost; results for names, multi-word queries and initials | "mbappe" → Kylian/Ethan Mbappé; "psg" → Paris Saint-Germain; "real madrid" → club then players; Enter opens the highlighted result |
| Search narrowing | Narrowing by one letter equals a fresh search | 16 queries, every prefix, 0 mismatches; max 19 ms per keystroke over 19,054 players, 734 clubs, 45 competitions |
| List filter typing (Joueurs, Matchs) | Fast typing and fast deletion keep every character; chip removal clears the field | "kylian mbappe" typed with no delay kept intact, URL follows after the pause; chip removal → empty field and no `q` |
| Club record | Matches the data | PSG all competitions: 12 matches, 9-2-1, 35–15; goal-time buckets sum to 50 = 35 + 15 |
| Pre-match causality | Only matches before kickoff | Juventus before Juventus–Napoli (1 Nov 2026): 12 matches, 6-3-3, 20–13, identical to an independent recount of raw matches and fixtures; latest match used 28 Oct |
| Saved clubs and matches | Saved entries appear in their lists | PSG listed in Clubs › Mes clubs, Juventus–Napoli in Matchs › Mes matchs |

## Corrections found during verification

- Event labels showed raw source codes (`goal`, `yellowcard`): the source uses lower-case types.
- Season averages of possession were drawn as a shared split bar in the pre-match markers.
- Second yellow listed after the red card it caused at the same minute.
- Initials search lost "psg" when narrowing from "ps".
- Club comparison highlighted volumes (clearances, saves) as "better": only outcome metrics are highlighted now.

## Screenshots

screenshots/ — home with navbar search, search results, club overview, style profile, comparison, match pre-match context, event timeline, mobile light grid.
