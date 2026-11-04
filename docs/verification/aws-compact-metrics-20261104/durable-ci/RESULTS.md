# Durable 009 acceptance in CI

Four checked-in gzip archives hold 411,416 metric rows and 62,577 exact group headers, 4,324,109 bytes compressed. The compressed hashes, decoded hashes, row counts and native COPY column order are recorded in the [input manifest](../inputs/manifest.json). Every decoded digest independently matches the original sealed-migration receipt.

The CI-definition check passed 1/6 before and 6/6 after. Both push and pull requests now trigger on 009 fixture or harness changes. The existing relational job checks out the corpus, verifies the fingerprints, runs 009 on isolated PostgreSQL 18, and saves the new receipt even on failure. The timeout remains 10 minutes.

With default repository inputs, the real process completed in **30.326 seconds locally**, including initializing and removing the disposable PostgreSQL instance. It preserved all 411,416 existing metric rows, passed all eight rollback, concurrent-reader/writer and source-compatibility checks and recorded `inputSource: repository inputs`. A separate isolated named-column trial confirmed that METRIC_COPY_INPUT reaches its Python child and reproduced all rows with zero source or adversarial differences. A missing explicit override returned a file-not-found failure referencing precisely that directory. The local duration describes the added suite. The next GitHub run will establish the complete new Linux job duration.

See [baseline definition](before.json), [final definition](after.json), [full migration receipt](local-e2e/results.json), [wall time](wall-time.json), [hash verification](verified-inputs.json), [alternate-directory trial](named-override.json), and [missing override](override-missing/results.json). Commands are recorded in the JSON receipts. Reproduction from the repository root requires Node, psycopg 3 and embedded-postgres@18.6.0-beta.19 in STATARENA_TEST_TOOLS. Set STATARENA_TEST_PYTHON to the directory containing the Python dependencies. The local fixture corpus is used automatically.

All four AWS writer workflows now propagate the same configured STATARENA_SQL_LIMIT_BYTES repository variable. This change does not alter its value or provision storage.

Suggested commit `ci: retain the complete metric corpus and verify migration 009 on PostgreSQL`.
