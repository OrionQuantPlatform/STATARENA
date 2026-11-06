# Entity reader lot: actual-router local acceptance

Suggested commit: `feat: add typed edition-bound entity profile readers`.

The new entities-v1 helper serves eight existing route forms through the actual
aws-app.handleRequest in Pro mode: provider player/team/league profiles, their
three archive profile envelopes, the league catalogue and scoped scouting routes.
Profiles/routing require an existing single-edition pro1 token. SQL uses typed
published facts, selected versions/aliases and explicit source-qualified profile
precedence; it never falls back to mutable identity names or source documents.
The only existing source edit is the helper import+dispatch in aws-app.js.
The original reader SHA remains exactly
`4815cdfb184fbae31fa501b50695b235c2ca14b85660db6e6aee8f5fef979616`.

Run `20261105T115323556411Z-actual-router-reviewed-fixture-v3` passes30/30 with
the exact setup, expected cases, archived input sources, HTTP/SQL traces and
cleanup in its result.json. Its SHA256 is
`02bd5cee2ca8bf8bb73e9ba887a13ebbc9db12bb2f82f0c81208e2a7e19c2f21`.
The run took3.291seconds with213initial typed rows,90HTTP requests,187serving SQL
queries and19,709response bytes; maximum individual SQL was9.383ms. These are
synthetic local observations, not a production latency comparison. PostgreSQL,
Bun and the admin connection stopped, and the owned directory was removed.
No external/provider/object/Neon/RDS action ran. Every recorded source pin was
unchanged throughout the campaign and at delivery review.

The precode structural RED and two actual fixture failures are retained. The
first used an invalid enum, the second inherited a fixed player counter.
FIXTURE_FAILURES.md explains both. FIXTURE_MODEL_REVIEW.md documents ROOT's
approved E29 correction: a same-context canonical ambiguity is prevented by the
native unique index, so the E2E proves exact23505+rollback and stable C
GET/HEAD/ETag instead of fabricating an invalid sealed database. Other expected
product outcomes did not change. No constraints, models or migrations changed.

Exact rerun from repository root:

```
/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 tests/orion_pro_entities_local.py --label actual-router-reviewed-fixture-v3
```

Prerequisites observed locally: Python3.14.6/psycopg3.3.4, Bun1.4.4,
Node26.4.0, installed dashboard dependencies and PG18.6 binaries under
`/tmp/statarena-cache-test-tools/node_modules/@embedded-postgres/darwin-arm64/native/bin`.
The runner accepts --pg-bin, constructs a fixed source-free child environment,
owns one cluster/server and enforces the ROOT90second/5000typed-row/200HTTP
allocation. Retrying uses a new timestamped run and preserves every old result.

Code SHA256:

* orion-pro-entities.js:88e9ec4295451080a4ca784ac96a3bf908f5011021d4af644a061de5725efbfa
* aws-app.js:a73f03c40a4b8f64169ae0752c8f15bf9b592bc604ff65087f7d5b5ec1348099
* tests/orion_pro_entities_local.py:6b5b64319eb14e44591d2b574c7dbd6c72773af7694d904b4ca801b9236c7fcb
* entity_fixture.py:32db4866366244da90f22560b36df16c8203e67ce2fe9e55281761a0ee051acf

ROOT_REVIEW_BUNDLE.json lists exactly which concrete GET/HEAD paths succeeded;
this is not a claim that every possible route/query combination was executed.
The57-route map now contains4existing readers,3operational/media exceptions,
8locally qualified entity forms and42remaining reader/data contracts.
BACKEND_GAPS.md covers existing similarity/cohort behavior and precise103 gaps.

This is backend fixture acceptance only. Frontend token/cache integration,
real RDS facts/publication, hosted flows, linked media, full native provider-state
fidelity, ProOFF/original-reader regressions, collector adaptation and global
history/appearance/aggregate/comparison products remain. The league catalogue
currently has per-row metadata reads and inherits the2048-build discovery
ceiling; neither is accepted as the final broad-directory design. Profile media
uses revalidation even at a frozen edition because media_assets is mutable.
The following lot will compare the unchanged fixture before/after batched
metadata and qualify linked-media behavior without any cloud/object reads.

No deployment, cloud write, source deletion, new scoring or final runtime
independence is claimed. ROOT owns independent review, main integration and the
remaining backend acceptance matrix.
