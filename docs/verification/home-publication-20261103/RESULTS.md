# Homepage publication — 2026-11-03

Setup: isolated sparse blob:none clone `/tmp/statarena-push-home-20261103`, base `66f6ca81119d3a31dbfc8f81a8690a14608160cf`. No raw-data checkout or original checkout reset/pull. Bun 1.4.4, frozen lockfile dependencies.

Input: local commit 1a745e8b06, replayed with git format-patch/git am --3way without conflict. Preserves the remote club-profile link correction.

Rerun from repository root:

```sh
cd dashboard
bun install --frozen-lockfile
bun run build > ../docs/verification/home-publication-20261103/build.log 2>&1
cd ..
node --test tests/home-insights.test.mjs tests/overview-featured-render.test.mjs > docs/verification/home-publication-20261103/tests.log 2>&1
git diff --check 66f6ca81119d3a31dbfc8f81a8690a14608160cf HEAD
```

Expected: successful production build, targeted checks pass, no whitespace errors.
Actual: build exit 0; targeted checks 14 passed, 0 failed; whitespace check exit 0. Logs alongside this report. No new tests, browser E2E, live deployment or full data validation performed.

Publication: normal fast-forward git push origin HEAD:main. Original local commit and unrelated files preserved.
