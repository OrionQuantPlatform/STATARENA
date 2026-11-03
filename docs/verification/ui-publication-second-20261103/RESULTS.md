# Second UI publication verification — 2026-11-03

Goal: publish five new committed UI changes without pulling raw data into the original Football_ranking checkout.

Setup: isolated sparse worktree `/tmp/statarena-push-ui-second-20261103`, based on remote main `0aad2d51fb95d3b6af940d41987300bdee2f7259`, in an existing partial clone (`blob:none`). Sparse paths: dashboard/frontend, dashboard/shared, dashboard/backend, dashboard/scripts and tests. Raw data excluded; only `data/computed/dashboard/index.json` materialized for compilation. Bun 1.4.4; dependencies installed using the frozen lockfile.

Inputs (local → integrated):

- f75d670a30 → 81611ed: upcoming match pre-match view.
- 154820751e → cc432b3: navbar and saved-list defaults.
- b2ec625a71 → 98efd89: national/super cup scope.
- b9a2418a56 → 966adf3: saved clubs and standings zones.
- 8f2d6c17e2 → 969eaed: provider names and licence credits.

Transferred with `git format-patch -5` and `git am --3way`. All five applied without conflict. Original checkout and untracked files preserved. Existing remote Neon changes retained.

Rerun from repository root:

```sh
cd dashboard
bun install --frozen-lockfile
bun run build > ../docs/verification/ui-publication-second-20261103/build.log 2>&1
cd ..
node --test tests/competition-render.test.mjs tests/competition-standings-notice.test.mjs tests/standings-zones.test.mjs tests/archive_attribution.test.mjs > docs/verification/ui-publication-second-20261103/targeted-tests.log 2>&1
git diff --check 0aad2d51fb95d3b6af940d41987300bdee2f7259 HEAD
```

Expected: production compilation succeeds; existing affected checks pass; patches have no whitespace errors.

Actual: build exit 0, all 15 static pages generated; 7 checks passed, 0 failed; whitespace check exit 0. Logs included alongside this report. No new tests authored here. No browser E2E, complete data validation or live deployment verification performed.

Publication uses a normal `git push origin HEAD:main`, preserving all incoming history; no force push, pull or local reset.
