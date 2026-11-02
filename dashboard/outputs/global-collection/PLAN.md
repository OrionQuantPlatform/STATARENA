# Worldwide PitchAPI collection

Scope: every league and season advertised by /leagues, fixtures of every status, match endpoints, individual player match/halves/shots/advanced routes, individual shots, and league/team/player profiles. Follow discovered identities. Use both documented heatmap frames. Date listings duplicate league fixtures and are not separately stored.

Expected: stable endpoint+sorted-parameters task identity prevents duplicate jobs; successful canonical archive responses are referenced in place; new response bodies use content-addressed gzip storage. A durable local SQLite queue is an internal worker index, not a replacement for the JSON dataset. Interrupted tasks resume. A second worker must refuse the lock. 404 records unavailable data; 401 stops; 403 is recorded as blocked; transient failures respect Retry-After and are reported, never claimed complete. Existing raw and serving indexes must remain untouched during collection.

E2E: start with real catalogue and archives; inspect durable queue and JSON progress, validate a stored response hash, then stop/restart and verify completed task identities and blob counts are preserved. No unit tests are added. Save results and exact commands in RESULTS.md. Full completion is not established by worker startup.

Run: python3 -u dashboard/scripts/collect_pitchapi_world.py
Progress: data/computed/pitchapi-world/progress.json
New JSON bodies: data/raw/pitchapi-world/blobs/<sha256>.json.gz

## GitHub Actions handoff

Duplicate the daily-data workflow using its existing PITCHAPI_API_KEY secret and pinned checkout. Export completed local request records to deterministic compressed JSON checkpoints; exclude SQLite, lock files, and local pending jobs. Reconstruct work per catalogue country, reuse completed responses globally, and commit/push when a country finishes. Checkpoint within long countries before the runner deadline and continue via workflow_dispatch. One shared concurrency group prevents simultaneous daily-data pushes.

Expected E2E: exported successful task count matches local completed count; every checkpoint reference resolves; a cached country index and match response require no HTTP call; second replay adds no files; a short time budget checkpoints without marking a country complete; no credentials in git; GitHub accepts the workflow, starts it and shows country progress. Preserve failures accurately in the receipt. Existing UI changes are separate commits and require a production build.
