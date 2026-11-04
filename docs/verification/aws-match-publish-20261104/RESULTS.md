# Match publication benchmark

The candidate publishes (match_id, family_responses, optional_metadata, saved_variants) records in a single database transaction. It locks match IDs in sorted order before reading existing digests. It writes changed family headers in groups, then copies each populated domain table once per group. One call accepts up to 32 distinct match records. A COPY group retains at most sixteen matches or roughly 8 MiB of canonical source response data, excluding the unavoidable size of a single larger family. The original single-match and nested-resource interfaces delegate to the same writer.

| Real PostgreSQL workload | Original SQL / COPY / transaction commands | Candidate SQL / COPY / transaction commands | Modeled serial exchanges, original → candidate |
| --- | ---: | ---: | ---: |
| One complete match | 17 / 39 / 4 | 5 / 39 / 4 | 99 → 87 |
| 16 complete matches | 272 / 624 / 34 | 5 / 39 / 4 | 1,554 → 87 |
| 32 complete matches | 544 / 1,248 / 66 | 7 / 78 / 4 | 3,106 → 167 |
| Repeat 32 unchanged matches | 128 / 0 / 66 | 4 / 0 / 4 | 194 → 8 |

The model charges one exchange to each SQL or transaction command and two to a complete COPY handshake. At 5–30 ms per exchange, the additive modeled delay for 16 matches falls from 7.77–46.62 seconds to 0.44–2.61 seconds. For 32 matches it falls from 15.53–93.18 seconds to 0.84–5.01 seconds. Data-transfer time and source-read latency are separate.

The no-delay and injected-delay JSON receipts contain wall-clock measurements for every case. before-simulated-5ms.json and after-simulated-5ms.json inject sleeps into real psycopg operations against local PostgreSQL. OS scheduling can increase an injected sleep. These measurements use a loopback connection.

Both writers produced identical PostgreSQL JSON for all 49 seeded matches. The candidate preserved existing context and absent families, canonical variant precedence, opposite-order overlapping transactions, and transaction rollback on a failing seventeenth record. The private candidate also passed the existing 63 match and 65 catalog HTTP workflows that exercise the normalizers.

The reviewed writer is integrated into the existing 16-fixture publication loop. Worker validation rejects unsupported saved endpoints before passing variants to the batch API. Source quality, headroom, receipts and dirty-marker checks still operate within the original partition transaction. The verification used disposable local databases.

Suggested commit `perf: batch typed match publication across fixtures`.

## Measured timings

| Real SQL and COPY operations | Original loopback | Candidate loopback | Original with injected 5 ms | Candidate with injected 5 ms |
| --- | ---: | ---: | ---: | ---: |
| 16 full matches | 1.408 s | 0.999 s | 12.897 s | 1.595 s |
| 32 full matches | 2.777 s | 2.058 s | 26.759 s | 3.289 s |

The no-delay benchmark process peaked at 146,833,408 bytes with the original writer and 162,021,376 bytes with the candidate on macOS. Each process includes the caller-owned cloned source records and the verification reader. The full single-writer SQL contract checks are in match-http-after.json and catalog-http-after.json, with the candidate writer digest recorded explicitly.

## Review artifact

The baseline writer is from commit c0e44523be. The review patch at /tmp/statarena-match-batch-writer-20261104/candidate.patch applies cleanly to that commit and changes only dashboard/scripts/relational_match.py. Its SHA-256 is aefb6706b94601923fc1d0a5d0002b5ccd7cc4bcd59a9169ff4c4df6e53edfdc. The resulting writer SHA-256 is 306720599a0ff43d0c7130253549165a8916bca04bdced0962c814afc354475c.

From the repository root, use a private worktree to independently replay the candidate without changing the frozen checkout.

```sh
git worktree add --detach /tmp/statarena-match-batch-review c0e44523be
git -C /tmp/statarena-match-batch-review apply /tmp/statarena-match-batch-writer-20261104/candidate.patch
PYTHONPATH=/tmp/statarena-archive-remat-pg/python STATARENA_MATCH_WRITER=/tmp/statarena-match-batch-review/dashboard/scripts bun docs/verification/aws-match-publish-20261104/run.mjs after
PYTHONPATH=/tmp/statarena-archive-remat-pg/python STATARENA_MATCH_WRITER=/tmp/statarena-match-batch-review/dashboard/scripts STATARENA_SIMULATED_RTT_MS=5 bun docs/verification/aws-match-publish-20261104/run.mjs after
```

The private E2E fixture replay used the same candidate import ahead of the frozen single-match seed imports. The harness checkout and launcher used for that run are in /tmp/statarena-match-batch-e2e-20261104. The candidate patch received a successful git apply --check, and the worker and benchmark Python passed Ruff.


## Integrated worker verification

All 16 actual publisher workflows passed. In the 64-match interleaved-shard case, the original worker started 64 event-sheet COPY sessions and the integrated worker started four. Both read each archived source file once. A seventeenth record with a valid events response and an unsupported additional resource raised after one earlier group COPY. PostgreSQL rolled back that group, preserved the generation and partition receipts, and retained the dirty marker. Removing the offending saved endpoint published 17 matches; an eighteenth fixture without data acquired no detail header.

The integrated source hashes are 306720599a0ff43d0c7130253549165a8916bca04bdced0962c814afc354475c for the match writer and ca551ca4313bd56a2fb10ea5d60e41c7ba86432a0e5c9cba642cea597dae4e51 for the partition worker. Individual results are in worker-before/batch-integration.json, worker-after/batch-integration.json, worker-after/results.json, match-http-integrated.json and catalog-http-integrated.json.
