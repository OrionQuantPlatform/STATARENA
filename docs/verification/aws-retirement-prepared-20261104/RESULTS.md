# Prepared AWS retirement patch

The detached review patch applies to `887b560bf767993c989ab0631018b16490a70cb1`. Applying it to a separate Git index reproduced the verified tree `3782079dabb9026ef184075bce39e1c1f4e6d114`. The patch contains 63 changed paths, totals 253,462 bytes, and has SHA-256 `aa65a25166ba97c94357842f1e9fef2c88ca05787d6d7e92c397999d3711f6b8`. [Review patch](/tmp/statarena-aws-retirement-prepared-20261104.patch) · [Independent apply, checksums and affected definitions](review.json) · [Path inventory](patch-files.tsv)

Only the private detached worktree at `/tmp/statarena-aws-retirement-prepared-20261104` contains the candidate product changes. Activation still requires full AWS acceptance. The original dirty worktree and original patch were preserved. The prior patch has SHA-256 `243622bc4b07903c63dc579e51061b1e1703da173e3f26875a2efa36a5a0794d`. No live provider, production database, storage, deployment or Git branch was modified.

## Integration

Two paths had also changed between original base 2c4ac0c06a and the current base. Three-way application cleanly retained the current materializer and the Actions verification harness. The former’s existing capacity guard, schema installation, logical SHA handling, bounded discovery, source preparation, batching, partition writes and global publication functions remain identical to 887b560bf7. The patch changes `run` and `main` and adds `collector_plan`. Across 175 sensitive paths, all SQL migrations, typed read DAOs, wire handling, browser implementation and deployed workflow definitions retain the baseline contents. [Apply log](apply.log) · [Review](review.json)

Two compatibility issues required small corrections during replay.

* The old retirement bootstrap exported the ingest writer DSN under both `DATABASE_URL` and `INGEST_DATABASE_URL`. The candidate now exports `DATABASE_URL` only in runtime mode and `INGEST_DATABASE_URL` only in ingest mode. The four ingest workflow jobs keep their current shared writer concurrency and SQL cap. Only the runtime monitor consumes `DATABASE_URL`. Common TLS settings and the CA certificate remain available. [Failing role check](bootstrap-before.json) · [Final 14 checks](bootstrap.json)
* The original competition render fixture lacked the performance and comparison state that the latest frontend expects. The fixture now supplies empty performance and comparison rows and the actual catalog. The current UI code remains untouched. [Initial failure](frontend-fixture-before.log) · [Three passing bootstrap workflows](frontend.log)

The first standalone build overlapped the bootstrap test’s own Next build and hit the build lock. The archive browser test completed successfully during that run. The final standalone build and the corrected bootstrap suite both completed when run sequentially. Original three-way application reported 35 trailing-whitespace lines in historical verification logs. The logs are retained verbatim.

## Verification

| Workflow | Result |
|---|---|
| Four worker entry points on loopback PostgreSQL 18.6 and disk-backed S3rver | 10 checks passed. Worker parsing preserved gzip, immutable versions, nested envelopes and metadata. Deterministic provider fixtures exercised supplemental, UEFA and coach updates. [Worker](worker.json) |
| Standalone collector and package aliases | Scoped history published only its league’s two pending seasons. Daily mode kept the two priority slots and 20 ordinary jobs. Pulse preserved priority order. Explicit staging-only remained pending until default history publication. Missing writer config and invalid hosts failed closed. [Worker and queue ordering](worker.json) |
| Ordinary publisher and isolated bootstrap | 16/16 publication cases and 14/14 AWS role/workflow checks passed. [Publisher](ordinary.json) · [Bootstrap](bootstrap.json) |
| Current typed core and HTTP entry point | Five publisher cases and ten HTTP checks passed, including rollback, record and cursor behavior and read-only/fail-closed configuration. [SQL](core.json) · [HTTP](http.json) |
| 009 migration on durable source corpus | Eight checks passed on 411,416 source metric rows, including 221,906 half and 189,510 player rows, resource digests, concurrent reads and rollback. [Full corpus](metric-corpus.json) |
| Current compact/default wire format | Disposable HTTP parity, native types, missing fields, reserved property names, invalid format and conditional HEAD/GET passed. [Wire](wire.json) |
| Production Next, archive and competition flows | Production build passed, the browser rendered the fixture archive via the AWS API contract, and three bootstrap/selector/schedule checks passed. [Build](next.log) · [Archive](next-archive.json) · [Competition](competition.json) |
| Daily collector scheduling | Seven existing refresh cases passed. [Result](daily.log) |

## Reproduction

