# Capture-v2 source-only RAM inspection

ROOT_RELEASE_V2 permits one capture and metadata-only RAM inspection, not a local
PG import. Capture1498/normalizer4b98 are frozen. The ready RAM source must remain
alive until ROOT orders STOP. No new source query, object HTTP or reread is used.

The inspector reads the already captured snapshot via the owned0700/0600 Unix
socket and uses the independent packed-table decoder/FIELDS registry from the
reviewed E2E, never a mapper/SQL result as the expected source. It emits only
counts,type/precision metadata,source/version hashes,digests and missing IDs.
No sports scalar values,rows,biography,body,pickle or source table is persisted.

Count exact fixture/match/performance/shot/profile/team IDs,then31native slots
per accepted normalized performance. Preserve absent,null,number,string,boolean
and separate zero/empty-string observations. Evaluate exact nonnegative int32,
finite unconstrained-numeric projection and finite shortest-decimal double
round-trip rules independently. Unsupported/negative/fraction/range/precision
forms identify the field and source IDs without exposing the value. Check the
three common count-pair inequalities only when both observations are numeric.

For the declared direct Neon heatmap,independently count teams/player parents and
sparse triplets. Validate explicit grid metadata,frame,source ordering,triplet
arity,integer bounds/counts and duplicate coordinates without filling cells or
rotating. Compare every actor/side/team to normalized fixture and performance
cohort; missing/ambiguous IDs are qualified gaps,never synthesized participants.
Useful names/shirt fields remain unmapped qualifications; this source-only
inventory cannot accept their typed fidelity or repair the cohort.

Historical478547slots/1344triplets are compared to actual counts,not forced.
Typed SQL comparisons remain0 and fullAcceptance=false. Hash both old ledgers
and current budget before/after; no capture/normalizer/model/candidate change.
After writing metadata evidence,exit the inspector only and leave PID/socket
alive. No E2E main/worker or PostgreSQL harness is invoked.

```sh
PYTHONPATH=/tmp/statarena-publication-test-python python3 docs/verification/orion-pro-real-native-spatial-20261104/inspect_ram_v2.py
```

Suggested commit: `test: reconcile native metric and spatial source values`.
