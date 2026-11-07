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
  /^(before|before-nested|before-head|before-cache|before-completeness|before-etag|before-large-cache|after)$/,
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
    "PYTHONPATH=/tmp/statarena-archive-remat-pg/python bun docs/verification/aws-catalog-20261104/verify.mjs " +
    phase,
  setup:
    "PROTOCOL.md; PostgreSQL 18, verified local TLS, migrations 006/032; seed.py, PROTOCOL.md and source archive captures",
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
    "dashboard/backend/migrations/006_catalog_models.sql",
    "dashboard/backend/migrations/032_archive_read_projection.sql",
    "dashboard/backend/services/relational-catalog.js",
    "dashboard/backend/services/catalog-model.json",
    "dashboard/backend/services/archive-projection-model.json",
    "dashboard/scripts/relational_catalog.py",
    "dashboard/scripts/relational_catalog_keys.py",
    "dashboard/scripts/relational_match.py",
    "dashboard/scripts/relational_match_ddl.py",
    "dashboard/scripts/consolidated_storage.py",
    "dashboard/scripts/consolidated_model.py",
    "dashboard/scripts/archive_projection.py",
    "dashboard/scripts/archive_projection.mjs",
    "dashboard/shared/archive-projection.js",
    "dashboard/shared/archive.js",
    "dashboard/shared/archive-text.js",
    "dashboard/shared/openfootball-history.js",
    "docs/verification/aws-catalog-20261104/supplemental-full.json.gz",
  ]) {
    report.inputHashes[name] = createHash("sha256")
      .update(await readFile(path.join(root, name)))
      .digest("hex");
  }
  await admin.query("CREATE SCHEMA statarena_app");
  await admin.query(
    await readFile(
      path.join(root, "dashboard/backend/migrations/006_catalog_models.sql"),
      "utf8",
    ),
  );
  await admin.query(
    await readFile(
      path.join(
        root,
        "dashboard/backend/migrations/032_archive_read_projection.sql",
      ),
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
      "SELECT table_name,column_name,data_type FROM information_schema.columns WHERE table_schema='statarena_app' AND data_type IN ('json','jsonb','bytea') ORDER BY table_name,column_name",
    )
  ).rows;
  // Only these explicit derived read columns may be JSON. Canonical catalogue
  // facts must keep the original typed-column contract; no blanket exception.
  assert.deepEqual(columns, [
    {
      table_name: "archive_read_editions",
      column_name: "competitions",
      data_type: "jsonb",
    },
    {
      table_name: "archive_read_editions",
      column_name: "source_fence",
      data_type: "jsonb",
    },
    {
      table_name: "archive_read_editions",
      column_name: "summary",
      data_type: "jsonb",
    },
    {
      table_name: "archive_read_matches",
      column_name: "goals",
      data_type: "jsonb",
    },
    {
      table_name: "archive_read_matches",
      column_name: "listing",
      data_type: "jsonb",
    },
  ]);
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
  const { getCatalog, getProfile } = await import(
    path.join(root, "dashboard/backend/services/relational-catalog.js")
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
        const u = new URL(request.url),
          p = Object.fromEntries(u.searchParams),
          key = u.pathname.slice(1),
          head = request.method === "HEAD",
          withMeta = request.headers.has("x-fixture-meta");
        let value;
        try {
          value =
            key === "profile"
              ? await getProfile(p.kind, p.id || null, { head, withMeta })
              : await getCatalog(key, p, { head, withMeta });
        } catch (e) {
          return new Response(e.message, { status: 503 });
        }
        return value == null
          ? new Response(null, { status: 404 })
          : head
            ? new Response(null, {
                headers: value.etag ? { etag: value.etag } : {},
              })
            : withMeta
              ? Response.json(value.value ?? null, {
                  headers: value.etag ? { etag: value.etag } : {},
                })
              : Response.json(value);
      });
    },
  });
  const { readdir } = await import("node:fs/promises"),
    { gunzipSync } = await import("node:zlib");
  const inputs = {};
  for (const file of await readdir(path.join(import.meta.dir, "captures"))) {
    const name = file.slice(0, -3).replaceAll("__", "/");
    inputs[name] = JSON.parse(
      gunzipSync(await readFile(path.join(import.meta.dir, "captures", file))),
    );
  }
  async function check(route, expected, head = false) {
    const pos = telemetry.length,
      start = performance.now(),
      r = await fetch(new URL(route, http.url), {
        method: head ? "HEAD" : "GET",
      }),
      bytes = Buffer.from(await r.arrayBuffer()),
      m = telemetry.slice(pos).at(-1)?.metrics;
    const row = {
      route,
      status: r.status,
      method: head ? "HEAD" : "GET",
      bytes: bytes.length,
      ms: performance.now() - start,
      metrics: m,
      sha256: createHash("sha256").update(bytes).digest("hex"),
    };
    report.requests.push(row);
    assert.equal(r.status, expected == null ? 404 : 200);
    if (!head)
      assert.deepEqual(bytes.length ? JSON.parse(bytes) : null, expected);
    else {
      assert.equal(bytes.length, 0);
      assert.equal(m.sql_json_rows || 0, 0);
    }
    assert.equal(m?.object_bytes || 0, 0);
    row.passed = true;
  }
  for (const [name, v] of Object.entries(inputs)) {
    const archive =
      /^raw\/(openfootball|historical-goals)\/([^/]+)\.json(\.gz)?$/.exec(name);
    if (archive) {
      const k = archive[1] === "openfootball" ? "results" : "goals";
      if (archive[2] === "index") {
        const clean = structuredClone(v);
        for (const e of clean.seasons) delete e.path;
        await check("/archives/index?kind=" + k, clean);
      } else
        await check(
          "/archives/season?kind=" +
            k +
            "&season=" +
            encodeURIComponent(v.season),
          v,
        );
    }
    if (name.startsWith("profile/")) {
      const [, kind, id] = name.split("/");
      await check(
        "/profile?" + new URLSearchParams({ kind, ...(id ? { id } : {}) }),
        v,
      );
    }
    const edition = /^raw\/rankings\/([^/]+)\/([^/]+)\.json$/.exec(name);
    if (edition) {
      await check(
        "/rankings/edition?" +
          new URLSearchParams({ kind: edition[1], edition: edition[2] }),
        v,
      );
      if (edition[1] === "uefa-associations" && edition[2].endsWith(".uefa"))
        await check("/rankings/associations?year=" + edition[2].slice(0, 4), v);
    }
    const cup =
      /^raw\/cup-worker\/(native|open-cups|standings|openligadb|nations-results)\/([^/]+)\/([^/]+)\.json$/.exec(
        name,
      );
    if (cup)
      await check(
        "/cup-snapshot?" +
          new URLSearchParams({
            kind: cup[1],
            competition: cup[2],
            season: cup[3].replace("-", "/"),
          }),
        v,
      );
    if (name.startsWith("computed/matchdays/")) {
      const competition = Object.keys(v)[0];
      await check(
        "/matchdays?" +
          new URLSearchParams({ competition, season: "2026/2027" }),
        { matches: v[competition] },
      );
    }
  }
  const links = inputs["raw/rankings/club-links.json"].links,
    club = Object.keys(links)[0];
  await check("/club-links?club=" + club, { links: { [club]: links[club] } });
  const index = inputs["raw/rankings/index.json"],
    expectedRows = index.editions
      .filter((e) => e.kind === "uefa-clubs" && e.provider === "UEFA")
      .map(({ path, ...edition }) => ({
        edition,
        row:
          inputs[path]?.rows.find((r) => r.entityId === links[club].entityId) ??
          null,
      }));
  await check("/rankings/club?club=" + club, { rows: expectedRows });
  for (const [kind, file] of [
    ["worker", "raw/cup-worker/index.json"],
    ["supplemental", "raw/supplemental-index.json"],
  ]) {
    const input = inputs[file],
      clean = structuredClone(input);
    for (const comp of clean.competitions) {
      const first = Object.values(comp.tables)[0];
      comp.season ??= first.path
        .match(/(\d{4})-(\d{4})/)
        .slice(1)
        .join("/");
      comp.tables = Object.fromEntries(
        Object.entries(comp.tables).map(([key, ref]) => [
          key,
          { rows: ref.rows },
        ]),
      );
    }
    await check("/cup-index?kind=" + kind, clean);
    const c = input.competitions[0];
    for (const [table, ref] of Object.entries(c.tables))
      if (inputs[ref.path])
        await check(
          "/cup-table?" +
            new URLSearchParams({
              competition: c.folder,
              season: clean.competitions[0].season,
              kind: table,
            }),
          inputs[ref.path],
        );
  }
  await check("/rankings/associations?year=2027", {}, true);
  await check("/archives/season?kind=goals&season=0000", null);
  await check("/rankings/club?club=t_NOMAPP", { rows: null });
  const errorProfile = {
    status: 404,
    error: { code: "RESOURCE_NOT_FOUND", message: "unavailable" },
  };
  for (let i = 0; i < 2; i++) {
    await check("/profile?kind=players&id=p_FAIL00", errorProfile);
    assert.equal(
      report.requests.at(-1).metrics.cache_catalog_representation_hit || 0,
      0,
    );
  }
  const incomplete = await fetch(new URL("/supplemental", http.url));
  assert.equal(incomplete.status, 503);
  execFileSync(
    process.env.PYTHON || "python3",
    [path.join(import.meta.dir, "seed.py"), "supplemental"],
    { env: { ...process.env, LOCAL_FIXTURE_DB: conn.href }, stdio: "pipe" },
  );
  const full = JSON.parse(
    gunzipSync(
      await readFile(path.join(import.meta.dir, "supplemental-full.json.gz")),
    ),
  );
  const index2 = inputs["raw/supplemental-index.json"];
  await check("/supplemental", {
    meta: index2.meta,
    competitions: index2.competitions.map(({ tables, ...meta }) => ({
      ...meta,
      ...Object.fromEntries(
        Object.entries(tables).map(([kind, ref]) => [kind, full[ref.path]]),
      ),
    })),
  });
  for (const route of [
    "/archives/index?kind=goals",
    "/rankings/club?club=" + club,
    "/club-links?club=" + club,
    "/cup-table?competition=AUT_1_bundesliga&season=2026%2F2027&kind=goals",
    "/supplemental",
    "/profile?kind=players&id=p_FAIL00",
  ]) {
    const base = await fetch(new URL(route, http.url)),
      tagged = await fetch(new URL(route, http.url), {
        headers: { "x-fixture-meta": "1" },
      }),
      header = await fetch(new URL(route, http.url), { method: "HEAD" });
    assert.match(tagged.headers.get("etag") || "", /^W\/"/);
    assert.equal(tagged.headers.get("etag"), header.headers.get("etag"));
    assert.deepEqual(await tagged.json(), await base.json());
    assert.equal(telemetry.at(-1).metrics.sql_json_rows || 0, 0);
  }
  report.warmLarge = [];
  for (const route of [
    "/supplemental",
    "/archives/season?kind=goals&season=2023%2F2024",
  ]) {
    const expected = await (await fetch(new URL(route, http.url))).json(),
      rows = [];
    for (let i = 0; i < 5; i++) {
      await check(route, expected);
      rows.push(report.requests.at(-1));
    }
    report.warmLarge.push({
      route,
      medianMs: rows.map((r) => r.ms).sort((a, b) => a - b)[2],
      jsonRows: rows.map((r) => r.metrics.sql_json_rows || 0),
      sqlCounts: rows.map((r) => r.metrics.sql_count),
    });
  }
  for (const set of report.warmLarge) {
    assert.ok(set.jsonRows.every((n) => n === 0));
    assert.ok(set.sqlCounts.every((n) => n === 1));
  }
  const fullUrl = new URL("/supplemental", http.url),
    prior = (await fetch(fullUrl, { method: "HEAD" })).headers.get("etag");
  execFileSync(
    process.env.PYTHON || "python3",
    [path.join(import.meta.dir, "seed.py"), "change-supplemental"],
    { env: { ...process.env, LOCAL_FIXTURE_DB: conn.href }, stdio: "pipe" },
  );
  const newer = await fetch(fullUrl, { headers: { "x-fixture-meta": "1" } });
  assert.notEqual(prior, newer.headers.get("etag"));
  assert.equal(
    (await newer.json()).competitions.find(
      (c) => c.folder === "ENG_1_premier-league",
    ).goals[0].scorer,
    "Updated sample",
  );
  if (process.argv.includes("--all")) {
    execFileSync(
      process.env.PYTHON || "python3",
      [path.join(import.meta.dir, "full_roundtrip.py")],
      { env: { ...process.env, LOCAL_FIXTURE_DB: conn.href }, stdio: "pipe" },
    );
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
