# Relational match detail acceptance

Use the repo's unchanged captured responses in dashboard/outputs/data-completeness. production-archive is a complete published match, browser-historical-archive contains saved 404 responses, and browser-upcoming-archive includes null lineups and empty arrays. Compare every endpoint, leaf value, order, zero, false, explicit null, absent key, and archive metadata. A single SQL query should suffice for a cold whole-match response and for one individual family. Replacing just one family must not remove the other twelve. Heatmaps variants coexist. Exercise retry, unknown schema rollback, no refs to raw storage, and an ID with no observations. No PostgreSQL JSON/JSONB/bytea source payload columns in the detail tables. Use fresh local PostgreSQL 18 over verified TLS and the real HTTP DAO. Report queries, source bytes, timings, returned bytes and digests. The earlier object-path experiment is historical baseline only.

Run from repo root with `bun docs/verification/relational-match-20261104/verify.mjs before` and repeat with `after`. Dependencies are Bun, openssl, installed dashboard packages, embedded-postgres in STATARENA_TEST_TOOLS (defaults to /tmp/statarena-cache-test-tools), and psycopg 3 installed for PYTHON (defaults python3). Set PYTHONPATH for an external psycopg installation. The runner creates/tears down a local database and uses no production credentials, AWS objects, source API or production writes.

Suggested commit `feat: serve match details from normalized football tables`.

## Nested saved match resources

All five advertised nested variants have 200 data on RDS. The November 4 read-only source probe compares at most 600 indexed references per match and route, with a five-second statement timeout. Inputs and sample bodies are in nested-source.json, including two different 404 error codes. Exact command:

`STATARENA_PROBE_CONFIG=/tmp/statarena-aws-runtime-20261104.json STATARENA_PROBE_CA=/tmp/statarena-rds-us-east-2-20261104.pem PYTHONPATH=/tmp/statarena-archive-remat-pg/python python3 docs/verification/relational-match-20261104/probe_nested.py`

Normalize each captured nested response independently by match, family, subject and canonical parameters. SQL must return its exact saved response for the corresponding match/subject and preserve its saved error if unavailable. Nested-only matches must not expose nested resources inside the thirteen-family match envelope. An unknown nested ID returns no resource. Use the same `verify.mjs` workflow with argument `before-nested` and then `after`.

## Sample imported provider schemas

The worker must reject an unknown field explicitly and retain the preceding published version. Sample read-only current SQL migration inputs across distinct indexed match prefixes, validate conversion in memory, retain the sampled IDs/status, byte counts and any errors. Sample up to eight distinct matches, 13 parent endpoints each, no source over 600 KB and no more than 8 MB cumulatively. Use `STATARENA_PROBE_CONFIG`, `STATARENA_PROBE_CA` and `PYTHONPATH` as for probe_nested.py and run `python3 docs/verification/relational-match-20261104/probe_shapes.py`.

HEAD requests must return existence/status with one SQL query, no body, and no JSON rows assembled by PostgreSQL. Compare cold ID, warm ID, unavailable individual response, and missing ID. `verify.mjs before-head` captures the unoptimized behavior. Exact before/after values remain equal for GET. Compare like-for-like with `bun docs/verification/relational-match-20261104/legacy.mjs`, which restores commit 923bb0ff4a into scratch, gzips the same three checked-in matches into one shared legacy shard, and asserts the complete legacy handler payloads. Cold full-match transfer should decline from 28 SQL and 14 object reads to one SQL and zero objects. Report times as local observations, including an increased latency where applicable.

## Version-checked representation cache

The initial normalized reader generated the large archived result again for every GET. Add seven repeated HTTP reads for the same complete match before implementing caching. Each warm GET must return its complete unchanged body while doing one current-version metadata SELECT, zero SQL JSON rows and zero object reads. First reads may cost two SQL statements. Compare medians over the seven warm requests. In the same process change source metadata only and then one endpoint. The weak ETag and the next GET must reflect each committed update immediately. An unavailable nested response never enters the representation cache. An oversized result must bypass admission without evicting a previously retained match. HEAD of an existing aggregate/endpoint returns its weak ETag without building JSON. `before-cache` records the failing implementation before the optimization.

Request optional version metadata on aggregate and targeted GETs. Compare the ETag with the corresponding metadata-only HEAD and compare the complete GET JSON to its captured expected value. A caller using the default continues to receive the original JSON.
