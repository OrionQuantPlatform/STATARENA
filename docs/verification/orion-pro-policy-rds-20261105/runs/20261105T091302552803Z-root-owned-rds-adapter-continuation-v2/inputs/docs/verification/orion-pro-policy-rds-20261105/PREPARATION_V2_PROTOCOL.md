# Reviewed v2 preparation — no PG release

ROOT approved F01–F05, a NEW private-passfile guard, a private shared transition core and conservative cleanup. This preparation authorizes no PG/cloud/SSM/RDS/source/RAM call and creates no actual continuation release/ledger. Original ledger3d65/attempt1receipt520d/manifest2a4d/archived inputs and19protected inputs remain exact. Suggested commit: `fix: qualify exact RDS policy metadata and private authentication`.

Chronology: auth_guard_e2e.py and AUTH_GUARD_PROTOCOL were written first; the actual missing-guard RED is0pass/1fail/14unverified without PG. Then the complete E2E was amended before product corrections: raw-contract/marker symlink CLI negatives; actual CREATEDB flag and role-membership mutations via verified owned OS-superuser only; unknown777/099 chains,014journal/P0body,014body/P0journal, old/newNULLclock negatives. F01setup and F02/F03synthetic display_name fixtures are corrected in that harness. V2_BEFORE_PRODUCT.json binds these bytes while the product guard is still absent. No isolated tests are added later for the existing SQL path.

Product corrections: Q04 captures t plus n and filters both only for historical1476comparison; raw leaf lstat precedes resolve in artifact/marker gates. New validated_rds_passfile checks only metadata (raw regular0600/currentUID leaf, raw0700/currentUID nonsymlink parent, absolute dedicated ORION_RDS_PASSFILE; all PG* refused). Remote explicitly supplies passfile before DNS/driver, no home/SSM/secret-CLI fallback. Its same physical-file cases run standalone source-free and later inside full20-case E2E. WrongUID stays explicitly unisolated if OS cannot provision a sole-wrong-UID file.

Fixed one-function/journal/fault/ack statements move unchanged into private _transition_core; the strict owned wrapper/public API remain the only writable entry point. No remote apply mode or shared local/RDS acceptance is added. Eventual ROOT RDS wrapper must enforce its own target/auth/release/native contract and then reuse that core; none exists now. Cleanup deletes the private PG parent only after stop/removal are proved; otherwise it records retained location/failed status. Cleanup-failure branch remains unqualified without a fault test; normal cleanup requires later actual PG proof.

## Exact future continuation inputs

Revised full E2E refuses before any PG unless all three explicit flags are supplied: --continuation-release <BASE/ROOT_LOCAL_CONTINUATION_V2.json>, --expect-continuation-sha256 <actualSHA>, --ledger <BASE/campaign-v2.json>. Both files must be regular raw files at exactly those paths. Neither file is produced by preparation or by the E2E itself.

The future ROOT release schema is:

```text
kind: rds_policy_owned_continuation_release_v2
authorizedBy: ROOT
scope: source_free_owned_only
parentSha256: {campaign: original3d65…, result: original520d…, manifest: original2a4d…}
codeSha256: {repo-relative e2e.py: frozenSHA, adapter.py: frozenSHA, auth_guard_e2e.py: frozenSHA}
inputsSha256: exact INPUTS.json SHA
expectedCases: exact20 CASES in e2e.py
expectedAuthCases: exact15 CASE_NAMES in auth_guard_e2e.py
limits: exact LOCAL_LIMITS in e2e.py
ledgerPath: docs/verification/orion-pro-policy-rds-20261105/campaign-v2.json
```

ROOT's new ledger must contain exactly kind=rds_policy_owned_campaign_v2, state=unstarted, pgStarts=0, maximumPgStarts=1, releaseSha256=<that actual release SHA>, parentCampaignSha256=<original3d65…>, limits=<same exact LOCAL_LIMITS>. It is a new authorization/counter, never an old-ledger reset. All future claim/finalization writes select only that v2 path and check the original evidence. Missing/mismatched/consumed inputs refuse before PG.

Future command shape (not executed):

```text
PYTHONPATH=/tmp/statarena-publication-test-python python3 docs/verification/orion-pro-policy-rds-20261105/e2e.py --label owned-rds-adapter-continuation-v2 --pg-bin /tmp/statarena-cache-test-tools/node_modules/@embedded-postgres/darwin-arm64/native/bin --continuation-release docs/verification/orion-pro-policy-rds-20261105/ROOT_LOCAL_CONTINUATION_V2.json --expect-continuation-sha256 <ROOT-issued-SHA> --ledger docs/verification/orion-pro-policy-rds-20261105/campaign-v2.json
```

One future owned TLS PG18.6/≤2DB/600s,8s statements/1s locks,8GiB hard/7GiB soft disk,32MiB metadata/64MiB evidence/512MiB temp. ROOT coordinates its slot with dense validation. Complete20cases plus required auth subcases, exit0, native preservation, old evidence exact and actual cleanup are required; partial receipts cannot pass. Other untested variants from static-review remain explicit limits, not implied by a broad workflow label. fullAcceptance=false; remote authentication/preflight/apply remain separate unqualified work.
