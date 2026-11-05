# Readonly recovery of the committed real core

This distinct workflow recovers only the already committed core for the backend.
It does not replay construction or spatial ingestion and does not redefine full
data acceptance. The failed source receipt, its ledgers and ROOT cleanup recovery
remain immutable. No business row, sequence, schema, grant or old marker changes.

Fixed retained root:
`/var/folders/8z/mp96_9353w79bsgv7kftgk2h0000gn/T/orion-pro-e2e-939fcgo9`,
database postgres, port55467, PG18.6. ROOT stopped it after the spatial57014
rollback. The committed core has839players,20teams,612matches,478547native metric
slots,0heatmaps and one core run1/generation2/snapshot2 sealed. This is the only
root that may be restarted; no initdb, CREATE DATABASE, fixture or reconstruction.

Failure matrix and expected outcomes, fixed before new controller code:

| Stage | Expected result |
|---|---|
| Missing controller | Genuine missing-file RED; dependent cases unverified;0PG/RAM/cloud |
| Default CLI | Offline plan,0connections/PGstarts/RAM GETs; ambient credentials ignored |
| Absent/stale release or unknown root/host/spatial flags | Refuse before driver, process, socket or PG action |
| Source pins | Exact failed receipt/ROOT recovery/overlay, frozen model/012013014/normalizer/candidate/capture/independent oracle, capture-v3 READY and unchanged cloud ledger |
| Once-only allocation | Separate ROOT release binds controller/test/protocol/pins and exact old root/port; no reuse/reset |
| Retained root | Private same-UID root/data/old marker/certificate; PG_VERSION18; server stopped; no different root or running postmaster accepted |
| Restart | One pg_ctl start of that data directory, literal loopback/55467/TLS, default_transaction_read_only=on at server startup;8s SQL/1s lock/15s idle transaction settings |
| Native identity/security/P1 | postgres, ordinary runtime/ingest/owner roles, actual TLS, RO RR; model94/1709/431FK/2475constraints/46views/67seq; exact validator OID22061/owner/ACL/body/properties from retained overlay; journal012013 only |
| Existing core phase | Exactly one partial source run, phase core/run1/g2/sid2 sealed, no additional nonbootstrap snapshot/run; exact frozen normalizer version/hash; expected core counts,0heatmaps |
| Independent native31 | One frozen RAM GET, no cloud request; frozen independent unpack/native oracle proves478547slots/15437performances/31fields, identities/states/values/digests exact; no spatial oracle or import |
| Native94/sequence67 before | Independent SQL-native oracle through runtime, sequence values through readonly owner; record all digests/counts/values, including gaps left by spatial rollback |
| Fresh core-only no-op | Separate fresh process, one additional RAM GET; actual orion_pro_ingest connection is read-only; frozen candidate called with core_only=True exclusively; reused core=true,0newFactRevisions/duplicates, no spatial result; mutating SQL/function names refused before execution |
| Native94/sequence67 after | Exact equality with before; no reseeding/setval/new rows; source capture cloud ledger byte exact |
| READY | New private marker with actual new postmaster epoch, readonly source descriptor, native94 evidence and one-phase checkpoint. Scope=committed_core_only; fullAcceptance=false, heatmaps absent and other detailed families open |
| Retained idle / STOP | Close every DB client; retain readonly server for the separately released adapter, at most3600s. STOP or failure stops this owned server but preserves its typed data directory/corpus. Never call LocalPostgres.cleanup/rmtree on it |

The operational recovery command is the end-to-end workflow. The test harness
executes real CLI source-free tripwires and can replace itself with that command
only under a separate exact ROOT recovery release. No new PG or RAM access is
authorized by this preparation. Future proposed bounds:1restart,0construction,
0business writes,2RAM GETs,300s active work,3GiB retained allocated disk,64MiB
evidence,3600s idle. All subprocesses use the qualified global-deadline helper;
cleanup has its own bounded15s deadline and always retains the typed root.

Evidence per attempt contains exact nonsecret inputs/hashes/rerun command,
expected/actual cases, query log, native31 and native94/67 results, readonly SQL
counts, actual updated epoch/descriptor, unchanged cloud ledger and cleanup.
RAM snapshot values are never persisted. The original source counters remain
4SELECT/9682314decodedB/3HTTP/3961physicalB; this workflow records only its own
two RAM reads without resetting the earlier source allocation or ledgers.

P1 and source provenance remain local SQL checkpoint facts, never RDS policy
aliases. ROOT owns real target P1 comparison, credentials, pair/release and RDS
independent readback. Spatial admission/performance and full-data completion stay
open; the new core checkpoint must make those missing families visible.

Suggested commit: `feat: recover committed real core through readonly checkpoint`.
