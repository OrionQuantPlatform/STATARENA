# AWS Actions verification protocol

Prepared before workflow/helper edits, from 923bb0ff4a. Compare the same checks before and after. Run the real AWS CLI against a loopback SSM HTTP server with disposable credentials. Write GitHub environment and output files in a temporary directory. Inspect only redacted results. Exercise the monitor against disposable PostgreSQL 18. No remote configuration changes or workflow dispatch.

| Scenario | Expected observable result |
|---|---|
| Ingest bootstrap | Reads only rds-ingest and s3-ingest using WithDecryption. Percent-encoded DSN round trips credentials and enforces verify-full. CA valid. S3 restricted to staging worker inputs. |
| Reader bootstrap | Reads only rds-runtime. Exports DATABASE_URL, CA, AWS provider and pool max 1. No storage credentials. |
| Malformed host/database or SSM denial | Nonzero exit, empty environment file, no secret disclosure. |
| Monitor without rows / with complete typed rows | Stays active / reports completion, accepts zero scores, no provider requests. |
| Monitor unavailable DB | Fails without marking completion. |
| Scheduled collection | RDS staging first, --skip-materialize, then named relational publisher after all successful stages. Existing schedule/queue preserved. |
| Explicit rematerialize | One shared publication command, verified TLS, bounded minutes/batch and opt-in --all. |
| UEFA refresh | Existing upstream checks, staging and relational publication. Verification job has no production authority. |
| Pull request verification | Disposable PostgreSQL same major as RDS. No credentials, OIDC, or production writes. |
| Workflow principal | OIDC on AWS jobs only, trusted repo/ref, scopes separated; production roles and provider inventory reported separately. |
| Shutdown fixture | Explicit test still requires no provider, DB, or AWS call. |

Rerun from repo root with aws CLI v2, PyYAML 6 and node available. Install via `bun add --cwd /tmp/statarena-cache-test-tools embedded-postgres@18.6.0-beta.19` and `python3 -m pip install --target /tmp/statarena-publication-test-python 'psycopg[binary]==3.3.7' PyYAML` if needed.

```sh
node docs/verification/aws-actions-20261104/run.mjs after
```

The pre-change phase intentionally fails. Helpers and workflow sources missing required behavior produce explicit failures. Both phases store setup, assertions and redacted logs. OIDC issuance, live IAM trust, GitHub-hosted runner connectivity and live SQL publication require deployment verification.

## Hosted runner network admission

Added before the network action. Execute the real Node entry/post command as separate processes with real AWS CLI v2 against disposable loopback EC2 Query API responses. Inject only the public address lookup through a Node test preload. Validate IPv4/32, TCP 5432, fixed Ohio SG/account, confidence about ownership before cleanup, and post idempotence. Model foreign preexisting rules and changed owned descriptions. Both cases must preserve every foreign rule. Test malformed/private addresses, mismatched group/account and duplicate ownership. A runner killed before GitHub can execute post requires explicit reconciliation using its saved run marker.

## Relational backend CI

Before enabling the relational job, inspect its actual YAML steps for the full publisher, core HTTP entry points and captured detail/support/catalog suites. An omitted worker, frozen Bun install, disposable database pin, qualifying source path, artifact, or credential isolation guard fails the static coverage receipt. Locally replay the same suites and retain their exit codes, logs and reports. A failed suite must fail CI and artifact upload must still run. AWS credentials and live provider calls are excluded. Remote GitHub runner results belong to the subsequent push.
