# Approved core fields: 017 SQL and binding qualification

Suggested commit: `feat: preserve three native match core fields in typed observations`.

This workflow precedes the additive017 SQL. The approved f516 model and016 proof remain separate. Materialize a new107-table,1911-column model; the only structural changes are the six approved columns and three pair CHECKs on `football.match_observation_details`.

1. On an owned, populated016 database, read the old observation and old native binding. The six core columns must be unavailable before017. Apply017 and its journal inside a forced rollback and verify the old shape remains exact.
2. Commit017 and check98 active tables,1829 active columns and447 foreign keys. Existing typed values and native identity/clock remain exact; all six new values/states on legacy rows are NULL/unrecorded. A checked journal reapply has no DDL or writes.
3. Insert synthetic observations through ordinary ingest with recorded `''`, `false`, `null`, and omitted properties. Read the precise state and value from a separate runtime connection. Reject a value with `unrecorded`, a SQL NULL with `value`, and an unsupported state on each pair. No type coercion or URL safety fallback.
4. Existing append-only observation guard rejects updates/deletes and any attempt to append through a sealed generation. Corrected values have distinct source evidence under the existing observation grain. No new history relation or copied body.
5. READYs use unchanged `summary-v1-shots-v1` and pro1. 016-native and017-native select different immutable transform/metrics bindings and model hashes. Confirm the old native token remains valid, an upgraded 017 build changes the native token, and a current017 build cannot be replaced by 016 or legacy. Correctness of old/new HTTP bodies and selected publisher closure is separately measured by the category E2E, not a static model check.

Artifact: exact setup, SQL/command, fixtures, expected and actual rows/states, migration journal and role readback, old/new binding metadata, cleanup. No real RDS apply follows from a static model or local proof alone.
