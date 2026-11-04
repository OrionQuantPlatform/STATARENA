import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import {
  mkdtemp,
  readFile,
  writeFile,
  rm,
  chmod,
  symlink,
} from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { createRequire } from "node:module";
import { gzipSync } from "node:zlib";

const phase = "legacy-same-input";
const baseline = "923bb0ff4a";
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
  source: baseline,
  command: "bun docs/verification/relational-match-20261104/legacy.mjs",
  setup:
    "PROTOCOL.md; PostgreSQL 18, verified local TLS, legacy handler 923bb0ff4a, three identical provider archive captures, gzip encoded into one shared shard across three matches",
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
  const inputs = [];
  for (const file of [
    "production-archive",
    "browser-historical-archive",
    "browser-upcoming-archive",
  ])
    inputs.push(
      JSON.parse(
        await readFile(
          path.join(
            root,
            "dashboard/outputs/data-completeness",
            file + ".json",
          ),
          "utf8",
        ),
      ),
    );
  const docs = inputs.map(({ endpoints, ...metadata }) => ({
    id: metadata.fixture.id,
    metadata,
    endpoints: Object.keys(endpoints),
  }));
  const document = await put("documents", docs);
  const tables = {};
  for (const family of Object.keys(inputs[0].endpoints)) {
    const items = inputs
      .filter((d) => d.endpoints[family])
      .map((d) => ({
        documentId: d.fixture.id,
        response: d.endpoints[family],
      }));
    tables[family] = await put(family, items);
  }
  await admin.query("INSERT INTO statarena.shards VALUES ('s',$1)", [
    { document, tables },
  ]);
  for (const [idx, doc] of docs.entries())
    await admin.query("INSERT INTO statarena.observations VALUES ($1,'s',$2)", [
      doc.id,
      idx,
    ]);
  const tar = path.join(scratch, "legacy.tar");
  execFileSync("git", [
    "-C",
    root,
    "archive",
    baseline,
    "dashboard/backend",
    "--output=" + tar,
  ]);
  execFileSync("tar", ["-xf", tar, "-C", scratch]);
  await symlink(
    path.join(root, "dashboard/node_modules"),
    path.join(scratch, "dashboard/node_modules"),
  );
  const { handleRequest } = await import(
    path.join(scratch, "dashboard/backend/app.js")
  );
  http = Bun.serve({ hostname: "127.0.0.1", port: 0, fetch: handleRequest });
  for (const expected of inputs) {
    const route = "/api/archive/matches/" + expected.fixture.id,
      ri = reads.length;
    const start = performance.now(),
      r = await fetch(new URL(route, http.url)),
      bytes = Buffer.from(await r.arrayBuffer());
    const row = {
      route,
      status: r.status,
      bytes: bytes.length,
      ms: performance.now() - start,
      metrics: telemetry.at(-1)?.metrics,
      objectReads: reads.slice(ri),
    };
    report.requests.push(row);
    assert.equal(r.status, 200);
    assert.deepEqual(JSON.parse(bytes), expected);
    row.passed = true;
  }
  report.passed = true;
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
  report.requests.map((r) => [r.route, r.bytes, r.metrics]),
);
process.exitCode = report.passed ? 0 : 1;
