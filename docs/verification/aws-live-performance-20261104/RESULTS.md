# Paired reads from the first published RDS partition

The two backend handlers returned identical JSON values for the same published fixture and its shots. On a fresh process, the median full-match HTTP request fell from **3,132 ms to 1,460 ms**, a 53% reduction. The shots request fell from **1,879 ms to 1,050 ms**, a 44% reduction. Warm medians were 8.5 ms and 3.9 ms higher for the relational reader in this run.

| Route and process state | Legacy HTTP median | Relational HTTP median | SQL statements, legacy → relational | PG field payload bytes, legacy → relational | S3 bytes, legacy → relational | Source bytes parsed in application, legacy → relational |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Full match, cold | 3,131.9 ms | 1,459.9 ms | 28 → 2 | 4,170 → 349,585 | 242,734 → 0 | 3,313,881 → 0 |
| Shots, cold | 1,878.9 ms | 1,050.4 ms | 4 → 2 | 1,839 → 15,157 | 21,406 → 0 | 154,951 → 0 |
| Full match, warm | 98.9 ms | 107.4 ms | 1 → 1 | 1,454 → 67 | 0 → 0 | 0 → 0 |
| Shots, warm | 96.3 ms | 100.2 ms | 1 → 1 | 1,454 → 67 | 0 → 0 | 0 → 0 |

Cold trials include application-pool startup and verified TLS. The legacy reader fetched and parsed a shared S3 archive shard, then selected the match. The relational reader returned the selected match from PostgreSQL, increasing cold SQL result bytes while eliminating S3 reads. Warm relational requests checked the publication version and reused the stored representation. Both readers returned a 315,321-byte full-match body and a 14,014-byte shots body.

## Scope and parity

- The selected fixture was m_02vUAH in l_0275VP, season 2026/2027. Selection used the first eligible committed partition. No individually saved player profile qualified under the preregistered source checks at selection.
- The run took place November 4, 2026, from 03:16:30 through 03:17:29 UTC. Each reader served one screening request, five cold samples and ten warm samples per route, for 64 HTTP requests total. All returned status 200. Canonical response digests matched across every trial. Object key order differed between raw outputs, while ordered arrays and values were equal. Typed match version, legacy observation and resource references, and source object checksums remained stable.
- Both applications were served from local Bun processes on the Mac using revision 779d80d795735dda8ddd9dbe522ace25a0418110. Both connected to the same verified Ohio RDS PostgreSQL 18.6 database using enforced read-only startup settings. The legacy process also used the runtime S3 identity for the Ohio bucket. Its total S3 transfers across both routes were 1,584,840 bytes.
- The timings reflect the Mac-to-Ohio network path. Lambda, distribution caching and browser rendering are measured separately. The cold HTTP clock covers real request, handler and database-pool startup work, excluding benchmark-only key sorting and hashing. PG field payload bytes come from driver-observed DataRow frames and exclude SQL text, row descriptions and protocol/TLS overhead.

The input selection is in selection.json. All HTTP samples and version checks are in measurements.json. summary.json includes min, median, max, SQL time, pool wait and object-read time. The protocol contains the exact rerun command. Use STATARENA_BENCHMARK_REF=779d80d795735dda8ddd9dbe522ace25a0418110 to pin the original application snapshot; a new publication can change fixture selection.

Suggested commit `test: measure paired live AWS football reads`.
