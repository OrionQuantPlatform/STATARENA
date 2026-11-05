# Proposed single real local run: ROOT release still required

This is a reviewed-command proposal,not an executed run or a new authorization.
The source-only RAM capture is already available. ROOT must approve the final
code/bounds and supply its supervisor from
`docs/verification/orion-real-supervision-20261105/` before launching this one
real E2E. No further remote SELECT/HTTP,capture,login,raw copy or RAM STOP is
part of this command.

Repository root: `/Users/lemonnierhugo/Desktop/Coding Project/Football_ranking`.
Exact proposed child command:

```sh
PYTHONPATH=/tmp/statarena-publication-test-python python3 docs/verification/orion-pro-real-native-spatial-20261104/e2e.py --source-socket /tmp/orion-real-native-spatial-20261105-v2/source.sock --local-validator-overlay docs/verification/orion-validator-membership-20261105/candidate.sql --local-validator-overlay-sha256 e0810f8670b2cb627ade2c76e3c8eb527ab31fd595d5cf939fd63bfc5cf649d6 --label real-native-spatial-overlay-e0810f-v1
```

The option is explicit. The default remains sealed013. The single candidate
contains real source-derived facts only; preparatory source-free metadata probes
use their own disposable databases and create no synthetic sports facts in it.
The source snapshot/code/physical hashes/typed origins must still match. Existing
source budget counters4SELECT/9682314B/3HTTP/3961physical B must remain unchanged.

Proposed fixed operational envelope:

| Resource/observable | Required bound |
|---|---|
| Source access |0new remote SELECT/HTTP/decoded bytes; same private RAM socket |
| Writer SQL |statement_timeout8s,lock_timeout1s,actual local ingest role; main and fresh worker validate |
| Wall |1800s workload hardstop from launch; interrupt at1770s,force stop at1800s if needed |
| Disk |4GiB allocated bytes across this run's owned PG roots+evidence; warning/interrupt at3.5GiB; force stop at4GiB |
| Monitor sampling |At most1s for wall/disk; metadata heartbeat every15s |
| User-facing progress |At least every60s,using current/last completed phase and measured elapsed/disk |
| Cleanup grace |At most30s after force-stop; all owned child PGs stopped and directories removed; RAM untouched |

The disk threshold is a live supervisory threshold,not a filesystem-quota proof.
No automatic monitor was added/executed in this overlay preparation lot. ROOT's
launcher must use a minimal environment without inherited PG* variables,retain
the actual OS user/runtime paths and set STATARENA_SOURCE_FORBIDDEN=1 (RAM IPC
remains allowed). It must enforce the above independently; running the bare child without it
would not meet this proposed operational envelope. A different wall/disk bound
requires an explicit ROOT decision,not a silent retry or a larger SQL timeout.

Required supervisory procedure:

1.Verify RAM PID54737/socket exist without GET/refetch; hash the four frozen
source manifests/ledgers and code/overlay bytes. Refuse another real run directory
with this label. Launch the child as an owned process group and record PID/start.
2.Discover ONLY that new run under this namespace. Register its temporary PG
roots from its commands.json -D metadata. Accept only owned newly created
orion-pro-e2e-* roots from this process; never scan/delete unrelated roots.
3.Measure allocated disk across those registered roots and run evidence. Persist
only phase names,elapsed seconds,disk bytes,exit codes and hashes. Child PASS/
FAIL names and final counts/evidence path are allowed output. Unknown stdout or
stderr content is not copied verbatim; retain stream byte count/digest and use
the metadata-only result/error fields. No pg_dump,pickle,native SQL row or body
is an output artifact. Require the bootstrap pg_settings readback for terse/panic/parameters0,all from
configuration file. e2e.py now initializes each owned PG and writes those keys
before start; no shared harness is changed. This prevents statement/bind/failing-
row DETAIL retention before business writes.
4.Report heartbeat even while a core import/SQL oracle is in progress. The child
currently emits PASS/FAIL boundaries; the monitor must mark the active phase
from the known case order and identify that inference. Do not invent row-progress
percentages from uncommitted or absent rows.
5.On timeout/disk bound,interrupt the E2E process group so Python cleanup runs;
force-stop at the hard threshold if it does not exit. Stop any still-running
registered owned postmaster via its exact pg_ctl -D metadata,then remove only
those verified owned roots. Persist aborted/partial status. Never send STOP to
the source RAM server and never restart the capture.
6.Accept only exit0 AND all15workflow cases present exactly once and passing,independent478547native-state
and1344ordered-cell comparisons,matching source/typed digests and exact actor/
source-record/period/variant/units/cohort/locator contracts. A child status string
alone is insufficient. The success set is11preparations+4real cases,with exact
478547/1344 counters and the fresh no-op94/67 check. The fresh process must report reused core/spatial receipts
and unchanged94table/67sequence fingerprints. A timeout/abort/partial receipt is
failure even if some earlier cases passed. On SIGINT/hardstop/cleanup failure,
ROOT's external receipt must be failed/interrupted and all remaining cases
unverified. The child finally may emit a partial statuspass; it must never be
accepted as global success. Keep fullAcceptance=false for the
explicit remaining useful-field/profile/family gaps.

Expected phases are local empty/worker-DSN/overlay/deadline/source-startup/checkpoint/budget/
metadata/error preparations,then pure real_core_import,independent_native31,
real_spatial_import_and_oracle and fresh_process_noop. No synthetic correction,
foreign player or provider-collection fixture enters the real candidate.

ROOT's separate validator semantic/performance evidence remains the basis for
selecting this candidate. This integration preparation does not re-certify that
whole real sealing/import/oracle workload fits8s statements/1800s wall. Any new
performance/mapping failure must be preserved and reviewed from the same RAM.

Suggested commit: `test: add explicit local validator candidate policy`.
