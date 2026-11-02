# Country-by-country GitHub Actions handoff

Workflow: .github/workflows/historical-data.yml, duplicated from daily-data.yml with the same pinned checkout, publication identity, PITCHAPI_API_KEY secret and concurrency group. Manual dispatch starts a historical catch-up. Each country is processed sequentially; every completed country is committed and pushed. Long countries also publish every 15 minutes, and the worker yields after 280 minutes before dispatching its next run. The daily midnight workflow remains in place.

Local worker was interrupted with SIGINT before exporting 65,549 completed request records. Pending work is reconstructed from catalogue country/season indexes and cached responses, so the 338 MB local SQLite queue is not uploaded. Exported JSON checkpoints retain successful existing-archive references and downloaded content-hash paths. All referenced files exist; 23,038 response references had their decompressed SHA-256 verified. Multiple references can share a single physical blob. A zero-minute Brazil run reused the catalogue without HTTP and left the country partial. It did not claim completion.

Rerun: `python3 dashboard/scripts/collect_pitchapi_countries.py --export-local`; `python3 dashboard/scripts/collect_pitchapi_countries.py --minutes 0 --country BRA`. Publication run: `python3 -u dashboard/scripts/collect_pitchapi_countries.py --minutes 280 --publish`.

Snapshot production build passed in a separate sparse worktree: `PATH=/Users/lemonnierhugo/.bun/bin:$PATH bun install --cwd dashboard --frozen-lockfile` followed by `PATH=/Users/lemonnierhugo/.bun/bin:$PATH bun run --cwd dashboard build`. See handoff-build.log. Current scouting UI source was captured as requested, with compilation verified; its full DataScout workflow E2E remains separate ongoing work.

GitHub execution and its first receipt must be read back before claiming that remote collection is running. New raw responses remain separate from the website serving index until a subsequent ingestion step.

Remote readback: run 41480152015 is in progress; checkout and publication setup succeeded, and the country collection step is running. First country publication and timeout continuation are not yet observed; see github-run.json and https://github.com/OrionQuantPlatform/STATARENA/actions/runs/41480152015. The local worker remains stopped.
