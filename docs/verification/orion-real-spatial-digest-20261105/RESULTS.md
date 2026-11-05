# Native spatial digest — bounded result

The new serializer passes **14/14 isolated contracts**,0failed/unverified, in [the source-free green receipt](runs/20261105T013047511236Z-exact-native-spatial-serializer-green/result.json). The identical test SHA7aee9086… first produced a genuine [missing-serializer RED](runs/20261105T012943620461Z-precode-missing-serializer-red/result.json):0pass/1fail/13unverified. Tests and manually expected typed bytes were written before implementation. This isolated scope covers only the new pure serializer; no existing SQL oracle unit, mock connection, PG start or real import ran.

The one authorized RAM type census confirms Decimal parent actions for2teams+30players, and Decimal action values for351+993=1344 cells. It persists counts/types/hashes only. Capture1498's parse_int=Decimal, the old Python tuple equality and the old JSON default=str explain a representational digest mismatch: Decimal/int can compare equal while encoding as string/number. The historical13/1/1 real failure remains unchanged. Its spatial digests were lost before persistence, so this result does not claim to reconstruct those digests or exclude another integration issue.

[spatial_native.py](spatial_native.py) uses explicit typed tags and a versioned domain; finite int/Decimal share an exact coefficient/exponent representation. No float, Decimal.normalize, context arithmetic or precision truncation is used. Strings/bools/null/arrays/objects stay distinct; tuple/list container representations agree. Numeric signed zero normalizes to numeric zero, with no claim to retain the original JSON numeric spelling.29+digit integers/fractions, restrictive Decimal contexts/traps, Unicode and rejected forms were actually exercised.

The [source-helper.patch](source-helper.patch) changes only spatial_oracle's digest use/binding and the real spatial branch's archival/persistence before assertion. The new serializer is archived with future run inputs. Future `spatial-oracle-result.json` holds only metadata, counts, provenance locators, SQL definitions and digests; native source_rows/typed_rows are never written. Global digest, Native31 oracle, mapper/candidate/capture/normalizer/model/SQL and all old ledgers/receipts remain unchanged. Static AST comparison verifies the existing helper's only changed functions are spatial_oracle and main; the patch was not executed against PG.

The original real result still has Native31 **478547 matched**, spatial1344visited but failed, and fresh-process no-op **unverified**. The patched spatial usage, failure-diagnostic persistence and whole15-case real acceptance await ROOT's separate v2 release/one-shot ledger. No retry, capture, cloud SQL/HTTP, deployment, git/staging, CI or WORKLOG action occurred. One existing RAM read was consumed; the server was not stopped. `fullAcceptance=false`; all prior field/profile/family gaps remain.

Exact serializer commands:

```sh
python3 docs/verification/orion-real-spatial-digest-20261105/e2e_serializer.py --label precode-missing-serializer-red
python3 docs/verification/orion-real-spatial-digest-20261105/e2e_serializer.py --label exact-native-spatial-serializer-green
```

The first command is historical: PREDRUN_CODE and its run inputs prove that spatial_native.py was absent then. It cannot reproduce a missing-file RED once the implementation exists. Both receipts retain the exact executable, protocol/test inputs, expected outcomes and actual statuses. No old code/receipt was rewritten to make the RED pass. Final regular-file hashes and protection checks are in [summary.json](summary.json) and final-hashes.json.

Suggested commit: `fix: canonicalize native spatial digest values exactly`.
