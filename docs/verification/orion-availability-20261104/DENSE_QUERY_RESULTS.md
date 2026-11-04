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
is61,558bytes. This exact ZIP is now deployed from main commit `eda0ce3e50`.

CloudFormation reached UPDATE_COMPLETE. Review showed only function code and
release stamp changes; the URL/distribution entries were dynamic references.
Function ARN, signed origin URL, CloudFront origin, Node24,512MiB and25s Lambda
timeout remained unchanged. No database migration or data write was performed.
`aws-change-set.json`, `aws-before-resource-identities.json` and the timestamped
post-release receipt make this review inspectable.

Post-release `verify_dense_release.py` passed all16 checks: three sequential
100-match/4,788-appearance GETs returned200 in **4,008.62 / 3,575.56 / 3,034.98ms**,
with equal bytes/hash/generation/ETag. Encoded431,386bytes, decoded1,973,314bytes;
HEAD200 in379.54ms and conditional304 in362.14ms returned empty bodies. All dense
GETs were CloudFront misses with no-store. These are bounded actual observations,
not a new paired HTTP baseline or a timeout-elimination claim.

Public cacheable-match smoke passed10/10 (unsigned origin403, health200,
GET/repeat bytes, edgeHIT, CORS, ETag,304,HEAD,OPTIONS and writes refused). An
initial smoke incorrectly expected an edgeHIT for a no-store partition and
failed that assertion; `aws-public-smoke.json` is preserved. No cache policy was
changed to make the test pass. A separate archive-index probe404 is preserved
as missing AWS data, reinforcing that this lot is not full migration acceptance.

Rerun the bounded HTTP check only when needed:

```sh
python3 docs/verification/orion-availability-20261104/verify_dense_release.py
python3 infra/aws-backend/public-smoke.py '/api/archive/matches/m_02vUAH' /tmp/statarena-public-smoke.json
```

Evidence: `aws-dense-release-20261104T172730943519Z.json` and
`aws-public-cacheable-smoke.json`. Existing RAM/deadlines, query count and
semantic volume are unchanged. No measured storage or monetary cost saving is
claimed. Schema redesign and full data coverage remain separate gates.

Suggested commit: `perf: batch appearance metrics while preserving match membership`.
