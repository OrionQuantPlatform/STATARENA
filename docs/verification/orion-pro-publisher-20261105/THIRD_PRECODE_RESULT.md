# Final authorized pre-code run — admission setup RED

Suggested commit: `test: prepare bounded PostgreSQL publisher workflow before implementation`.

Status: **P01 passed; setup remains blocked; STOP for ROOT review**. ROOT explicitly permitted this third attempt after the two earlier failures. No fourth attempt is authorized. No publisher product was implemented and no API/publisher process started.

Exact reproduction command, requiring the same local tools/dependencies as `WORKFLOW_RESULT.md`:

```sh
PYTHONPATH=/tmp/statarena-publication-test-python python3 docs/verification/orion-pro-publisher-20261105/publisher_workflow.py --label owned-pg-precode-red-third-final
```

Receipt: `runs/20261105T010836726415Z-owned-pg-precode-red-third-final/result.json`.
SHA256: `695d69984cc48961850f2ad768a1b4c102dd1f3c8bc4528c868ac8690b912f83`.
Elapsed2.055s including cleanup. Current oracle SHA256: `0c3950e4d278f75dd1868685509c94519d752b9d6de6f133b6d2feb0c3cb94ec`.

## Expected and actual

Expected: all five setup gates complete, then one real missing-CLI RED; P02–P29 remain unverified without duplicate error invocations. Actual: P01 completes, admission metadata raises `KeyError: 'revision_id'` before API export/start. The current phase therefore did **not** capture a new missing-CLI RED. The older cheap missing-CLI receipt is retained as historical evidence only.

The sole functional correction before this run was ROOT's requested identifier guard. Static validation confirmed94 unique canonical active names, all accepted by `(ingest|football|analytics)\.[a-z_][a-z0-9_]*`, and exact approved model SHA256. `snapshot()` separately verifies that SHA and exact list equality before composing SQL. Actual PostgreSQL then executed the94-table count/digest snapshot, build/pointer/dirty/sequence queries and connection-cap observation. P01 records94 tables and zero analytical outputs; the existing typed/output cardinality assertions passed. This closes the earlier identifier blocker.

The concrete new blocker is `typed_inputs.py`'s admission construction, which reads `coverage['revision_id']`. The approved model has no such column on `ingest.match_coverage`. Its exact primary key is:

```text
(match_id, source_id, feature_code, variant_key, recorded_from_gen)
```

Its revision-related columns are `data_revision` and `match_revision_id`. A faithful admission contract should bind that actual composite identity plus the relevant real revision values; replacing it with an invented surrogate revision is invalid. This contract/code correction is left unapplied for ROOT review. No schema or migration is needed or proposed to hide the harness error.

## Observed scope and limits

| Observation | Actual |
|---|---|
| PostgreSQL |18.6 / server_version180006, one owned loopback server |
| Schema | Exact approved012/013 and compact bootstrap; model103/94 active; no014 loaded |
| Input oracle |5 typed matches A3/B1/C1; distinct squad counts1/2/1; unused substitute played=false; dg3/cg2 |
| Build/publish hooks | Three builds and one publication suppressed; zero analytical outputs |
| Workflow case counts |1 pass (P01),0 failed cases,29 unverified; overall result FAIL from setup exception |
| HTTP / API / publisher |0 requests,0 API starts,0 publisher invocations |
| Operational SQL |7 reservations;6 actual PostgreSQL client commands after the application-name transition |
| Fixed setup SQL |213 server-logged client commands, separately accounted |
| Source changes during run |None |
| Cleanup | PG stopped, owned directory removed, no API/worker alive |

No API transport, actual writer/runtime ACL probe, worker/main8s/1s deadline calibration, source tripwire calibration, publication, concurrency or failure-recovery case was reached. Their functions/oracles exist before publisher implementation but are **unverified**. No acceptance claim is made for real sources, normalization, full parity, deployed behavior,014/107 or cloud.

All three run directories and their exact copied code/model/SQL inputs remain unchanged. `WORKFLOW_CHECKSUMS.json` remains the earlier two-run checkpoint (`e8b736384dbe1b47247175e177d538b940e0d2146c7aa6d4474a8b391f062e4b`); its old current-oracle entry is historical and corresponds to the copies inside those two receipts. `THIRD_PRECODE_CHECKSUMS.json` pins the current corrected oracle, all current harness/review files and all three receipts. The original preparation manifest `FINAL_CHECKSUMS.json` is unchanged. No product publisher, reader, guard, model,012/013, framework, Git/CI/WORKLOG or remote state was modified in this phase.
