# Owned journal corruption fixture correction

The v2 attempt passed nine cases and stopped at the first direct journal clock UPDATE with native SQLSTATE55000. The existing pro_typed_guard correctly rejects updates. The receipt, logs, inputs and consumed ledger remain byte exact in attempt-v2-closed/HASHES.json. All PostgreSQL/TMP data were removed. Zero remote calls occurred.

The corrected complete E2E first proves that direct UPDATE is denied. For the already documented clock/hash corruption negatives only, its verified owned table owner disables that one trigger, mutates journal rows, restores exactly the trigger before native inspection, then rolls back the entire transaction. This tests detection of owner corruption without weakening production SQL, grants or expected JOURNAL/CATALOGUE refusals. The adapter,014,model and all19 protected dependencies remain unchanged.

No unit tests are introduced. These are corrections to pre-code whole-workflow negative fixtures. Full20 cases still need a new explicit v3 release and one new600s owned/TLS campaign; v1/v2 remain exhausted. Actual command must pass absolute release/ledger paths because the old archival helper rejects relative paths. Fresh RDS authentication/preflight/adoption remain unverified.

Suggested commit: `fix: qualify exact RDS policy metadata and private authentication`.
