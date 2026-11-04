import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import { mkdtemp, readFile, writeFile, rm, chmod } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { createRequire } from "node:module";

const phase = process.argv[2];
assert.match(
  phase || "",
  /^(before|before-nested|before-head|before-cache|before-etag|after)$/,
);
const root =
  process.env.STATARENA_VERIFY_ROOT ||
  path.resolve(import.meta.dir, "../../..");
const require = createRequire(path.join(root, "dashboard/package.json"));
const { Client } = require("pg");
const tools =
  process.env.STATARENA_TEST_TOOLS || "/tmp/statarena-cache-test-tools";
const { default: EmbeddedPostgres } = await import(
  path.join(tools, "node_modules/embedded-postgres/dist/index.js")
);
const scratch = await mkdtemp(path.join(tmpdir(), "match-sql-"));
const report = {
  phase,
  source: execFileSync("git", ["-C", root, "rev-parse", "HEAD"], {
    encoding: "utf8",
  }).trim(),
  command:
    "PYTHONPATH=/tmp/statarena-archive-remat-pg/python bun docs/verification/relational-match-20261104/verify.mjs " +
    phase,
  setup:
    "PROTOCOL.md; PostgreSQL 18, verified local TLS, migration 004; seed.py, PROTOCOL.md and source archive captures",
  requests: [],
};
const telemetry = [];
let postgres, admin, closeRuntime, http;
try {
  const key = path.join(scratch, "server.key"),
    cert = path.join(scratch, "server.crt");
  execFileSync(
    "openssl",
    [
      "req",
      "-x509",
      "-newkey",
      "rsa:2048",
      "-nodes",
      "-keyout",
      key,
      "-out",
      cert,
      "-days",
      "1",
      "-subj",
      "/CN=localhost",
      "-addext",
      "subjectAltName=IP:127.0.0.1,DNS:localhost",
    ],
    { stdio: "ignore" },
  );
  await chmod(key, 0o600);
  const reserved = Bun.listen({
      hostname: "127.0.0.1",
      port: 0,
      socket: { data() {} },
    }),
    port = reserved.port;
  reserved.stop(true);
  postgres = new EmbeddedPostgres({
    databaseDir: path.join(scratch, "pg"),
    user: "fixture",
    password: "fixture",
    port,
    persistent: false,
    autoRehydrateSymlinks: true,
    postgresFlags: [
      "-c",
      "listen_addresses=127.0.0.1",
      "-c",
      "ssl=on",
      "-c",
      "ssl_cert_file=" + cert,
      "-c",
      "ssl_key_file=" + key,
    ],
    onLog() {},
    onError() {},
  });
  await postgres.initialise();
  await postgres.start();
  const url = "postgresql://fixture:fixture@127.0.0.1:" + port + "/postgres",
    ca = await readFile(cert, "utf8");
  admin = new Client({
    connectionString: url,
    ssl: { ca, rejectUnauthorized: true },
  });
  await admin.connect();
  report.database = (
    await admin.query(
      "SELECT current_setting('server_version') AS version,(SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()) AS tls",
    )
  ).rows[0];
  report.inputHashes = {};
  for (const name of [
    "dashboard/backend/migrations/004_match_details.sql",
    "dashboard/backend/services/relational-match.js",
    "dashboard/backend/services/postgres.js",
    "dashboard/backend/services/cache.js",
    "dashboard/scripts/relational_match.py",
    "dashboard/scripts/relational_match_model.py",
    "dashboard/outputs/data-completeness/production-archive.json",
    "dashboard/outputs/data-completeness/browser-historical-archive.json",
    "dashboard/outputs/data-completeness/browser-upcoming-archive.json",
    "docs/verification/relational-match-20261104/nested-source.json",
  ]) {
    report.inputHashes[name] = createHash("sha256")
      .update(await readFile(path.join(root, name)))
      .digest("hex");
  }
  await admin.query("CREATE SCHEMA statarena_app");
  await admin.query(
    await readFile(
      path.join(root, "dashboard/backend/migrations/004_match_details.sql"),
      "utf8",
    ),
  );
  const conn = new URL(url);
  conn.searchParams.set("sslmode", "verify-full");
  conn.searchParams.set("sslrootcert", cert);
  execFileSync(
    process.env.PYTHON || "python3",
    [path.join(import.meta.dir, "seed.py")],
    { env: { ...process.env, LOCAL_FIXTURE_DB: conn.href }, stdio: "pipe" },
  );
  const columns = (
    await admin.query(
      "SELECT table_name,column_name,data_type FROM information_schema.columns WHERE table_schema='statarena_app' AND data_type IN ('json','jsonb','bytea')",
    )
  ).rows;
  assert.deepEqual(columns, []);
  report.jsonOrByteaColumns = columns;
  report.tableCount = (
    await admin.query(
      "SELECT count(*)::int AS tables FROM pg_tables WHERE schemaname='statarena_app'",
    )
  ).rows[0].tables;

  Object.assign(process.env, {
    STATARENA_DATA_PROVIDER: "aws",
    STATARENA_TEST_DATABASE: "1",
    STATARENA_EXTERNAL_STORAGE: "1",
    STATARENA_METRICS_SAMPLE_RATE: "1",
    DATABASE_URL: url,
    DATABASE_CA_PEM: ca,
    STATARENA_DATABASE_CA_PEM: ca,
    NEON_DATABASE_URL: url,
  });
  const log = console.log;
  console.log = (...args) => {
    try {
      const row = JSON.parse(args[0]);
      if (row.event === "statarena.request") {
        telemetry.push(row);
        return;
      }
    } catch {}
    log(...args);
  };
  const { relationalMatchObservation, relationalResource } = await import(
    path.join(root, "dashboard/backend/services/relational-match.js")
  );
  ({ closeDatabase: closeRuntime } = await import(
    path.join(root, "dashboard/backend/services/postgres.js")
  ));
  const { instrumentRequest } = await import(
    path.join(root, "dashboard/backend/services/metrics.js")
  );
  http = Bun.serve({
    hostname: "127.0.0.1",
    port: 0,
    fetch(request) {
      return instrumentRequest(request, async () => {
        const url = new URL(request.url),
          [prefix, ...parts] = url.pathname.slice(1).split("/");
        const head = request.method === "HEAD",
          withMeta = request.headers.has("x-fixture-meta");
        const obj =
          prefix === "archive"
            ? await relationalMatchObservation(parts[0], { head, withMeta })
            : await relationalResource(
                "/" + parts.join("/"),
                Object.fromEntries(url.searchParams),
                { head, withMeta },
              );
        if (head)
          return new Response(null, {
            status: obj ? 200 : 404,
            headers: obj?.etag ? { etag: obj.etag } : {},
          });
        if (withMeta && obj)
          return Response.json(obj.value ?? null, {
            headers: obj.etag ? { etag: obj.etag } : {},
          });
        return obj ? Response.json(obj) : new Response(null, { status: 404 });
      });
    },
  });
  async function check(route, expected) {
    const start = performance.now(),
      ti = telemetry.length,
      r = await fetch(new URL(route, http.url)),
      bytes = Buffer.from(await r.arrayBuffer());
    const actual = bytes.length ? JSON.parse(bytes) : null;
    const metrics = telemetry.slice(ti).at(-1)?.metrics;
    const row = {
      route,
      status: r.status,
      bytes: bytes.length,
      ms: performance.now() - start,
      sha256: createHash("sha256").update(bytes).digest("hex"),
      metrics,
    };
    report.requests.push(row);
    assert.equal(r.status, expected ? 200 : 404);
    assert.deepEqual(actual, expected);
    assert.ok([1, 2].includes(metrics?.sql_count));
    assert.equal(metrics?.object_bytes || 0, 0);
    row.passed = true;
  }
  const suffixes = {
    match: "",
    player_halves: "/players/halves",
    advanced_teams: "/advanced",
    advanced_players: "/advanced/players",
    pass_networks: "/advanced/network",
  };
  for (const file of [
    "production-archive",
    "browser-historical-archive",
    "browser-upcoming-archive",
  ]) {
    const rec = JSON.parse(
      await readFile(
        path.join(root, "dashboard/outputs/data-completeness", file + ".json"),
        "utf8",
      ),
    );
    const mid = rec.fixture.id;
    await check("/archive/" + mid, rec);
    for (const [family, value] of Object.entries(rec.endpoints))
      await check(
        "/resource/matches/" + mid + (suffixes[family] ?? "/" + family),
        value,
      );
    if (file === "production-archive") {
      const variant = structuredClone(rec.endpoints.heatmaps);
      variant.data.grid.frame = "acting_ltr";
      await check(
        "/resource/matches/" + mid + "/heatmaps?frame=acting_ltr",
        variant,
      );
    }
  }
  await check("/archive/m_000001", {
    endpoints: {
      momentum: {
        status: 429,
        error: { code: "RATE_LIMIT", message: "retry" },
      },
      shots: {
        status: 200,
        data: { match_id: "m_000001", periods: [] },
        error: null,
      },
    },
  });
  await check("/archive/m_000004", null);
  const captured = JSON.parse(
    await readFile(path.join(import.meta.dir, "nested-source.json"), "utf8"),
  );
  for (const item of captured.sample) {
    await check("/resource" + item.endpoint, {
      status: item.status,
      data: item.sample?.data ?? null,
      error: item.error || item.sample?.error || null,
    });
  }
  await check("/archive/m_000Xjk", null);
  await check("/resource/matches/m_000Xjk/shots/s_ZZZZZZ", null);
  for (const [route, status] of [
    ["/archive/m_49qvGz", 200],
    ["/archive/m_000004", 404],
    ["/resource/matches/m_000Xjk/players/p_076Ulj/halves", 200],
  ]) {
    const pos = telemetry.length,
      res = await fetch(new URL(route, http.url), { method: "HEAD" });
    const bytes = Buffer.from(await res.arrayBuffer()),
      metrics = telemetry.slice(pos).at(-1)?.metrics;
    report.requests.push({
      method: "HEAD",
      route,
      status: res.status,
      bytes: bytes.length,
      metrics,
    });
    assert.equal(res.status, status);
    assert.equal(bytes.length, 0);
    assert.equal(metrics?.sql_count, 1);
    assert.equal(metrics?.sql_json_rows || 0, 0);
  }
  const rec = JSON.parse(
    await readFile(
      path.join(
        root,
        "dashboard/outputs/data-completeness/production-archive.json",
      ),
      "utf8",
    ),
  );
  const mid = rec.fixture.id,
    route = "/archive/" + mid;
  const warm = [];
  for (let i = 0; i < 7; i++) {
    await check(route, rec);
    const row = report.requests.at(-1);
    warm.push(row);
  }
  report.warmMedianMs = warm.map((r) => r.ms).sort((a, b) => a - b)[3];
  for (const row of warm) {
    assert.equal(row.metrics.sql_count, 1);
    assert.equal(row.metrics.sql_json_rows || 0, 0);
  }
  async function tag() {
    const r = await fetch(new URL(route, http.url), { method: "HEAD" });
    const etag = r.headers.get("etag");
    assert.match(etag || "", /^W\/"[^"]+"$/);
    return etag;
  }
  function update(mode) {
    execFileSync(
      process.env.PYTHON || "python3",
      [path.join(import.meta.dir, "seed.py"), mode],
      { env: { ...process.env, LOCAL_FIXTURE_DB: conn.href }, stdio: "pipe" },
    );
  }
  const oldTag = await tag();
  update("context");
  rec.competition_name = "Edited publication";
  assert.notEqual(await tag(), oldTag);
  await check(route, rec);
  const contextTag = await tag();
  update("family");
  rec.endpoints.momentum = {
    status: 200,
    data: { match_id: mid, points: [] },
    error: null,
  };
  assert.notEqual(await tag(), contextTag);
  await check(route, rec);
  const unavailable = captured.sample.find((x) => x.status === 404);
  for (let i = 0; i < 2; i++) {
    await check("/resource" + unavailable.endpoint, {
      status: 404,
      data: null,
      error: unavailable.error,
    });
    assert.equal(
      report.requests.at(-1).metrics.cache_match_representation_hit || 0,
      0,
    );
  }
  const oversize = {
    status: 200,
    data: { stadium: "x".repeat(2 * 1024 * 1024) },
    error: null,
  };
  for (let i = 0; i < 2; i++) {
    await check("/resource/matches/m_ZZZZZZ", oversize);
    assert.equal(
      report.requests.at(-1).metrics.cache_match_representation_rejected,
      1,
    );
  }
  await check(route, rec);
  assert.equal(
    report.requests.at(-1).metrics.cache_match_representation_hit,
    1,
  );
  for (const [url, expected] of [
    [route, rec],
    ["/resource/matches/" + mid + "/momentum", rec.endpoints.momentum],
  ]) {
    const response = await fetch(new URL(url, http.url), {
        headers: { "x-fixture-meta": "1" },
      }),
      head = await fetch(new URL(url, http.url), { method: "HEAD" });
    assert.match(response.headers.get("etag") || "", /^W\/"/);
    assert.equal(response.headers.get("etag"), head.headers.get("etag"));
    assert.deepEqual(await response.json(), expected);
  }
  report.passed = true;
} catch (error) {
  report.error = String(error.stack || error).slice(0, 2400);
  report.passed = false;
} finally {
  http?.stop(true);
  await closeRuntime?.();
  await admin?.end();
  await postgres?.stop();
  await rm(scratch, { recursive: true, force: true });
  await writeFile(
    path.join(import.meta.dir, phase + ".json"),
    JSON.stringify(report, null, 2) + "\n",
  );
}
console.log(
  report.passed ? "PASS" : "FAIL",
  report.requests.length,
  report.error || "",
);
process.exitCode = report.passed ? 0 : 1;
