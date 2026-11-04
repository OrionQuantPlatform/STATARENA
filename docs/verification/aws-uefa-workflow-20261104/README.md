The UEFA historical standings verify job failed on Linux at source revision 8b6dd3e387c670a384c8979d5fe6550527af694f. Its React render harness rejected the competition component's new catalog-client import before rendering the page. The mocked supplemental cup index also supplied a discarded storage path instead of the season field used by the AWS API. The component, backend, workflow and its original assertions were unchanged. [GitHub run 41761220465](https://github.com/OrionQuantPlatform/STATARENA/actions/runs/41761220465)

With dashboard dependencies installed from bun.lock, run these from repository root:

```sh
node --test tests/uefa-standings.test.mjs tests/standings-clubs.test.mjs tests/competition-render.test.mjs
node dashboard/scripts/neon_refresh_uefa_standings.mjs --check-source
```

Linux reported 10 passes and one unexpected import. A local Node 26 replay reproduced the same 10/1 result. With the render harness loading the real catalog client and using explicit season metadata, all 11 passed. The subsequent read-only UEFA source check returned eight groups and 32 teams for 2023/2024, then one group and 36 teams for 2025/2026. The separate production refresh job was skipped by the original run. Verification of the fix on a new GitHub runner requires publication of the changed test.

Inspect linux-failed.log, local-before.log, local-after.log and source-check.log for the full outputs. Suggested commit `test: align UEFA competition rendering fixtures with the AWS catalog`.
