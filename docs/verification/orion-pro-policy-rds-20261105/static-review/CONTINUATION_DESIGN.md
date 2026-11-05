# Proposed one-campaign continuation — not released

No continuation file/ledger has been created or code patched. ROOT review/authorization is required first. Keep original campaign.json byte-exact SHA `3d65c2ca695bd261959c4831f0585b77a4050d7111257a923259924e884d3114`, state stop_for_ROOT, pgStarts1/max1. Keep result520d42… and ATTEMPT_1_HASHES2a4dd3… plus all run-local original source inputs exact. The historical manifest records original unversioned source hashes; future authorized source edits do not rewrite that historical cohort. Its archived run inputs preserve those exact bytes.

## Before another PG start

1. ROOT reviews F01–F05 and the explicit coverage gaps. Freeze a revised E2E before the next implementation changes, including real owned-CLI contract/marker symlink counterexamples. A new passfile guard needs its own documented cases/test and actual missing-guard RED without PG before guard code. That RED is a new source-free proof, not replaying the old missing-adapter RED or resetting precodeRuns.
2. Apply only reviewed fixture/Q04 corrections. Keep SQL012/013/014/model/old policy/upgrade/bulk/helpers/other namespaces exact. Decide explicitly whether the private transition-core extraction and conservative cleanup are included before this final code hash, so later remote work does not clone/diverge from a different tested SQL path.
3. ROOT writes a separate fixed `ROOT_LOCAL_CONTINUATION_V2.json` only after the final test/adapter bytes exist and the new guard test-first chronology is preserved. The release binds original ledger/result/artifact hashes, INPUTS69f72c… and protected19inputs, exact new e2e/adapter/protocol/test hashes, expected workflow names/nested auth cases, new ledger path and limits. It grants precisely one new owned campaign, not remote permission.
4. ROOT creates **new** `campaign-v2.json` with a new kind, pgStarts0/max1, state unstarted, parent hashes/release hash, explicit checkpoint and unchanged resource caps. It is not a copy of campaign.json with counters reset. Original precodeRuns/pgStarts/state never change. Total historical starts1→at most2 only under this separate release.

Proposed revised E2E CLI accepts explicit fixed continuation release/hash and new ledger path. It rejects missing/mismatched/consumed release or nonzero new checkpoint before PG; it never chooses a new ledger automatically or falls back to original campaign.json. All claim/finalization operations select only this reviewed v2 ledger. Original ledger hash is checked at entry and exit. Its failure leaves the attempted v2 ledger consumed with remaining workflows unverified; no v3 generation or retry is automatic.

Proposed command shape, not runnable/authorized yet:

```text
PYTHONPATH=/tmp/statarena-publication-test-python python3 docs/verification/orion-pro-policy-rds-20261105/e2e.py --label owned-rds-adapter-continuation-v2 --pg-bin /tmp/statarena-cache-test-tools/node_modules/@embedded-postgres/darwin-arm64/native/bin --continuation-release docs/verification/orion-pro-policy-rds-20261105/ROOT_LOCAL_CONTINUATION_V2.json --expect-continuation-sha256 <ROOT-reviewed-sha> --ledger docs/verification/orion-pro-policy-rds-20261105/campaign-v2.json
```

The tool must still default to refusal on the exhausted original allocation. Revised code/commands/manifests are archived before PG. Execution is source-free, one owned SSL PG18.6, at most2DB/600s, statement8s/lock1s,8GiB hard disk/7GiB soft stop,32MiB metadata/64MiB proof including existing namespace evidence,512MiB temp/backend. An owned-setup writable OS-superuser connection is narrowly separated from the tested statarena actor entry points, which retain startupRO/TLS/8s/1s. Fresh native Q04 count is measured, not forced to historical2475. No hard cap is increased.

Acceptance requires actual exit0, every declared top-level workflow and required nested auth case present/pass, exact protected inputs/old ledger, native old clocks, function/properties, sequences and bootstrap preserved where specified, measured budgets and verified owned cleanup. A broad20-case title does not imply the missing variants listed in STATIC_REVIEW. Resource, interruption, cleanup or missing-case failures are failed/unverified, never partial pass. New fixture results remain local-only/fullAcceptancefalse. Remote auth/RO preflight/apply all need later separate releases.

## One tested transition core, distinct scope wrappers

Optional for ROOT approval now: extract the existing with-transaction/fences/accepted-state/fixed014/journal/native-clock/postcondition/commit-ack logic into private `_transition_core(conn, contract, accepted, identity_check, *, fault=None)`. It opens no connection and accepts no SQL/path/target from CLI. Preserve actual statements and exception/commit semantics; preserve the public owned_transition signature and current owned CLI.

The strictly owned wrapper continues to verify marker/loopback/start time/TLS/actor/contract/acceptance, open its pinned connection, invoke the private core and close it. Remote preflight never calls this core and remains read-only. A future ROOT-controlled RDS apply wrapper would require its own destination/auth/release/RDS-native contract and acceptance, perform the native RO identity/preflight checks, then call this **same already-qualified core**. It must not alias an owned acceptance/contract or expose an arbitrary connection/SQL/remote-apply CLI flag. No such wrapper is implemented or authorized now.

The single future complete local campaign then exercises that actual private core through the unchanged owned API for normal adoption, both rollback faults, lost acknowledgement and true fresh-process no-op. No new isolated tests for the already implemented SQL path are proposed. The only new isolated pre-code guard scope is private-file metadata before DNS/driver; its inputs and missing-guard RED precede implementation. This avoids qualifying one SQL path locally and cloning another for eventual RDS.

Suggested commit: `test: audit owned RDS policy fixtures before continuation`.
