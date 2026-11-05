# Entity catalogue batching and linked media — pre-code E2E

Suggested commit: `perf: batch typed entity catalogue metadata reads`.

Baseline is the frozen first entity lot: helper88e9ec4295451080a4ca784ac96a3bf908f5011021d4af644a061de5725efbfa,
actual appa73f03c40a4b8f64169ae0752c8f15bf9b592bc604ff65087f7d5b5ec1348099,
first-lot manifest01346dd19d64ca0f09b34828427bb7eda83a42696a7b3ed465166176586d5bd9,
and actual-router30/30 result02bd5cee2ca8bf8bb73e9ba887a13ebbc9db12bb2f82f0c81208e2a7e19c2f21.
The first lot and its131-file manifest remain immutable. No old reader/app/model/
migration/source/front-end/cloud change belongs to this lot. Only the new entity
helper's catalogue metadata loading may change after an actual SQL-budget RED.

## Failure modes and expected outcomes before the batching code

The existing source-free213-row A/B/C/D EntityFixture is used unchanged for both
RED and after. Its four editions represent two public competitions. A catalogue
GET at limit100 must use at most3SQL statements (publication metadata, batched
catalogue+asset metadata, content), with identical response bytes/ETag and total
ordering to the original helper on the same fixture. HEAD/matching304 must use
at most2SQL and no entity content query. Counts must not grow with the number of
catalogue items, including non-NULL media. This is a SQL-count/local-volume
comparison, not a production latency claim. Page1+page2 remains complete and
unique; filter/cursor/version/error behavior is not relaxed.

Linked media is a required observable branch, using locally generated1pixel PNG
blobs and actual typed media rows/profile/competition refs. Their SHA256 bytes,
keys, MIME, author/license/source URL/retrieved-at metadata are saved as inputs.
No blob is uploaded, fetched from S3, or fetched from the returned URL. The source
URL is provenance only; response image URLs must use the configured canonical
HTTPS origin and immutable key. Wrong MIME/key/origin must fail503/no-store
before content. No source/provider/image HTTP request is permitted.

The media row is mutable: a valid key/hash change at the same asset ID changes
the image URL/ETag even when the edition token and profile ID stay fixed. Old
edition names/scalar/profile refs remain frozen, and media uses explicit browser
revalidation (max-age0, no immutable). Old ETag now receives200+new ETag;
new ETag receives304/body0/metadata only; HEAD agrees. A historical profile whose
image ref wasNULL remainsNULL after the newer linked profile/media mutation.

| Case | Input/workflow | Expected |
|---|---|---|
| B01 setup | exact first fixture/schema/runtime |213rows/read-only;0external; original pins |
| B02 SQL budget | full two-competition catalogue limit100 |≤3SQL;2items; same body/ETag as RED after batching |
| B03 cold validators | GET then HEAD/listIfNoneMatch |HEAD/304≤2SQL, body0, no content |
| B04 pages | two limit1 pages / q filter |stable total order, no duplicate/skip, scoped cursor |
| M01 media input | local PNG A/B + typed source/asset/profile/competition refs |hash/key/MIME/provenance exact, no cloud |
| M02 linked profile | fixed linked edition v |image URL exact configured HTTPS host/path, revalidation headers; no provenance URL leak |
| M03 linked catalogue | two-competition GET/HEAD/304 |same≤3/≤2SQL bound with media; metadata-only validators |
| M04 asset correction | mutate asset to B without publication/profile correction |same token/name/profile, changedURL/ETag, oldtag200, newtag304, HEAD agrees |
| M05 historical profile | pre-media edition token |same old body/ETag andNULL image |
| M06 invalid media | bad key, mismatched MIME, invalid configured origin |503/no-store/no content; restore fixtures afterward |
| M07 source URL | mutate provenance URL to another HTTPS host |response remains configured canonical origin; unused provenance change does not alter ETag |
| M08 boundary/cleanup | request trace + runtime write attempt |0source/S3/provider HTTP, no legacy/current sports reads, runtime write denied, ownedPG/Bun removed |

Commands from repository root (each needs a ROOT coordinated PG slot):

```
python3 tests/orion_pro_entity_batch_media_local.py --label batch-budget-red
python3 tests/orion_pro_entity_batch_media_local.py --label batched-media --compare-red docs/verification/orion-pro-entity-batch-media-20261105/runs/RED/result.json
```

Every run records its exact command, archived changing inputs, references/hashes
to the frozen first-lot inputs, HTTP+SQL traces, outcomes/logs and cleanup.
The run owns one cluster/server, ≤5000typed rows, ≤200HTTP, ≤90seconds (85second
alarm reserves cleanup),8second SQL/1second locks and a fixed source-free child
environment. First unexpected failure stops dependent cases as unverified.

UX: unchanged profiles/catalogue with correct image refresh. DX: one batched
metadata query rather than per-item queries. AX: constant query budget and
explicit typed media provenance/validators. Actual hosted media delivery and
global2048-build ceiling remain outside this local lot's acceptance.
