import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import { mkdtemp, readFile, writeFile, rm, chmod } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { createRequire } from "node:module";
import { gzipSync } from "node:zlib";

const phase = process.argv[2];
assert.match(phase || "", /^(before|after)$/);
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
  command: "bun docs/verification/aws-sql-reads-20261104/verify.mjs " + phase,
  setup:
    "PROTOCOL.md; PostgreSQL 18, verified local TLS, migrations 001 and 002; fixtures and expected values in verify.mjs",
  requests: [],
};
const files = new Map(),
  reads = [],
  telemetry = [];
let postgres, admin, storage, http;
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
  for (const migration of ["001_neon.sql", "002_aws_documents.sql"])
    await admin.query(
      await readFile(
        path.join(root, "dashboard/backend/migrations", migration),
        "utf8",
      ),
    );
  storage = Bun.serve({
    hostname: "127.0.0.1",
    port: 0,
    fetch(request) {
      const key = decodeURIComponent(new URL(request.url).pathname).replace(
        /^\/fixture\/data\//,
        "",
      );
      const b = files.get(key);
      reads.push({ key, bytes: b?.length || 0 });
      return new Response(b, { status: b ? 200 : 404 });
    },
  });
  Object.assign(process.env, {
    STATARENA_DATA_PROVIDER: "aws",
    STATARENA_EXTERNAL_STORAGE: "1",
    STATARENA_METRICS_SAMPLE_RATE: "1",
    STATARENA_DATABASE_URL: url,
    STATARENA_DATABASE_CA_PEM: ca,
    NEON_DATABASE_URL: url,
    NEON_STORAGE_ENDPOINT: storage.url.origin,
    NEON_STORAGE_BUCKET: "fixture",
    NEON_STORAGE_ACCESS_KEY_ID: "fixture",
    NEON_STORAGE_SECRET_ACCESS_KEY: "fixture",
    NEON_STORAGE_REGION: "us-east-2",
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
  async function put(name, data, stale = false) {
    const p = "raw/" + name + ".json.gz",
      b = gzipSync(JSON.stringify(data)),
      sha = createHash("sha256").update(b).digest();
    files.set(p, b);
    await admin.query(
      "INSERT INTO statarena.objects(path,size,sha256,etag) VALUES ($1,$2,$3,$4)",
      [p, b.length, sha, sha.toString("hex")],
    );
    const indexed = stale ? Buffer.alloc(32, 99) : sha;
    await admin.query(
      "INSERT INTO statarena.file_documents(document_path,source_path,source_sha256,format,document) VALUES($1,$1,$2,'json',$3::jsonb)",
      [p, indexed, JSON.stringify(data)],
    );
    await admin.query(
      "INSERT INTO statarena.file_document_sources(source_path,source_sha256,status,document_count,error_count) VALUES($1,$2,'ready',1,0)",
      [p, indexed],
    );
    return { path: p };
  }
  const target = "m_000001",
    archiveId = "opaque-actual-doc",
    keys = ["match", "shots", "stats", "misc", "events"],
    metadata = { id: target, season: "2026/2027", absent: null };
  const other = {
    documentId: "other",
    response: { data: "irrelevant".repeat(25000) },
  };
  const document = await put("documents", [
    { id: "other", metadata: {}, endpoints: [] },
    { id: archiveId, metadata, endpoints: keys },
    { id: "missing-row", metadata: {}, endpoints: ["shots"] },
  ]);
  const tables = {},
    archived = {},
    recentError = { code: "ARCHIVED_REPLACED" },
    saved = (data) => ({ status: 200, data, error: null });
  for (const key of keys) {
    archived[key] = {
      status: 200,
      data: { family: key, count: 0, missing: null, flag: false },
      source: "archive",
    };
    tables[key] = await put(key, [
      other,
      { documentId: archiveId, response: archived[key] },
    ]);
  }
  await admin.query("INSERT INTO statarena.shards VALUES ('s',$1)", [
    { document, tables },
  ]);
  await admin.query(
    "INSERT INTO statarena.observations VALUES ($1,'s',1),('m_000003','s',2)",
    [target],
  );
  async function resource(
    endpoint,
    ref,
    status = 200,
    error = null,
    params = "{}",
  ) {
    await admin.query(
      "INSERT INTO statarena.resources(endpoint,ref,status,error,params) VALUES($1,$2,$3,$4,$5)",
      [endpoint, ref, status, error, params],
    );
  }
  const direct = await put("direct", { data: { score: 0 } }),
    ordinal = await put("ordinal", [other, { observation: { data: false } }]),
    byId = await put("by-id", [
      other,
      { documentId: archiveId, response: { data: [] } },
    ]),
    stale = await put("stale", { data: true }, true);
  await resource("/matches/" + target, direct);
  await resource("/matches/" + target + "/stats", null, 429, recentError);
  await resource("/matches/" + target + "/momentum", {
    ...ordinal,
    ordinal: 1,
  });
  await resource("/matches/" + target + "/lineups", {
    ...byId,
    documentId: archiveId,
  });
  await resource("/matches/m_000002", await put("null", { data: null }));
  await resource("/players/p_000001", stale);
  await resource("/players/p_000002", { ...ordinal, ordinal: 99 });
  const { handleRequest } = await import(
    path.join(root, "dashboard/backend/app.js")
  );
  http = Bun.serve({ hostname: "127.0.0.1", port: 0, fetch: handleRequest });
  async function check(route, status, expected, single = false) {
    const ri = reads.length,
      ti = telemetry.length;
    const start = performance.now(),
      r = await fetch(new URL(route, http.url)),
      bytes = Buffer.from(await r.arrayBuffer());
    let actual;
    try {
      actual = JSON.parse(bytes);
    } catch {
      actual = bytes.toString();
    }
    const metrics = telemetry.slice(ti).at(-1)?.metrics;
    const row = {
      route,
      expectedStatus: status,
      expected,
      actualStatus: r.status,
      actual,
      bytes: bytes.length,
      ms: performance.now() - start,
      metrics,
      objectReads: reads.slice(ri),
      failures: [],
    };
    report.requests.push(row);
    const verify = (f) => {
      try {
        f();
      } catch (e) {
        row.failures.push(e.message);
      }
    };
    verify(() => assert.equal(r.status, status));
    if (expected !== undefined)
      verify(() => assert.deepEqual(actual, expected));
    verify(() => assert.ok(metrics, "sampled metrics required"));
    verify(() => assert.equal(row.objectReads.length, 0, "object reads"));
    verify(() =>
      assert.equal(
        metrics?.parse_bytes || 0,
        0,
        "application parsed file bytes",
      ),
    );
    if (single)
      verify(() =>
        assert.equal(metrics?.sql_count, 1, "cold match SQL statements"),
      );
  }
  await check(
    "/api/archive/matches/" + target,
    200,
    {
      ...metadata,
      endpoints: {
        ...archived,
        match: saved({ score: 0 }),
        stats: { status: 429, error: recentError },
        momentum: saved(false),
        lineups: saved([]),
      },
    },
    true,
  );
  await check("/api/pitchapi/matches/" + target + "/shots", 200, {
    data: archived.shots.data,
  });
  await check("/api/pitchapi/matches/" + target + "/stats", 429, {
    ok: false,
    error: recentError,
  });
  await check(
    "/api/archive/matches/m_000002",
    200,
    { endpoints: { match: saved(null) } },
    true,
  );
  await check("/api/archive/matches/m_000003", 503, undefined, true);
  await check("/api/archive/matches/m_000004", 404, undefined, true);
  await check("/api/archive/profiles/players/p_000001", 503);
  await check("/api/archive/profiles/players/p_000002", 503);
  report.passed = report.requests.every((r) => !r.failures.length);
} finally {
  http?.stop(true);
  storage?.stop(true);
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
  report.requests.map((r) => [
    r.route,
    r.actualStatus,
    r.metrics?.sql_count,
    r.failures.length,
  ]),
);
process.exitCode = report.passed ? 0 : 1;
