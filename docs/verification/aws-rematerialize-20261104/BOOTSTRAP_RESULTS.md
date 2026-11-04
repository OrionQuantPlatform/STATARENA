# Initial source receipts and automatic historical discovery

A manifest-only historical scope was missed by normal resume unless the operator forced all partitions into the queue. The real PostgreSQL E2E now builds that scope without `--all`: newly discovered scopes0→1; immediate unchanged rerun0partition rebuilds. A bad pinned source is rejected, with queued work retained and neither a partition nor a source receipt committed. Typed partial refresh keeps the original receipt and ignores an obsolete corrupted seed pack.

Migration010 adds only typed source-path/SHA/time metadata. The actual physical SHA is captured in the same read that obtains the first seed content and is recorded in the existing partition transaction. Later typed refreshes retain it. Applied003–009 files are unchanged. Website readers/response contracts do not change; this change adds a metadata write during first construction and an inexpensive missing-scope discovery statement per worker run. No website-latency improvement is claimed.

Tests/failure modes registered first in BOOTSTRAP_PROTOCOL.md. Before: 15/19, with the new assertions reproducing missing receipts and missed manifest-only work. After: 19/19 actual PostgreSQL E2E cases pass, including archived/current precedence, missing/failed families, rollback/retry, late dirty markers,32interleaved shards, bounded resume/idempotence, capacity refusal, stale-index fallback, lease, orphan records, native positions and both limited schema-ownership installations. Exact rerun/setup/results/logs are in bootstrap-before/ and bootstrap-after/. Raw PostgreSQL logs are retained unchanged, including their whitespace.

Production installation of010 and hosted CI on this commit are pending until main push. Existing production partitions built before010 have no historical consumption receipt; this change deliberately does not invent one from today's object metadata. Full stable-generation source/value/API/browser acceptance remains outstanding.

Suggested commit: `fix: discover manifest-only scopes and pin initial serving sources`.
