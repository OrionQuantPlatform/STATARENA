# Streaming capacity gate — stopped RED before importer

**The 478,547-row native core cannot be accepted under the current measured eight-second seal gate. No streaming importer was written.** The [third run](runs/20261104T232206790496Z-native-canonical-seal-gate-complete-inputs/result.json) built the intended canonical shape and hit SQLSTATE57014 while sealing generation2. All three authorized starts are consumed and [campaign.json](campaign.json) records `stopForROOTReview`. No further SQL, large run, timeout change, source split, guard change or remote action followed.

| Observation | Result |
|---|---|
| Source shape before seal | 478,547 scalar rows =15,437 appearances ×31 metrics;478,547 distinct native scalar grains, all canonical, one primary variant |
| Match construction | 612 draft matches with exact match-team, player/profile/participant-revision, source-record/provider and period bindings |
| Scalar insertion | 25,840.739 ms overall, using bounded statements inside the single core generation |
| Native seal | Cancelled after8,005.000 ms;57014; no commit attempted |
| Last active expression | Metric→participant membership anti-existence check inside `ingest.validate_generation`, then snapshot seal trigger |
| Third-run wall time |36.197s |
| Peak observed owned PG directory |1,228,419,072bytes, below7GiB soft stop/8GiB ceiling |
| Cleanup |All connections closed, owned server stopped and owned directory removed |
| Receipt coverage |0passed /1failed /21unverified workflows; the importer-availability case is explicitly unverified in fixture-only mode |
| Not measured |Streaming COPY,32/16MiB importer memory, destination oracle, source EXPLAIN/workfiles, destination seal/commit and v1 capacity comparison |

[setup-observations.json](runs/20261104T232206790496Z-native-canonical-seal-gate-complete-inputs/setup-observations.json) records the native COUNT/DISTINCT/canonical/variant checks before the failure. The error context identifies the expression active when the **whole seal statement** exhausted its8seconds; it is not an isolated timing of that one expression. No EXPLAIN was run, so no nested-loop, missing-index, spilling or statistics diagnosis is presented as proven.

The first two starts failed before scalar loading: ambiguous smallint `generate_series` parameters, then required columns omitted from a fixture INSERT. Their receipts remain unchanged. Explicit integer casts and a model-driven audit corrected those inputs; no schema constraint was relaxed. Profiles do not observe raw position/shirt fields in this synthetic fixture, so their explicit `absent` states express that fixture definition; no real value was converted to0 or absence. The final fixture source bytes remained unchanged during its run.

The [protocol](PROTOCOL.md) and complete E2E scaffold preceded implementation. [The missing-importer RED](runs/20261104T231812089399Z-frozen-precode-stream-red/result.json) separately proves that no importer existed; the fixture-only gate deliberately does not claim availability. It stops before the remaining streaming workflows. Native transaction rollback is issued by the fixture handler, and directory removal is independently confirmed; no post-rollback row-count readback was executed.

The [static review](static-validator-review.json) confirms all529 frozen v1 artifacts are byte-identical, model18da43… and sealed012/013 are unchanged, and the pure current compiler still emits sealed013 byte-for-byte. The [validator review plan](VALIDATOR_REVIEW_PLAN.md) proposes the next bounded, separately authorized diagnostic. It does not patch a helper or create migration014.

Reproduce only after ROOT gives a new budget; the current campaign is stopped:

```sh
python3 tests/orion_pro_bulk_stream_local.py --fixture-gate --label native-canonical-seal-gate-complete-inputs
```

This failure occurs upstream of transport. Source and target were two owned local databases; no live source/API/RDS/Neon was connected, no data was published, and no original body or typed export was archived. Full acceptance, real-candidate capacity, RDS import, cutover and purge remain open.

[summary.json](summary.json) contains the current stopped conclusion. [final-hashes.json](final-hashes.json) binds this lot; [environment-postrun.json](environment-postrun.json) is a separately labelled dependency readback. [changes.patch](changes.patch) contains only the new E2E fixture/runner, not a streaming implementation.

Suggested commit for this stopped lot: `test: record canonical bulk generation seal capacity gate`.
