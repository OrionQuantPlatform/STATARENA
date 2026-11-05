# Real core transport to the independently verified RDS015 policy

Suggested commit: `feat: bind minimal real core transport to verified RDS015`.

This once-only supervisor retains the qualified earlier copy core. It requires a separate explicit fresh source service identity (V4), its exact semantic/native continuity, the independently observed target015 (not the earlier P1), exact code/bindings/proof hashes and an out-of-band ROOT authority SHA. Default invocation is offline. No RDS business write is permitted before an actual passed readonly preflight with the same authority.

Preflight reads only the two bounded typed endpoints with TLS and verifies the exact native source, target, ACL and journal policy. It must produce zero COPY and nextval. Apply is a separately consumed command with a fixed900s outer deadline,8s statement timeout and1s lock timeout, one source runtime and one target ingest connection. Source capture remains unchanged; no provider/Neon/body copy or additional AWS resource. No automatic retry or reset. Stop the owned source after operation and independent readback. Failure receipts are retained; a failed or uncertain apply is never classified as committed without actual target evidence.

A successful apply requires the independent native91+3 committed-core oracle before admission/publication. Physical sequence gaps are normal only when exactly accounted by reserved nextvals. Only the minimal typed core is in this allocation; source reconciliation, missing inputs, publisher, deployment and activation remain separate.
