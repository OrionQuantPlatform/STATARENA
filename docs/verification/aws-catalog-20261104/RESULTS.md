# Catalog and profile verification

The source inventory contained 537 objects across historical results and goals, FIFA and UEFA rankings, cup snapshots and competition indexes, OpenMatchday supplemental fixtures and goals, and matchday rounds. The 31,402,371 source bytes were read through a pinned, read-only source audit. The first complete pass found 82 objects with unmodeled fields or score shapes. After modeling those variations, all 537 inputs passed.

A disposable PostgreSQL 18.6 instance with verified TLS published those 537 inputs as 743 independently selectable catalog records and reproduced every normalized source value in 80.34 seconds. The full catalog plus the test profiles, indexes, TOAST and allocated pages occupied 814,645,248 bytes in that local database. The 63 application tables contained zero JSON, JSONB or bytea payload columns. Stored source files and the migration database were untouched.

The local HTTP workflow passed 65 recorded requests plus additional validator checks. It covered every selector class, all five cup snapshot kinds, the saved league list, individual league, team and player profiles, linked and unlinked clubs, missing sources, explicit saved errors, and all 65 supplemental competitions. The optional tagged GET and metadata-only HEAD returned the same weak ETag. Replacing one goal without changing the index immediately invalidated the aggregate response. An incomplete supplemental publication gave HTTP 503. The independent read-only RDS profile sample accepted 50 imported resources for each of leagues, teams and players. Other profile records remain unverified.

| Warm HTTP GET, five repeats | Minified bytes | Prior median | Version-checked median | Warm database work |
| --- | ---: | ---: | ---: | --- |
| Full supplemental catalog | 3,806,859 | 271.4 ms | 13.1 ms | One metadata SELECT, zero JSON rows |
| Historical goals 2023/2024 | 2,833,323 | 161.4 ms | 4.4 ms | One metadata SELECT, zero JSON rows |

These local measurements include HTTP body transfer on loopback. The catalog cache has a 24 MiB logical representation budget and a 4 MiB entry limit. The largest cup snapshot in the source inventory was 137,888 minified bytes. No production runtime latency or public availability was measured in this workflow.

## Reproduce

Run from the repository root with Bun, openssl, installed dashboard packages, standalone embedded-postgres 18.6.0-beta.19 in /tmp/statarena-cache-test-tools, and psycopg 3 available to python3. The normal HTTP workflow uses the committed compressed captures and requires no cloud credentials.

```sh
PYTHONPATH=/tmp/statarena-archive-remat-pg/python bun docs/verification/aws-catalog-20261104/verify.mjs after
```

The full source replay additionally needs the version-pinned source objects from the audit. With the read-only AWS profile statarena configured and boto3 installed alongside psycopg, first populate the temporary local cache using the committed source-inventory.json. Recreating the inventory separately selects the then-current source versions.

```sh
PYTHONPATH=/tmp/statarena-archive-remat-pg/python python3 docs/verification/aws-catalog-20261104/audit_sources.py after
PYTHONPATH=/tmp/statarena-archive-remat-pg/python bun docs/verification/aws-catalog-20261104/verify.mjs after --all
```

The files after.json, before-large-cache.json, full-postgres-roundtrip.json, source-audit-before.json, source-audit-after.json and profile-shape-audit.json contain individual receipts. test-host-guard.json records an intermediate fixture configuration failure after the shared runtime started enforcing RDS hostnames. The final fixture explicitly enables the localhost test profile and still verifies TLS.

The profile shape sample uses the runtime SSM configuration and RDS CA only for bounded read-only queries.

```sh
STATARENA_PROBE_CONFIG=/tmp/statarena-aws-runtime-20261104.json STATARENA_PROBE_CA=/tmp/statarena-rds-us-east-2-20261104.pem PYTHONPATH=/tmp/statarena-archive-remat-pg/python python3 docs/verification/aws-catalog-20261104/audit_profiles.py
```

Suggested commit `feat: serve football catalogs and profiles from typed PostgreSQL tables`.
