# Owned local supervision — protocol before launcher code

ROOT owns this namespace. The source helper, normalizer, model and sealed migrations remain untouched here. Suggested commit: `test: supervise the real native source reconciliation within fixed bounds`.

The launcher defaults to an offline plan. A real run requires an exact external ROOT release binding its label, launcher/helper/candidate/normalizer/SQL hashes and existing source metadata. It consumes one local execution ledger before starting a child. It never reads source bodies, calls AWS/Neon/PitchAPI, restarts the capture or sends STOP to RAM PID54737. A separate smoke mode uses only an empty owned PostgreSQL and the helper's explicit overlay probe.

| Failure or workflow | Expected observation |
|---|---|
| Launcher absent | Genuine CLI RED retained before implementation; no PostgreSQL or source call |
| Default/offline plan | JSON metadata only; no subprocess, source socket read or real execution ledger |
| Real run without release or with malformed release | Exit2 before any child or execution ledger; no implicit authorization |
| Source-free smoke | One exact overlay probe and actual fresh worker;1/1 case,0source calls,0real native/spatial comparisons,owned PostgreSQL cleaned |
| Real authorized workload | One run only; exit0 and all15 cases individually pass;478547 independent native slots and1344ordered cells agree by digests; fresh process reuses core/spatial receipts and94tables/67sequences are unchanged |
| Unexpected output / stderr | Retain byte counts and SHA256 only; persist only closed PASS/FAIL case names and final metadata, never arbitrary sports rows or raw stderr |
| Environment | Minimal local environment, fixed PYTHONPATH, no inherited PG* or cloud credentials; no source fallback |
| Owned roots | Discover only new child run directories and their recorded initdb/pg_ctl -D paths. Require exact tool path, current UID, real newly created temporary orion-pro-e2e-* root; no broad cleanup scan |
| Wall / disk | Sample at most every1s; metadata heartbeat15s. Interrupt at1770s or3.5GiB allocated; force at1800s or4GiB. Smoke limit60s |
| Abort / incomplete child receipt | Outer result is failed/interrupted even if the inner finally says pass; unexecuted cases explicitly unverified |
| Cleanup fallback | Only registered owned roots; verify PID command/data directory before pg_ctl stop and removal. RAM source never targeted. A remaining unverified process/root fails acceptance |

Disk monitoring is live supervision rather than a filesystem quota. The launcher must not invent row percentages: active phase is inferred from the known case order. PostgreSQL's terse/panic/zero-bind logging must already be checked by the child before business writes. The ordinary child evidence retains exact setup/code/SQL and metadata oracles; this outer receipt binds it and independently checks completion and unchanged source ledgers. The source corpus cannot be reconstructed from hashes alone after RAM loss; a new capture remains a separate authorization.

Pre-code E2E: `python3 docs/verification/orion-real-supervision-20261105/monitor_gate.py --label precode-missing-launcher-red`. Preserve that RED. Only after launcher implementation may the same gate run its source-free owned-PG smoke. No real run is authorized by this protocol or a passing smoke.

## Fault workflows before the supervision corrections

Static review identified two unexercised failures in the first launcher. A process killed during initdb can leave an owned root before commands.json exists; an exited parent with a descendant holding its pipes can bypass the wall guard. Before correcting them, fault_gate.py runs the actual supervisor in an owned subprocess with two explicitly synthetic infrastructure children. These do not invoke the source helper or read RAM.

The first child creates a genuine temporary PG18 initdb root, records its ownership for this E2E, then is killed with its owned group before any postmaster or SQL session starts. Expected: the supervisor finds/removes the orphan even without commands.json. The second child starts a ten-second pipe holder and exits immediately. Expected: the supervisor bounds post-exit drain, terminates the owned holder and returns within four seconds. Both outer fault executions must remain failed/aborted; a passing fault test means cleanup/deadlines worked, not that source reconciliation passed. The test cleans only its exactly attested orphan/holder if the old launcher leaks them.

The correction will create and attest one private0700 TMPDIR before Popen, discover only PG roots under it, and remove it only after verified postmaster cleanup. Source forbiddance becomes explicit in the minimal environment. Preserve the old4/4 smoke and its exact input snapshot; it did not exercise these fault branches. After the genuine fault RED, rerun these two OS-process workflows and the ordinary source-free smoke. No extra real corpus start or capture is permitted.

## Explicit second attempt after the actual spatial digest failure

The v1 real execution is consumed and remains failed13/1/1. Native31:478547 comparisons passed; spatial1344 rows were visited but its digest assertion failed, and fresh-noop was not executed. Its release, ledger and all receipts remain immutable. The new serializer's separate test-first14/14 evidence corrects numeric representation only; it does not authorize a retry.

The current launcher may accept only explicit attemptv2, an external ROOT_REAL_RELEASE_V2.json with its exact supplied SHA, a new fixed-v2label and real_execution_ledger_v2.json. It must never reset or reuse v1. Pins add the new spatial serializer and consumed v1ledger. Default remains offline; unsigned/malformed v2refuses before process/ledger creation. The CLI gate expands to6cases, including actual v2selection and an empty-PG smoke. Old4/4 and real-v1 inputs remain recoverable from their snapshots and commitd4767fccf93b2148d26a2424f4e7b7a262f4b2f9. One v2real start remains separately reviewed/authorized, with unchanged source corpus/counters/limits and no new remote/capture.
