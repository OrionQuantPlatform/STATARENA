# Neon quota interruption — 3 November 2026

Run [41723613754](https://github.com/OrionQuantPlatform/STATARENA/actions/runs/41723613754) failed at 22:59 UTC (23:59 Paris), before its 100-minute deadline. The last successful SQL poll recorded 100 dirty partitions, oldest 2025/2026. This is a checkpoint; the interrupted transaction and present count cannot be rechecked while Neon refuses connections.

The job log shows `psycopg.errors.AdminShutdown: terminating connection due to administrator command` at 22:59:15 UTC. The later advisory-unlock error is secondary: its connection was already closed. Neon records the compute as suspended at that same time. A subsequent read-only SQL query returns HTTP 402, account/project quota exceeded. Both public data endpoints return HTTP 503, `Neon data unavailable`.

Neon reports plan `free_v3`, 5,964,464,180 transferred bytes and consumption-period end 1 December 2026 UTC. Public network transfer is the probable cause: [the official plan documentation](https://neon.com/docs/introduction/plans#public-network-transfer) gives Free projects 5 GB per month and says an exhausted transfer/compute allowance suspends compute until renewal or an upgrade. The generic SQL error does not identify the exhausted resource, so this diagnosis remains qualified. No paid upgrade or billing modification was performed.

## Setup, inputs and expected result

These checks use real GitHub Actions, production Neon project `sweet-queen-11955006`, branch `br-mute-bonus-be23014e`, read-only role `statarena_runtime`, database `neondb`, and public origin `https://statarena-analytics.vercel.app`. There are no mocks, provider collection calls or production fixture writes.

Expected completion: a successful workflow with `remaining:0`, an empty SQL dirty queue, available public data, then the complete six-season HTTP and default-Europe browser verification. Actual: workflow failure, last known queue 100, SQL denied and both availability checks failed. Full final data/UI verification remains pending. Existing earlier partial passes are preserved separately and do not establish completion.

## Exact reruns

From the repository root, use the already authenticated GitHub CLI:

```sh
gh run view 41723613754 --repo OrionQuantPlatform/STATARENA --json conclusion,createdAt,event,headSha,jobs,name,status,updatedAt,url
gh run view 41723613754 --repo OrionQuantPlatform/STATARENA --log
gh run download 41723613754 --repo OrionQuantPlatform/STATARENA --name rematerialize-41723613754-1 --dir /tmp/statarena-remat-41723613754
python3 docs/verification/rematerialization-completion-20261103/quota-incident/check_availability.py --output /tmp/statarena-availability.json
```

The availability script exits 1 when either public endpoint is unavailable, and always writes its setup, inputs, exact rerun command, expected status, actual status and response body. The saved execution was at 23:09:12 UTC, 4 November 00:09:12 Paris, and returned 503 twice.

For a database recount, call Neon `run_sql` with project/branch/database/role above and:

```sql
SELECT now() AS checked_at, count(*) AS remaining, min(season) AS oldest_season
FROM statarena.dirty_partitions;
```

`incident.json` preserves the exact tool input and denied response, a minimal project/compute snapshot, the last successful queue checkpoint and its limitation. `workflow.json` contains GitHub's terminal run/job state. `failed-job-126222520905.log` is the complete decoded job log; `rematerialize.log` is the downloaded stdout artifact. That artifact contains partition reports but no terminal remaining receipt; it is not a successful completion report. Earlier public historical/stall-check receipts are included for continuity.

## Recovery

Do not dispatch duplicate failing runs while the quota denial persists. Restore Neon availability/quota first; a paid subscription change requires the user's decision. The existing heartbeat checks public health once per wakeup and suppresses repeat quota alerts. Once health returns, recheck the real SQL queue and workflows, then resume on main with `queue_all=false` only if nonempty and no run active/pending. Keep already committed publications and all archived source responses.

After a successful remaining:0 receipt and empty queue, run the full commands in the parent RESULTS.md, save evidence, update the runbook/worklog and commit/push final verification. The monitor is removed only after that verified completion.

Suggested commit: `docs: record Neon quota interruption and public outage`.
