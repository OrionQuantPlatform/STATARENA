# Historical refusal handling — verification

## Setup and exact rerun

Python 3 and Git; no provider credential or internet access is needed for this E2E. Run from the repository root:

```sh
python3 docs/verification/history-refusals-20261103/e2e.py > docs/verification/history-refusals-20261103/after.log 2>&1
```

The harness starts a local HTTP provider, invokes the real CLIs in fresh processes, and uses real SQLite databases, gzip response files/checkpoints, Git commits, sparse checkout and a temporary bare remote. `e2e.py` contains the exact catalogue and response fixtures. Fixture credentials are never printed. Temporary repositories are removed after completion; receipts, HTTP endpoint calls and captured process logs remain beside this report.

## Expected and actual results

- Before the fix, traversal returned `continue=true` after ARG's refusals; the regression assertion failed as expected (`before.log`, baseline ff8ca44e).
- After the fix, all four E2E scenario groups passed, with 23 local HTTP requests (`e2e-result.json`, `after.log`).
- Refusals: ARG becomes `complete_with_errors` with two explicit failed endpoint records; BRA is still downloaded and becomes `complete`. The receipt and response files were committed and pushed to the local bare remote (`traverse.log`).
- Restart: terminal countries were skipped without any new provider requests (`restart.log`).
- Explicit retry: sparse-checkout workflow recovered one fixture profile, retained one 403, published an independent response archive and left checkpoint buckets byte-identical. Partial-country resumption consumed the recovered response without another call to that profile (`retry.log`, `resume-recovery.log`).
- Deadline: a zero-minute country remained `partial` with `continue=true`; its subsequent run completed traversal and reached BRA (`deadline.log`, `deadline-resume.log`).
- Authentication: HTTP 401 produced a nonzero process exit, saved a partial receipt and stopped before BRA (`authentication.log`).
- Two intermediate harness defects (reading a gzip Git blob as UTF-8, and accidentally tracking the fixture SQLite database) were corrected; their original failure logs are retained. These were fixture failures, not successful application checks.

## Behavior and limits

`complete_with_errors` means the country's discovered request queue was exhausted with recorded gaps. It is terminal for normal continuation, not a claim of full data coverage. Deadlines/storage interruptions remain resumable; authentication and publication errors remain fatal.

The independent manual retry uses the existing API client, credentials, domain and user-agent. It attempts up to ten archived HTTP 403 keys and publishes sanitized response records under `data/raw/pitchapi-world/refusal-retries/`. Successful retry responses can be reused by subsequent country traversal. The active historical runner is not cancelled or modified in memory; its automatic successor checks out the new collector from main.

Live retry executed successfully at 10:29 Paris on November 3: [run 41603644923](https://github.com/OrionQuantPlatform/STATARENA/actions/runs/41603644923). All ten profiles were actually requested through the unchanged normal client; zero recovered, ten HTTP 403 / PLAN_UPGRADE_REQUIRED responses. The current API still returns the message that contradicts its public free-plan documentation. Job success establishes completion of the attempt, not successful profile recovery. Sanitized full response records were published in commit 4aeed40d6e6366d035e527326f7043613873a658 under data/raw/pitchapi-world/refusal-retries/41603644923-1793694575680361443.json.gz, then independently downloaded and checked to contain ten distinct refused profiles. See live-retry.log and live-retry-summary.json. The historical runner remains active on its original code until its automatic successor starts; live country-to-country traversal with the new code has not yet occurred.

Suggested commit: `fix: continue historical collection past refused resources`.

## Retry with the user-supplied test key

On November 3 at 10:37 Paris, [run 41604581667](https://github.com/OrionQuantPlatform/STATARENA/actions/runs/41604581667) retried the same ten distinct profiles with the newly supplied test key. Actual result: ten HTTP 403 / PLAN_UPGRADE_REQUIRED responses, zero profiles recovered. The raw published archive was independently downloaded and verified; see supplied-key-retry.json for per-profile results and the archive pointer. The credential was transported as a temporary encrypted repository secret, not committed or printed. The primary collection secret was unchanged. After completion, the temporary secret and temporary remote workflow branch were deleted. No further retry is pending.

To reproduce with another authorized key: use the same workflow on a temporary branch referencing a dedicated GitHub secret, set that secret via stdin, dispatch, inspect the archive, then delete the temporary secret and remote branch. Never pass credentials as workflow inputs or tracked file contents. Suggested commit: docs: record supplied-key profile retry.
