# STATARENA — home widgets, independent seasons and competition filters

All changes belong to Football_ranking / STATARENA. Sport Prediction is a separate worktree and its original uncommitted files were untouched. The preceding consolidated delivery was f982142904; remote work through 830c82e6c6 was preserved by fast-forward without overlapping application changes.

Final combined run: **10 browser workflows, 131 assertions, all passed**. Production build exited 0. Cleanup retained zero reviewed copies. No production rematerialization was dispatched.

## Behavior checked

The browser workflows exercise real navigation and read-only Neon data: independent seasons across home/calendar/players, reload and history; explicit historical links; missing, corrupt and blocked storage; default Europe versus saved All; loading-shell footer removal; current and archived home layouts; player dialogs; all four ranking shortcuts with the same totals and competition cohort; profile/comparison navigation; country grouping in players, clubs, calendar, home, archives, club analysis and comparisons.

The personal-fixture workflow runs the complete home in a separate browser tab with controlled packed responses at the browser boundary. It checks saved clubs and the latest club of saved players from every saved list, transfers and national-team exclusion, duplicate fixtures, competition scope, seven-day horizon, empty-preference fallback, mobile and the fixture action. Within one Paris day, personal Champions League games precede Europa, Conference and domestic games. No mock responses are written to Neon or the repository data tree. Exact generated fixtures, preferences, appearances and times are included in its JSON report.

The title-race chart now fills its actual container, with six teams. Finishing shows eight players; scorers and assists show ten; Le mur shows three distinct defensive clubs with actual statistics. Screenshots include before/after layouts, wide/mobile and light/dark variants. At 1920px, the weekly match is approximately 681px high (previously 796px); the player spacer is about 29px (previously 120px). Title, defence and scorers retain 17px of bottom padding.

## Setup and exact rerun

Original environment: macOS arm64, Node 26.4.0, Bun 1.4.4, Next 16.4.3, Python 3.14, installed project dependencies, configured read-only dashboard runtime, and cached Chromium 1228. System Google Chrome is absent. The supplied `cli-headless.config.json` points to the cached executable; adjust that path if reproducing on another machine. No credentials are included here.

From `/Users/lemonnierhugo/Desktop/Coding Project/Football_ranking`:

```sh
mkdir -p output/playwright/page-seasons-layout-20261103
cp docs/verification/page-seasons-layout-20261103/e2e/* output/playwright/page-seasons-layout-20261103/
```

Start the application in a separate terminal:

```sh
cd '/Users/lemonnierhugo/Desktop/Coding Project/Football_ranking/dashboard'
bun run dev
```

Open the dedicated browser session:

```sh
cd '/Users/lemonnierhugo/Desktop/Coding Project/Football_ranking/output/playwright/page-seasons-layout-20261103'
/Users/lemonnierhugo/.codex/skills/playwright/scripts/playwright_cli.sh -s=statarena-seasons open 'http://127.0.0.1:3000/?focus=europe' --config cli-headless.config.json
```

Run all workflows from the repository root, or substitute a single case name after `run_cli.py`:

```sh
python3 output/playwright/page-seasons-layout-20261103/run_all.py
python3 output/playwright/page-seasons-layout-20261103/run_cli.py ranking-links
python3 output/playwright/page-seasons-layout-20261103/cleanup-final.py
```

The runner saves timestamped JSON reports and exact Playwright CLI output after each case. `reports/final-e2e.json` selects the final reports and assertion counts; the corresponding raw logs are in `logs/`. Live data can evolve, so record the manifest/season and inspect a changed ranking or count before interpreting a rerun.

Compile production routes:

```sh
cd '/Users/lemonnierhugo/Desktop/Coding Project/Football_ranking/dashboard'
bun run build
```

`reports/build-final.json` and `logs/build-final.log` record a successful final application build. A deployed production page was not verified in this task.

## Failures and corrections retained

Earlier runs and their raw failures are retained. Several harness errors came from reading a control before navigation settled, assuming a selector on a different page, using `textbox` for a native search input, using `[role=dialog]` for a native `<dialog>`, or requesting dynamic import inside the CLI sandbox. The corrected workflows wait for observable state and use the actual native roles.

Manual inspection also found a real layout defect missed by an initial one-sided gap assertion: Le mur’s last row was clipped (negative bottom gap). The stack now respects its content height, and the final checks reject negative gaps as well as excessive blank space. The final defence screenshot shows all three clubs.

An intentional interruption closed the local server and browser during the first combined run. `interrupted-browser-final-e2e.*` records that environment failure; the server/browser were reopened before the complete final rerun. Earlier evidence may report a passed individual case while the interrupted batch exit code is nonzero; that interrupted batch is not a pass.

## Recoverable duplicate cleanup

The reviewed manifest is `e2e/delete-plan.json`. Removed copies: 39 tracked numbered files (13 identical, 26 differing historical variants), the identical unused `prototypes/accueil/option-a.html`, and two unused untracked numbered variants that appeared later. All 42 were archived outside the repository and hash-verified before unlinking. The two apply receipts record archive paths, archive/member hashes and canonical hashes at each deletion checkpoint. Later intended UI changes naturally have different canonical hashes; the cleanup itself did not change them.

The 40 tracked paths remain recoverable from ce21ca42a1eb0945a8a715a54c949a1c8c724a99 using `git show COMMIT:'path' > /tmp/recovered-file`. For complete external archives, use the absolute `archive` path in the apply receipt and inspect/extract to a separate directory. Untracked variants have `archive_only: true` in the manifest. The WAL `data/computed/pitchapi-world/queue 2.sqlite-wal` has no canonical counterpart and is retained. Distinct prototype options B/C remain.

Two invalid, iCloud-only Git ref placeholders (`main 2`) blocked fetch. They were moved on the same filesystem outside `refs/`, preserving their inode, size and flags without hydration. `reports/git-ref-recovery.json` records their locations. Valid refs/history were not removed or rewritten; normal fetch then succeeded.

## Rematerialization status and limits

The source enrichment and `neon_materialize.py` command were already present; this delivery adds the missing manual workflow and [runbook](../../REMATERIALIZE.md). `reports/rematerialize-check-*.json` records real CLI help, refusal to write outside Actions, YAML structure and Bash syntax checks. Dependencies for that local check were installed outside the repository. Exact commands:

```sh
python3 -m pip install --target /tmp/statarena-rematerialize-deps-20261103 boto3==1.43.123
python3 output/playwright/page-seasons-layout-20261103/verify-rematerialize.py
```

`queue: max` with `cancel-in-progress: false` follows [GitHub’s concurrency documentation](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency). No production Actions dispatch, writer-secret validation or complete regeneration was performed. No `remaining: 0` completion is claimed.

Rerun the read-only inspection with `python3 output/playwright/page-seasons-layout-20261103/audit-published.py`. The read-only sample in `reports/rematerialize-published-samples.json` inspected one published Ligue 1 partition in each of six seasons, using the manifest’s content-addressed paths through the local Neon backend. None exposed the new shot endpoint/captain/match metadata columns at the time of inspection. This establishes a need for regeneration in those samples; it is not an exhaustive audit of all competitions. Column presence alone would also not prove that every source value is available.
