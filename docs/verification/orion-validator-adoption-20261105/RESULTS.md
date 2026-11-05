# Local validator policy adoption — final evidence

The [final owned PostgreSQL E2E](runs/20261105T010443812152Z-exact-journal-clocks-final-root-green/result.json) passes **14/14 workflows**, with0failed/unverified. Receipt SHA256 `2c0ee1e7b7d873cd619c9703ec79e60baaa5cc5bfc847b9f0804816c9b513a3b`. This is **local-only compact adoption acceptance**, not an RDS apply, real-source import, streamer,107 approval, publication/cutover or purge. `fullAcceptance=false`.

## Delivered behavior

- [orion_pro_policy.py](../../../dashboard/scripts/orion_pro_policy.py) validates closed M0/P0/P1 artifacts, the existing approval/amendment and sealed012/013/producers, exact139/46 reversal, native nullability/catalogue and bootstrap. It creates no connection on import and accepts no arbitrary SQL/path/latest policy.
- [orion_pro_upgrade.py](../../../dashboard/scripts/orion_pro_upgrade.py) defaults to an offline plan. Preflight/apply accept only the owned loopback PG marker, two fixed local DB names and ordinary local roles. Apply additionally requires exact manifest/code/scope/current-state acceptance, the existing schema owner and migration/generation leases. It refuses populated first-adoption targets, drift and unknown/compensated chains.
- [014](../../../dashboard/backend/migrations/014_orion_pro_membership_nonnull.sql) contains only the previously qualified function. SHA256 `e0810f8670b2cb627ade2c76e3c8eb527ab31fd595d5cf939fd63bfc5cf649d6`; actual function-string SHA remains `30f86fa262fd4cf10307e78431350f25b9d7a5b353d0c76abc0594340edb5d20`. No table/column/index/trigger/grant/model or default compiler is changed.
- [P0 manifest](../../../dashboard/backend/schema-policies/orion-pro/m18da43-p013-original-v1.json), [P1 manifest](../../../dashboard/backend/schema-policies/orion-pro/m18da43-p014-membership-nonnull-v1.json) and their [native local oracle](../../../dashboard/backend/schema-policies/orion-pro/m18da43-p014-local-oracle-v1.json) are explicit and hashed. The oracle precedes the manifests; separate acceptance/receipts reference them, avoiding a hash cycle. They are marked local-only, with no qualified import pair.
- [099 restore](local-compensation/099_restore_original_validator.sql) and its [separate manifest](local-compensation/m18da43-p099-local-restore-v1.json) are explicit LOCAL test artifacts. They append099 while keeping014, restore only the original function and require their own acceptance. There is no production099/015 file. Future RDS compensation requires a separate manifest/acceptance and review.

Current hashes: helper `288139f30d6ba003f5befbb4d7a1a71ef6b0a9d2ada8b42641a1158c9ce32d63`; runner `1b1eade5be41dadb361267fff457b72083caab8d2e7f21543f1ef9e2c541fd14`; E2E `8c228f2c0d78b5b0f34f691745879302ca588c59b742c77d0cc81b3a87ac8b02`. P1 manifest `5250beb9a8f1bba003e44880eea04fd81029665912c2aa9e586f2d81e15ecdb9`; oracle `42e3f90c2c95fdae53c42839897649f6a20b166bcb51a1b202df8850095289d2`.

## What actually ran

| Workflow / measurement | Final observed outcome |
|---|---|
| Cluster / actors | One owned PG18.6, two DBs; schema owner/ingest/runtime all ordinary, no superuser/createrole/createdb/replication/bypassrls |
| Physical M0 |103 definitions /94 active tables /1709 active columns /431 FK; sealed012/013, original producers/bootstrap and13 protected input hashes unchanged |
| Function |139 exact NOTNULL membership substitutions,46 nullable comparisons retained across81clauses; actual1709 nullability declarations match; OID/owner/ACL/all native procprops preserved |
| Schema catalogue | Only the expected validator definition changes; every other native catalogue row stays exact |
| Bootstrap / facts | B0 artifact `379ef1…` and manifest `215870…`, ten seeds/two contracts/g1 and all sequence states preserved on adoption/compensation/no-op |
| Native facts fixture |40 appearances ×31=1240 canonical scalars, four draft matches;1585 native rows in39populated relations; independent SQL-native oracle covers all94relations |
| Typed fidelity | Large exact numeric/fraction, JSONB precise number, SQL NULL/JSON null, array/string and native metric states retained; no JSON→float round-trip in native hashing |
| Populated first target | Exact BOOTSTRAP refusal for three sealed generations; no adoption. A transactionally rolled-back local P1 overlay preserves all94native digests |
| Security / leases | Ingest/runtime runner refusals and native42501 function/journal denials; migration/generation leases each refuse without mutation |
| Atomic failure | Faults after function/before journal and after journal roll back actual DDL/journal, facts/bootstrap and sequences |
| Lost commit ack | Exception injected after actual commit; fresh RO readback proves P1+014; no false rollback claim, new-process retry is a no-op |
| Old guard | The actual frozen bulk v1 baseline guard refuses014; no compatibility tolerance added |
| LOCAL099 | Distinct acceptance, exact P0 restore and append-only012/013/014/099 chain; no-op unchanged; reapply014 on compensated chain refuses |
| Final campaign |20.407s; no additional dense fixture or remote/source action; all connections closed, owned PG stopped and directory removed |

