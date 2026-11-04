# Preserve appearance membership while removing repeated aggregates

Registered before the semantic fix: the existing uncommitted optimization is
saved as `before-semantic-fix.patch`; its source SHA-256 is
`0152b2e3004074ff76217e249efb3a1ee89670c34f4615b3ee2a386bd8beb0b9`.
The deployed `b2ec973d` source SHA-256 is
`91c59681f3187b2311991561661b67876b5c5d378dbb615714f4131ed03ff6e7`.

The first paired HTTP E2E (`reader-comparison.json`) demonstrates an actual
failure mode: if an appearance's `season` differs from its parent match,
the deployed reader returns two appearances but the scoped candidate returns
one. No database constraint currently prevents this discrepancy. Excluding the
row silently changes the existing contract.

Expected change: select appearances only by the selected page's parent match
IDs, as the deployed query does; retain materialization of the selected
appearances and one grouped aggregation of their extra metrics. With the same
database snapshot, old and revised readers must return identical semantic
records and pagination for both consistent and deliberately inconsistent
fixture data; native scalar, null, zero, reserved-key, compact-wire, ETag,
cursor, league isolation and named-record fallback checks must continue to
pass. The original dense query's latency must be measured under the existing
8-second deadline; a local fixture or one successful request is not proof of
production latency reliability. No schema change or production write.

The `compare_readers.mjs` E2E is updated to require the adversarial row to be
preserved before editing the product code. The first failure and all later
runs remain separate artifacts. Any actual RDS comparison must use a bounded,
read-only baseline/candidate pair under one fixed repeatable-read snapshot,
never print row data or secrets, retain timeouts, and leave the deadline
unchanged. If the baseline times out, report comparison incomplete rather than
substituting a different generation or asserting equivalence.
