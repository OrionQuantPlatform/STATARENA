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
