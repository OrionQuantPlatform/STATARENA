# Independent schema/bootstrap readback

Suggested commit: `test: retain independent RDS schema and bootstrap readback`.

This matrix precedes the readback script and the first remote schema apply. The script is read-only: an existing libpq password entry, pinned host/database/role, TLS verify-full, PG18.6, one repeatable-read snapshot, 8s statements, 1s lock timeout and at most 14 SELECTs. It accepts no DSN or password in arguments and retrieves no secret.

| Setup or observable outcome | Expected result |
|---|---|
| Missing/tampered/failed apply receipt or current model/SQL mismatch | Reject before connecting |
| Wrong database, role, TLS, engine, transaction access mode | Fail identity case, retain safe evidence |
| Missing/extra business table, column, type, nullability, PK/FK/UQ/CHECK or declared index | Fail catalogue case and list metadata discrepancies |
| Missing/unvalidated constraint or disabled integrity trigger | Fail integrity case |
| Journal SQL/commit, bootstrap code/manifest or seed values differ | Fail immutable binding case |
| Any business facts beyond bootstrap | Fail scope case; do not erase or repair |
| Runtime role can mutate new relations or execute writer helpers | Fail privilege case; do not alter grants |
| Expected state | 94 tables, 1709 columns, 431 FKs, exact model constraints/index names, one sealed bootstrap, ten typed seeds, no business facts and correct existing-role grants |

The run saves its setup, source/receipt/model/SQL hashes, exact command, query text, safe catalogue/role/bootstrap metadata, expected/actual cases, relation footprint and connection closure. It never selects a raw football source body. Existing source-schema presence and estimated row counts are an observation, not byte-level reconciliation or proof of complete migration.

Rerun from the repository with Python dependencies installed:

```sh
PYTHONPATH=/tmp/statarena-publication-test-python python3 docs/verification/orion-pro-pilot-20261104/rds_readback.py --apply-receipt <repository-relative-result.json> --apply-sha256 <sha256> --label schema-bootstrap
```

No remote rollback, real-source import, publication, cleanup or production switch is performed. A passing readback establishes only the schema/bootstrap scope. New relation storage is overhead at this stage; no latency/storage saving is inferred from it.
