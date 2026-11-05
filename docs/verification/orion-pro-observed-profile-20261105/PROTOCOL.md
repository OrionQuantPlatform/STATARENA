# Retained observed profile — corrective pre-code contract

Suggested commit: `fix: retain captured appearance profile observations`.

The original appearance22/22 bundle remains immutable. This new focused E2E is
written before any corrective production change. No model/DDL/old-reader/entity/
operational/common module or original22-case expectation changes.

## Concrete allowed state

012:7289 binds `(match_players.profile_version_id,player_id)` to the physical
`player_profile_versions(id,player_id)` row. 013:519–544 makes its typed values
immutable but permits one interval closure. The native membership guard at
013:2340 requires a selected canonical parent having the same player_id and
profile_context as the anchored profile; it deliberately does not require the
same physical profile ID. A changed profile in the same context can therefore
replace the canonical selection while a canonical match participant retains its
captured physical pointer. The native unique indexes permit exactly this closure
plus replacement, without allowing two overlapping canonical profiles.

The physical captured profile must continue supplying the performance name,
playerRef and image pointer. Neither a later cg nor a later dg should replace or
hide it. Reading at(pp,cg) currently loses it; merely switching to at(pp,dg) would
still lose it for a later data snapshot with the same retained participant.
The intended narrow correction is physical ID+actor ownership and a nondeleted
observed row; preferred/current resource profile selection remains separate.

## Before-code cases

| Case | Setup / input | Expected observable outcome |
|---|---|---|
| P01 | Original7357row/36match/192performance typed fixture, PG18.6/Node24 actual handler | Native012/013/014 and runtime read-only; original token resolves |
| P02 | Initial JSON partition, limit2 |200 with captured Cohort player01/cohort_observed_01 and imageA; baseline body/tag saved |
| P03 | Close physical profileA in one native generation; insert changed profileB sameactor/context, new name/ref and distinct imageB; seal; publish oldDG/newCG and then newDG/newCG | Native constraints accept both builds and publication; six still-selected participants keep profileA; current profileB is selected; physical old name/ref/image immutable and retained |
| P04 | Actual HTTP oldDG/newCG |200, all appearance fields exactly equal baseline; current code expectedRED503 at this case |
| P05 | Actual HTTP newDG/newCG |200, same captured fields; prevents a dg-only workaround |
| P06 | Packed full partition under later token | Existing decoder recovers192rows and all old captured structural/native fields/types; no profileB name/ref/image leaks |
| P07 | Old/new token GET, HEAD and IfNoneMatch; mutate only unused imageB metadata | Old facts/body/tag unchanged; new token body stable; HEAD304metadata-only/zero body; unused profileB asset does not invalidate captured profileA responses |
| P08 | Boundary/cleanup |0legacy/current/source/external reads; all source pins stable; owned processes/directory removed |

One owned local cluster is proposed under the existing8k typed-row allocation,
600seconds/4000externalSQL/200actualHTTP/96MiB evidence/1GiB owned disk/5connections,
COPY batches≤1000. Launch only in ROOT's coordinated slot. Stop at first failure,
retain exact command/setup/inputs/SQL/HTTP/expected/actual/cleanup. No constraint,
index, interval or trigger may be bypassed to create this state.

UX: captured historical identity remains stable. DX: one physical-join correction
with no formula or DTO expansion. AX: reproducible legal closure+membership proof,
named RED and unchanged original acceptance cases. Real-data/cutover remain open.
