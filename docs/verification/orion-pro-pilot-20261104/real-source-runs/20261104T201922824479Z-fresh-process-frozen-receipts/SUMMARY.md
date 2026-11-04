# Local typed pilot: fresh-process retry proof

The frozen code passes **17/17 workflow checks**. `fullAcceptance=false`: this proves bounded local restart/idempotence, not complete source fidelity or a remote typed-data migration.

- Initial RED: `real-source-runs/20261104T195411591350Z-fresh-process-precode-red/result.json`. A fresh exec process could see the old core receipt but could not reconstruct its IDs/maps.
- Final run: `result.json`; code/spec snapshots are in `inputs/`. The exact normalizer, test and protocol bytes match the captured inputs.
- Local PostgreSQL18.6, sealed migrations 012/013, actual `orion_pro_ingest` role. Runtime migration/migrator hashes are independently verified in `runtime-artifacts.json`.
- Canonical source comparison: 612 matches including 387 finished, 839 players, 20 teams, 15437 performances/common-stat rows, 9795 shots; 61748 registered common native-state slots. No missing-to-zero conversion or rounding is accepted.
- Core-only local phase boundary resumes in a new interpreter, creates only the two missing phase receipts, then a further new interpreter reuses all three.
- Real import-only workers PID 67785 and PID 67855 reconstruct IDs from SQL and reuse core/family/profile receipts. Complete fingerprints of 94 tables and 67 sequences remain identical: `5b4e059f3b902855337004270734d6e52972cef4af825e33bdd9254cbeec2566`. They execute no demonstration correction.
- Negative workers reject a changed physical family hash and a changed profile ordinal with the same full SQL fingerprint. Every source input is sent over owned same-user memory IPC; no importer maps or connection objects are passed.
- Family scope stays 26 members/13 families/two matches, 12852 typed projection rows. Full source-leaf reconciliation remains unaccepted.
- Profiles: 776 matched player observations and 20 team observations; 62 absent exact player resource lookups remain separate from the rejected `p_1JuxKR`→`p_1Gu9XI` wrong-member reference. No biography is invented.

The one authorized capture consumed 11 indexed read-only RDS queries and 31,923,069 decoded bytes; cumulative 78 queries/222,873,283 bytes out of 100/268,435,456. Both complete real E2Es and all fresh workers reused RAM and consumed zero additional source queries/bytes. `sourceCapture` in `summary.json` links the exact SQL, parameters, timings and physical/content hashes. No remote writes or raw bodies were persisted.

The initial fresh database alone runs the explicitly labelled E2E correction (xG number changed, xA null, xGOT absent, minutes unchanged). Both fresh normal imports preserve that later selected correction exactly. Their current-selection oracle can therefore differ from the earlier unmodified source; this is declared in each child report and is not called source-fidelity acceptance.

The four measured local read queries and hashes are recorded in `normalizer-report.json` (list/player/club/match). The local database was stopped and its owned directory removed. The RAM server exited successfully; its owned socket and directory were removed, as recorded in the separate capture receipt.

Exact executed command (requires the original live RAM capture):

```sh
PYTHONPATH=/tmp/statarena-publication-test-python /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 tests/orion_pro_real_pilot.py --label fresh-process-frozen-receipts --phase families --source-socket /var/folders/8z/mp96_9353w79bsgv7kftgk2h0000gn/T/orion-pro-source-cache-o5p_2yh2/source.sock
```

After RAM shutdown no raw fallback remains. The source-free process boundary rerun is:

```sh
PYTHONPATH=/tmp/statarena-publication-test-python python3 tests/orion_pro_real_pilot.py --label fresh-process-local --phase families --preflight-only
```

Remaining gates are enumerated in `summary.json`, including full 512-source reconciliation, other native metric contracts, fixed-scale precision for unsampled standings/rankings, changed-input repair and application integration. Missing/draft receipt recovery beyond the demonstrated core-only boundary is unverified. Root owns future transfer reconciliation and any remote data application; this lot changes no schema or shared module.

Hashes:

- Normalizer: `33aa00448ada3852ed246fbc7e7ba699b5e2153be882456596f4834d2e85d2d7`
- E2E: `f31e961afedfbc634844b2ac6fd9ee2bdd97d141f1ad9393d8c8cc8d2290f33a`
- Protocol: `3589a5625f868fd05e999ae5a7ce4793fe8531df6527e2ca71be6af99cb2b779`
- Result: `2d1b84f0f3a5e7c77aaeb995696e1df8480f383feeab61965bb2f4ac1fc12121`

Suggested commit: `fix: resume the local typed pilot with exact persisted phase receipts`.
