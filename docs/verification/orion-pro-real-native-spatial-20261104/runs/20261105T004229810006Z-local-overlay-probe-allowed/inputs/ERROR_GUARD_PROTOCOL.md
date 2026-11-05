# JSON error null: source-free corrective E2E before code

ROOT separately authorized this local-only correction after its one-shot remote
metadata result proved the existing pinned resource has JSON null in jsonb error:
SQL-null false, jsonb_typeof null, equals JSON null true,4text bytes. The object
fingerprint is unchanged. ROOT's `neon-error-metadata/result.json` is read only
and must not be rerun or modified by this agent.

The failed source ledger4SELECT/9666054B/0HTTP, the old89-query ledger, original
88aa2067 capture input snapshots and preparation9a receipts are immutable. There
is no authorization for a new source connection, HTTP, capture-v2, reset or retry.
Only the capture metadata flag, local E2E and new corrective evidence may change.
The normalizer/model/sealed migrations remain untouched.

| Local metadata fixture | Expected actual capture guard |
|---|---|
| status200,error SQL NULL | accept metadata stage |
| status200,error JSON null | accept metadata stage; current code must show genuine RED |
| status200,error object or empty object | refuse |
| status200,error string or empty string | refuse |
| status200,error boolean false/true | refuse |
| status200,error array empty/nonempty | refuse |
| status200,error number0/nonzero | refuse |
| status404,error SQL NULL or JSON null | refuse status independently |

The E2E starts a SEPARATE owned disposable PG18.6 server, installs the unchanged
sealed012/013 with the shared harness and creates local metadata-only mock
statarena.resources/objects tables with jsonb error. It grants SELECT to the
actual local orion_pro_ingest role. No sports fact enters the candidate database.
SQL INSERT fixtures are administrative metadata setup only in that separate DB.

Call the real unchanged capture.capture() path. Its AWS control-plane results are
explicit local synthetic empty metadata adapters; connect() routes only the Neon
query to this local PG connection, with the real startup RO/RR8s/1s options.
verify_connection() adapts only expected local identity/TLS context; no production
TLS success is claimed. neon_object() is a no-HTTP reachability sentinel. The
actual NEON_SQL is passed verbatim to PostgreSQL through the real execute()
function, and the original capture() fingerprint/error if-condition executes.
Do not rewrite the predicate in Python or assert only a proposed expression.
The sentinel reaching/not reaching HTTP is the guard's observable result.

The old JSON-null case must fail before the one-expression projection fix.
Afterwards, every non-null JSON kind and both failing-status cases must still
stop before the sentinel. Save all cases, exact SQL/hash, current capture hash,
local role/settings, expected versus actual and both DB cleanups. Both immutable
source ledger SHA values and ROOT metadata result SHA are checked before/after.
No part of this E2E connects to AWS/Neon or loads private credential values.

Proposed minimal correction after RED: project
`r.error IS NOT NULL AND r.error <> 'null'::jsonb` at the existing flag position.
Keep the existing Python fingerprint/error guard. This classifies no-error
sentinels without treating0,false,empty string/object/list as absent and without
removing status/selector/version checks. No source normalizer changes.

```sh
PYTHONPATH=/tmp/statarena-publication-test-python python3 docs/verification/orion-pro-real-native-spatial-20261104/e2e.py --prepare-only --label json-null-guard-precode-red
```

Real native/spatial phases remain unverified. A new source capture requires
ROOT review/commit and a separately authorized ledger-v2; never reset the first.

Suggested commit: `fix: distinguish JSON null from resource errors before source capture`.
