# Pro runtime selects RDS only — pre-code E2E

Suggested commit: `fix: prevent Pro runtime from falling back to Neon configuration`.

Failure: common postgres.js currently selects NEON_DATABASE_URL when both the
provider and DATABASE_URL are absent, even while STATARENA_PRO_API=1. A Pro
runtime must require its AWS database configuration. Legacy OFF behavior remains
an explicit compatibility control during migration; source access for transfer
is separate from web runtime.

Before code: actual Node24 AWS HTTP handler, fixed minimal child environments,
no PostgreSQL/cloud/provider, pg.Client.connect tripwire and external-fetch
tripwire. The Neon-shaped input points only to an owned loopback address; it is
never a real credential or endpoint. Startup intentionally does not query SQL.

Cases N01–N07:
- Pro ON with only NEON_DATABASE_URL: /status configured=false; no SQL/driver.
- Same environment: /health503 pending/revisionnull/no-store, HEAD body empty,
  no SQL/driver. Missing configuration must not appear ready.
- Same environment: native /fixtures fails as configuration error500/no-store,
  no pg.Client.connect or external fetch; never an empty successful data response.
- Invalid POST405 before any driver.
- Pro ON with DATABASE_URL pointing outside RDS and a Neon setting: refuse native
  access before driver; never fall back. This test does not enable local DB bypass.
- Pro OFF legacy /status retains configured=true for its existing Neon setting;
  no actual source connection is made.
- Every child reports actualNode24; no source/driver/network call; input hashes
  unchanged and all owned children stopped. Preserve initial RED and failed cases.

Bound90s/three owned HTTP children sequentially/≤30local requests/8MiB evidence.
No source content, external browser, RDS, SSM, source corpus or AWS action.
Positive actual typed PG behavior is already covered by the separate14case
Node24 operations E2E and remains a required regression after the change.

Rerun:
`PYTHONDONTWRITEBYTECODE=1 python3 tests/orion_pro_runtime_origin_local.py --node /tmp/statarena-node24-runtime/v24.22.2/node-v24.22.2-darwin-arm64/bin/node --label precode`
