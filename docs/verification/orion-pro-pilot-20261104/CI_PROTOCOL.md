# Local PostgreSQL CI contract

Suggested commit: `ci: exercise the approved Orion Pro pilot without cloud access`.

The `orion-pro` job in `.github/workflows/verify-ingestion.yml` runs the already written E2E contracts on an owned disposable PostgreSQL 18.6 instance. It receives no AWS, provider or production database secrets. The real-source importer is deliberately outside this source-free job. This document records the workflow expectations before the first remote CI run; it does not report a pass.

| Input or failure | Expected outcome |
|---|---|
| Missing original approved Git model or changed amendment chain | Model gate fails; no remote connection |
| Wrong PostgreSQL version or unavailable local binaries | Setup fails, evidence and logs uploaded |
| Schema, bootstrap, revision, publication or role regression | Corresponding local workflow fails with SQLSTATE/output; owned server is stopped |
| Null/absent/zero/empty string/false regression | Native metric E2E fails; original approval and actual applied SQL remain inspectable |
| Offline RDS gate invokes AWS | AWS sentinel detects the call and fails the CLI E2E |
| Column write privilege, CHECK expression, FK/UQ property, index or current view drifts | The full local TLS readback rejects the changed catalogue; restored golden passes |
| Complete expected behavior | 23 schema workflows, 25 native-state workflows, seven offline CLI workflows and eight local TLS/readback workflows pass; actual counts come from retained result files |

The job uses `embedded-postgres@18.6.0-beta.19` on Linux x64, Python 3.13, Node 24 and the repository's Python requirements. Full Git commit history with filtered blobs makes the immutable approved plan commit available to the model gate. Sparse checkout contains the runtime, tests, certificates, model and evidence dependencies. No public deployment or RDS apply follows from a green job.

Rerun the GitHub job for the relevant commit, or run its four test commands locally with the platform's `--pg-bin` directory and an installed `--python-path`. Each E2E result records its exact command, inputs, applied SQL, expected/actual outcomes, logs and cleanup. The uploaded artifact is `orion-pro-<run-id>-<attempt>`; its original failures must be retained. The local TLS certificate/key are generated only inside the owned disposable cluster, then removed. CI latency is not production API latency or an RDS before/after benchmark.
