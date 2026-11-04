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

Suggested commit: `feat: normalize verified AWS sources into the local Orion Pro pilot`.
