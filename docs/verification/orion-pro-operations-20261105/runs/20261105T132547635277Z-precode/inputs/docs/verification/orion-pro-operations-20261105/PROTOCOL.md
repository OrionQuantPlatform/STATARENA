# Typed operational endpoints — E2E before product

Suggested commit: `feat: serve Pro health settings and media from typed SQL`.

Scope: /api/health, /api/status, /api/settings and /api/assets in Pro mode.
Existing non-Pro routes and four frozen reader contracts stay covered by the
existing guard regression. No schema, ingestion or deployment is changed here.

Failure matrix and expected behavior, fixed before implementation:

1. Ordinary runtime role is read-only with8s statement/1s lock deadlines; the
   owned PG18.6 contains only the approved012/013/014 schemas, no legacy schemas.
2. Health with bootstrap only returns503 pending/no-store, one bounded metadata
   query, no fabricated ready state. Once a sealed dataset/catalogue and ready
   current publication exist, it returns200/sourceAWS/statusok/revision string.
3. Status preserves source/configured/basePath, zeroSQL. Unknown or duplicate
   parameters and invalid methods fail beforeSQL; GET and HEAD remain supported.
4. Health GET/HEAD/If-None-Match share ETag; HEAD/304 body is empty,≤1SQL and no
   sports body/materialization. Publication correction changes revision/tag.
5. Settings reads only a bounded scalar projection of import_runs; parameters,
   counters/checkpoint/error and credentials never enter responses. Descending
   ID cursor pages (default20,max50) preserve all rows without overlap. Sync
   envelope and workflow URL remain; schedule shows the declared repository crons,
   explicitly scheduling activation is unknown (this endpoint does not call GitHub).
   Settings are no-store. HEAD needs noSQL. Invalid limit/cursor is400/noSQL.
6. Assets resolves only ingest.media_assets.legacy_asset_url; source_url is
   attribution, never a fallback. Exactly one hash/key/MIME tuple is required.
   A valid PNG/WebP/JPEG returns empty307 to configured canonical HTTPS CloudFront
   /data/<content-addressed-key>, GET/HEAD match and revalidate after mutable update.
   No remote fetch. Duplicate mappings503, absent mappings404, bad inputs400,
   invalid storage key/hash/MIME or origin503, no-store on errors.
7. All successful requests use only ingest/football/analytics; no statarena,
   statarena_app, object/provider/Neon transport. GETs cannot mutate SQL. Retain
   actualNode24identity, inputs, commands, body/SQL traces, failures and cleanup.

One owned compact local campaign bound180s/1cluster/1HTTP/≤5000typedrows/≤150HTTP/
96MiBevidence. No cloud/provider/RAM calls; binary asset delivery is not tested.
The initial RED is retained and expected to stop at the first unsupported contract;
remaining cases are unverified. A successful rerun requires reviewed product code.

Command from repository root:
`PYTHONPATH=/tmp/statarena-publication-test-python PYTHONDONTWRITEBYTECODE=1 python3 tests/orion_pro_operations_local.py --node /tmp/statarena-node24-runtime/v24.22.2/node-v24.22.2-darwin-arm64/bin/node --label precode`
