# Typed worker credential boundary

Prepared before the new `typed-ingest` mode exists. The mode must load only the existing `/statarena/app/rds-ingest` SecureString and export the seven canonical RDS/TLS variables, never storage credentials or historical Neon/raw-document aliases. It pins the existing RDS endpoint,5432,statarena_prod,statarena_ingest. Existing ingest/runtime modes remain temporary compatibility paths for currently disabled workflows; no workflow is activated or dispatched.

End-to-end harness: real bootstrap CLI process → real AWS CLI v2/SigV4 → owned loopback SSM protocol fixture → private GitHub environment file → inspection/cleanup. AWS responses and credentials are synthetic declared fixtures. No live AWS/OIDC/RDS/provider connection is made. This verifies process/service-protocol/output behavior, not live IAM, database ingestion or scheduled collection.

Failure matrix, before implementation:

| Case | Expected result |
|---|---|
| New typed mode with valid existing endpoint/role | One decrypted rds-ingest request, seven canonical variables, credential URL encoding round trips, verify-full and CA valid; no S3 or legacy variables |
| Different valid-looking RDS host | Refuse, one metadata request, empty env |
| Wrong database | Refuse, empty env |
| Wrong port | Refuse, empty env |
| Wrong actor in ingest parameter | Refuse, empty env |
| SSM denial | Refuse, empty env |
| Non-SecureString response | Refuse, empty env |
| Unknown mode | Refuse before any SSM request |
| Existing ingest positive control | Existing two-parameter compatibility output retained |
| Existing runtime positive control | Existing one-parameter read-only output retained |

All visible log lines except intentional GitHub add-mask directives must omit synthetic secrets. Raw credentials/env files remain private temporary inputs and are removed. Retain only redacted outcomes, parameter names/counts, exported variable names, exact inputs/source hashes and cleanup. Before-code run stops on the first genuine missing-feature failure and preserves remaining cases unverified. After implementation execute the same tests. Max10scenarios/12SSMrequests/180s,one owned HTTP fixture at a time, no PostgreSQL, retries or cloud access.

Rerun: `python3 docs/verification/orion-typed-worker-20261105/e2e.py --label <label>`.

Commit suggested: `feat: add RDS-only typed ingestion worker credentials`.
