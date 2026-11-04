# Discovery cost on the RDS metadata shape

Run 41764262462 hit the 120-second statement timeout while building `work_matches`. The previous query grouped all saved match resources inside the fixture join and repeated the grouping for matches without fixtures. The new code computes the same ordered fingerprint once, in indexed ranges of up to 256 distinct match identities, then joins its keyed result to fixtures and orphans. Session-local statistics are refreshed before dependent joins.

From the 03:06 UTC RDS snapshot, one read-only TLS session copied 103,409,505 bytes of structural metadata. Inputs comprised 58,922 fixtures, 415,426 saved resource selectors, 53,842 observation memberships, 3,719 shard references and 306,110 object paths. Original payloads and document bodies were excluded. Both versions of the actual discovery function then ran against identical rows on disposable PostgreSQL 18 with the RDS work_mem setting of 4 MB. Payloads were synthetic and source timestamps and stored SHA values locally generated. The old and new functions ran in order on the same database, so their elapsed timings also reflect cache warmth.

| Local execution | Before | After |
|---|---:|---:|
| Fixture join previously timing out on AWS | 3,015.706 ms | 216.437 ms |
| Full discovery | 7.954 s | 5.207 s |
| Saved resource aggregation within fixture join | 379,421 rows | 0 rows |
| Largest independent digest statement | One full aggregation | 102.7 ms over 31 ranges |

All 60,764 combined match stamps, 486 partition fingerprints, 486 queued partition identities, and 36,228 catalog identities/fingerprints matched exactly. The original plan estimated 200 grouped match IDs versus 7,889 actual. The new fixture query joins pre-analyzed, individually keyed rows. The old orphan pass alone took 2.714 s. The 31 digest ranges contained between 9,179 and 14,192 source rows each. The separate 16-workflow publisher regression passed against the new code.

A live RDS capability probe returned SQLSTATE 25006 for CREATE TEMP TABLE in a READ ONLY transaction. The plans captured here are local EXPLAIN ANALYZE runs over actual production metadata distributions. The unchanged 120-second limit and performance on the credit-depleted micro instance require a new hosted workflow.

Read [the preregistered protocol](PROTOCOL.md), [source counts and checksums](source-metadata.json), [original failure](before/results.json), [after and exact fingerprints](after/results.json), [both executed SQL plans](after/new-plans.json), and [publisher regressions](../aws-rematerialize-20261104/prepare-optimized/results.json). Rerun from the repository root:

```sh
PYTHONPATH=/tmp/statarena-publication-test-python python3 docs/verification/aws-prepare-20261104/capture.py
node docs/verification/aws-prepare-20261104/run.mjs before
node docs/verification/aws-prepare-20261104/run.mjs after
node docs/verification/aws-rematerialize-20261104/run.mjs prepare-optimized
```

The capture uses the Ohio runtime read-only SSM credential and TLS CA. Other commands use local Python dependencies at /tmp/statarena-publication-test-python and embedded-postgres@18.6.0-beta.19 under /tmp/statarena-cache-test-tools. The captured local gzip inputs are retained in /tmp/statarena-prepare-meta-20261104. Raw ordering and source values can change on a later capture. The before phase expects its plan gate to fail. baseline.txt pins the previous code for the final parity run.

Suggested commit `perf: compute publication fingerprints once in bounded match ranges`.
