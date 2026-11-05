# Porting the site pages to the AWS API — findings (5 Nov 2026)

No production change. The Vercel site still serves the legacy Neon bridge.

## What the frontend does on the AWS API

`FootballContext` renders only `/matchs` in Pro mode; every other view shows
"Données indisponibles pour cette vue" and `loadScope()` returns an empty season.
The pages (overview, competitions, clubs, players, Ballon d'Or ranking, archives,
match tabs) are built on a full season dataset (matches + appearances + team
stats per league-season), which the AWS side exposes through one reader,
`/api/seasons/partition` (`orion-pro-appearances.js`, versioned by `v=pro1…`).

## Why that reader fails on the real data

Measured against RDS with the actual router (runtime role, read-only):

1. **Revision anchors.** Admission (generation 8) re-revised `match_players`
   (played) and `match_teams` (labels) without re-anchoring the facts, which the
   native validator allows (it checks the logical parent). The reader joins stats →
   participant → side on exact revision ids, so it selects 0 of 12,200 performances.
   Other readers use the same pattern (competitions, archives, entities, match
   statistics, match details, spatial).
2. **Performance coverage.** The reader requires one `normalized_performance`
   coverage row per match; the frozen normalizer only recorded shots coverage
   (387 played matches). `orion_pro_coverage_recovery.py` records it from the
   source (plan verified: 387 rows, 15,437 performances equal to SQL); its RDS
   write was not run (blocked by the auto-mode check; needs approval).
3. **Cost per request.** The reader re-validates every native value of the season
   on each request: 35.6 s for Ligue 1 2025/26 (378,200 metric values, sort on disk
   at `work_mem` 4 MB on the t4g.micro), above the 8 s statement limit (57014).
   With logical joins, once-per-query alias resolution and native checks moved to
   the page: admission 4.2–4.6 s + page 5.0–5.1 s ≈ 10 s per 100-match page, one
   page over the 2 MiB response cap. A league-season needs 4 pages (≈ 40 s); the
   overview loads many league-seasons. Moving the native check to the page also
   breaks the reader's whole-season refusal invariant (regression A09 fails).
   The experiment is kept as `appearances-reader-experiment.diff`; the reader on
   `main` is unchanged.

## Consequence

Patching per-request readers cannot give usable page times at real volume on this
instance. The pages need read models computed once at publication (per edition:
season appearances, team/player season aggregates, standings), so a page request
is a small indexed read. The approved 103 model has candidate aggregate tables
(`player_competition_stats`, `team_competition_stats`, `analytics.metric_totals`,
`competition_summary`), but their exact contents, the publisher steps that fill
them and any missing read model are a schema/model decision for the user.
