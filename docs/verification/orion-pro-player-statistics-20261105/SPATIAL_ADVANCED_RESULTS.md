# Spatial and advanced statistics readers

Suggested commit: feat: serve typed spatial and advanced match statistics.

[Actual wired AFTER v2](runs/20261105T181446272678Z-spatial-advanced-actual-after-v2/result.json),
SHA 3c01f9bd: X01–X14 passed on the actual AWS application handler, Node
24.22.2 and owned PG18.6. 10.170 seconds, 2,047 SQL calls (115 runtime),
88 loopback HTTP requests including trace reads, 790 typed rows at initial
publication and 827 after the heatmap correction. No external attempts,
write denial 42501, no changed input pins, all clients closed and owned
cluster stopped and removed. The exact setup, inputs, commands, bodies,
SQL traces and result are in the receipt.

| GET | Body bytes | SELECTs |
|---|---:|---:|
| Sparse heatmaps | 913 | 4 |
| Directed pass network | 909 | 5 |
| Advanced teams | 566 | 4 |
| Advanced players | 817 | 4 |
| Advanced player | 490 | 4 |

Five HEADs and five matching 304s each used two metadata SELECTs and zero
body bytes. Missing coverage and older publication environment returned
named errors with no sporting value reads. The conditional miss returned
the same complete body and validator.

Both heatmap frames were read from separate typed observations. The tests
preserved sparse cell order, observed zero, an independent nullable actions
total, exact grid, captured repeated team contexts, and null/absent/empty
collection states. The directed network kept its declared metre frame,
window, node positions and edge direction. Unqualified frame and conflicting
typed advanced value candidates were refused by the independent synthetic
publisher in rollback-only transactions. The runtime did not invent a
valid READY for either negative.

The advanced shape retained exact typed null, 0, and the numeric token
0.8200000000000000001. An advanced player lookup stayed in the pinned
match and normalized actor cohort. A heatmap-only correction changed the
combined dependency, token and validator. Earlier pinned body bytes, prior
period environment, independent edition C and V1/native017 components
remained exact. The four period routes also served the superset environment.

See [earlier attempts](SPATIAL_ADVANCED_ATTEMPTS.md) for the preserved
unwired RED and transaction guard failure. No new DDL, formula, source
call or current-state fallback was introduced. The normalized release
does not prove raw source archive parity, real network axes, exhaustive
source data coverage, a production composite publisher, browser wiring
or hosted availability. Response bounds are implemented; overflow was
not exercised in this sublot.
