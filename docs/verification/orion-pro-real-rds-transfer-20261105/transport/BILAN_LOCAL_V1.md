# Native transport — local qualification

New implementation: dashboard/scripts/orion_pro_native_transport.py
SHA2569ec803b5caa6a5c5a47c2154256ea8199847281931fe73a538862c70fa371487.
The original writer/test/policies/model/SQL/normalizer/candidate remain unchanged.
The new adapter borrows bounded native COPY/ownership/sequence methods from the
pinned V2, while owning separate origin, endpoint, journal, acceptance, release,
parameters, checkpoint, four-clock and counter contracts. Real counters record
local_only=false; fixtures can only authorize owned local execution. RDS uses
only statarena_ingest, exact host/database, verify-full and a private passfile.
No AWS/SSM discovery, ambient DSN, new grant, schema change or raw staging exists.

The complete local E2E passes21/21 in44.161s with41CLI invocations, one compact
fixture and one PostgreSQL18.6 cluster. Actual receipt:
`runs/20261105T110727916843Z-root-owned-tls-compact-v1-absolute/result.json`
SHA256e3349a7a21a2ec1d9eb9afe3b026a8ebcc07ce7a2e3a5910372da117d9bf5694.
Exact rerun command, setup, frozen sources, expectations, CLI outputs, logs,
resource measurements and cleanup are in that receipt and its inputs directory.

| Observation | Actual result |
|---|---:|
| Native tables / columns per endpoint |94 /1709|
| Native constraints / views / sequences |2475 /46 /67|
| Functions / indexes / triggers |90 /352 /84|
| Compact appearances / scalar slots / matches |40 /1240 /4|
| Core / remaining family rows copied |1544 /22|
| Copied rows excluding preserved12B0 rows |1566|
| Mid-COPY fault |50rows attempted; all94native rows rolled back|
| Native deadline fault |57014; complete phase rollback|
| Core interruption and fresh-process resume |0scalar rows recopied|
| Simulated lost commit acknowledgement and resume |COMMIT_ACK_UNKNOWN;0scalar rows recopied|
| Checkpoint corruptions refused |unknown key/count/checksum/clock|
| Fresh no-op |0COPY /0nextval;94tables+67sequence values unchanged|
| Next native player identity / source maximum |42 /40|
| Sequence value SELECT calls by writer |0|
| Maximum accounted metadata / buffers |9461865B /4708878B|
| Peak allocated owned disk |145584128B|
| Complete successful run artifact bytes |2659837B|
| Cloud / RAM source calls / RDS writes |0 /0 /0|

All four generated technical timestamps equal the native transaction timestamp.
Source/target native OIDs, bootstrap clocks and012013-vs012013014 journal clocks
are independently bound, not aligned artificially. Runtime COPY is natively
denied42501; only ordinary target ingest performs business DML. Target policy,
source value, producer, endpoint, foreign-data and malformed-control refusals
preserve the inspected target. Sequence reservations use metadata plus monotone
nextval and never setval or SELECT on sequence values. SQL deadlines remain8s/1s.

Proof limits are explicit. The source oracle is independent; this first test's
target inverse oracle calls NativeTransport.business, the writer's observer.
Generation and snapshot allocation were not deliberately separated. The exact
COPY/projection methods have older independent V2 qualification, but this21/21
receipt does not establish a new independent target oracle under G!=SID. A
distinct supplement, INDEPENDENT_PROTOCOL.md / independent_e2e.py, has a frozen
106column contract and is prepared without PG. It must pass its own separate
allocation before those additional conclusions are claimed or RDS is released.

This is a source-free compact TLS qualification, not real-source/RDS acceptance,
a production benchmark, a p95, full leaf fidelity, closed-interval support or
global dataset completion. The500k/table,2Mtotal and64phase bounds remain explicit
pilot admission limits. Full production needs partition-aware scalable ingestion,
closed history, remaining detailed families, source-wide reconciliation and joint
backend acceptance. No gain in web latency, RDS space or cloud cost is claimed.

Retained failures and commands:

* Genuine missing implementation RED, before new code:
  `runs/20261105T105654369754Z-precode-missing-native-transport-red/result.json`,
  0pass/1fail/20unverified,0PG. Original test/protocol bytes are archived.
* Setup command failure before any PG or allocation consumption:
  `runs/20261105T110637459209Z-root-owned-tls-compact-v1/result.json`.
  The exact command used a relative `--release`; initial evidence archiving
  rejected path.relative_to(ROOT). The command and observed ValueError remain.
* ROOT explicitly allowed the same unchanged code/test/unconsumed allocation with
  the absolute release path. Both commands appear in their own receipts. No old
  counter or allocation was reset. That continuation is the21/21run above.

Cleanup verified server_stopped=true and owned_directory_removed=true for
`/tmp/orion-pro-e2e-f0hl_b06`; all three observer connections closed. The original
21/21bytes are frozen for ROOT independent review and the supplementary test.

Suggested commit: `feat: add explicit native SQL transport for real RDS pilots`.
