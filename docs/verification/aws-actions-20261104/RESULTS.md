# AWS Actions migration results

The six workflow definitions now separate disposable CI from five production AWS jobs. Four stage or publish data. One observes rows already published for Villarreal–PSG. PitchAPI access remains on the two collection steps. The monitor reads the five required coverage categories and advanced availability from typed RDS tables with one query, a read-only transaction and a ten-second statement timeout.

| Metric | Before | After |
|---|---:|---:|
| Production workflow files referencing legacy database/storage repository secrets | 4 | 0 |
| Workflow paths that explicitly invoke the normalized RDS publisher | 0 | 4 |
| Direct PitchAPI requests per monitor poll | 6 | 0 |
| Production read-only monitoring queries per poll | 0 | 1 |
| Preregistered bootstrap/workflow/monitor checks passing | 0/14 | 14/14 |
| Preregistered runner network checks passing | 0/9 | 9/9 |
| Foreign test rules removed in duplicate and ownership-change scenarios | — | 0/2 |
| Newly created runner rules remaining after normal cleanup | — | 0/1 |

The corrected before-run uses the exact original workflow tree from 923bb0ff4a. The first harness attempt encountered an incorrectly shaped player fixture and a weak missing-script check. The first after-run passed 13 checks and exposed a test predicate that mistook a path filter for a credentials action. The retained before, before-corrected, after and final directories show each outcome. baseline-replay resolves the original files from Git on demand.

The local E2E used the AWS CLI against loopback SSM and EC2 protocol fixtures, and exercised the monitor against disposable PostgreSQL 18 with the materializer's typed records. A zero home score correctly qualified as a published score. Missing data kept monitoring active. A database connection failure produced a failed check and no stop output. The SSM access-denial case produced no partially populated GitHub environment file. All temporary credentials stayed within local fixtures.

The hosted-runner cases created exactly one tagged TCP/5432 IPv4 /32 in the simulated security group, revoked it by its rule ID and tolerated a repeated post. Three invalid IP cases produced zero EC2 calls. Wrong group/account cases stopped after discovery. A foreign duplicate produced no revoke and a changed description preserved the existing rule. Saving the unique ownership marker before creation allowed post to identify the exact rule even if the returned ID was lost.

## Review and rollout

The AWS inventory on 4 November 2026 showed no GitHub OIDC provider and no GitHub role. The repository had zero Actions variables and used immutable OIDC subjects. Its actual subject prefix was `repo:OrionQuantPlatform@188998341/STATARENA@1441213700`. The current RDS group contained three IPv4 ingress ranges on 5432. The regional SSM credentials use the AWS-managed SSM key. The staged bucket is statarena-football-333rosky-70db6e5f. No secret values are in the evidence.

