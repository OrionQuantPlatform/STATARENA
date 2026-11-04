# Immediate availability release protocol

Separate lot from the unapproved Pro schema revision. No schema/data, provider,
workflow or DB-size changes. Root reviews source and owns releases; main only.

## Dense reader

Require paired local PostgreSQL/HTTP acceptance for records, native scalars,
ETags, pagination, compact wire and adversarial parent membership. Keep red and
green evidence. Require bounded read-only RDS baseline/candidate in the same
repeatable-read snapshot: equal semantic hashes/counts, exact SQL and8s deadline.

Package committed source with `python3 infra/aws-backend/package.py
/tmp/statarena-backend-releases`. Run `release.py dry-run` identity/network checks.
Prepare the SHA-named ZIP; inspect unexecuted CloudFormation changes. Execute
only a code modification to existing backend function, no replacement/new
resource. Preserve previous ZIP for code rollback. Investigate any other change.

After UPDATE_COMPLETE verify Lambda CodeSha256 against ZIP and existing
Node24/512MiB/25s configuration; CloudFront must remain deployed. Run existing
`infra/aws-backend/public-smoke.py` on a real stable cacheable route. Then at most
three sequential GETs of actual100-match compact partition and one bounded
HEAD/conditional pair. Normal generation, no cache-busting or parallel load.
Save statuses, wall times, generation, validators, lengths/hashes and failures;
distinguish edge hits from origin work. This is sample acceptance, notp95 or a
load test. No larger deadline, provider call or RDS write.

## Vercel current-UI recovery

Review transport/loaders against BRIDGE_PROTOCOL.md. Require production build,
HTTP and desktop/mobile browser acceptance; label all shim/synthetic checks.
Preserve configuredAWS precedence, errors, publicIDs and currentUI routes.
Missing/invalid saved data fails observably, never becomes empty success.
Availability503 is the baseline; no invented response-time comparison.

Verify teamteam_IYt7KqupdSTtMuQuMvNa9wiJ,
projectprj_DhaqrVkH3Gi4uysT7IRsm9fB2bjR, committed main SHA and production
configuration. Stage `vercel deploy --prod --skip-domain` with existing
server-side credentials. Never export/print/publish secrets. Test immutable
stage with actual runtime credentials and representative current/historical
six-season UI routes. Local shims do not satisfy this gate. Keep alias unchanged
until acceptance, promote only the same tested production build, then verify
canonical paths desktop/mobile. This is temporary complete-Neon recovery;
finalAWS cutover still requires full joint data/backend acceptance.

Every run saves setup/inputs/exactcommand/expected/actual, artifact and commit
identity, logs/statuses/screenshots and limits. Suggested commits:
`perf: batch appearance metrics while preserving match membership`;
`fix: bridge the current frontend to saved Neon data`.
