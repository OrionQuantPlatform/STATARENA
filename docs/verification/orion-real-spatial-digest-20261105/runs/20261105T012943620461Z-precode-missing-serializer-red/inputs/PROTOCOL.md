# Spatial native digest — pre-code isolated contract

ROOT authorizes only this narrow serializer correction and the spatial oracle's use/diagnostic persistence. The frozen real receipt `18a95e0…` is13pass/1fail/1unverified: Native31 compares478547 slots exactly;1344 spatial cells were visited, but the spatial assertion failed with `errors={}`. Its PG was cleaned up and its source budgets remain unchanged. That is the integration RED. It does not establish a mapper/source defect or a spatial success. The actual failed code SHA7ab6cd… is copied in PREDRUN_CODE before changes.

The old spatial oracle compares a parent tuple using Python equality, then hashes it with the global JSON digest's `default=str`. Capture1498 decodes JSON integers as Decimal, whereas PG integer columns return int. Decimal(1)==1, but that encoding treats Decimal as a JSON string and int as a JSON number. The new serializer must make the same native JSON number hash identically without equating a number with a string or boolean. A single RAM census may observe **type counts only**, never values. No cloud/source query, new capture, PG start/import or retry is authorized.

An isolated test is necessary because the new serializer does not yet exist and is a pure byte-format contract. The sequence is this failure matrix, complete test file, genuine missing-serializer RED, then implementation and the same test file unchanged. No new isolated tests cover the existing SQL oracle, connection mocks or mapper. The original real13/1/1 remains the integration RED; a separately authorized future15-case real run must verify usage and persistence. This small proof cannot replace it.

## Canonical format

The canonical UTF-8 JSON is `["orion_spatial_native_digest_v1",<tagged-value>]`, no whitespace, no Unicode normalization and no default coercion. Tags are `number`, `string`, `boolean`, `null`, `array`, `object`.

- A finite builtin int or Decimal is one JSON number. Encode as `["number",signed_coefficient_digits,base10_exponent]`, with the two components represented by strings, no leading coefficient zeros, and trailing coefficient zeros removed while increasing the exponent. Use Decimal.as_tuple and integer digit operations only: no normalize, context arithmetic, float or fixed decimal expansion. Thus1,1.00 and1E+0 agree;29+digits and all fractional digits survive. Numeric signed zero becomes coefficient"0"/exponent"0" because the comparison concerns the numeric value, not its original lexical spelling. The string"-0" stays a string. No raw lexical-source preservation is claimed.
- Boolean is checked before numeric and cannot become0/1. Strings, including empty and Unicode, retain exact code points. None is `["null"]`.
- Lists and tuples share the array tag because source containers and DB row tuples represent the same ordered sequence; order, nesting and empty arrays remain exact. A metadata dict uses object with sorted exact string keys and recursively typed values. Non-string keys refuse; object/array/scalar shapes cannot collide.
- Float, nonfinite Decimal, bytes, sets, arbitrary objects and unsupported types refuse with a generic error containing no value. Decimal contexts/traps cannot change canonical bytes. SHA256 is over the exact canonical bytes; the policy ID participates in those bytes.

## Failure matrix, written before implementation

| Case | Expected outcome |
|---|---|
|New serializer absent|Actual RED, remaining serializer cases unverified;0SQL/PG/cloud.|
|int/Decimal/equivalent decimal exponents|Identical bytes and digest for one exact numeric value.|
|number/string/boolean/null/empty|Distinct tagged bytes; no string=number or bool=0/1 collision.|
|signed zero|All numeric zeros agree; strings"0"/"-0" remain distinct.|
|29+digit ints and fractions|Exact expected coefficient/exponent; last-digit differences remain different.|
|Tiny/large exponent and trailing zeros|Canonical compact representation; no expansion or rounding.|
|Precision1 and28 plus Inexact/Rounded traps|Same bytes as the explicit expected representation.|
|Unicode and escape characters|Exact UTF-8; NFC and NFD remain distinct; no ambiguous framing.|
|Lists/tuples/ordering/nesting/empty arrays|Tuple/list equivalence only at container representation; order/nesting/state distinctions retained.|
|Metadata object order/keys|String-key sorting deterministic; non-string keys rejected.|
|Synthetic spatial-shaped metadata tuples|Source Decimal and typed int agree recursively; replacing number with string/bool refuses equality. No SQL mock or actual source values.|
|NaN/Infinity/float/unsupported type|Generic refusal with no payload echo.|
|Digest and type framing|Digest exactly SHA256 of manually expected typed bytes; malicious-looking string/array cannot impersonate a tag.|

## Narrow integration patch and later gate

Leave the global digest function, Native31 oracle, capture/candidate/normalizer/model/SQL, old receipts/ledgers and ROOT supervision untouched. Only spatial_oracle loads this versioned serializer and uses its digest for source_rows/typed_rows. Its result binds the serializer policy/path/code SHA. The real spatial branch must persist its metadata/counts/errors/digests to a new run-local `spatial-oracle-result.json` **before** asserting ok, so an error-free digest mismatch is inspectable. It must not persist the native source_rows/typed_rows or any sporting value. The future real E2E inputs also archive the exact new serializer bytes at that branch; old run inputs are immutable.

The test receipt contains explicit synthetic test inputs as code snapshots, exact command, expectations, actual statuses and byte/digest checks. No body is written. Source and typed real digests are not available from the old failed receipt; do not reconstruct them or call the old spatial run accepted. A future ROOT release must pin the changed E2E and new serializer and use a separate consumed-once attempt ledger. No v1 reset. Full acceptance stays false and fresh_process_noop remains unverified until it actually executes.

Suggested commit: `fix: canonicalize native spatial digest values exactly`.
