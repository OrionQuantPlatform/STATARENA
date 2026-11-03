# Rematerialization correction and production verification

The initial run 41711363014 was cancelled after public data verification found that archived partitions were cleared from the dirty queue without receiving enrichment. Their fixtures exist, but standalone `/matches/{id}` resources do not: successful original responses are in observation shards. The materializer required a newer standalone match resource and skipped those archived matches.

The corrected materializer loads standalone and archived indexes for each partition, prefers successful recent resources, and falls back to stored archive summaries/players/shots/lineups/stats. A fixture can be normalized without a collected match summary when its actual player/shot/stat responses exist. Missing families retain previous normalized data and player references. Archived response tables are indexed once per shard; no provider call is introduced.

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
