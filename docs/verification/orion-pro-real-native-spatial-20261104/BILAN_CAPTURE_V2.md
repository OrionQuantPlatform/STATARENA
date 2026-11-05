# Capture-v2 READY,source-only inspection complete

**The unique v2capture is READY and the RAM server remains alive. No PostgreSQL
candidate/import or real E2E was run.** `fullAcceptance=false`. Only ROOT may
order STOP or separately release the import.

PID54737,tool session70680,private socket
`/tmp/orion-real-native-spatial-20261105-v2/source.sock`. ROOT_RELEASE_V2 was
verified before launch and OPERATOR_RELEASE_V2_RECEIPT records that check.
Capture1498 ran once with the exact declared AWS and Neon versions. Its source
connections closed before READY; the process now serves the captured snapshot
only. It consumed4SELECT,9682314decoded bytes,3object HTTP calls and3961physical
HTTP bytes,under11/33554432/3/1048576caps. No retry/login/fallback,remote write or
source body/file/pickle persisted. Both previous ledgers remain byte-identical.

Independent RAM inspection confirms actual source membership:612fixtures,
387finished normalized matches,15437performances,9795shots,1151profile variant
rows,839unique players and20unique teams. Every normalized finished ID has a
fixture. Counts and ID/content digests are saved without source rows or values.

The31registered fields yield exactly478547native observations:
45591absent,188032null,244924number (including69517numeric-zero observations),
0string,0boolean and0empty-string observations. The source corpus therefore does
not add real examples of string/bool/empty common metrics. All numeric observations
satisfy the frozen exact int32/numeric/double round-trip contracts,with0rejected
forms and0common completed/attempted pair violations. Maximum observed numeric
fractional places2/integer digits3 are precision metadata,not a numeric value
copy. These are SOURCE checks only; typed native states compared remain0.

The direct Neon heatmap has2unique team parents and30unique player parents,
1344observed sparse triplets,an explicit16x12grid and home_ltr frame. Triplet order,
integer bounds/counts,duplicate coordinates/logical parents,grid-metres
representability,fixture sides and all player/team/normalized-performance cohorts
pass source-side checks. No cell was filled or rotated. There are0missing or
ambiguous actor/side/cohort IDs in this source scope. Typed cells compared remain0.

Useful field fidelity is still incomplete:30player names,30player shirt numbers,
30player-context team names and2team-context team names remain qualified/unmapped
by the spatial importer.62exact full-profile resource lookup gaps remain named;
no biography is invented and no global source loss is inferred. Other original
families/full profiles were not captured. No supplier recency order is inferred
between AWS and Neon. Indexed normalized JSON does not independently prove the
partitions' physical gzip lexical number spellings. The one Neon blob's exact
physical SHA was checked during capture.

Evidence: capture-v2/ready-snapshot.json (immutable READY metadata copy),
source-only-inventory.json (per-field type/precision counts,IDs/digests/gaps),
source-only-summary.json,and inspection-inputs containing exact code/spec/metadata
only. The initial census is preserved as source-only-inventory-initial.json;
adding explicit zero-kind/unique-parent metadata reread only the SAME RAM socket,
with0new remote SELECT/HTTP and unchanged source budget. The live capture.json
will change on ROOT's eventual STOP and is excluded from immutable hashes.

No source body is recoverable from these metadata artifacts alone. The exact
inspection command in RAM_INSPECTION_V2_PROTOCOL.md is reproducible while this
owned RAM socket remains alive. Its loss would need new authorization,not a
silent source reread. Whole-seal8s performance and SQL fidelity remain separate
ROOT gates before any real import. No old013 import was attempted.

Hashes:

- V2budget: `30cd865d10da6d2dc28e53f0f741756549c576bfa35a90e050062a462dc078ac`
- Immutable READY copy: `4d2ac59a6815eb02850ea78f74cae8fc22d33f17d082688676a1925744a01d2b`
- Source-only inventory: `58a8b055c6b6a6fbbb6cc9ee1494638038e70328f249d66ff2c85d1069ccd5e2`
- Native source token stream: `495ab40dc082a76599cf623197496f60e2a1add5e488d92f42e8458b920241e6`
- Ordered sparse source cells: `f42ed19ed8d00655ce5fb5f5a9ad5111576968538ebe5098276f9c896251d10e`
- Inspector: `94d2e251fd539800bd2d4d9ce9c25d8c8bfd9a4ed2ba8169dd3435da3860e053`
- Frozen capture: `1498d36da2f83ea548db8a3433dd4d78f08add0e0bd6a5c90ef68b60851f7fe9`

Suggested commit: `test: reconcile native metric and spatial source values`.
