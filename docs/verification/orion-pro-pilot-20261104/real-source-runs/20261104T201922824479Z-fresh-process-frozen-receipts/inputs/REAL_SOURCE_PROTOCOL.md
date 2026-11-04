# Real-source local typed pilot contract

Specified before `orion_pro_normalize.py` exists. This contract supplements the
approved SQL pilot; the synthetic fixture is not production-source acceptance.

## Setup and frozen inputs

- Owned disposable PostgreSQL 18.6 through the existing `LocalPostgres` harness
  and `orion_pro_migrate.py --local --target 013`. Never edit the shared harness,
  model, migrations or integrity code from this subtask.
- Existing AWS RDS source documents only: Ligue 1 `l_3FJFUl`, 2025/2026 and
  2026/2027, exact paths/versions in `source_scope.json`.
- Expected comparison scope: 612 fixtures, 387 finished normalized matches,
  15,437 performance rows, 9,795 shots; 839 player identities and 20 teams.
- One read-only AWS connection at a time, repeatable-read snapshots, verified
  TLS, 8 s statement / 1 s lock deadlines; at most 100 indexed batched queries
  and 256 MiB decoded source bytes per full E2E run. No provider calls, source
  transfer, remote write or persisted raw source body.
- Local writes use `orion_pro_ingest`, `ingest.begin_generation` and
  `ingest.seal_generation`; provenance records metadata/locators/hashes only.
  Transform digest is computed from the real normalizer code.

## Interface frozen before code

`orion_pro_normalize.run_real_pilot(conn, evidence, source_scope, phase)` owns
one in-memory source reader for initial import, identical reimport and an
explicitly labelled source correction through the same transform. `phase` is
`core` or `families`; the report separates imported, rejected and unverified
fields/tables. It may not return full acceptance while useful fields remain
unmapped, numeric/state fidelity is unproved, or a required family is absent.

CLI: `orion_pro_normalize.py --local --source-scope PATH --phase core|families
--evidence DIR`; the local DSN is supplied through the existing environment,
never command arguments. The E2E test pins the accepted counts and independently
queries typed local rows. No importer code exists at the initial RED.

## Failure and edge-case matrix

| Trigger | Expected observable result |
|---|---|
| Importer missing | RED after actual local schema/bootstrap; zero AWS reads |
| Wrong local host, ownership, role or engine | Reject before source read/write |
| Source pointer/hash/index version changed | Reject with exact path/hash diagnostic; no partial sealed generation |
| Query/decoded byte budget exceeded | Stop source reads, roll back current local import; record consumed budget |
| Fixture, match, appearance, shot or public ID dropped/duplicated | Reject exact key/count comparison; no acceptance from net totals |
| Native null/absent/zero/empty string/empty list/unavailable | Preserve their distinct approved typed states; no `missing -> 0` coercion |
| String versus numeric shirt/position/metric fields | Approved native representation or explicit rejection; no silent string/number collapse |
| Fixed-scale numeric cannot represent exact value | Reject before SQL rounding; report target and source path, no raw response |
| Double precision decimal policy is unproved | Mark unverified/rejected; no lossless claim from a `number` type |
| 62 player resource lookups missing | Retain observed player/profile identities; quality issue, no fabricated biography |
| Wrong selected profile, team, provider or period | Reject or fail SQL constraint; preserve exact source/dependency revision |
| Identical source + transform | Reuse retained rows/generation selection; no duplicate typed facts or source metadata |
| Changed source value through same transform | New selected revision; old snapshot still reads old value, no direct SQL fixture shortcut |
| Unknown useful field/variant | Explicit rejected/unverified mapping disposition; blocks full acceptance and purge |
| Atomic network/heatmap change | Whole parent collection version and correctly bound typed children; no partial collection accepted |
| Structured source body in JSONB or EAV escape | Reject; only approved metric definitions/extensions and bounded technical metadata |
| List/player/club/match reads | Actual local SQL result keys/metrics match independently derived source oracle; measured timings labelled local |

## Evidence and rerun

Run `PYTHONPATH=/tmp/statarena-publication-test-python python3
tests/orion_pro_real_pilot.py --label NAME --phase core` from the repository.
Each run saves commands, setup/expected outcomes, exact code/model hashes,
metadata-only source budgets/version receipts, actual assertions, local SQL
read timings and cleanup. Original failures remain inspectable. No source
payload, local data directory dump or connection secret enters evidence.

Initial RED precedes importer implementation. Subsequent runs cannot relabel
source/mapping limitations as passed SQL checks. Family coverage and full
native-field inventory remain separate acceptance gates.

## Original-family phase, specified before its implementation

Before implementing the family transformer, the families-mode E2E must fail on
its missing interface after local bootstrap, with no additional AWS read.
The first representative scope uses the 26 uniquely resolved original members
for `m_0anhgc` and `m_2SY7ro`, thirteen families in each season. Core counts and
canonical comparison projections remain fixed. Raw observations may retain an
explicit noncanonical variant alongside the accepted normalized comparison
variant; the report must distinguish them and never count them as additional
canonical appearances or shots.

