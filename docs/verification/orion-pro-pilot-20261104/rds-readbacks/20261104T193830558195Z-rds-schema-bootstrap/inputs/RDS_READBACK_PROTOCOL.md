# Independent schema/bootstrap readback

Suggested commit: `test: retain independent RDS schema and bootstrap readback`.

This matrix precedes the readback script and the first remote schema apply. The script is read-only: an existing libpq password entry, pinned host/database/role, TLS verify-full, PG18.6, one repeatable-read snapshot, 8s statements, 1s lock timeout and at most 14 SELECTs. It accepts no DSN or password in arguments and retrieves no secret. An expected catalogue and its SHA-256 are mandatory and checked against current source/model/SQL before connecting; its preparation is strictly local.

| Setup or observable outcome | Expected result |
|---|---|
| Missing/tampered/failed apply receipt or current model/SQL mismatch | Reject before connecting |
| Wrong database, role, TLS, engine, transaction access mode | Fail identity case, retain safe evidence |
| Missing/extra business table, column, type, nullability, PK/FK/UQ/CHECK/index, sequence or view; changed constraint/index/view definition or properties | Fail catalogue case and list metadata discrepancies |
| Missing/unvalidated constraint or disabled integrity trigger | Fail integrity case |
| Journal SQL/commit, bootstrap code/manifest or seed values differ | Fail immutable binding case |
| Any business facts beyond bootstrap | Fail scope case; do not erase or repair |
| Runtime role can mutate new relations through table or column grants, or execute writer helpers | Fail privilege case; do not alter grants |
| Expected state | 94 tables, 1709 columns, 431 FKs, exact model constraints/index names, one sealed bootstrap, ten typed seeds, no business facts and correct existing-role grants |

The run saves its setup, source/receipt/model/SQL hashes, exact command, query text, safe catalogue/role/bootstrap metadata, expected/actual cases, relation footprint and connection closure. It never selects a raw football source body. Existing source-schema presence and estimated row counts are an observation, not byte-level reconciliation or proof of complete migration.

Rerun from the repository with Python dependencies installed:

```sh
PYTHONPATH=/tmp/statarena-publication-test-python python3 docs/verification/orion-pro-pilot-20261104/rds_readback.py --apply-receipt <repository-relative-result.json> --apply-sha256 <sha256> --expected-catalogue <repository-relative-expected-catalogue.json> --expected-catalogue-sha256 <sha256> --label schema-bootstrap
```

No remote rollback, real-source import, publication, cleanup or production switch is performed. A passing readback establishes only the schema/bootstrap scope. New relation storage is overhead at this stage; no latency/storage saving is inferred from it.

## Catalogue and column-grant corrections — test first

The following E2E matrix and `tests/orion_pro_rds_readback_local.py` are written before the corresponding guards. They run only on an owned disposable loopback PostgreSQL18.6 database named `statarena_prod`. The reader's pinned transport is replaced inside the E2E process by a checked loopback transport using a local TLS certificate for the pinned hostname. All catalogue, identity, role and privilege SQL executes on real PostgreSQL. This transport is test-only; it proves no remote network/CA behavior and is not an option in the production CLI.

| Local action after an exact 012/013 bootstrap | Expected readback outcome |
|---|---|
| Golden catalogue and existing-role grants | All eleven readback cases pass |
| Existing privilege UNION evaluated on the golden PG18.6 catalogue | No WrongObjectType error; compare only applicable privilege functions per relation kind |
| Grant only `UPDATE(numeric_value)` to runtime | Runtime effective privilege case fails |
| Replace the native metric one-value CHECK with `CHECK(TRUE)` under the same name | Constraint definition case fails |
| Rebuild the named source HTTP dedup index on a different column, without its uniqueness/predicate | Index definition case fails |
| Drop `football.periods_current` | Exact relation/view case fails |
| Change an FK action while keeping its name, columns and parent | Constraint definition case fails |
| Remove `NULLS NOT DISTINCT` from a declared UQ without changing its name/columns | Constraint definition case fails |

The original reader is run first with no oracle arguments to retain the actual false-PASS RED baseline. The corrected reader requires an immutable expected-catalogue artifact and its digest, prepared by a distinct `--prepare-local` helper. Preparation applies the exact current migrations in an owned PG18.6 process, compares its migration journal, captures PostgreSQL-normalized definitions, closes the connection and removes only its owned cluster. The artifact binds model, compiler, integrity generator, migrator and SQL hashes plus preparation provenance/cleanup. Remote verification compares exact relation/view/sequence inventories, table column definitions, CHECK/FK/UQ/PK properties, complete index definitions and function/trigger definitions; physical byte sizes are observational and excluded from equality.

```sh
PYTHONPATH=/tmp/statarena-publication-test-python python3 tests/orion_pro_rds_readback_local.py --label catalogue-guards-red --baseline
PYTHONPATH=/tmp/statarena-publication-test-python python3 docs/verification/orion-pro-pilot-20261104/rds_catalogue.py --prepare-local --label reviewed-catalogue
PYTHONPATH=/tmp/statarena-publication-test-python python3 tests/orion_pro_rds_readback_local.py --label catalogue-guards-green
```

Each local run retains exact commands, captured code/SQL/model inputs and SHA-256, expected/actual readback cases, safe DDL/role-mutation descriptions, PostgreSQL logs, oracle and readback receipts, TLS setup and owned cleanup. No AWS/SSM call or remote SQL is performed. Initial RED and harness failures are retained and never counted as passing acceptance.

## Retained local outcomes

- `rds-readback-local-runs/20261104T190412243121Z-catalogue-guards-red/result.json`: first local run revealed a genuine golden-path `WrongObjectType 42809` in the sequence privilege UNION; the sequence branch lacked its relation-kind filter. The FK fixture initially searched only NO ACTION while the model uses RESTRICT. Both original failures and cleanup are retained.
- `rds-readback-local-runs/20261104T190511159318Z-catalogue-baseline-diagnostics/result.json`: corrected FK fixture and local-only SQL diagnostics exercised all eight workflows; the same sequence error remained. No guard success was claimed from this run.
- `rds-readback-local-runs/20261104T190551365193Z-confirmed-blind-spots-red/result.json`: after fixing only sequence-kind filtering, **golden and restored golden passed 11/11**. All six adversarial changes still returned an overall PASS, giving the required **two passed / six failed E2E assertions** before catalogue/column-grant guards were added.
- `rds-readback-local-runs/20261104T190937868865Z-catalogue-guards-green/result.json`: **8/8 E2E workflows pass**. Golden and restored golden readbacks pass 11/11. Column UPDATE, CHECK(TRUE), changed index, deleted view, changed FK action and changed UQ NULL semantics each fail their intended case. Every readback executes exactly **14 SELECTs** on the owned PG18.6 instance with actual local TLS. Both E2E and separate oracle clusters were stopped and their owned directories removed.

The reviewed oracle is `expected-catalogues/20261104T190938014223Z-catalogue-guards-green-oracle/expected-catalogue.json`, SHA-256 `b6adf85ed582866c435b6e64f01c59cc271488a2df1ba21958131961f8546610`. It captures 207 relations, 1,709 table columns, 1,476 constraints, 352 indexes and 174 integrity functions/triggers from the exact checked 012/013. Physical relation byte sizes are excluded from equality. Function/trigger signatures and definitions are also compared, so extra overloads do not collapse to a matching name.

The source files are frozen at the green run; no remote readback, RDS schema apply, AWS operation, source transfer, commit or publication was executed by this correction subtask. A current committed-source apply receipt is still required by the remote command. Suggested commit: `fix: detect schema and column privilege drift in RDS readback`.
