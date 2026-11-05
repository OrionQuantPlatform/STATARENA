# Typed fixture aliases: local qualification

Suggested commit: `feat: serve versioned typed fixture aliases`.

Two existing routes now serve admitted typed data in Pro mode:
`/api/pitchapi/date/{date}` and `/api/pitchapi/leagues/{league}/matches`.
They retain the existing `data.matches` fixture DTO and add bounded pagination
with a required published edition token. This brings the local route inventory
to 19 supported forms and 38 remaining forms out of 57. ROOT owns the current
global matrix, guard, CI integration and commit.

The new helper invokes the frozen `orionProRoute` fixture interface. It does not
copy or modify its sports SQL, DTO, source-qualified profile policy or existing
four readers. Alias admission verifies the selected edition, league aliases and
optional season. Outer cursors bind route, date/league, season filter, status,
limit and version. The two new routes cannot exchange cursors with each other or
with the core reader. Responses identify `fixtures-alias-v1` and the source v.

The pre-code protocol and all 16 expectations were written before the helper.
Retained RED: `runs/20261105T150206681162Z-actual-node24-alias-precode-red/result.json`,
SHA256 `c7b3fb69a889af40386fc7e53173efed182858649b6724baaf88fc5286654393`.
F01 qualified the unchanged 213-row fixture. F02 received actual-app 501 before
implementation; the other 14 cases remained unverified. Runtime: 3.689 seconds,
430 SQL calls, 4 actual HTTP requests, exact pins and complete owned cleanup.

The first implementation AFTER passed 16/16 without a fixture or expectation
change: `runs/20261105T153026017357Z-actual-node24-alias-after-v1/result.json`,
SHA256 `78207e0dfe885c4529a8bd26869dcf7152607d78629fa5021852f0a696a8b219`.
Actual Node v24.22.2 on darwin-arm64 and PostgreSQL 18.6 were used, through
`aws-app.handleRequest`, ordinary read-only runtime credentials and only typed
schemas. No provider, Neon, source database, S3 or other external HTTP was used.

Exact rerun from the repository root:

```sh
/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 tests/orion_pro_fixture_aliases_local.py --label actual-node24-alias-after-v1 --node24 /tmp/statarena-node24-runtime/v24.22.2/node-v24.22.2-darwin-arm64/bin/node
```

The result records setup, exact inputs and code pins, every public HTTP request
and SQL trace, expected/actual case outcomes, server logs and cleanup. The official
local Node archive acquisition is retained in the prior runtime receipt; this
runner's acquisition check is Darwin-specific and needs a distinct portable
runtime-acquisition adapter for Linux CI. This is not hosted Lambda acceptance.

Measured run: 3.802 seconds, 213 initial and 230 final typed rows, 654 external
SQL calls, 99 actual HTTP requests (49 public API calls), 24,548 public response
bytes. Maximum recorded request SQL: 7.857 ms. Observed owned disk: 72,772,339 B;
evidence before the final report: 3,039,237 B. These are synthetic local numbers,
not production latency or a comparative speedup claim.

GET used exactly 3 SQL calls for both limit 1 and limit 100. HEAD and matching
304 used 2 metadata SQL calls and zero response bytes, with no fixture list or
heavy-family payload query. Invalid input and cursor requests made zero SQL
calls; wrong edition scope made one metadata call and returned 400. The source
code's nonmatching conditional GET branch plans 4 calls; that specific branch
was not exercised by this 16-case run and is not reported as passed.

The date traversal returns exactly the two known same-day fixtures in the named
edition; league traversal retains all three fixtures with the unknown date last.
Status filtering, known-empty day, default limit, nullable scores/time/playoff,
observed names, exact native-shaped key set and core-reader DTO equality pass.
Later corrected publication changes the new token's score/name while an old
token's body and ETag remain exact. Original manifest, fixture, summary and shots
routes still return 200 through the actual app, and reader 481 remains exact.

All code pins stayed unchanged. PostgreSQL, Node and admin clients were closed,
and the owned cluster directory was removed. No remote action or credential
value is recorded. No original evidence bundle, appearance b3d4 helper, entity
950 helper, operational helper, common runtime or sealed model/DDL changed.

Important scope: a pro1 token names one edition. This date view is not a complete
worldwide day. A global caller must traverse relevant manifest edition tokens
and every page; the old ProOFF saved-data bridge is unchanged. Ordering inherits
the frozen V1 reader; the qualification fixture uses numeric public IDs and does
not establish separate mixed-case/collation parity. Native image/playoff null
projections remain the existing V1 DTO, without a new completeness claim.

App source SHA256:
`3f00f75efb0218c26bb10d180c29931de8e8730628673933e9732c405d536686`.
Helper SHA256:
`bbc59b6cef3fd5e9e54bd33d0709105559e4d266d6db26c563aec44dfcc2c5f8`.
Test SHA256:
`99f66e3cecf723c72aa7adffaaa04fe3d8a4649e9953ebafea06e9e972dcf739`.
The app change is one import plus two dispatch lines after appearance dispatch.
The separate follow-up document records the appearance reader's whole-edition
admission work; no optimization is included in this alias lot.