Each family must have an explicit source-version/member receipt, typed target
disposition, input/typed row count, and mapped/rejected/unverified leaf census.
Events, momentum and H2H require exact typed collection coverage parents.
Networks and heatmaps require atomic parents and typed children. Lineup native
shirt/position variants must retain their native type. Registered scalar metric
values may use the approved typed metric extension; unknown keys or value shapes
remain rejected/unverified, never an opaque source document or generic EAV body.
Null/absent scalar states are accepted only if the approved model supports them
and the accepted response plus registered field contract establishes that state.
Missing HTTP data or an omitted metric row alone remains unknown.

Full profile observations must select their exact source ordinal/member and
match provider identity. A resource status alone is not sufficient. The 62
missing full-profile resource lookups remain explicit quality issues.
The family test first requires the missing profile transformer interface before
source access, then accounts for 777 linked player candidates and 20 linked team
observations. Every accepted selector must return its requested ID and report its exact
physical version. Unavailable biographies remain absent rather than invented.

The subsequent independent metadata-only census
`real-source-runs/20261104T184401605916Z-profile-observation-census/profile-observations.json`
exposed a real pinned-source mismatch, after the first full-profile import was
correctly rejected and rolled back. Of the 777 player candidates, 776 select the
requested ID. `/players/p_1JuxKR` points to ordinal 25 in
`raw/profiles/profiles_players/1df490b9590737d7e9b09b2e.json.gz`, which actually
contains `p_1Gu9XI` (status 200). The original failure remains in the preceding
run. Before implementing the conflict disposition, the refined expected outcome
is: reject that biography, record one exact identity-conflict quality issue,
retain the normalized `p_1JuxKR` identity/profile, and accept only the 776 matched
player observations plus 20 matched team observations. The 62 absent resource
keys and this one existing-but-mismatched reference are separate findings.

## Four common metric native states, specified before implementation

Register the normalized source slots `xg`, `xa`, `xgot`, `minutes`. Each accepted
complete packed performance row establishes whether that property is numeric,
explicit null, or absent from that row. An absent metric SQL row is UNKNOWN and
must fail the oracle; it cannot establish source absence. HTTP failures, partial
provider responses and raw unregistered metric fields do not use this contract.

For every common projection, the registered scalar shares its exact
`source_record_id`, match participant revision, match/player/team, full-match
period definition, variant and selected generation cohort. The E2E independently
LEFT JOINs all four expected slots, checks all bindings, selected intervals and
numeric equality against `player_match_stats`. Null/absent rows have no scalar
or auxiliary values. No new model fields or opaque payloads are introduced.

Freeze a source-based correction through the actual mapper: use a real
performance with nonnull xG/xA/xGOT/minutes; change xG, make xA null, remove xGOT
from an explicitly labelled in-memory simulated source row, and retain minutes.
The new selected wide row must have matching number/null/absent/number states;
old snapshot keeps its old values and states. Unchanged scalar rows remain
selected and are reused rather than acquiring unnecessary revisions.
"Same generation cohort" means selected at the common row's knowledge
generation, checked with `ingest.selected_at`; it does not require equal physical
`recorded_from_gen` for an unchanged retained scalar. Re-inserting an identical
scalar merely to copy the wide row's generation would violate the selective
no-op guard. Every identity/dependency/variant binding must still match exactly.

Repeated raw metric group items are retained as separate noncanonical typed
observation variants with exact source sub-record locators. No group/item is
silently deduplicated or summed. Selection/aggregation of those variants remains
unaccepted until their semantic grain is reconciled.

Suggested commit: `feat: normalize verified AWS sources into the local Orion Pro pilot`.

## Review corrections: source collections and context-free numeric hashes

Specified before the reviewed implementation is changed. The pre-source E2E
boundary workflow uses the real local PostgreSQL numeric type and actual typed
collection writer, under the ingest role, inside a rolled-back synthetic
generation. It performs no AWS read.

- A 29-digit Decimal and another differing only in its last digit must preserve
  their exact PostgreSQL numeric values and produce distinct canonical hashes,
  even with Decimal precision set to 28. Integers larger than 28 digits,
  fractional precision, trailing zeros and signed zero are covered. Hash
  canonicalization must not call context-sensitive arithmetic or rounding.
- `events`, `points` and `recent_matches` properties are required in their
  respective accepted collection responses. Missing, null, non-list and invalid
  member forms must be rejected before a coverage receipt is written. Explicit
  `[]` alone is a verified empty list, stored as `empty_response`/`empty`/0.
  Invalid forms cannot clear or invent an accepted empty collection.

Capture both initial RED counterexamples, then implement the corrections and
execute one new representative real-source pass within the unchanged cumulative
100-query / 256-MiB source budget. No schema, remote migration or scope expansion.

## Fresh-process retry lot — frozen before implementation

