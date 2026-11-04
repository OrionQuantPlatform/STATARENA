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

Suggested commit: `feat: normalize verified AWS sources into the local Orion Pro pilot`.