Use a separate worktree. The commands below describe review and local tests. They do not activate the patch. The original local tools are embedded-postgres 18.6.0-beta.19 at `/tmp/statarena-archive-remat-pg`, its Python target with psycopg/boto3/PyYAML, and s3rver 3.7.1 at `/tmp/statarena-js-worker-s3-20261104`. Existing Playwright CLI and Chromium are used by the bootstrap browser case.

```sh
git worktree add --detach /tmp/statarena-retirement-review-copy 887b560bf767993c989ab0631018b16490a70cb1
cd /tmp/statarena-retirement-review-copy
git apply --check /tmp/statarena-aws-retirement-prepared-20261104.patch
git apply /tmp/statarena-aws-retirement-prepared-20261104.patch
(cd dashboard && bun install --frozen-lockfile)
export STATARENA_TEST_TOOLS=/tmp/statarena-archive-remat-pg
export STATARENA_TEST_PYTHON=/tmp/statarena-archive-remat-pg/python
export STATARENA_TEST_PYTHONPATH="$STATARENA_TEST_PYTHON"
export PYTHONPATH="$STATARENA_TEST_PYTHON" AWS_EC2_METADATA_DISABLED=true
bun docs/verification/aws-legacy-retirement-20261104/verify.mjs after
bun docs/verification/aws-actions-20261104/run.mjs retirement-prepared
bun docs/verification/aws-rematerialize-20261104/run.mjs retirement-prepared
(cd dashboard && bun run verify)
node docs/verification/aws-compact-metrics-20261104/run.mjs retirement-prepared
STATARENA_CI_EVIDENCE=docs/verification/aws-actions-20261104/retirement-wire bun docs/verification/aws-wire-pages/disposable.mjs --ci
python3 -m unittest discover -s tests -p test_daily_refresh.py -v
(cd dashboard && bun scripts/verify_competitions_render.jsx)
node --test tests/dashboard_bootstrap.test.mjs
(cd dashboard && NEXT_PUBLIC_API_ORIGIN=http://127.0.0.1:18947 bun run build)
```

The source fixture intentionally rejects provider URLs without recorded inputs, preserving the earlier successful observations. These local runs do not establish coverage of a fully published production dataset. Historical migration utilities and archived evidence still contain their original Neon names; the candidate removes the active website’s alternate runtime and requires explicit AWS staging credentials for collectors.

## Exit and receipt provenance

The [phase manifest](phase-manifest.json) pairs the original logs, exit codes, UTC file timestamps and SHA-256 hashes for these runs.

| Workflow | Initial result | Final result |
|---|---|---|
| AWS role bootstrap | 13/14, child exit 1, printed as `red=1`. No separate red exit file was created. [Initial log](bootstrap-before.log) | 14/14, exit 0 at 05:40:58 UTC. This was the corrected bootstrap run within the parallel batch. The later copy of the JSON is byte-identical to that run’s original output. [Final exit](bootstrap.exit) · [Result](bootstrap.json) |
| Standalone Next build | Concurrent build lock, exit 1 at 05:40:53 UTC. Both original files were renamed before retry. [Initial log](next-overlap-before.log) · [Initial exit](next-overlap-before.exit) | Sequential build exited 0 at 05:41:45 UTC. [Final log](next.log) · [Final exit](next.exit) |
| Frontend bootstrap and fixture | Missing performance data, 2/3 passed, exit 1. [Initial log](frontend-fixture-before.log) | Final fixture run passed 3/3 and exited 0 at 05:43:09 UTC. Its log replaced an intermediate successful replay. [Final log](frontend.log) · [Final exit](frontend.exit) |

Reconciliation used only existing receipts. The private patch SHA-256 remains `aa65a25166ba97c94357842f1e9fef2c88ca05787d6d7e92c397999d3711f6b8`.

## Parent review

The parent reviewed the runtime entry, TLS/fail-closed connection selection, explicit staging configuration and collector publication bounds. An independent run through the candidate `app.js` passed all five isolated PostgreSQL publisher workflows and all ten actual HTTP cases. Its intentional database-failure health503 remains in the log and is an expected case. No active application or deployment was changed. [Parent SQL/HTTP](parent-core/http.json) · [Publisher](parent-core/results.json).

Exact parent rerun from the detached worktree:

```
STATARENA_CORE_API=1 STATARENA_CORE_EVIDENCE=/tmp/statarena-aws-backend-20261104/docs/verification/aws-retirement-prepared-20261104/parent-core bun dashboard/scripts/verify_relational_core.mjs
```

The generic runner receipt omits STATARENA_CORE_API from its generated command; the command above retains the actual flag used for the ten HTTP cases. [Durable review patch](retirement.patch) is a byte-identical copy of the isolated patch, retained for later review and replay; storing it here does not apply it. Its hash and future activation gate remain unchanged.