1. Review actions-roles.yaml. CloudFormation ValidateTemplate accepted it. It creates a GitHub OIDC provider and two scoped roles in account 361769570630. The writer may read only rds-ingest and s3-ingest. The monitor may read only rds-runtime. Main and codex/aws-backend-20261104 are the exact allowed refs. The roles also check the repository ID and the relevant workflow name. Remove the migration branch from trust after rollout. Branch protection governs which trusted code may run under these names. AWS documents these condition keys in its [IAM OIDC reference](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_iam-condition-keys.html).
2. Set repository variable STATARENA_AWS_INGEST_ROLE_ARN to the IngestionRoleArn output and STATARENA_AWS_MONITOR_ROLE_ARN to MonitorRoleArn. The existing PITCHAPI_API_KEY remains scoped to source collection. The staging implementation receives compatibility environment names populated only from AWS. The optional STATARENA_AWS_RUNNER selects another runner label. A self-hosted runner must have its own authorized RDS network path.
3. On hosted runners, the post action is registered after AWS authentication and before credential cleanup. Six-hour role sessions cover the longest 330-minute timeout. Both roles can inspect regional group/rule metadata and authorize/revoke ingress on only sg-0667c20e8ff5d2431. Rule creation requests carry the ManagedBy=statarena-actions tag. The action enforces the protocol, port, public IPv4/32, owner description, account, group and exact rule ID. AWS authorizes revoke on the group resource, so these per-rule checks live in the action. Protect the trusted workflow/action sources accordingly. [EC2 authorization metadata](https://servicereference.us-east-1.amazonaws.com/v1/ec2/ec2.json)
4. If a hosted VM disappears before post can run, review leaked tagged rules against their GitHub run/attempt/job in the unique description. Confirm the run ended, the rule still matches the account/group, TCP 5432 and exact /32, then revoke only that verified rule ID. The action never deletes rules based only on source IP. No schedule or global purge is added.
5. First activate after dashboard/scripts/relational_materialize.py and its migrations land together. Check that the ingest database identity can apply the intended schema migrations and the monitor identity has read grants on the new tables. Run the controlled rematerialize workflow, inspect its receipt, then verify publication and removal of the temporary runner rule. The local tests and template validation do not establish live OIDC, RDS ingress, DDL grants, or completed publication.

The first hosted release kept the legacy concurrency group. The four migrated writers now share the dedicated AWS queue. See the [cutover protocol](concurrency/PROTOCOL.md). queue: max is supported by GitHub and preserves pending work. actionlint 1.7.12 reports only its four unsupported queue keys, as recorded in actionlint.log. Narrowly ignoring that diagnostic leaves zero lint diagnostics. [GitHub concurrency documentation](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency)

## Rerun

See PROTOCOL.md for prerequisites. Both baseline commands intentionally exit nonzero.

```sh
node docs/verification/aws-actions-20261104/run.mjs baseline-replay
node docs/verification/aws-actions-20261104/run.mjs final
python3 docs/verification/aws-actions-20261104/ingress_e2e.py ingress-before
python3 docs/verification/aws-actions-20261104/ingress_e2e.py ingress-after
aws --profile statarena --region us-east-2 cloudformation validate-template --template-body file://docs/verification/aws-actions-20261104/actions-roles.yaml
actionlint -shellcheck= -pyflakes= -ignore 'unexpected key "queue" for "concurrency" section' .github/workflows/*.yml
```

Suggested commit: `feat: run ingestion and relational publication on AWS through scoped GitHub roles`

## Relational CI coverage

The Verify ingestion workflow adds a separate, ten-minute relational job. Backend services, migrations, worker code, frontend data loaders and checked-in fixtures trigger it. It installs Node 24, Bun 1.4.4, the frozen dashboard dependency graph, the pinned Python worker dependencies, and disposable embedded-postgres 18.6.0-beta.19. Its token has contents:read. The five suites use loopback PostgreSQL, checked-in inputs and local HTTP. The existing CI job still verifies daily ingestion and AWS bootstrap/runner behavior.

The before/after CI definition gate improved from 0/9 to 9/9. The local replay passed 16 publisher workflows, five core SQL workflows, ten core HTTP checks, 63 match HTTP requests, 65 catalog HTTP requests, and equality on 1,880 support projection keys. The catalog job uses the recorded HTTP fixtures. The separate 537-input full-source size audit remains a dedicated audit. Local replay used the installed Mac tools; remote Linux CI results belong to the subsequent push.

The first replay exposed two setup errors documented in ci-first-replay. The captured match and catalog suites needed the actual checkout for commit provenance. The support suite needed the explicit loopback test-database flag. capture_ci.py now supplies both, runs each suite from a fresh fixture copy and collects only a newly generated report. CI uploads fresh reports, SQL/HTTP logs and the runner status on failure or success.

From repository root after installing the tool dependencies above:

```sh
python3 docs/verification/aws-actions-20261104/ci_contract.py ci-after
node docs/verification/aws-rematerialize-20261104/run.mjs ci-replay
STATARENA_TEST_PYTHONPATH=/tmp/statarena-publication-test-python STATARENA_CORE_API=1 STATARENA_CORE_EVIDENCE=docs/verification/aws-actions-20261104/local-replay/core bun dashboard/scripts/verify_relational_core.mjs
PYTHONPATH=/tmp/statarena-publication-test-python STATARENA_TEST_TOOLS=/tmp/statarena-cache-test-tools python3 docs/verification/aws-actions-20261104/capture_ci.py match
PYTHONPATH=/tmp/statarena-publication-test-python STATARENA_TEST_TOOLS=/tmp/statarena-cache-test-tools python3 docs/verification/aws-actions-20261104/capture_ci.py support
PYTHONPATH=/tmp/statarena-publication-test-python STATARENA_TEST_TOOLS=/tmp/statarena-cache-test-tools python3 docs/verification/aws-actions-20261104/capture_ci.py catalog
```

Suggested commit: `ci: verify relational publication and AWS backend HTTP contracts`
