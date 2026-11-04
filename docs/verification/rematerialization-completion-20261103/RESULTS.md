# Rematerialization correction and production verification

The initial run 41711363014 was cancelled after public data verification found that archived partitions were cleared from the dirty queue without receiving enrichment. Their fixtures exist, but standalone `/matches/{id}` resources do not: successful original responses are in observation shards. The materializer required a newer standalone match resource and skipped those archived matches.

The corrected materializer loads standalone and archived indexes for each partition, prefers successful recent resources, and falls back to stored archive summaries/players/shots/lineups/stats. A fixture can be normalized without a collected match summary when its actual player/shot/stat responses exist. Missing families retain previous normalized data and player references. Each archive file is read once per partition, retaining only responses needed for that partition; no provider call is introduced.

## Regression reproduction

Failure modes and expected outcomes were documented in WORKLOG.md, and `tests/rematerialize_archive_postgres.py` was written and executed before changing the implementation. It exercises the actual PostgreSQL schema, materializer, normalizer and packed publication contracts with isolated stored-response fixtures. A MemoryStore replaces external object I/O; all queue and publication SQL executes on real temporary local PostgreSQL. No fixture writes target production.

Before: archive-only, missing-summary and partial-family scenarios fail; recent standalone resources pass. After: all four scenarios and 27 assertions pass. The existing daily/pulse workflow also passes for MLS and Saudi Pro League. The first setup attempt lacked boto3; its infrastructure failure is retained separately and is not counted as a regression result.

Exact environment/bootstrap and commands from the repository root:

```sh
npm install --prefix /tmp/statarena-archive-remat-pg --no-audit --no-fund embedded-postgres@18.6.0-beta.19
python3 -m pip install --target /tmp/statarena-archive-remat-pg/python boto3==1.43.123
mkdir -p output/playwright/rematerialization-completion-20261103
cp docs/verification/rematerialization-completion-20261103/run_archive_postgres.mjs output/playwright/rematerialization-completion-20261103/
node output/playwright/rematerialization-completion-20261103/run_archive_postgres.mjs after
node output/playwright/rematerialization-completion-20261103/run_archive_postgres.mjs daily
```

The system Python already supplies psycopg. The runner creates a temporary cluster on a free localhost port, requires the test database name, and stops/removes that cluster in `finally`. Setup uses the [embedded-postgres primary documentation](https://github.com/leinelissen/embedded-postgres). JSON reports, exact stdout and PostgreSQL setup logs are retained in the output directory; the relevant regression results are copied here.

## Production operation

The original cancelled-run log is retained. It contains 58 partition reports with zero updated matches, despite stored archives. The public six-season Ligue 1 sample records new path digests but absent historical columns, versus enriched current-season rows. These observations demonstrate why `remaining: 0` alone is insufficient.

Because earlier archived partitions were incorrectly cleared, the fixed version requires one new full queue initialization. Subsequent resumptions must use queue_all=false. Completion and live site verification are still pending; this report does not claim that the production regeneration has finished.

## Archive read regression

The first corrected run exposed repeated source reads while the first transaction was pending. A second PostgreSQL scenario was written before modifying this path: 32 matches interleaved across 16 archive shards. The 16-entry LRU caches reloaded the 96 needed files twice (192 reads). The revised code streams each shard once and retains only selected match responses: all 96 source files are read once, all 32 matches are normalized, and every player reference remains consistent. All five PostgreSQL scenarios pass, and the existing daily/pulse workflow still passes.

Run 41721830156 was cancelled for this replacement. Resume the same dirty queue with queue_all=false after publication; already correctly published partitions must not be requeued.

## Live UI checkpoint and continued operation

On the public production site, an explicitly selected Ligue 1 match passed 12 browser checks: actual noncentral goal-line coordinates, visible source height, block coordinates, retained player/match actions, captain/attempted-pass payloads, mobile layout and no application exception. Screenshots and its timestamped report/log are included. This is a real partial-scope checkpoint, not a claim that all historic seasons are regenerated.

The efficient reader is pushed in 58acaf1428. Run 41723613754 resumed the existing queue with queue_all=false, minutes=100 and batch=10. The count fell from 220 at 21:42 UTC to a last successful SQL reading of 100 at 22:59 UTC. It then failed: Neon terminated the connection at 22:59:15 UTC. Subsequent read-only SQL returns HTTP 402, account/project quota exceeded. Public health and manifest both return HTTP 503 as of 23:09 UTC. The Free project reports 5,964,464,180 transferred bytes; public network transfer is the probable limiting quota, although the generic SQL denial does not name the resource.

This is incomplete and affects public data availability. No final remaining receipt exists for that run. The final six-season/default-scope checks have not been run to completion and must not be called passed. [Incident evidence, exact reruns, failure logs and response bodies](quota-incident/README.md) are retained. The five-minute heartbeat remains active, checking health without relaunching while quota denial persists. After availability returns, it must recheck SQL/workflow state, resume with queue_all=false, obtain remaining:0 plus an empty queue, then execute the full checks and publish final evidence. No paid plan, quota limit or source data was changed.

Full final verification commands, after copying these prepared scripts to the output directory and opening the dedicated Chromium session:

```sh
python3 output/playwright/rematerialization-completion-20261103/verify_public_data.py
python3 output/playwright/rematerialization-completion-20261103/run_cli.py production-ui
```

The already completed partial-scope browser command was:

```sh
python3 output/playwright/rematerialization-completion-20261103/run_cli.py production-ui '{"league":"l_3FJFUl"}'
```

The final default-scope browser run and six-season HTTP assertions remain pending until the queue drains.

At 00:07:29 UTC on 4 November (01:07 Paris), the single scheduled health probe changed from the application error to Vercel HTTP 503 / DEPLOYMENT_PAUSED. [Exact response, setup, inputs and rerun](deployment-paused-20261104.json) are preserved. The cause of the pause and the current Neon quota were not rechecked; this response does not establish either. No deployment/billing state was changed and no rematerialization retry was dispatched. The monitor continues one health probe per wakeup and awaits restored availability before rechecking Neon/workflow state. This is a new availability failure, not completion.
