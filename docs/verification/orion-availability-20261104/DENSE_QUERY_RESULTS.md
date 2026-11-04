# Dense partition reader — reviewed candidate

The reader materializes only appearances belonging to selected match IDs and
aggregates their extra metrics together. Public records, pagination and ETags
stay equal to deployed b2ec973d. The original optimization's additional season
predicate silently omitted an inconsistent appearance; the red proof is kept.

| Comparable RDS read-only snapshot | Baseline | Candidate |
|---|---:|---:|
| Match count |100|100|
| Appearance count |4,788|4,788|
| Canonical result bytes |5,821,148|5,821,148|
| Execute and client fetch |2,605.772ms|2,019.623ms|
| Heavy SQL statements per GET |1|1|
| Statement deadline |8s|8s|

Time fell586.149ms (22.49%) in one ordered pair. SemanticSHA256 is identical:
`26c261285aed32db2c9920eb39493c19e0b380999365cf440282402eb9297de2`.
This is notp95, a load test, a measured cost reduction or proof that production
cannot time out. Statement count and returned semantic bytes did not decrease.

Root independently reviewed the SQL diff and reran the disposable real
PostgreSQL/HTTP E2E:8checks passed, covering pagination, compact wire, native
scalars/reserved metrics, conditional304, other league, future-column fallback
and adversarial membership. Original red and corrected green remain separate.

Rerun local proof (no cloud calls):

```sh
STATARENA_TEST_TOOLS=/tmp/statarena-cache-test-tools STATARENA_TEST_PYTHONPATH=/tmp/statarena-publication-test-python bun docs/verification/orion-availability-20261104/compare_readers.mjs
```

Requires Bun, installed dashboard dependencies, embedded-postgres tools and
psycopg under the stated temporary dependency paths. PostgreSQL is created and
stopped by the runner; only disposable synthetic data are written. Exact setup,
expected/actual outcomes and source/SQL hashes are in the timestamped JSON.

RDS receipt `rds-pair-20261104T164032339102Z.json` records the8s deadline,
read-only repeatable-read snapshot and generation. `compare_rds.py` reruns one
bounded pair using existing.pgpass with verified TLS; it saves only hashes and
counts. Do not rerun merely to improve a sample. Captured SQL comes directly
from baseline/current handlers in `reader-sql-20261104T163921235Z.json`.

Release preflight passed account/network/template checks; candidate code ZIP
`6827c8a889c2622b84ef05f5eb088cdae8255a3d00321f553d0cb77b3cb00ddb.zip`
is61,558bytes. Deployment/post-deploy acceptance is still pending and governed
by RELEASE_PROTOCOL.md; those results must be added after actual execution.

Suggested commit: `perf: batch appearance metrics while preserving match membership`.