The installed RDS 012/013 files are sealed and are not changed by this lot.
All writes remain in owned disposable local PostgreSQL. The source budget is
already 67 queries / 190,950,214 decoded bytes, capped at 100 / 268,435,456.
At most one further real-source capture (~11 queries / 32 MB) is allowed.
Subsequent iterations and exec-created fresh processes reuse that capture via
local memory-only IPC; no raw body, dump or serialized source file is written.

| Failure/transition | Expected result |
|---|---|
| Core sealed receipt exists, fresh interpreter has empty maps | Rehydrate exact IDs, aliases, documents, records, participants/stats and selected states from SQL |
| Identical core/family/profile inputs + transform + model | Reuse exact sealed receipts; zero new generation, metadata/fact rows, IDs or variants |
| Family/profile phase has same code but a different source hash/selector | It cannot be classified as the old no-op; reject or explicitly reconcile before writes |
| Phase receipt is draft, missing, inconsistent or not bound to transform/model | Reject; no reuse based only on a code SHA or an in-memory attribute |
| Normal CLI or fresh-process reimport | Import-only; never execute the demonstration correction automatically |
| Explicit E2E correction, then fresh import-only process | Preserve the later selected correction exactly; no repeated correction/new generation |
| IPC source cache unavailable | Fail; never silently re-read AWS or persist a raw fallback |
| Existing gaps | Keep fullAcceptance=false, 62 resource gaps and the wrong-profile conflict; no fabricated source success |

First capture a true exec-process RED with a small explicitly synthetic local
core/family/profile workflow and memory socket payload (AWS reads zero). Then
implement SQL rehydration and persistent metadata-only receipts in existing
operational tables. The final real run compares SQL row/identity/receipt
fingerprints before and after at least two fresh interpreter reimports, including
after the separately labelled demonstration correction. The child receives
source inputs only, never parent importer objects/maps or a persisted raw file.

Direction update explicitly relayed from Hugo: root now also owns missing/stale
Neon→AWS transfer and ID/version/content reconciliation. The earlier friend's
ownership limitation is superseded. This local retry lot performs no transfer,
provider collection, Neon/S3 action or remote DML.

### Restart implementation and reproducibility

`run_real_pilot(..., source_provider=..., exercise_demo=False)` is import-only
by default. The CLI also requires the explicit `--exercise-demo-correction`
flag to execute the labelled E2E mutation, and refuses that flag once a core
receipt already exists. A later selected correction is preserved on reimport.
This is retry/resume of identical inputs; changed source/selector/transform
bindings are rejected for explicit reconciliation rather than silently repaired.

Each core, family and profile phase stores one metadata-only
`orion_pro_phase_receipt_v2` in `ingest.import_runs.checkpoint`. The binding
includes the actual transform SHA/version, model SHA, sorted physical source
hash manifest, exact selector digest and dependency on the core input manifest.
The sealed dataset manifest also binds the compact report digest, while
`dataset_snapshot_documents` records exact document membership. Reuse verifies
all these bindings, the sealed status, generation and unique import run. It does
not update receipt counters/timestamps or call `begin_generation`.

A fresh interpreter reconstructs identity/alias maps, source documents and
records, participants, current common stats and registered native-state rows
from SQL. Source payloads cross same-user private Unix IPC only; importer maps
and connections never cross the process boundary. The source server closes its
one read-only RDS connection before serving the captured inputs. Missing IPC
fails without a live-read or persisted-body fallback. `pickle` is confined to
this owned same-user socket; it is not an external input protocol.

The preserved initial RED is
`real-source-runs/20261104T195411591350Z-fresh-process-precode-red/result.json`:
the fresh process found the old sealed core but could not reconstruct its maps.
The local boundary workflow now resumes from core-only, creates the two missing
phase receipts once, then retries all three in a second exec-created process.
The real workflow imports the pinned source input, runs a separately labelled
correction, and uses two further new interpreters to retry import-only. An
independent SQL fingerprint covers every row in all 94 typed/operational tables
and every sequence before and after each child. Two negative children change
one physical family hash and one profile selector; both must reject with the
same complete SQL fingerprint.

The source capture receipt and query metadata are in
`real-source-runs/20261104T201252441807Z-restart-source-memory-capture/`.
Its single capture consumed 11 indexed queries / 31,923,069 decoded bytes,
making the cumulative budget 78 / 222,873,283. Further local/IPC runs consume
zero source queries/bytes. The exact full test command, argv, code/spec inputs
and all worker PIDs/outcomes are captured by each `result.json`. An always
available source-free rerun is:

```sh
PYTHONPATH=/tmp/statarena-publication-test-python python3 tests/orion_pro_real_pilot.py --label fresh-process-local --phase families --preflight-only
```

The real E2E additionally needs `--source-socket PATH` while the owned RAM server
is alive. Once stopped, its raw inputs are intentionally unrecoverable from
evidence. Repeating a real capture requires a separately authorized source
budget; the current capture command rejects a changed cumulative checkpoint.
All acceptance limitations above remain, including fullAcceptance=false,
62 absent exact resource lookups and the one rejected wrong-profile member.

Suggested commit: `fix: resume the local typed pilot with exact persisted phase receipts`.
