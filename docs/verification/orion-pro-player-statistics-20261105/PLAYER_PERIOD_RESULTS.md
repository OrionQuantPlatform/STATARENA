# Four normalized player period readers

Suggested commit: feat: serve versioned typed player period statistics.

[Actual unwired RED](runs/20261105T174049131949Z-player-period-composite-unwired-red-v1/result.json),
SHA 62ea77c0: P01 passed, P02 returned 501/no-store/zero runtime SQL for the
native statistics request. P03–P14 were unverified. 10.185 seconds,
1,017 SQL calls, eight loopback HTTP requests, owned cleanup complete.

[Actual wired AFTER](runs/20261105T174455206462Z-player-period-composite-after-v1/result.json),
SHA 8df3039a: P01–P14 passed on Node24.22.2 and PG18.6. 10.389 seconds,
1,410 SQL calls of which 105 runtime, 80 loopback HTTP including traces,
632 typed rows at initial combined publication and 701 after correction.
No external attempts; the runtime write was denied with 42501; all clients
closed and the owned cluster was stopped and removed with no changed pins.

| GET representation | Payload bytes | SQL SELECTs |
|---|---:|---:|
| Match player rows | 904 | 5 |
| Selected player | 812 | 5 |
| Match player halves | 786 | 5 |
| Selected player halves | 646 | 5 |

Every measured native statistics HEAD/304 used two metadata SELECTs and
zero body bytes. Known empty reads use metadata alone. The numbers above
describe local synthetic responses, not production performance.

The existing 017 transform/metrics pair and V1 pro1 grammar are retained.
The exact composite environment is e5a436a8 and a separate independent
typed statistics component joins the existing V1/native017 dependencies.
An old 017 environment fails closed. The stats-only correction changed
the combined dependency and ETag while preserving the V1/native017
component hashes, previous response bytes and independent edition C.

The body oracle preserved the exact 9007199254740993 and
0.8200000000000000001 number lexemes, observed total 7, false, zero,
empty string, explicit null and absent property. It also verified no
fabricated half and no fallback to a global profile. The wrong-profile
input was retained as a typed candidate and rejected before synthetic
publication; no invalid READY was fabricated. Existing original summary
and native events were re-read with their old pinned tokens.

Rerun with the exact command and input hashes in the result. This is a
normalized player/period metric projection, not a complete original
source archive. The bound typed runtime and synthetic writer are
qualified here; the production composite publisher, source acquisition,
browser adaptation and hosted cutover remain distinct. Maximum
row/encoded-size caps are implemented; an overflow case was not run in
this sublot. No new formula, schema or source access was used.
