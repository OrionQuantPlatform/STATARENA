# Retained RAM probe V2: bounded decode without a second wire copy

V1 actual observation received 12,208,712 wire bytes from the expected peer in one GET, then refused RSS_BOUND before any source classification. Keep its exact receipt, ledger and release. No UTC/performance conclusions were admitted. V2 is a separate candidate and does not reuse that allocation. Do not reopen the retained socket during qualification.

V2 retains the exact V1 capture identity, old ledger/input pins, one Unix GET, wire receive-to-EOF, closed fields, profile/fixture/coverage witness rules and per-row canonical digests. The replacement decodes using the restricted C unpickler (same whitelist and persistent-ID refusal) after a bounded protocol5/frame/STOP scan over a memoryview. Both readers share one wire buffer; there is no full copy for BytesIO. Reject trailing bytes inside/outside the last frame, external buffers, extension lookups, unapproved global reductions and persistent references. Clear the decoder memo and release the wire before walking the packed rows. Project the old immutable inventory files to a small metadata-only manifest before decoding; never load the old actor arrays into memory alongside the live snapshot. Evidence retains stage RSS peaks, wire bytes/hash, case classifications and digests only. The 60s/32MiB/256MiB/1MiB limits and no SQL/provider/write remain exact.

Before-code E2E:
- Real missing-module RED. Offline plan and unreleased live refusal with no socket/DNS/driver.
- Real protocol5 parser over synthetic compact packed data: date and scope checks, explicit empty vs absence, no typed value/identity persistence; reject trailing bytes, altered frame, unsupported class and tiny wire cap.
- Separate source-free process emits two synthetic editions through an owned in-memory pipe; consumer alone measures decode and traversal RSS. Require 612 fixture rows, 387 detail rows, 15,437 performances, 46/89 packed columns, decimal/string/boolean/NULL diversity and wire at least 12,208,712 bytes, strictly below32MiB. No synthetic body is written. Preserve exact wire hash, input shape, stage peak RSS, process status and cleanup.
- Actual GET remains unexecuted until ROOT approves exact V2 bytes/receipt/release. A positive synthetic result is resource evidence for that shape, not a real-source grammar or coverage claim.

Suggested commit: fix: bound retained RAM metadata decoding without copying the wire