The two new journal clocks were tested **natively**, including their exact transaction start and an observed clock after INSERT:

| New row | applied_at as UTC instant | transaction timestamp | clock after INSERT |
|---|---|---|---|
|014|2026-11-05 01:04:56.303160Z|01:04:56.303160Z|01:04:56.745180Z|
| LOCAL099|2026-11-05 01:05:01.935071Z|01:05:01.935071Z|01:05:02.360780Z|

Both are nonNULL and equal the actual transaction timestamp. Existing012/013 nonNULL installation rows remain exact; compensation also preserves014. Repeated applies change no applied_at. Marker Europe/Paris and runner UTC compare the same aware instant with microseconds; one-microsecond mismatch, naive and malformed values refuse. No fact timestamp normalization is allowed.

The row-digest oracle reads SQL-native text in real PK order and uses bounded framing, independent of the producer adapter. The runner's metadata accounting is retained-object accounting, not process RSS. Its reported buffer peak concerns the bootstrap inspection, not a streaming COPY transport or full-universe memory benchmark; configured row/buffer/metadata limits are enforced. See [summary.json](summary.json) and [environment.json](environment.json) for exact resource observations.

## Preserved chronology

| Run | Actual outcome and attribution |
|---|---|
| [Pre-code missing modules](runs/20261105T004016806082Z-precode-missing-policy-upgrade-red/result.json) |0pass/1fail/13unverified; no PG; real RED before product modules/014 |
| [First compact start](runs/20261105T004924688372Z-closed-policy-compact-adoption/result.json) |4pass/1fail/9unverified; text start-time guard incorrectly compared Europe/Paris vs UTC; ROOT approved exact aware-time correction |
| [Second start](runs/20261105T005346460618Z-exact-aware-start-time-root-run2/result.json) |11pass/1fail/2unverified; test incorrectly expected BUSINESS before the stricter BOOTSTRAP guard; product unchanged |
| [Historical functional14/14](runs/20261105T005756332134Z-exact-bootstrap-refusal-root-run3/result.json) | Real14/14 with runnerEA052; new applied_at was NULL and not asserted yet. Retained explicitly as pre-clock-fix history, not current clock acceptance |
| [Actual clock RED](runs/20261105T010315553525Z-journal-clock-null-actual-pre-fix-red/result.json) |9pass/1fail/4unverified; unchanged old runner fails exactly NEW_JOURNAL_CLOCK_NULL; precedes the one-line INSERT fix |
| [Final clock green](runs/20261105T010443812152Z-exact-journal-clocks-final-root-green/result.json) |14/14 on final runner, same E2E bytes as actual clock RED;014/helper unchanged; new oracle/manifests bind the new runner |

Every started cluster was cleaned up. Previous result bytes were not edited. Five prepared artifacts for each PG run are archived within that run; the historical14/14 artifacts remain linked to their old code/manifest hashes. [campaign.json](campaign.json) and ROOT authorizations2–5 retain the exact conditional allocations; five total compact starts are consumed. The expected clock RED is not a passing test or an unanticipated service failure. No sixth start is authorized.

## Reproduction and limits

```sh
python3 tests/orion_pro_validator_policy_local.py --label exact-journal-clocks-final-root-green
```

This is the exact final command. The current exhausted ledger deliberately refuses a new PG start. Further reproduction needs a fresh explicit ROOT campaign allocation while retaining this namespace/ledger/receipts; do not clear or reset old evidence. Snapshotted code/protocol, commands, prepared native catalogues, actual results, PostgreSQL logs, acceptance and diagnostics are inspectable in each run. [changes.patch](changes.patch) contains the new source/SQL/manifests, excluding the large generated oracle/proof copies whose bytes are bound by [final-hashes.json](final-hashes.json).

The previous exact-function9/9 proof remains the separate478547-scalar equivalence/performance evidence. This14/14 is compact adoption/journal/rollback acceptance. It does not re-prove the dense load or establish real source coverage, complete metric/identity/collection mappings, RDS micro-instance/global validator cost, WAN transport, streamer source-policy compatibility, public representation/reader readiness,107, cutover or purge. Production/RDS still require their own scope-specific adapter/acceptance/preflight/readback; this closed local runner cannot connect there. No typed source/overlay import pair is automatically accepted merely because it is called P0/P1.

Suggested commit: `feat: adopt versioned non-null membership validation locally`.
