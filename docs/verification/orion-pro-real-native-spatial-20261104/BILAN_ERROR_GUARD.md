# Resource JSON-null guard correction

**8preparatory workflows pass, including14/14 local metadata guard cases.**
Four real-source workflows remain unexecuted. This correction makes0remote
SELECT/HTTP requests and decodes0new source bytes. `fullAcceptance=false`.

ROOT's separate diagnostic proved that the unchanged heatmap resource stores
JSON null in jsonb error, not SQL NULL. Its one-shot receipt remains read only:
`neon-error-metadata/result.json`, SHA `5e1369ee600b2785cf7f758d1eb9a9f1283364a426a4efd4bc59000287936ac9`. This lot did not rerun
that probe or reconnect to either source.

The protocol/failure matrix and E2E preceded the fix. The genuine RED receipt is
`runs/20261104T232225587029Z-json-null-guard-precode-red/result.json` (7pass/1fail/4unverified). The unchanged
88aa2067 capture code executed its actual capture() branch, actual NEON_SQL
verbatim through execute() and actual Python if-guard against a separate owned
local PostgreSQL18.6 metadata database. SQL NULL passed; JSON null alone failed.
All12other metadata/status counterexamples were refused correctly.

The production delta is ONE SQL expression at the existing error flag position:
`r.error IS NOT NULL AND r.error <> 'null'::jsonb`. The Python fingerprint/error
if-guard, exact status/selector/path/SHA/size checks and all normalizer code remain
unchanged. No0,false,empty string/object/list is treated as no-error.

Final receipt: `runs/20261104T232254169669Z-json-null-guard-final-source-free/result.json`, status
prepared_real_unverified,8pass/0fail/4unverified. Detailed14case results and exact
SQL are `runs/20261104T232254169669Z-json-null-guard-final-source-free/resource-error-guard/result.json`. Both null
sentinels now reach the no-HTTP observation sentinel. Object/empty object,
string/empty string,boolean false/true,array empty/nonempty,number0/1 and both
status404-null cases refuse before it. This tests the real SQL projection and
capture if-condition, rather than a Python reimplementation of error semantics.

The metadata fixture uses a SEPARATE disposable local server with the sealed
migrator and actual local ingest role. AWS control metadata and object HTTP are
explicit no-network adapters. The real Neon SQL executes with RO/RR8s/1s local
settings. No production TLS success is claimed from this local fixture. No sports
fact, foreign participant or demo correction enters the candidate database.
Both local PostgreSQL servers were stopped and their owned directories removed.
Their logs verify the same model and sealed012/013 runtime artifacts.

Preserved unchanged: preparation9a inputs/receipts, original88aa2067 source input
copies, ROOT_RELEASE/CAPTURE_BLOCKED receipts, consumed v1budget4SELECT/9666054B/
0HTTP (`58266b444de46a8c957e2f5b480f5dfcb2f9bddba83402615723c16d5cca7281`), old89-query ledger (`d539243f7ff612ee3819d8023d95c6ef186848873e511e226e49b1c71d152d6b`), ROOT diagnostic result,
normalizer4b98/model/sealed schemas and candidate wrapper. No ledger-v2 was
created, reset or claimed. The old COMMANDS.md describes the historical v1capture;
it must not be reused to reset or relaunch the consumed budget.

Native478547slots and1344real sparse triplets are still unverified. ROOT review,
commit and a NEW distinct source authorization/budget are required before another
capture. This local error-sentinel fix does not demonstrate native or spatial
source acceptance, source freshness, a remote import or purge eligibility.

Hashes:

- Capture code: `1498d36da2f83ea548db8a3433dd4d78f08add0e0bd6a5c90ef68b60851f7fe9`
- E2E: `0ec8e0c8a0fd756ee50c544a7ad04edbbfce3a3a8edd35d29630dd7ea4a60602`
- Final result: `8c6a23de87cbfa71ae2fa40240d551f1c632f60c4dc73be44327b37e36e56177`
- Metadata case result: `892e2a8405872c1d43e4fbbef80b8a0bae32ae127847bc7e4b59bf2ef782156c`
- Error protocol: `f5b1ca7e8cbf597fa38b80e312531f36acdb5ec2a2156cf888d4990ccfe4edc5`

Exact source-free rerun:

```sh
PYTHONPATH=/tmp/statarena-publication-test-python /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 docs/verification/orion-pro-real-native-spatial-20261104/e2e.py --prepare-only --label json-null-guard-final-source-free
```

Suggested commit: `fix: distinguish JSON null from resource errors before source capture`.
