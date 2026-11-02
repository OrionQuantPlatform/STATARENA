# Publication verification — 2026-11-02

The five dashboard commits were merged with origin/main at adf2ec06 in an isolated worktree. Git merged all overlapping frontend changes without conflicts. Existing browser evidence covers 42 observations; no new browser run was claimed for this merge.

The integrated production build passed with Bun 1.4.4 and Next.js 16.4.3. Rerun from the repository root:

```sh
PATH=/Users/lemonnierhugo/.bun/bin:$PATH bun install --cwd dashboard --frozen-lockfile
PATH=/Users/lemonnierhugo/.bun/bin:$PATH bun run --cwd dashboard build
```

Expected: successful compilation and generation of every application route. Actual: command exited 0; see publication-build.log. An initial sparse-checkout attempt lacked data/computed/dashboard/index.json; restoring that exact indexed file resolved the setup failure without source changes.

The original checkout and its ongoing match-standings/country-selector modifications were left in place. Unrelated local duplicate files were excluded from the published commits.
