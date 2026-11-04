# Native common metrics: source-free result

The final frozen v2 transformer passes **8/8 local PostgreSQL workflows**. It registers 31 known normalized fields, including the 27 additional destinations in PLAN.md/FIELD_MATRIX.json. **0/416799 additional real states have been compared**. `fullAcceptance=false`; this result cannot be promoted by adapting counts in the frozen real-pilot test.

- All input fixtures are explicitly synthetic. The complete producer writes actual typed local SQL under the ingest role, with independent SQL native/common oracles.
- Numeric/null/absent/zero baseline: 124 slots; mixed five-kind fixture: 310 slots, with zero unknown missing native rows. Empty/09/4/7 strings and both booleans retain their exact scalar type/value with common NULL.
- 82 complete invalid imports reject atomically: int32 fractions/overflow/negative counts, precision-losing doubles, nonfinite/container values and inconsistent completed/attempted pairs. Rolled-back sequence gaps are distinguished from no-op retries.
- Numeric xG keeps 29 integer digits plus fraction in NUMERIC. Double-compatible 17-significant-digit rating keeps the original exact Decimal in numeric_value. Double projection uses only the documented finite shortest-decimal roundtrip rule, not an exact binary-rational claim.
- Registry definitions/mappings, unit/aggregation/signed flags, common_sql_type and exact number_projection rules are read back independently from SQL. The xG rule explicitly says exact finite unconstrained numeric, not int32/double.
- Canonical mismatch is refused; an independent SQL oracle also detects a deliberately injected mismatch. A separate source-record/variant retains 31 noncanonical scalars. The labelled correction preserves the old snapshot and 26 unchanged scalar revisions.
- A fresh exec process rehydrates and reuses the receipt: 94 tables and 67 sequences remain identical. Fingerprint: `082160f79a7f65a7ad8505a6316ad9224fc4218f2917d9647e92bfa19cda8416`.
- Frozen v1 receipt and direct v1 target refuse before writes. A synthetic stale prior with only metric_definition_version=v1 also refuses despite identical value/binding. Target/prior guards inspect already loaded metadata and add no per-field/performance SELECT.

Final receipt: `runs/20261104T213636678845Z-native31-final-contract-and-sha-guards/result.json`. Exact runtime inputs, SQL/logs, hashes, setup/rerun command and cleanup are retained there. The disposable local server/directory were removed. Shared sealed 012/013 remain byte-identical; no model/014/remote DDL or DML, source read/capture, real body copy, CI/frontend/WORKLOG/git publication occurred in this lot.

The old pilot folder, real test/counts and ledger are byte-identical to baseline fc524ec8be. Its 89/254796352 budget is historical and untouched. Older four-slot/source proofs and every RED/green in this lot remain historical; see the explicit RED index in final summary.json. The earlier test-oracle False==0 failure is preserved and explained.

Exact source/spec review delta from fc524ec8be: `review-from-fc524ec8be-native31-final.patch`. Immutable run evidence is listed separately in the file manifest. Old candidate `review.patch` is retained for its already archived manifest.

Runtime hashes:

- Normalizer `60ffccc54b9f83b109c896bd1daccfe438c25e371ed4fc5efe6a52676cc88843`
- Local E2E `c934633af65c1ef31574081ea49625c6d7e9e30c6c24c3882c377f978ff1435b`
- Model `18da43f940870b7a3a3cb49323c847dd5e5174e5eea1f8ff0c8a159cf373cb08`
- SQL 012 `f255868599c72d69f40f575a919045325ea1093a00fe4f5a6b96eae9f2c49f65`
- SQL 013 `85525221cad51b32aff79a777098211b4112f9f00ea7161ac93945654eeb6968`
- Result `373b75c31f4b41765d95e546017bbe0285cc3e2c1d4d40f1ff0f40b189909ca8`

Rerun from repository root:

```sh
PYTHONPATH=/tmp/statarena-publication-test-python /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 tests/orion_pro_native_contracts_local.py --label native31-final-contract-and-sha-guards
```

Remaining work is explicitly separate: acquire a bounded v2 source sample, compare the 416799 additional real states/IDs/versions, report incompatible numeric observations without silent drops, then reconcile remaining fields and the actual publication/application flow. No new source acquisition is authorized by this source-free receipt.

Suggested commit: `feat: preserve native states for all registered common player metrics`.
