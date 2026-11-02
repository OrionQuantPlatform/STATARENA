# Worldwide collection startup E2E

Run from repository root: `python3 -u dashboard/scripts/collect_pitchapi_world.py`.

Setup: current local JSON archives and configured server-side PitchAPI key. Source contract checked against https://pitchapi.dev/. No key is logged. Worker output is worker.log; current process is in process.json; durable progress is data/computed/pitchapi-world/progress.json.

Expected: live catalogue schedules jobs for every league-season; endpoint keys are unique; new gzip response hashes validate; existing successful match observations are reused without network requests or response copies; interrupt/restart preserves completed tasks; another process refuses the lock. Actual: all these startup checks passed, with counts and reference evidence in e2e.json, storage-check.json and resume-before.json. Interrupt used SIGINT on the first worker; the process was relaunched with the identical command. An actual canonical match response was reused with zero requests, and a downloaded response hash was recomputed successfully.

Storage guard: stop with paused_storage below 3 GiB free; rerun the same command after freeing storage. Failed or blocked requests remain explicit in the queue; complete is never reported when they exist. Queue is internal SQLite coordination state; business responses remain compressed JSON. Existing serving tables were not rebuilt or replaced. This run verifies startup, persistence, storage and resumption, not completion of the whole crawl or every individual endpoint. New data is not yet automatically visible on the website.

Suggested commit: feat: add resumable worldwide PitchAPI collection.
