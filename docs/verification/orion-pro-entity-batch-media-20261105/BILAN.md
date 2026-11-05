# Batched catalogue metadata and linked-media acceptance

Suggested commit: `perf: batch typed entity catalogue metadata reads`.

The entity helper now reads a catalogue page and its optional media metadata in
one bounded SQL query, replacing one metadata query per item plus separate media
lookups. The original media validator/fingerprint is shared with profile reads.
Publication tokens, body fields, visible ordering, pagination, errors and ETag
semantics stay the same. No app/router, original V1 reader, model, migration,
normalizer or frontend source changed in this lot.

The pre-code SQL-budget RED is retained at
`runs/20261105T121925487909Z-batch-budget-red`:1passed/1failed/10unverified,
stopping exactly at B02's4SQL >3budget. That run used the unchanged213-row first
fixture and verified130historical files from the immutable first-lot manifest.
The original first-lot30/30 and its source remain archived at maina07668ad61.

The AFTER run `20261105T122208637691Z-batched-media` passes12/12 in2.521seconds.
The same catalogue body is389bytes and the same ETag, with4→3SQL; HEAD/304 use
at most2SQL, including a non-NULL media reference. The run starts with the exact
same213typed rows and finishes with237after explicitly recorded media/profile/
competition/publication additions. It makes33public requests and70actual HTTP
transport requests including trace/config controls,102serving SQL queries,
12,992response bytes, and zero external HTTP/object/provider attempts. Maximum
individual SQL was7.045ms. These are local SQL-count/volume measurements, not
production latency or maximal-load proof.

The linked-media workflow creates two valid1pixel PNG blobs locally, records
their bytes/SHA256/hash-bearing keys/MIME and provenance, and links actual typed
asset/profile/competition rows. It verifies canonical HTTPS image URLs and
headers without fetching or uploading any blob. A same-ID asset key/hash change
changes URL/ETag at the same frozen edition/profile: old tags receive200/new tag,
new tags receive304, and HEAD agrees without content. A genuinely historical
NULL image reference remainsNULL and keeps its old body/ETag. Bad keys, mismatched
MIME and invalid media origins fail503/no-store before content. Changing only an
unused provenance URL does not redirect delivery or change content/ETag.

Exact rerun from repository root:

```
/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 tests/orion_pro_entity_batch_media_local.py --label batched-media --compare-red docs/verification/orion-pro-entity-batch-media-20261105/runs/20261105T121925487909Z-batch-budget-red/result.json
```

The source-free environment/runtime prerequisites match the first lot. The new
runner snapshots changing source inputs and pins/references the immutable first
bundle instead of duplicating its model/SQL corpus. Both runs retain commands,
expected/actual outcomes, full HTTP/SQL logs, PNG inputs and cleanup. PostgreSQL,
Bun and admin connections stopped and owned directories were removed; pins stayed
unchanged. No second campaign ran without ROOT's coordinated resource slot.

SHA256:

* helper:95021dedb122e90e2db946301813fed20f0601b7fa7b48c25b7ed26111c1351a
* E2E runner:c0925892f6c330d919b40a67585de47c97c3934b68044396ad70b7e5349ee4d6
* RED result:7500a5fce8e39466b25bdd89ff761adc61d994e3f71f9deb0ab114fb3cbe51e1
* AFTER result:299d21e2b0def19a04cae9aa94560f6dc663fcdbdd6b95f6e32b485249fab2ca

ROOT_RESULT_REVIEW.json provides the compact review receipt. Actual binary image
delivery/retention and hosted flows remain separate from this local metadata
contract. The original2048-build discovery ceiling remains an explicit global
pagination task. No new score, complete backend, full source normalization or
production runtime independence is claimed.

The next-lot source inventories preserve existing player/club similarity rules,
unweighted appearance rating means, complete cohort denominators and the gaps in
structural appearance fields. Native31 fidelity alone does not establish complete
appearances or reliable club/player cohorts. Those inventories contain no model/
normalizer/aggregate code change.
