# Paired live AWS origin-reader measurement

Preregistered before fixture selection. Gate match work on a committed backend-owned partition and an indexed legacy source shared by a published match. Read only the runtime SSM identities, actual statarena_prod RDS and the retained Ohio S3 bucket. Require TLS with the RDS CA, a read-only database session and bounded SELECTs. Measure local Bun HTTP listeners calling the committed legacy-app.js and aws-app.js modules directly. Exclude Lambda, CDN and public origin traffic. Pin the Git revision and package dependencies, select sources before reading HTTP values, and track the publication digests before and after trials.

Choose the earliest published partition by published_at, season and league ID that has at least one eligible match. Within it prefer the highest count of published default-parameter families, then match ID ascending. Require a successful stored summary and at least one successful family among shots, stats and events. Choose the first qualifying family in that order. Legacy candidate source references must be available and total at most 8 MiB compressed for the match. Use only independently compatible routes, namely the full archived match, the selected individual family, and optionally a saved player profile if published and present in both schemas. Skip any unmatched route with its reason. Canonicalize object-key ordering only, require exact content, ordered arrays, presence, nulls and value types. Record raw response bytes and SHA-256 as well as canonical digests. A status or value mismatch prevents speedup claims for that route.

Run a screening pair followed by five fresh-process cold pairs and ten warm requests per reader per eligible route. Alternate the order of readers by trial. Warm means additional requests in one already-populated process within the legacy TTL. Only one benchmark HTTP request is active at a time. Each fresh process opens its own application pool. Do not flush database, S3 or OS caches. Enforce an overall 64 MiB per-route legacy source read budget and a 20 s request ceiling. Abort further reads of a route on first source divergence, missing access or repeated error. For steady data report times and SQL/query counts, pool wait and SQL time, compressed source bytes, decompressed/parsed source bytes, logical HTTP bytes and measured application cache hits. Client-side timings include the Mac-to-Ohio path. Do not equate SQL row counters with PostgreSQL wire bytes or estimate Lambda latency from these numbers. No AWS writes or profile refresh from external football providers.

Suggested commit `test: measure paired live AWS football reads`.

The passive node-postgres DataRow observer counts each decoded protocol frame from its length field plus its message-type byte. Field payload bytes exclude the frame length, two-byte column count and each four-byte column length. These are real server result data bytes at the driver, without socket handshake, SQL text, TLS, command tags or row descriptors. Elapsed time ends when the HTTP body is consumed and precedes benchmark-only canonicalization. Each application connection is checked at startup for database/hostname and enforced read-only options.

Run from the repository root with the read-only AWS profile, the SSM runtime credentials cached at the private path used by the release, verified RDS CA, Bun and installed dashboard dependencies.

```sh
export STATARENA_PROBE_CONFIG=/tmp/statarena-aws-runtime-20261104.json
export STATARENA_PROBE_CA=/tmp/statarena-rds-us-east-2-20261104.pem
export PYTHONPATH=/tmp/statarena-archive-remat-pg/python
python3 docs/verification/aws-live-performance-20261104/benchmark.py
python3 docs/verification/aws-live-performance-20261104/summarize.py
```

Use STATARENA_BENCHMARK_REF to rerun a measured Git SHA. A missing eligible partition exits with code 3 and saves selection.json. A non-200 response, changed source, canonical mismatch, quota stop or timed-out subprocess is an incomplete/failed comparison. Credentials, source bodies and private connection strings are excluded from the retained receipts.
