# P2 dense-page origin release

The typed appearance read optimization is deployed in immutable ZIP `becaa1bf45650936555cd01a69fb1e41406e4e60c8da43cf30b68eb76fa35e91`. CloudFormation is UPDATE_COMPLETE. The signed origin and CloudFront distribution are unchanged. Lambda remains Node24/512MiB and RDS remains db.t4g.micro/20GiB with no pending modifications. [Change set](change-set.json), [stack](stack.json), [safe Lambda metadata](lambda-safe.json).

Six sequential public GETs per release returned **the same complete decoded body, gzip size and ETag**: 1,973,314 decoded bytes,431,391 gzip bytes,SHA `0d6bbe72588aa8df43b6d7933093a9d9cd8f028a1b53d61fc8c68bdc37f7d403`. All were HTTP200/no-store/CloudFrontMISS. Every response request ID matched its Lambda REPORT.

| Observation | Before | After | Difference |
|---|---:|---:|---:|
| Median public HTTP, subsequent five requests | 4,016.95ms | 2,729.43ms | −32.05% |
| Median Lambda duration, same five IDs | 3,614.97ms | 2,393.34ms | −33.79% |
| Median billed GB-seconds, same five IDs | 1.8075 | 1.1970 | −33.78% |
| First HTTP observation, reported separately | 5,030.87ms | 4,523.47ms | −10.08% |
| Maximum Lambda memory observed in six requests | 226MiB | 247MiB | No memory reduction claimed |

These are small ordered before/after samples of one dense page, not randomized traffic, p95 estimates or a monthly invoice. The origin duration reduction supports the HTTP finding, while network variation remains in the HTTP samples. Billed compute units are measured; total infrastructure costs and database billed egress are not inferred. [All requests](before.json), [after](after.json), [exact REPORT attribution and computed medians](summary.json).

The independent read-only SQL trial reduced actual PostgreSQL DataRow field bytes from **11,744,517 to 6,243,107 (−46.8%)**, with exact reconstructed rows and HTTP bytes. This changes query-result transport, not database storage. The released query checks the sealed87-column layout once within its existing SELECT, then returns90 ordered values per appearance. New columns trigger the prior named-object representation. Direct public-record construction and cached schema field names avoid repeated transformations. [Read plans](../aws-pagination-plans-20261104/RESULTS.md), [Node24 actual SQL→HTTP and CPU proof](../aws-pagination-plans-20261104/candidate/RESULTS.md).

The parent reran the Node24 SQL/HTTP scenarios against the final shared code: exact source hash/ETag, empty and sparse data, native positions, own reserved fields, zero/null future columns, and HEAD/conditional304 without body SQL. The ingestion CI fixture also observed `array→object→object→array` across native layout, additive typed field and its removal, preserving all fields. Its expected pre-change failure is retained. [Shared Node24 receipt](../aws-pagination-plans-20261104/candidate/after.json), [CI guard](../aws-pagination-plans-20261104/candidate/shared-ci-after.log).

After deployment, both complete published partitions traversed the actual public API in seven HTTP200 pages. All189matches/677fixtures/8,304appearances matched their previous canonical content hashes. OAC403,GET/HEAD/304,CORS and CDN HIT behavior passed the existing public smoke. The hosted Vercel match/player workflow then passed26/26 against the verified new Lambda ZIP, preserving zero overview partitions and on-intent player loading. [Full published traversal](traversal.json), [public smoke](public-smoke.json), [hosted rerun](../aws-deferred-preview-20261104/RESULTS.md).

No schema migration, index, RDS storage/class increase, concurrency increase or data rewrite was performed. The explicit field list must be reviewed when the sealed model evolves; the named fallback protects additive compatibility meanwhile. Full publication and full-scale endpoint/plan acceptance remain gated by available RDS storage.

[Setup and exact rerun commands](PROTOCOL.md). Original artifact17c9 remains available for rollback. Running the before benchmark again requires separately deploying that reviewed baseline and retaining its source publication; the script checks the exact Lambda code SHA and source body before accepting samples.

Suggested commit: `test: record deployed PostgreSQL transport and compute improvements`.
