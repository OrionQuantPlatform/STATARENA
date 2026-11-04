# Relational backend core — requirements before code

Updated explicit user contract: website uses normalized relational tables, no JSON/document/file/object reads. Existing migration/import tables and original bytes are retained by their owner; only ingestion/rematerialize may inspect staging while building typed application records. Every data-model change must be incorporated into rematerialize, and all GitHub Actions must target AWS.

Backend-owned schema statarena_app is additive and independent of friend's statarena import. Typed entity/match/appearance/shot/statistic/relationship/coverage tables, no JSON/JSONB/payload/body/document columns. Atomic partition publication + generation; SQL reader is a separate SELECT-only role. Keep unknown values/null/zero and native civil seasons; no inferred rankings/data.

Before implementation, expected actual-PG workflows:
1. Normalize an existing synthetic rich provider fixture through existing build_snapshot, split to coretyped tables, retrieve an SQL-built season part, compare IDs/stats/shot geometry/counts/captain/attempts/nullzero with source. All table datatypes are relational scalar/arrays, noJSON.
2. Repeat unchanged partition: samecounts/generation/hash; changedgoals/stats update atomically and replace old affectedrows, preserving otherpartitions, versions of playeridentity and allmetricnames.
3. Force publication rollback after writes: priorvalues/generation/dirtywork survive. Late dirtymarker change during publication is not acknowledged.
4. HEAD/304 onlyreadmetadata; ready overview selects onebounded result, heavyshots/player/network onlywhen requested. Page/traversal defaults50max100, cursor generation and scope bindings, unknown/invalidID dates/errorswithoutproviderfetch.
5. Runtime RDS-only config + TLS/CA/read-only pool/session; noS3/Pitch credentials required. Failclosed ifschema/partition notready, withoutfallingbacktofiles/provider.
6. Existing criticalUI recordcounts, standings/cohorts,search/playerhistory/clubhistory/archives, matchstatistics/detailfamilies andall APIroute contracts remain supported by normalizedqueries. Export or full-season needs use bounded complete traversal, not silently truncated.

Evidence: isolated embedded PostgreSQL18.6 +real production Python normalizer, Node/BunHTTP routes andNext builds. Freeze baseline beforeproduct changes, preserve everyfailingrun. Record exactinputs/setup/versions/commands/expected/actual, SQL/logs andpayloadbytes. LiveRDSprobes are read-only withtimeouts; productionDDL/backfill onlyafter ownnamespace/privileges/importcoordination checks. Numerical resultsdistinguish fixturesfromproductionlatencyandcost.

Suggested commit: `feat: materialize normalized application tables on AWS RDS`.

## AWS HTTP and transport readback

Replay from the repository root. All writes in these commands target newly created disposable local PostgreSQL databases. The core verifier needs Bun, Python with psycopg3, installed dashboard dependencies and the embedded PostgreSQL 18.6 runtime.

```sh
STATARENA_CORE_API=1 STATARENA_SERVER_TIMING=1 STATARENA_CORE_EVIDENCE=docs/verification/aws-relational-core-20261104/api-replayed bun dashboard/scripts/verify_relational_core.mjs
PYTHONPATH=/tmp/statarena-archive-remat-pg/python bun docs/verification/aws-relational-core-20261104/integrated-api.mjs
PYTHONPATH=/tmp/statarena-archive-remat-pg/python bun docs/verification/aws-support-20261104/verify.mjs green
```

The initial HTTP implementation passed one of nine cases (method/path rejection). The final run in `api-integrated` passed all ten HTTP scenarios and all five materializer cases, including failure when AWS's required URL is absent. Inspect `http.json` for exact inputs, statuses, bodies and validators and `requests.log` for query counts and timings. Season pages and fixtures took one SQL query, cold summary two, warm summary/304/HEAD one, and malformed inputs zero.

The combined verifier installs 003–006, publishes checked-in catalog and match source captures, serves the actual AWS app through the Function URL transport adapter, and compares public HTTP responses under a dedicated read-only role. It covered 67 GET inputs: 60 successful representations (each also requested via HEAD and conditional GET), five known misses, one invalid parameter and one retired file route. The 3,806,859-byte supplemental response and 2,833,323-byte archived goal edition round-tripped through gzip. The initial SportsAPI edition rejection is preserved separately. See `integrated-api.json` for every route, actual bytes, encoding, status, validator and comparisons. The supporting test separately passed 1,880 source keys through the actual AWS route. Production AWS networking and current RDS coverage require the release owner's live acceptance run.

Suggested commit `feat: serve versioned football pages and match summaries from relational AWS tables`.

Before changing edge expiry: ready committed catalog, support and match data must return browser max-age=0/must-revalidate with positive s-maxage no greater than 60. HEAD and conditional 304 must preserve the same shared cache policy; a 304 has no body. A pending fixture-only overview, missing data and non-200 errors must return no-store. A positive immutable-image redirect uses a 60-second mutable-alias window shared by the local lookup cache and CDN; a miss is never retained. Test the actual Function URL adapter and HTTP headers against disposable SQL records before building the release.

The subsequent edge-policy run first failed because the archive returned no-store. The corrected run passed 71 recorded inputs (the 67 above plus GET/HEAD for pending summary and binary redirect). Every successful catalog/detail representation in this run was also read by HEAD and a matching If-None-Match request. All three responses advertise browser `max-age=0,must-revalidate` and shared `s-maxage=60`. The transport explicitly disables stale-if-error extension. An edge may therefore serve the previous committed version for up to 60 seconds after publication. Pending/dirty summaries and errors return no-store. Positive image lookups have a 2MiB bounded process cache with a maximum object size of 4KiB; only the remaining lifetime from the last metadata lookup is sent to the edge. READY core summaries and the manifest use 15 seconds, scoped scouting routes 30 seconds, and generation-bound pagination bypasses shared caching. The pre-policy failure is in edge-policy-red.json. Exact core SQL counts and values remain in api-integrated/.
