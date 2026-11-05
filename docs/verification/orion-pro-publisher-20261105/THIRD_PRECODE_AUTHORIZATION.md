# ROOT-authorized final compact setup attempt

Suggested commit: `test: prepare bounded PostgreSQL publisher workflow before implementation`.

After reviewing the two preserved setup failures and the exact static diagnosis, ROOT explicitly authorized one third and final local pre-code run. The previous `WORKFLOW_RESULT.md` and `WORKFLOW_CHECKSUMS.json` remain an immutable checkpoint of the exhausted initial budget; this new authorization does not change either historical receipt.

The only functional change is the snapshot identifier guard: `(ingest|football|analytics)\.[a-z_][a-z0-9_]*`, plus exact equality with the94 active names read from the canonical model pinned by SHA256. It accepts no source-derived/free identifier. Static validation must confirm all94 canonical names before PostgreSQL starts. No unit test, publisher implementation, schema, migration, admission, source input or product is changed.

The same limits remain:1 owned loopback PG18.6,1 API,2 workers maximum,5 connections,5000 typed rows,200 HTTP,1500 operational SQL and10-minute hard stop. Only exact012/013 plus compact bootstrap are loaded; a separate current014 file is outside this harness. Actual main/worker statement8s and lock1s probes remain required. Existing frozen receipts/snapshots and original REDs are retained byte-for-byte.

```sh
PYTHONPATH=/tmp/statarena-publication-test-python python3 docs/verification/orion-pro-publisher-20261105/publisher_workflow.py --label owned-pg-precode-red-third-final
```

Expected: schema, typed input, real HTTP unavailable/no-store, source-fence calibration, actual deadline and ACL setup gates finish, then exactly one actual absent publisher CLI error leaves P00 RED and all helper-dependent P02–P29 unverified. No substitute publication or repeated absence errors are allowed. Another failure is preserved and reported with no implicit fourth attempt. Stop for ROOT review afterwards.
