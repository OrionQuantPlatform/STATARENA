# Proposed local budget — awaiting ROOT review

Suggested commit: `test: specify Pro V1 publisher gates and preserve missing CLI red`.

Current authorized work stops after static review, protocol/matrix and **one absent-helper CLI RED**. No PostgreSQL, API server, source RAM or publisher implementation runs now.

Next proposed gate, not yet executed/authorized:

| Resource / work | Proposed cap |
|---|---|
| Environment | One owned loopback PG18.6, exact existing012/013 and94 active tables; no historical159-table fixture needed for this publisher |
| Fixture |3 editions /5 initial matches; at most12 match identities and5000 typed rows across all corrective/negative scenarios |
| Results/history | At most20 builds,100 match_summary rows,20 competition_summary rows,24 accepted generations and30 publication intervals |
| Concurrency | At most2 publisher subprocesses,1 Bun API,1 admin observer; at most5 simultaneous DB connections; no additional agent |
| HTTP | At most200 actual API requests per run; no browser/CDN/remote fetch |
| Operational SQL | At most1500 traced publisher/API statements per run, excluding the fixed existing DDL/bootstrap and fixture setup; statement/lock/process timeouts explicit |
| Fault tests |3 deterministic crash points, one same-edition race and one newer-dirty-watermark race; no randomized/soak/load campaign |
| Execution | First complete pre-code PG/HTTP RED, plus at most one fixture/harness correction if setup is invalid; preserve both. Publisher code remains a later separate authorization |
| Wall time | Aim ≤5 minutes/run; hard stop10 minutes/run with owned cleanup. Do not silently broaden the campaign if the budget is insufficient |

After that complete pre-code RED, ROOT can review and authorize implementation and a bounded green/retry campaign separately. The anticipated full matrix is30 cases including the already cheap CLI case. Failures must remain visible; budget exhaustion is not acceptance.

Evidence must include exact command/config/code/model/SQL hashes, explicit canonical source export, writer and runtime identities, SQL/function-call/sequence/watermark counts, all HTTP status/header/body bytes, independent expected/actual summaries, concurrency/fault barriers and complete owned cleanup. No source payload, secret, data transfer, installed cloud resource or new schema object is needed. Old guard19/19 and all prior artifacts stay immutable.
