# RDS schema and bootstrap gate — 4 November 2026

This failure matrix and `tests/orion_pro_rds_gate.py` precede the wrapper implementation. Only the parent agent may execute a remote apply. This agent executes offline gates and read-only preflight. Suggested commit: `feat: add guarded Orion Pro RDS pilot gate`.

The allowed remote scope is **schema_and_bootstrap_only**: deterministic 012/013, six periods, four positions, their sealed generation/contracts, journal entries, and grants to the existing `statarena_ingest` and `statarena_runtime` roles in `ingest`, `football`, `analytics`. There is no provider collection, source transfer, real-data import, publication, source deletion, remote rollback, new role/resource, resize, parameter/security-group change, S3 write or public cutover. A local toy workflow does not prove full migration or source fidelity.

## Failure matrix written before code

| Gate / input | Expected observable outcome |
|---|---|
| Missing wrapper | E2E records RED and the exact missing entry point before implementation; dependent cases unverified |
| `--plan` with an AWS sentinel executable | No AWS/SQL call; deterministic model/SQL/grants hashes and current blockers in JSON |
| Contradictory modes / malformed digest | Reject before cloud/SQL/secret access; sanitized JSON or argparse error |
| `--check-apply` without acceptance or fresh receipt | Offline rejection; no AWS/SQL/secret access; this mode never applies |
| Untracked/modified relevant execution/model/approval/SQL source, non-main, HEAD not current origin/main | Apply blocked; unrelated numbered copies do not block read-only preflight and are not changed. GitHub branch-protection policy is observed, not changed or made an extra requirement |
| SQL differs from pure compiler; approval/amendment chain differs | Apply blocked before connecting; original approval is retained |
| Missing/stale/wrong-scope acceptance; mismatched model, commit, evidence or applied SQL hashes | Apply blocked; require current 23-case SQL, 25-case metric and candidate 9-case real-core local acceptance, verified journal SQL, and parent acceptance receipt |
| Wrong account/profile/region/instance/host/database/PG18.6/64GiB, pending change or unavailable instance | Preflight records observed safe metadata and blocks apply |
| Missing/stale CloudWatch samples, free storage <8GiB, CPU >=80%, credits <1 | Preflight blocks apply; observations are not a causal performance benchmark |
| TLS not verify-full/SSL, missing CA, unexpected database role or unsafe existing role privileges | Reject; `.pgpass` is used indirectly for reads, no credentials printed or stored |
| Target namespace partially exists or target journal differs | Reject; only all three absent or all three present with exact 012/013 checksums and bootstrap-only state may proceed |
| Active write-capable transaction or advisory worker/migration lease | Block; stale workflow markers alone are not leases; no session is cancelled |
| Receipt older than 10 minutes, wrong expected hashes/commit/plan or changed relevant source | Offline check rejects; apply also performs a fresh read-only preflight in-process |
| Parent-reviewed apply after all gates | One advisory-locked atomic transaction; recheck target/roles; apply scoped DDL and bootstrap; journal checksums; existing roles only; no remote reset path |
| SQL/privilege/lock failure during apply | Transaction rolls back; sanitized error type/SQLSTATE; no PostgreSQL row detail or DSN in evidence |

## Setup and exact reruns

Use the existing `aws --profile statarena --region us-east-2` CLI session for account `361769570630`. Read-only DB access uses libpq's existing password file without opening or copying it. Endpoint is `statarena-postgres.clcy2iqyajbl.us-east-2.rds.amazonaws.com`, database `statarena_prod`, CA `dashboard/backend/certs/rds-us-east-2.pem`, TLS `verify-full`. No credential is accepted in arguments. Apply retrieves the existing `/statarena/app/rds-admin` SecureString privately in process only after every offline gate and fresh read-only preflight passes.

```sh
python3 tests/orion_pro_rds_gate.py --label missing-wrapper-red
python3 tests/orion_pro_rds_gate.py --label offline-gates
python3 dashboard/scripts/orion_pro_rds.py --plan --label review
python3 dashboard/scripts/orion_pro_rds.py --preflight --label before-parent-review
```

Default invocation is read-only `--preflight`. `--plan` and `--check-apply` perform no network I/O. Actual `--apply` requires an explicit acceptance file, fresh preflight receipt and its SHA-256, and explicit expected commit/model/012/013 hashes. It is deliberately not run by this subtask. The parent must review code and emitted plan first.

Parent acceptance JSON contract: `status=accepted_for_schema_bootstrap`, `remoteScope=schema_and_bootstrap_only`, `commit`, `modelSha256`, `migrationSha256={012:…,013:…}`, and `evidence={sql,metrics,source}` each containing a repository-relative `path` and `sha256`. Evidence files must be actual passing current-model E2E results, not hand-created success summaries. Acceptance may be generated after the source commit; its hash, and all evidence hashes, are recorded in the gate receipt.

## Evidence and limits

Every E2E/preflight stores timestamp, exact safe command, setup, expected/actual gates, source/model/SQL/receipt hashes, safe AWS response projections, query text and bounded metadata outputs, counts, timing and exit state. No raw football source rows, password, DSN, decrypted SSM response, CLI credentials or network IP is saved. AWS/DB exceptions expose error type and SQLSTATE only. Preflight is capped at 20 read-only SQL statements and bounded CLI reads for this one account/region/instance. Apply is a separate explicit mutation and is never represented as a read-only run.

