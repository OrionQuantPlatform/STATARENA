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
