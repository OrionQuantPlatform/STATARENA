# Committed core ready through readonly recovery

The original stopped typed root is recovered and retained readonly for ROOT's
separately released RDS transport. No database, fixture or sports corpus was
constructed again. The recovery passed7/7stages in27.953s with2RAM reads,
0cloud calls and0business/schema/sequence writes. The spatial57014failure and
all prior consumed allocations remain unchanged and visible.

Ready evidence:
`runs-v2/20261105T115732447984Z/ready.json`
SHA2565fff62d19c678dabdebd3595da250b5d2a9c86419c9b777e679036f5d29af837.
Checkpoint:
`runs-v2/20261105T115732447984Z/checkpoint.json`
SHA25635dba5b977335c957d39472ca85dbfc6c2ce0074a94a558badbec32f82fb73cc.
Its exact command, code/pin/release inputs, queries, native oracles, fresh process
receipt and resource observations are adjacent. A final stopped receipt will
only be written after STOP; READY does not claim completed cleanup.

| Verified observation | Result |
|---|---:|
| Actual engine/TLS |PostgreSQL18.6 / verify-full|
| SQL/lock/idle transaction deadlines |8s /1s /15s|
| Database/journal |postgres /012013+exact P1body, no fabricated014row|
| Native tables/columns/FK/constraints/views/sequences |94 /1709 /431 /2475 /46 /67|
| Committed source phase |core/run1/generation2/snapshot2, sealed|
| Players/teams/matches/native metric slots/heatmaps |839 /20 /612 /478547 /0|
| Source performances/native fields |15437 /31|
| Native31 source and SQL digest |5f9175c1526ad2db4426ebe02d3e412e20999c2bd6486aef5d82d082f34255e0|
| Native31 oracle duration |6.284s overall|
| Native94+67 independent observations |4.826s before /4.848s after|
| Fresh core_only no-op duration |10.046s overall; per-SQL deadline unchanged|
| Fresh no-op new fact revisions/duplicates |0 /0|
| Native94 rows/hash |553562 /220b5da11d56ae16c010fbaa35c535b389af6fe8bc55988a84804f27057d1eb8|
| Before/after native94+67 comparison |Exactly equal, including rollback sequence gaps|
| Peak observed allocated retained disk |1602404352B|

The actual ordinary ingest fresh process used the frozen candidate exclusively
with core_only=True. Runtime and ingest have zero privileged flags and zero
effective/explicit memberships. The readonly owner has exactly the implicit
pg_database_owner membership after database ownership proof, zero explicit
membership grants and no privileged flags. The installed PostgreSQL catalogue
definition supporting that implicit relationship is pinned and archived. No
permission was granted to make a test pass.

The previous recoveryv1 remains a real failure:
`runs/20261105T114758199244Z/result.json`,
SHA256f762912c787f4431d28d6cada245c60902a6148a39b334c631174d08ef6ca7b2.
It confirmed core/native31, then rejected the legitimate implicit owner role
before the67sequence read/no-op. It consumed1restart/1RAM read and stopped the
server while retaining data. V2 has distinct code/test/pins/release/ledger/run/
marker files; it neither resets nor relabels that attempt. The v1/v2 missing-code
REDs and source-free4/4CLI receipts also remain inspectable.

Scope remains the committed core minimum for backend progress. Heatmaps and
remaining original detailed families/full leaf fidelity are explicitly open;
0typed heatmaps does not mean an observed empty provider response. This is no
RDS business-write proof, final dataset acceptance, web benchmark or source
cleanup authorization. All original sources and the typed root remain retained.

Service handoff at READY: controller PID50858, postmaster PID50865, session43479,
port55467, private control `/tmp/orion-core-checkpoint-hltp2a74/control.sock`.
Actual source descriptor:
`runs-v2/20261105T115732447984Z/source-descriptor.json`,
SHA25646d33e0521f3a37e8bacef337663ae65218bdc89b24ca94cc3631e1af3c51c1b.
Only ROOT may order STOP after its transport; the service is limited to3600s idle.

Suggested commit: `fix: verify readonly recovery of the committed real core`.
