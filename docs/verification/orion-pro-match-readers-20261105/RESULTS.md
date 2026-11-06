# Native match detail reader qualification

Suggested commit: feat: serve six versioned typed match detail routes.

The actual AWS application serves six existing match detail paths from typed
PostgreSQL when the request names an admitted native publication. The 016
publication pair serves momentum, events, lineups, H2H and team stats. A native
core match request on that older pair returns
NATIVE_CORE_FIELDS_UNRECORDED with the three known fields. The separately
approved 017 publication pair also serves the full observed core shape.

The independent body oracle compares key presence, types, order and numbers
parsed as Python Decimal. It sees 9007199254740993 and 0.8200000000000000001
as exact JSON number tokens. A stats layout update changes the joint
representation and ETag while retaining the four tested item scalar pairs
from the original typed observation. An old pinned body and an unrelated
edition retain their bytes and validators. On 017, the referee, playoff
indicator and observed league image URL each preserve value, null or omission.
Updating linked delivery asset metadata does not change the native league URL.
The original four Pro readers keep their pinned response bytes and validators.

| Actual Node 24.22.2 and PG 18.6 workflow | Result | Elapsed | Typed rows | SQL calls | HTTP calls |
|---|---:|---:|---:|---:|---:|
| 016 [unwired baseline](runs/20261105T170149678930Z-native016-actual-unwired-red-v3/result.json) | R01 pass, R02 actual 501, later cases unverified | 8.909 s | 415 before READY | 617 | 14 |
| 016 [final actual handler](runs/20261105T171053104195Z-native016-actual-after-v3/result.json) | 32/32 | 11.019 s | 508 maximum counted | 1,430 | 146 |
| 017 [final actual handler](runs/20261105T171116890811Z-native017-actual-after-v1/result.json) | 23/23 (13 regressions, 10 core cases) | 10.952 s | 486 at upgrade checkpoint | 1,179 | 154 |

HTTP counts include the loopback trace request per public call. The 016 run
used 206 runtime SQL calls; the 017 run used 236. In the measured positive
GETs, core/momentum/events took four SELECTs, lineups/H2H five and stats six.
Admitted native HEAD/304 used two metadata SELECTs and sent zero body bytes.
The 1 MiB overflow returned 413/no-store; no data was silently truncated.
The runtime role had read-only transactions and a separate attempted write
was denied with SQLSTATE 42501. Both final runs report no external HTTP,
all clients closed, owned PG stopped and removed, and no changed input pins.

From the repository root, with the official verified Node archive adjacent
to the extracted runtime, local PG 18.6 and psycopg available:

    PYTHONDONTWRITEBYTECODE=1 /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 tests/orion_pro_match_readers_local.py --phase after --target 016 --label native016-rerun --deadline-seconds 60 --node24 /tmp/statarena-node24-runtime/v24.22.2/node-v24.22.2-darwin-arm64/bin/node --pg-bin /tmp/statarena-cache-test-tools/node_modules/@embedded-postgres/darwin-arm64/native/bin

Use target 017 and a new label to reproduce C01–C10. The Node verifier also
accepts the pinned official Linux x64 binary and archive; this particular
reader evidence was executed on macOS arm64. Each result records the exact
executed command and an input snapshot. See [failed attempts](ATTEMPTS.md) for
the retained earlier setup and test failures.

These are local reader results using guarded synthetic READY publications.
The production publisher must independently certify exact source types,
complete coverage, physical witnesses and source-specific interpretation at
the effective dataset/catalogue pair before the API can trust metadata for
HEAD/304. The synthetic publisher is not qualification of the production
publisher or exhaustive source coverage. This test covers the admitted
momentum series and rejects missing publication/coverage in the HTTP path;
foreign/multiple source series and arbitrary precision outside the admitted
momentum domain were not independently executed here. The 017 case verifies
inconsistent core state/value SQL rejection and no legacy core admission;
it does not manufacture an invalid READY to simulate an unrecorded 017 field.
The existing consumer fields fit the native data shape. Wiring version
discovery in the frontend, translating known event sides for its normalized
team IDs and preventing unresolved H2H IDs from becoming links remain
consumer integration work. No hosted route availability, production latency,
real-data transfer, Neon cutover or deployment is asserted.
