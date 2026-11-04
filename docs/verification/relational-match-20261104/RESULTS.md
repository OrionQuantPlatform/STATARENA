# Match detail read verification

The local HTTP workflow passed 63 recorded requests using PostgreSQL 18.6 over verified TLS. Complete, historical and upcoming match JSON values round-tripped through 43 typed tables. The checks include ordered arrays, explicit nulls, absent fields, empty lists, false and zero, archived 404 envelopes, all thirteen aggregate families, all five independently saved nested routes and a heatmap parameter variant. The catalog check found zero JSON, JSONB or bytea columns in the match-detail schema. PostgreSQL constructs JSON responses at read time.

| Same complete match, local HTTP | Legacy archive | Relational before cache | Relational with version check |
| --- | ---: | ---: | ---: |
| First GET SQL statements | 28 | 1 | 2 |
| First GET object reads | 14 | 0 | 0 |
| Compressed source bytes downloaded | 45,448 | 0 | 0 |
| Source bytes parsed by application | 469,680 | 0 | 0 |
| HTTP response bytes | 333,449 | 333,449 | 333,449 |
| First GET elapsed, one sample | 106.3 ms | 97.7 ms | 103.5 ms |
| Median of seven repeated GETs | Unmeasured | 39.6 ms | 2.1 ms |

A warm GET checks the currently committed digest in one indexed SQL query and receives zero SQL JSON rows. Unavailable individual responses bypass the cache. The two oversized GETs each returned their full representation and bypassed cache admission. A previously retained match remained available. Context-only updates and family replacements produced new ETags and immediate updated bodies. HEAD builds neither an archived JSON payload nor an HTTP body.

The legacy handler used commit 923bb0ff4a and a local object store with the same real data. Both timings include HTTP serialization. Single cold timings include local TLS and pool startup. The final warm median compares repeated reads of the same match. These timings do not measure live AWS or public-site latency.

The separate enforced read-only RDS probe found successful saved examples for all five nested route kinds. The bounded shape probe validated 28 indexed family responses totaling 548,241 bytes. Unknown fields cause the offline writer to reject the corresponding transaction so that an earlier valid representation survives. A complete import and public cutover require separate verification.

Fixtures, commands and predeclared acceptance checks are in PROTOCOL.md. The final PostgreSQL version, source hashes, individual request timings and counters are in after.json. legacy-same-input.json and before-cache.json record the comparisons. No database migrations or writes were executed against AWS during this verification.

Suggested commit `feat: serve version-checked match details from normalized football tables`.
