# Historical collector refusal handling

Goal: attempt the 10 refused profiles through the existing authenticated GitHub runner client; preserve results; continue to later countries despite individual refusals. Preserve all successful archives and checkpoint references. Do not change API credentials, hostname, transport or user-agent. Do not cancel the running collector or discard its unsaved work.

UX: published receipts distinguish completed traversal with gaps from complete coverage. DX: keep the existing queue, publication and continuation mechanisms. AX: persist failed endpoint/status/error records and make terminal country states explicit for reliable resumption.

## Failure modes and expected outcomes (before implementation)

1. ARG has a persistent 403 and BRA has downloadable data: visit BRA, persist the 403 details, mark ARG `complete_with_errors` and BRA `complete`; no needless continuation after both traversals finish.
2. Restart from exported checkpoints: skip both terminal countries, make no duplicate provider calls, retain successful response references and refusal evidence.
3. A deadline interrupts ARG: keep it `partial`, emit `continue=true`, then resume its traversal on the next run. A partial country with errors must not be skipped.
4. HTTP 401: save the partial country and stop with nonzero exit before BRA. Do not hide invalid authentication as a per-resource gap.
5. Explicit retry workflow: make one bounded pass over blocked checkpoint keys, retain HTTP 403 refusals without claiming recovery, persist HTTP 200 response bodies in a separate immutable archive. Never overwrite checkpoint buckets while the existing collector runs.
6. A retry recovered a previously blocked key: later collection reuses its archived response, discovers its contents and updates the request checkpoint without another provider call.
7. Publication: real local Git commit/push preserves checkpoint and response files, including concurrent independent archives; no fixture credential reaches output.

## Planned E2E execution

Run the real CLI against a local HTTP fixture through a subprocess bootstrap, with real SQLite, compressed response bodies, exported checkpoints, continuation files and a temporary bare Git remote. Verify the full country traversal, process restarts, deadline/authentication cases, retry archive and publication. Keep commands, fixture inputs, observed receipts and captured subprocess logs in `RESULTS.md` and `e2e-result.json`. Live retry outcomes must be reported separately from simulated workflow checks.

Suggested commit: `fix: continue historical collection past refused resources`.
