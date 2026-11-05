# Captured physical profile correction

Suggested commit: `fix: retain captured appearance profile observations`.

The appearance reader incorrectly applied the later catalogue interval to an
already captured physical player profile. The approved103schema permits that
profile to close while a selected participant retains its physical pointer and
a changed profile of the same actor/context becomes canonical. The reader now
joins the retained physical ID and actor with its nondeleted state, preserving
the captured name/playerRef/image rather than hiding them or using a current
resource profile. The sole production difference is saved in SOURCE_FIX.diff.

Native policy:012:7289 binds profile_version_id+player_id to the physical profile;
013:519–544 permits interval closure with immutable values;013:2340 verifies a
selected parent of the same actor/context, not physical ID equality. The E2E
closes profile11 at generation8, inserts profile45 at8 with different name/ref/
image, retains6selected participant pointers to11, seals generation8 and legally
publishes oldDG/newCG plus newDG/newCG. Both typed guard triggers remain enabled.
No constraint/index/trigger/replica-role override or schema amendment is used.

The corrective8-case matrix/fixture/consumer checks were written before the
production correction. Actual pre-code RED:
`runs/20261105T144257819403Z-actual-node24-profile-precode-red/result.json`,
SHA256 `a07840ba733565b7ddbb553ee387b549e76ac23626085c9308be3369a0c8898d`.
P01/P02/P03passed; P04returned503/PERFORMANCE_COVERAGE_UNAVAILABLE instead of200;
four later cases remained unverified.10.750seconds/1,994SQL/8actualHTTP. Cleanup
and source pins were exact. The legal SQL state is independently retained in its
membershipProof; the error was the reader predicate, not a fixture constraint.

After the one-clause correction, all8cases passed in
`runs/20261105T144546085192Z-actual-node24-profile-after-v1/result.json`,
SHA256 `e39d564bb3d2e2d5ea587d7f03e4f86437c5c2611773f55f085f7e9359614f5c`.
12.083seconds/2,183SQL/41actualHTTP(20public)/7,440final typed rows,
507,039public response bytes/max recorded SQL62.650ms. Nodev24.22.2/darwin-arm64,
PG18.6,0external attempts, all pins stable and owned processes/directory removed.

Exact rerun:

```sh
/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 tests/orion_pro_observed_profile_local.py --label actual-node24-profile-after-v1 --node24 /tmp/statarena-node24-runtime/v24.22.2/node-v24.22.2-darwin-arm64/bin/node
```

Both oldDG/newCG and newDG/newCG retain all captured appearance fields. A dg-only
join replacement would fail the latter. Full packed192row output passes exact
independent Decimal/state checks and the existing JavaScript decodePartition.
Old token body/ETag stays exact; HEAD/304 remains metadata-only/zero bytes. A valid
change to the distinct, unused replacement-profile asset leaves captured-profile
responses unchanged; captured media does not acquire an unrelated dependency.

The original22functional expectations then passed unchanged in a fresh namespace:
`../orion-pro-appearances-regression-20261105/runs/20261105T144627298556Z-actual-node24-original22-after-profile-fix/result.json`,
SHA256 `9c9e9fc61bb10b7257127e0cc1110df8d996cda477a570508b73ca505335bd63`.
18.709seconds/3,370SQL/107actualHTTP/7,785final rows/484,698response bytes,
max recorded SQL114.295ms. This is a local observation, not a performance
improvement or hosted/production claim.0external/pins exact/cleanup verified.
NAMESPACE_ADAPTATION.json records the only3runner substitutions and byte-identical
fixtures/consumer/HTTP/runtime inputs; the22case block hash is unchanged.

The original lot3manifest44d71c93d720369a881e6bfdb7a1c820aae5a1d5f9f65672941ad1ff31654ad9
and all347listed files were independently rehashed after both corrected runs:
0mismatches. No original22-case source, expectation, evidence or manifest changed.
The current app dispatch and original481/entity950/operational/common services are
unchanged by this correction. No app wiring was needed. No new formula/model107,
real-data ingestion, cloud/source access, hosted rollout or cutover is claimed.

Current helper SHA256:
`b3d4ae1fa078ccfcc8fb498b42f7a9e7c5135cbb96f7e219cc2c0bd55134c88c`.
The earlier fa400b37qualified bytes remain in the original22 and correctiveRED
run input archives. ROOT owns code review/integration and subsequent route/CI
coverage changes. Remaining40route forms and real-data admission remain open.
