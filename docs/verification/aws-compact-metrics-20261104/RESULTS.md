# Compact relational metric publication

Migration 009 reduced the measured allocation of the two published metric families from **89,554,944 to 8,454,144 bytes**, a **90.56% reduction**, including all destination indexes, dictionaries and PostgreSQL TOAST allocations. This was a local PostgreSQL 18 replay of the real copied metric rows from 189 published matches.

| Source | Metrics | Original groups | Before | After | Bytes per metric after |
| --- | ---: | ---: | ---: | ---: | ---: |
| Player halves | 221,906 | 39,840 | 48,013,312 | 4,825,088 | 21.74 |
| Full players | 189,510 | 22,737 | 41,541,632 | 3,629,056 | 19.15 |

Both directions of SQL EXCEPT ALL returned zero rows across all eleven original columns. The source checksum, full group metadata and allocation by physical relation are in after/results.json. The 189 resource-layer SQL digest pairs per family also matched before and after. That check used the original metric and group rows with minimal synthetic ancestors. The separate HTTP fixture uses a complete original football match.

## What changed

The writer still sends typed COPY rows, once per populated relation in each bounded batch. PostgreSQL places established measures into named columns, shares typed provider label and layout definitions, and stores unusual values and unmodeled or duplicate keys in a relational overflow table. Missing and null markers, the source numeric values, order and independent resource ownership remain recoverable through the original relation names. Digest lookups are checked against exact typed metadata and ordered membership before reuse. Numeric values are not part of the shared templates.

The old derived heaps stay available for reads throughout conversion. A real reader using a 500 ms lock timeout succeeded while an injected lock blocked compact data insertion. Both old heaps are checked in both directions before the transaction enters its final schema handover. The final exclusive lock request is bounded to 250 ms, retaining a stricter caller limit where applicable. An intentionally invalid second family aborted the transaction and left both original heaps and their rows intact. Existing explicit SELECT grants survived the handover. Database source and staging tables are outside this migration.

The compatibility views support existing reads. Writers must use the updated typed COPY-and-fold path after cutover. A transaction-scoped dictionary-writer lock is acquired before any per-match lock. Independent callers that concurrently introduced new definitions and templates in opposite family order both committed. The existing production worker already processes publication under an advisory lease. Published dictionary entries are immutable and can be reused.

## Measurements and limits

- Clean migration took **4.73 s** on the local fixture. Computing all 378 complete player/half response-layer digests took **3.62 s before and 4.54 s after**. These timings do not measure RDS latency.
- A 16-match local publication took **1.025 s before and 1.154 s after**. Both performed 39 COPY streams. The compact path used nine SQL commands instead of five. For 32 matches it took 2.090–2.092 s before and approximately 2.29 s after, with the original 78 COPY streams. An unchanged 32-match retry performed no COPY.
- The full 63-request match HTTP workflow and all 16 existing partition workflows passed. The interleaved 64-match case kept its four event-sheet COPYs. Real late-source failure, dirty marker and retry checks passed. The new receipts include source/spool, normalization/matching, typed-detail publication and core publication/checkpoint times, plus total time including commit.
- At the sampled estimates of 45.51 million half and 48.41 million full-player metrics, these measured production-layout densities imply **about 1.92 GB** for the two metric families. Other detail domains, core and catalog storage remain additional. This migration alone does not establish complete coverage within the current 20 GiB volume or 16 GB SQL guard.
- The capacity experiment and the new SQL operated on local PostgreSQL. Production cutover, live performance and subsequent total database growth require separate receipts.

The long-key regression rejected valid source text with the preliminary B-tree definition index. The final store admits arbitrarily long provider labels through a fixed-size digest plus a typed equality check. Tests also preserve Unicode-distinct keys, duplicate semantic keys, absent and null fields, exact floating negative zero, out-of-range counts, fractional values, independent replacement, rollback, idempotent migration and retries.

## Replay

Run from the repository root with node/Bun, the installed dashboard dependencies, psycopg 3, embedded-postgres from STATARENA_TEST_TOOLS, and the authorized immutable COPY inputs in /tmp/statarena-metric-values-20261104 or METRIC_COPY_INPUT. The required inputs are half_stat_metrics.tsv.gz, player_stat_metrics.tsv.gz, half_stat_groups.tsv.gz and player_stat_groups.tsv.gz. Their checksums are in after/results.json. The tests below write only to disposable local PostgreSQL instances.

```sh
node docs/verification/aws-compact-metrics-20261104/run.mjs after
PYTHONPATH=/tmp/statarena-archive-remat-pg/python bun docs/verification/relational-match-20261104/verify.mjs after
PYTHONPATH=/tmp/statarena-archive-remat-pg/python bun docs/verification/aws-match-publish-20261104/run.mjs after
node docs/verification/aws-match-publish-20261104/worker.mjs schema-009
python3 dashboard/scripts/relational_metric_ddl.py | cmp - dashboard/backend/migrations/009_compact_player_metrics.sql
```

The named-column design comparison is preserved in named-column-trial/results.json. The actual migration and integrated runner receipts are in after/ and integrated/. before/, before-read-availability/ and before-long-key/ retain the observed failures that preceded the fixes.

Suggested commit `perf: compact normalized player metric storage`.
