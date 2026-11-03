# Evidence map

Final delivery uses `final-all/` (34 HTTP/client checks, including both production Next transports), `materializer-final/` (8 actual SQL workflows / 103 assertions), `daily-final/`, `publication/final-sql-admission/` (18 SQL/S3 workflows), `browser/` (11 UI assertions / four screenshots), and `build/final-build.log`. `source-manifest.json` pins the product and harness sources. `validation-receipt.json` records separate build/format/compilation and existing CI-test checks. `comparison.json` aggregates final numerical observations.

`before/`, intermediate `after-*`, `materializer-*` and publication phase folders preserve original results including failures. They are not additional passing coverage. Some early materializer reports inherited the earlier rematerialization runner label; `RUN.json` is their launcher receipt. The daily-regression launcher originally omitted its `--daily` label; `daily-final/RUN.json` corrects it and records a rerun. Final materializer output now records its exact launcher command in both files. Historical intermediate harness/source versions are not all frozen; rerunning the final harness may exercise additional cases and must use a new evidence directory.

The original P0 materializer is frozen in `materializer-baseline.py`. To compare it using today's final harness:

```sh
STATARENA_MATERIALIZER_MODULE=docs/verification/backend-p1-20261103/materializer-baseline.py STATARENA_SUMMARY_EVIDENCE=docs/verification/backend-p1-20261103/materializer-baseline-replay bun dashboard/scripts/verify_match_summary_materializer.mjs
```

Expected failure: P0 publishes no new summary rows. Publication's frozen P0, admission and SQL-dedup sources have separate rerun phase prefixes documented in `publication/PROTOCOL.md`. Its final 18-workflow replay and exact Python/PostgreSQL dependencies are specified there. The materializer runner also accepts `STATARENA_TEST_PYTHONPATH`; point it to the same installed psycopg/boto3 dependency directory if the default temporary archive-test directory is absent. The HTTP runner shares PostgreSQL tooling from the P0 protocol.

`activation-checkpoint.json` and `production-p0-checkpoint.json` are read-only operational observations. They do not establish P1 migration, writer activation or summary backfill in production. Browser replay requirements and exact service/CLI commands are in `browser/REPLAY.md`.

Suggested commit: `test: preserve P1 workflow evidence and quantified results`.
