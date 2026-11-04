# Source-free native common metric contracts

Only `orion_pro_normalize.py`, the new local E2E and this evidence directory are
owned. No source service, capture, frozen proof/ledger, schema, migration,
frontend, CI or shared module is modified. Every fixture is explicitly synthetic.
The existing four-slot/source oracle remains historical. **0/416799 new real
states are verified**; real confirmation needs a separate authorized capture.

The exact 27 destinations/checks are frozen in FIELD_MATRIX.json and PLAN.md.
All 31 registered normalized fields use the existing scalar metric table with
number/string/boolean/null/absent states. Strings, including empty/09/4/7, are
never parsed; booleans are never counts. Non-numbers have NULL common numeric
projections. Numeric integer counts must fit nonnegative int32; npxg is
nonnegative. Rating/goalsPrevented are signed finite values without an invented
rating scale. Units stay source_native and aggregation none. No numerator,
denominator or display value is invented from a standalone scalar.

For existing double columns the rule is exactly
`Decimal(str(float(native_decimal))) == native_decimal`, with a finite float.
This is shortest-decimal roundtrip compatibility, not exact binary rational
equality and not proof of original lexical JSON spelling. The native
numeric_value is always the original exact Decimal, never the float result.
Unrepresentable fractional/overflow count numbers, inexact double projections,
nonfinite numbers and arrays/objects reject the observation atomically. They
block that field rather than trigger schema changes, rounding or a JSON escape.

| Failure/transition, specified before mapper code | Observable expected result |
|---|---|
| Numeric/null/absent/zero core import | 31 registered slots per accepted performance; exact independent SQL native/common oracle |
| Empty/text/boolean source forms | Exact typed scalar and NULL common projection, never coerced |
| Fractional or overflowing count; inexact double; nonfinite/container | Actual complete core import fails and leaves no committed fact/metadata rows; rolled-back sequence allocations may leave gaps |
| Pair checks (completed<=attempted) | Reject inconsistent numeric projections; do not fabricate denominator |
| Independent native/common mismatch | Producer refuses and independent SQL oracle detects a manually injected mismatch |
| Repeated variant/period/source observation | Distinct record/variant rows remain distinct, with exact participant/source/period/cohort bindings |
| Labelled correction | New number/null/absent/text/boolean states match new common row; old generation stays exact; unchanged scalar rows retained |
| Same source/transform, new interpreter | Rehydrate, reuse receipt, preserve all table rows/sequences/IDs and later corrections |
| Old v1 four-slot receipt | New `real_source_core_v2_native31` rejects before writes; old receipt/rows remain exact |

The E2E first imports numeric fixtures through the old mapper to capture the
actual missing-27-slot RED. It then uses owned disposable PostgreSQL18.6,
sealed012/013 through the shared migrator and the actual ingest role. SQL oracles
read the typed tables independently of mapper helpers. Invalid inputs traverse
complete core imports inside rolled-back transactions; their sequence gaps are
distinct from identical-input retries, which must not allocate anything.

The final receipt saves code/spec/model hashes, exact rerun command, synthetic
fixture recipe, expected/actual case results, SQL hashes, subprocess metadata and
cleanup. No real row/body is stored or read. Frozen pilot tests/protocol/ledgers
remain unchanged. Old transform receipts are not upgraded in place.

```sh
PYTHONPATH=/tmp/statarena-publication-test-python python3 tests/orion_pro_native_contracts_local.py --label native31
```

Suggested commit: `feat: preserve native states for all registered common player metrics`.
