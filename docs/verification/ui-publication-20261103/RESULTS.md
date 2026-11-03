# UI publication verification — 2026-11-03

Goal: publish the four local UI commits without downloading the raw-data collection into the original working tree.

Setup: isolated sparse worktree `/tmp/statarena-push-ui-20261103` from partial clone with `remote.origin.partialclonefilter=blob:none`; base `579b47107e0cd4fa4f9a12a5a95dd6a1be274ed9`. Sparse paths include frontend, shared code, scripts, backend and tests; raw data excluded. Only `data/computed/dashboard/index.json` materialized for compilation. Dependencies installed with `cd dashboard && bun install --frozen-lockfile` (Bun 1.4.4).

Inputs, in order: local commits `281c6718ea`, `065f778f3e`, `aa68695a1e`, `aa65ae09fe`, transferred with `git format-patch -4` and `git am --3way`. Each applied without conflicts; prior DataScout features and concurrent remote history retained. Original working tree and its untracked copies untouched.

Rerun from repository root:

```sh
cd dashboard
bun install --frozen-lockfile
bun run build > ../docs/verification/ui-publication-20261103/build.log 2>&1
cd ..
node --test tests/competition-render.test.mjs > docs/verification/ui-publication-20261103/competition-render.log 2>&1
git diff --check HEAD~4 HEAD
```

Expected: successful production compilation, existing competition render test passes, no patch whitespace errors.

Actual: production build exit 0; all 15 static pages generated. Existing competition render test exit 0 (1 passed, 0 failed). Patch whitespace check exit 0. Logs saved alongside this report. No new tests written; no browser E2E, live deployment or complete data validation performed. These checks establish compilation and the existing render contract only.

Publication: use a normal `git push origin HEAD:main`; never force-push or overwrite incoming collection commits. The original local main remains on its existing commit and is not pulled/reset by this operation.
