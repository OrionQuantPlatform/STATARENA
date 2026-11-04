# Private patch verification

The final change reduced local Node 24.22.2 processing of the genuine 100-match page by 47.0%. Twelve warm paired runs used the already-decoded result of each real PostgreSQL query. The recorded public response SHA-256, ETag and all 1,973,314 bytes matched both implementations. The browser capture contains 4,788 appearances on this page. [Final patch](page-origin.patch) and [all request and timing records](after.json).

| Processing on the same machine | Baseline median | Final candidate median | Faster pairs |
|---|---:|---:|---:|
| Whole handler elapsed after DB results are available | 242.87 ms | 128.67 ms | 12/12 |
| Process CPU, user and system | 251.68 ms | 151.24 ms | 12/12 |

The initial private decoder recreated a full internal record before converting it to the public shape. It passed fidelity checks but increased the paired elapsed median from 232.79 to 245.18 ms. The final decoder writes positional values straight into the public record, converts native position values at their existing boundary, and merges dynamic metric extras with own-property semantics. [Intermediate regression](indirect-decoder.json).

The primary query checks the 87 typed appearance columns against the sealed layout once per page and appends the three explicitly joined fields to the positional transport. The local EXPLAIN showed exactly one catalog scan, returning 87 attributes. Dropped columns are filtered. A new typed field triggered the original named-record path in a real ALTER TABLE test and remained visible as zero and null. Removing or renaming a required column in sealed migration 003 requires a coordinated query change.

Eight HTTP scenario/format outcomes matched the pre-change bytes, hashes, status and ETags. Coverage includes normal sparse and empty partitions, SQL null versus a missing field, zero, numeric and string position IDs, own `constructor` and `__proto__` metrics, and an unrecognized future typed column. HEAD, conditional GET and conditional HEAD skipped body SQL and returned empty bodies. The dense ordinary-format request retained its existing 413 size guard. The complete packed dense page matched the existing public digest `0d6bbe72588aa8df43b6d7933093a9d9cd8f028a1b53d61fc8c68bdc37f7d403`.

The tests preceded the private product patch. The [initial failing receipt](before.json) stopped at the new transport assertion. [Exact inputs, local setup and ordered reruns](PROTOCOL.md). The private patch SHA-256 is `b6aa2cd97771f033515c4e934def54c2e7d348227b5e61094ae9f450f89775f8`. The prior read-only RDS trial measured 46.8% fewer PG field bytes for the positional projection. Its warm plan is separate from these paired local CPU results. A deployed matched-origin comparison remains outstanding.

Suggested commit: `perf: reduce dense season page transfer and decoding costs`.
