# Scoped fresh-process retry and explicit capture checkpoint

The final frozen code passes **17/17 workflows**, including **11 offline CLI transitions**. `fullAcceptance=false`: this is bounded local retry/resume proof, with the source-fidelity and application gates in `summary.json` still open.

- Initial fresh-process RED: `real-source-runs/20261104T195411591350Z-fresh-process-precode-red/result.json`.
- Capture-checkpoint CLI RED: `real-source-runs/20261104T203046620864Z-capture-checkpoint-cli-final-precode-red/result.json`. The old parser refused the current 78-query setup. Final subprocess tests deny every `psycopg.connect` and prove exact-checkpoint acceptance offline plus pre-connection refusal for omitted/mismatched/missing/over-budget input.
- Unrelated-identity RED: `real-source-runs/20261104T203929881838Z-unrelated-identity-final-precode-red/result.json`. Both exec processes failed with `SQL rehydration identity membership differs: people` after an unrelated player/alias was added AFTER core.
- Corrected rehydration uses expected alias keys and the sealed core's source/document membership. Final real import-only processes PID 75417 and PID 75429 load 839 pilot players while the global table retains 840 players including the explicit synthetic foreign identity. Its player+alias SHA remains `84f7a36ea0f44eb5e9268567f91eadf25e6fc02b9fd4e0c05fdfd121d553ea87`.
- All 94 table rows and 67 sequences remain exact after each of the four exec children, including changed family-hash/profile-selector refusals. Global fingerprint: `bd17884207c4740b59507228bf9c35bd7102c7e716fb55b3b04be054630217b8`. The baseline includes the foreign fixture; its initial setup generation is not counted as an idempotent replay.
- Core/family/profile receipts bind actual physical source versions, exact selectors, model and typed transform. Every normal retry is import-only; the demonstration correction is separately requested only in the initially fresh E2E database and is retained exactly by fresh reimports.

Scoped canonical source oracles check 612 matches including 387 finished, 839 players, 20 teams, 15437 performances/common-stat rows, 9795 shots and 61748 registered common native slots. Representative family scope stays 26 members/13 families, 12852 typed projection rows. Profiles retain 62 absent exact lookups separately from the one rejected wrong-member biography (`p_1JuxKR` selecting `p_1Gu9XI`); no biography is invented.

The one newly authorized capture started from explicit 78/222,873,283 counters and consumed 11 indexed RDS read-only queries/31,923,069 decoded bytes. Final cumulative usage is **89 queries/254,796,352 bytes**, under unchanged 100/268,435,456 hard caps. RDS closed before serving RAM. Every final E2E/replay consumed zero additional AWS queries/bytes. Capture code SHA and typed transform SHA are separately recorded because the SQL-scoping fix used the same already validated in-memory source inputs.

Only 13,639,104 decoded bytes remain. The real post-capture check-only attempt at 89/254,796,352 correctly refuses a full 32-MiB capture before connecting, with the ledger unchanged. No reset or fallback is permitted. See the capture directory's `capture-checkpoint.json`, `capture.json`, exact query/timing metadata and `post-capture-checkpoint-refusal.json`.

Runtime: owned disposable local PostgreSQL 18.6 and actual `orion_pro_ingest`; sealed 012/013 SQL/migrator hashes verified in `runtime-artifacts.json`. Local SQL list/player/club/match timings and hashes are in `normalizer-report.json`. Local database cleanup is complete. RAM source exited successfully; its socket and owned private directory were removed, as recorded in its separate capture receipt. No shared schema/module, remote DDL/DML, provider, Neon/S3, WORKLOG or git action was performed by this lot.

Exact final command, from repository root while its original RAM server is alive:

```sh
PYTHONPATH=/tmp/statarena-publication-test-python /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 tests/orion_pro_real_pilot.py --label final-scoped-restart-and-explicit-checkpoint --phase families --source-socket /var/folders/8z/mp96_9353w79bsgv7kftgk2h0000gn/T/orion-pro-explicit-capture-xq0cgxwy/source.sock
```

Exact newly authorized capture command (historical checkpoint 78, cannot be replayed against final 89 without legitimate remaining budget):

```sh
PYTHONPATH=/tmp/statarena-publication-test-python /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 dashboard/scripts/orion_pro_normalize.py --local --source-scope docs/verification/orion-pro-pilot-20261104/source_scope.json --phase families --evidence docs/verification/orion-pro-pilot-20261104/real-source-runs/20261104T203343341015Z-explicit-checkpoint-memory-capture --memory-source-server --source-socket /var/folders/8z/mp96_9353w79bsgv7kftgk2h0000gn/T/orion-pro-explicit-capture-xq0cgxwy/source.sock --expected-source-queries 78 --expected-source-bytes 222873283
```

Always available offline/synthetic reruns:

```sh
PYTHONPATH=/tmp/statarena-publication-test-python python3 tests/orion_pro_real_pilot.py --capture-cli-only --label capture-cli --phase families
PYTHONPATH=/tmp/statarena-publication-test-python python3 tests/orion_pro_real_pilot.py --preflight-only --label scoped-retry --phase families
```

Full source bodies are intentionally absent from evidence; no raw fallback remains after RAM shutdown. Full 512-source/native-field fidelity, unsampled fixed-scale precision, changed-input repair and frontend/backend/remote bulk acceptance are not established. The tested foreign graph is explicitly only a player+alias, not a complete second competition. Test-launcher/fixture setup failures are preserved and distinguished from the concrete production REDs in `summary.json`.

Hashes:

- Normalizer `0795110b6cdc170237bdd8fbf29a4afbafbf2b47f12b0870236c75c3df3b0b40`
- Test `b29c51f115fb67df233f56fea2ca87c6284f918cb2189a06bb8dd88d16167aef`
- Protocol `57398efe91139c901afc2f887c8e3b925257ae2cab6e29827ed1ada333bf057c`
- Result `c0a77ad59ffe154989f3dd813dcc0f6b4f02dd635ccd6d49cc53b7a13af8d2c9`

Suggested commit: `fix: scope pilot retries and require explicit capture checkpoints`.
