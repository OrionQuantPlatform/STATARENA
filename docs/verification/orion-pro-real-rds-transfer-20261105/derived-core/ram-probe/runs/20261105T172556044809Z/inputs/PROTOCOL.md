# One-shot retained RAM metadata observation

This is a separate precode qualification of the read-only observation in the parent derivation protocol. The only live operation is at most one GET to the exact previously owned private Unix socket and peer PID29953, under an explicit unexpired ROOT release and single-use ledger. No SQL, RDS, capture/restart, provider call, auth, write, publication, data persistence or call to the old capture's connection routines. A stopped or changed capture refuses before GET. Its old ledgers and readiness must remain exact. Bounds:60s active,32MiB received wire,256MiB observed peak process RSS,1MiB proof; enforce wire/deadline and sample the process peak before every wire read, during packed traversal and at completion. Current Darwin peer credentials and owner/socket permissions are checked before sending. No process or DNS path exists in the live module.

The known protocol is the frozen server's protocol5 pickle. Decode with a restricted class whitelist for the frozen primitive/decimal/aware datetime metadata and no arbitrary callable or persistence hook. Reject stream truncation, trailing content and nonconforming envelope, physical document paths/hashes, frozen source identity/counters and packed shape. Independently decode each targeted packed table one row at a time, checking dictionary indices and explicit missing flags. Compare the canonical row-array hashes for fixture/detail/performance/team/profile tables with the prior actual metadata receipt. One GET does not convert the source into a new snapshot or produce a business dataset.

The metadata-only result reports the actual number of dates and strings, validated grammar counts (full UTC versus time of day needing rule review, offset/naive/unqualified, explicit null and absent, malformed, matching/mismatching UTC date), and detail/fixture time agreement. It does not emit any individual date, kickoff value, actual source ID, name, score, raw source scalar or document body. It counts source memberships and keeps witness digests only: exact matchId/playerId/teamId/id/playerRef occurrences in performances and their matching explicit detail players list, the declared players boolean/count and selected fixture-side/profile scope. A positive exact nonempty list can qualify observation; a listed empty with false availability is not an observed empty HTTP response. No detail row remains unknown. Teams are counted from unique exact edition sides and digest of first ordinal witness, not from the listed count alone.

| Before-code workflow | Expected |
| --- | --- |
| Implementation missing | Actual RED; external calls remain zero. |
| Default and unreleased inventory | Offline plan / refusal before driver, DNS, process, socket. |
| Owned local structural wire/packed fixture | Independent decoder runs on memory bytes only, no socket. Explicit time and coverage categories, exact result keyset, no fixture value/identifier emitted. |
| Distinct date/time and detail conflict | Absent, null, midnight, time-only and contradiction retain distinct counts and no raw values. |
| Explicit empty vs no detail vs proven present | Empty not inferred as coverage; exact list and typed actor/profile/witness constraints. |
| Out-of-scope side, repeated performance and corrupt packed index | Refuse without source or writes. |
| Truncated/trailing wire, wire cap or unsupported pickle class | Fail closed, without evaluator or alternate route. |

ROOT's later live allocation must bind exact code/test/protocol/pins hashes, capture SHA/PID/socket,60s/32MiB/256MiB/1MiB, zero SQL/cloud/provider/write, a distinct allocationId and aware expiry. Invocation: python3 probe.py --inventory --release ABS --release-sha256 SHA, with clean routing environment. Preserve exact commands, resource counts, cleanup and digest-only results. Closed report is a classification, not a typed SQL acceptance or authority for an apply.

Suggested commit: test: qualify one bounded retained RAM metadata probe