Capacity samples and catalogue checks describe one instant. The wrapper cannot establish full source reconciliation, production collector adaptation, browser/cache parity, WAL/performance gains, cleanup safety, or final AWS cutover. All original RED/failure receipts remain inspectable.

## Recorded outcomes

- `rds-gate-runs/20261104T183847546745Z-missing-wrapper-red/result.json`: initial RED before implementation, one failed prerequisite and six unverified cases. The wrapper was absent; test and protocol inputs were captured.
- `rds-gate-runs/20261104T184252493798Z-offline-gates/result.json`: first implementation, six passed and one failed. The tampered-receipt rejection occurred, but its blocker name did not expose the intended digest failure. The original failure remains; the implementation's reporting was corrected.
- `rds-gate-runs/20261104T184607311991Z-reviewed-offline-gates/result.json`: **7/7 CLI workflows pass** against the reviewed implementation. AWS sentinel saw zero calls; no `--apply` invocation occurred. Remote apply and existing-journal target-state behavior remain unexecuted.
- `rds-runs/20261104T184340163531Z-readonly-initial/result.json`: actual read-only preflight, seven SELECTs and three bounded AWS read calls. Expected account/profile/region, endpoint, PG18.6, micro/64GiB, `pending={}`, TLS, safe existing roles, source namespaces and absent target namespaces passed. No active transaction or advisory lease was found. Free storage was 50,498,281,472 bytes, latest CPU 5.525%, and CPU credits 59.455. The receipt was **blocked**, correctly, by uncommitted relevant source and missing parent acceptance; it was not a ready-to-apply acceptance.
- `rds-runs/20261104T184647860612Z-readonly-reviewed-default/result.json`: actual default-mode preflight, eight SELECTs, zero remote writes. The additional write-lock check passed; targets remain absent. It was **blocked** by uncommitted source, missing parent acceptance, an older-than-five-minutes credit sample and an active `statarena_ingest` source-pilot transaction (32s, `idle in transaction`). No advisory or write lock was present. The source pilot itself reads remotely, but preflight conservatively treats any transaction held by a write-capable role as a blocker. It cancels nothing. Refresh after the source E2E ends and a fresh credit sample arrives.

This subtask used **15 remote read-only SQL statements total** and stopped within its 20-query budget. It executed no remote apply, SSM secret retrieval, resource mutation, source import, publication or cutover. The parent must review the wrapper and create the explicit current-source acceptance before any apply.

## Admin parameter adaptation — test first

The parent's first apply stopped before opening its admin connection or attempting any write because the existing admin parameter has historical instance metadata: keys `database`, `password`, `security_group`, `username`, with no `host`. Its database label is `statarena`; the approved connection target remains the separately verified constants HOST and `statarena_prod`. The parameter is not changed and grants/network/resources are not widened.

This matrix and `tests/orion_pro_rds_apply_local.py` precede the adaptation. The E2E invokes the actual `apply_schema_bootstrap` function with a fully fake in-memory SSM response, an owned PG18.6 database, real local TLS and a checked loopback transport. It never invokes the remote `--apply` CLI or a real AWS/SSM/RDS service. Fake password values stay in memory. TLS key material exists only in the owned temporary cluster and is removed at cleanup; no key or parameter value is copied to evidence.

| Case / action | Required outcome |
|---|---|
| Historical SecureString: exact admin username, known historical database, absent host | Full 94-table 012/013 transaction, journal/bootstrap/grants; connection still uses fixed HOST + statarena_prod |
| Current target database, absent/exact host; historical database with exact host | Accept the same instance credential; preserve fixed connection target |
| Non-SecureString, non-object JSON, unknown/missing database, different/missing username, contradictory/null host, empty/non-string password or unknown key | Reject before any admin connection or DDL |
| First successful local apply followed by independent readback | Eleven readback cases pass, exactly 14 read-only SELECTs; exact catalogue and bootstrap binding |
| Repeat application on the exact journal/bootstrap | No new migration or generation, ten seeds preserved, bootstrap reused; independent readback still passes |
| Existing target table inventory uses the dict returned by active_tables | RED captures the invalid string indexing first; compare its key set after the bounded fix |

```sh
PYTHONPATH=/tmp/statarena-publication-test-python python3 tests/orion_pro_rds_apply_local.py --label historical-admin-red
PYTHONPATH=/tmp/statarena-publication-test-python python3 tests/orion_pro_rds_apply_local.py --label historical-admin-green
python3 tests/orion_pro_rds_gate.py --label historical-admin-offline-gates
```

Receipts retain only parameter key/type shape, expected/actual outcomes, input code/model/SQL hashes, actual local journal/bootstrap/readback, safe operation counts, exact rerun, PostgreSQL logs and owned cleanup. Local receipt fields named `remoteWrites` originate from the wrapper API but are explicitly marked as owned-local execution; the E2E envelope records zero real remote writes. The account/instance preflight remains a separate parent gate and is not claimed from this local test. Suggested commit: `fix: validate existing instance admin credentials without changing RDS targets`.
