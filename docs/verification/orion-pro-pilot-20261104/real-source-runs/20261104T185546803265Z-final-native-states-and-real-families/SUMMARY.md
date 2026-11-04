# Real-source typed local pilot — bounded result

**14/14 workflow checks pass; full data fidelity and migration acceptance remain blocked.**
This run used an owned disposable PostgreSQL 18.6, actual `orion_pro_ingest`,
012/013 and approved bounded model amendment `18da43f940870b7a3a3cb49323c847dd5e5174e5eea1f8ff0c8a159cf373cb08`.
It performed no RDS/S3/Neon write, provider call, second transfer or raw source copy.
The local server was stopped and its owned data directory removed.

## Verified scope

- Canonical typed rows: 612 unified match/fixture identities (387 finished),
  839 players, 20 teams, 15,437 participants/common statistic rows, 9,795 shots.
  Independent source/SQL oracle hashes cover fixture keys/status/dates,
  performance xG/minutes/goals/assists, shot IDs/xG/xGOT/minutes and public aliases.
- All 61,748 registered xG/xA/xGOT/minutes slots have matching source state,
  common numeric projection, source record, participant, source, team, period,
  variant and selected generation cohort. No missing state row is interpreted
  as source absence. Initial source/SQL SHA:
  `e08b11c0921f92580d77394619f3752108615404086e419c3da2f4c900716cf6`.
  Actual baseline states are number/null; absence is exercised only by the
  explicitly labelled in-memory simulated correction of a real source record.
- Correction through the real mapper changes xG 0.04→0.05, makes xA null and
  removes xGOT while retaining minutes. Old snapshot xG remains 0.04. The new
  complete state/value oracle also matches, SHA
  `6117b913b02db55a7f4873b7c07bd90bfcbf15ca3163a7f7c831f1793a236cb6`.
  Unchanged scalar revisions remain selected, avoiding artificial no-op versions.
- 26 exact archive members across two real matches and all 13 families produce
  12,852 additional typed projection rows. Raw metric occurrences have distinct
  source sub-records and explicit noncanonical variants; they are not silently
  deduplicated or summed. These family projections remain partial, and their
  complete leaf fidelity is unaccepted.
- 776 exact player profiles and 20 exact team profiles are accepted. The resource
  for `p_1JuxKR` selects `p_1Gu9XI`; that biography is rejected and a blocking
  identity-conflict issue retained. The 62 absent player resource lookups remain
  separate quality issues; normalized observed identities/profiles are retained.
- Same-instance/cache reimport adds zero rows/revisions across the checked facts,
  metadata and generation receipts. Fresh-process retry/recovery is not implemented.
- One local SQL read each: list 1.617 ms, player 10.129 ms, club 3.813 ms,
  match 0.731 ms. These are local samples, not an RDS benchmark, p95 or gain.

## Budget and reproduction

The final run used 11 indexed AWS reads and 31,923,069 decoded bytes. Cumulative
subtask usage, including preserved failed runs and metadata censuses, is 56
queries / 159,027,145 decoded bytes, below the approved 100 / 256 MiB caps.
Each run had one verified-TLS read-only source connection; original failures,
selectors, source hashes, exact queries and cumulative budget remain inspectable.
No source bodies are in evidence; only typed local SQL, code/spec inputs and
metadata/hashes were used.

From the repository, with the existing pgpass and local embedded PG18.6/runtime:

```sh
PYTHONPATH=/tmp/statarena-publication-test-python python3 tests/orion_pro_real_pilot.py --label final-native-states-and-real-families --phase families
```

A rerun consumes the remaining approved source budget recorded by
`../../real-source-budget.json`; do not reset that ledger to evade the cap.
`commands.json` and `result.json` give local setup, outcomes and cleanup;
`source-queries.json` gives source setup/SQL/parameters/versions/timings;
`normalizer-report.json` gives independent oracle SQL, bindings, profiles,
precision inventory, mapping gaps, no-op counts and read timings. `inputs/`
retains the executed importer/test/protocol/model, approval chain and local
migration SQL verified against runtime migration hashes. `summary.json` pins
artifact hashes and distinguishes remaining gates.

## Remaining gates

No acceptance of all useful source leaves, all 512 archive source bodies,
coordinate/media contracts, complete raw/common metric selection semantics,
fixed-scale ranking/standing precision, fresh-process restart, web/HTTP integration,
RDS typed data migration or purge follows from this bounded result. No common
nullable metric outside the four registered slots is declared native-lossless.

Suggested commit: `feat: normalize verified AWS sources into the local Orion Pro pilot`.
