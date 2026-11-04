# Source-free sparse heatmap E2E, before mapper

Only the normalizer, new heatmap E2E and this directory are owned. No AWS,
Neon/Pitch call, capture, real body, model/012/013/014 change or commit/deploy.
All supplied observations are explicit synthetic fixtures. Real acceptance is
**0/1344 triplets** until a separately authorized acquisition.

Every generated variant/correction has a distinct declared synthetic source
document/body hash and row locators. The first correction-fixture attempt reused
the old source record and was correctly stopped by the sealed no-op guard; its
failed receipt is preserved, and the SQL guard was not weakened.

| Failure/transition | Expected observable result |
|---|---|
| Unsorted sparse corners and observed zero | Exactly one child per triplet, source ordinal, explicit16x12 grid, exact counts/coordinates; no dense expansion |
| acting_ltr vs home_ltr, away side | Source coordinates/frame retained without rotation |
| cells absent/null/empty | Distinct parent states, zero children; parent descriptors remain explicit |
| outer collection absent/null/empty | Distinct coverage rows, no fictitious parent/grid |
| Bool/string/fraction/negative/overflow coordinate/count/dimension, nonfinite metres, ragged/nontriplet, duplicate coordinate/parent | Precise refusal, no committed partial family; rolled-back sequence gaps are not a successful retry |
| Missing grid for an existing collection, unknown frame, actions absent | Refuse/qualify the concrete model/contract gap; no defaults or body JSON |
| Wrong team/player/side or closed cohort | Reject before accepting a heatmap; no invented participation |
| Player reference inside a teams collection | Reject the ambiguous actor shape rather than silently dropping the useful player reference |
| Variant and labelled correction | Separate immutable parents/children, new parent ID, old snapshot exact; source ordinals do not become stable identities |
| Fresh interpreter, identical core/family input | Reuse persistent receipts; all94table rows/67sequences/IDs remain exact, with no correction replay |
| Observed profile candidate | Unique same-source/record/actor/variant/cohort join if representable; repeated-team collision remains an explicit gap, no global substitute |
| Existing native31 suite | Same unchanged test/spec, all8 workflows; evidence redirected only to this owned directory |

The profile experiment is conditional evidence, not a general mapping claim.
It stores exact synthetic name/shirt values in the existing typed profile
columns with the same source/record/actor/variant/cohort, then demonstrates the
current repeated-team context/variant collision. Profiles remain a qualified
source-field gap in the spatial importer; no value is stored in diagnostic JSON.

The first full PG run imports the sparse fixture through the existing dense
mapper to save a genuine RED. Then the mapper may change. The local harness uses
owned disposable PostgreSQL18.6, the sealed shared migrator and the actual ingest
role. SQL readback is independent of the mapper. Every run saves source/spec
hashes, exact command, synthetic recipe, outcomes, logs and cleanup. Frozen pilot
and native31 files are read only; no real source body is copied.

```sh
PYTHONPATH=/tmp/statarena-publication-test-python python3 tests/orion_pro_heatmaps_local.py --label sparse
```

Suggested commit: `fix: preserve sparse heatmap coordinates and native collection states`.

## Provenance-root correction, specified before code

Archive records sit at an observation containing response.data, while qualified
direct response documents contain data without a response wrapper. The helper
must retain its archive default but require an explicit allowed relative root
for direct data. Allowed roots are /response/data, /data, and the empty relative
root only when the record is already located at a data member. Resolve the root
against the already decoded source cache and compare the selected observation;
never invent an envelope, perform another source read or write a source body.

The new E2E first shows the old helper accepting a direct envelope with false
/response/data locators. After the guard, that default must refuse before any
child record/fact. Positive archive, direct /data and record-at-data cases must
read back exact SQL source_records document_id/source_id and every collection
and slot locator, in addition to existing cell checks. Invalid roots, missing
paths or a different supplied observation must refuse atomically. The previous
eight greens remain historical. No other spatial/metric/model scope changes.

## CI binary propagation, ROOT integration

The outer heatmap E2E accepts --pg-bin; its nested unchanged native31 workflow must receive that exact same path. Otherwise a Linux CI invocation silently selects the native31 default Darwin binary and fails without testing the intended workflow. Pass the explicit value through the subprocess argv, retain previous receipts, then rerun the complete9+8 local workflow. CI uses its installed Linux PG18.6; this portability correction changes no fixtures, expected values or product code.
