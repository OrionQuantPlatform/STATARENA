# Current UI on saved Neon data: pre-implementation protocol

The browser-facing routes and call sites are inventoried in
`frontend-route-inventory.txt`. Acceptance covers every current UI route
family, not merely health or the homepage:

- Manifest and season chunks: `/api/dashboard/manifest`, legacy `/data/*`,
  and the current `loadSeason` interface for six published seasons.
- Match and calendar: `/api/fixtures`, `/api/matches/{id}/summary`,
  `/api/archive/matches/{id}`, `/api/pitchapi/*`, `/api/matchdays`.
- Player, club and scouting: `/api/scouting/routes`, `/api/player-honours`,
  `/api/club-links`, `/api/club-wikidata`, `/api/coach-portrait`, player/team
  compatibility profiles and `/api/assets`.
- Competitions and historical content: `/api/standings`, `/api/open-cups`,
  `/api/openligadb`, `/api/nations-results`, `/api/stadium`,
  `/api/cup-snapshot`, `/api/cup-index`, `/api/cup-table`,
  `/api/supplemental`, `/api/archives/index`, `/api/archives/season`,
  `/api/rankings/associations`, `/api/rankings/club`. `/api/status` and the
  independent Next `/api/visitor-country` route are also used.

Existing legacy paths are handled by the existing Neon reader; adapters may
translate only the newer paths. Unknown paths retain 404. Missing saved data or
query errors must remain observable, never become fabricated success or empty
data. Inputs and saved object paths require bounded validation. A configured
`NEXT_PUBLIC_API_ORIGIN` must continue to win on AWS preview; absence in Vercel
production activates the legacy same-origin backend. Local non-Vercel transport
continues to use its configured local upstream. No layout edits, new provider
requests, raw-data copies, SQL/S3 writes, release or environment changes.

Failure modes requiring E2E coverage include a missing manifest; a JSON-packed
chunk decoded incorrectly or loaded from the wrong competition/season; duplicate
or omitted cursor pages; a changed publication during traversal; a silently
truncated legacy fixture query; absent/unknown data returned as 200; a rejected
malicious path or duplicate parameter; a broken HEAD/validator; a Neon secret
leaked to the browser; accidental partial-AWS use when legacy is selected;
configured AWS origin being ignored; and a legacy fallback masking an actual
error from the newer API. The fixture and scouting mappings must preserve
existing identities, data shapes, provenance and stored dates.

Pre-implementation E2Es must traverse the actual compatibility HTTP endpoint
with a bounded real saved-data sample (one current and one historical Ligue 1
season, one match, and representative player/club/competition, catalog,
ranking, scouting and error cases). A browser run must additionally exercise the
current UI at desktop/mobile: home, match and statistics, player/history, club,
competition, ranking and scouting navigation. Captured statuses, bodies or
content hashes, page exceptions, commands and first failures remain in this
directory. Synthetic fixtures may cover defensive edge cases; a stubbed adapter
or health check alone does not establish parity with production Neon. If any
UI route remains unimplemented or unverified, explicitly record it as a release
gap and keep the bridge local/preview only.

Before changing the competition view, browser E2E must reproduce the current
cup-index failure: the view's `cupIndex` resource shadows its imported function.
Both `worker` and `supplemental` index requests should actually run and return
200 when the saved indexes exist. The authorized fix only renames a binding;
it must not change layout or visual behaviour.
