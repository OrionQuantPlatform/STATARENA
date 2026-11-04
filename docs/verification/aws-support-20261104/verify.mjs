import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import { mkdtemp, readFile, writeFile, rm, chmod } from "node:fs/promises";
import { tmpdir } from "node:os";
import { createRequire } from "node:module";
import path from "node:path";
import { gunzipSync } from "node:zlib";

const phase = process.argv[2];
assert.ok(["red", "green"].includes(phase));
const here = import.meta.dir,
  root = path.resolve(here, "../../.."),
  require = createRequire(root + "/dashboard/package.json");
const tools =
  process.env.STATARENA_TEST_TOOLS || "/tmp/statarena-archive-remat-pg";
const { default: EmbeddedPostgres } = await import(
  tools + "/node_modules/embedded-postgres/dist/index.js"
);
const { Client } = require("pg"),
  scratch = await mkdtemp(path.join(tmpdir(), "statarena-support-"));
const expected = await readFile(path.join(here, "projections.json.gz")),
  rows = JSON.parse(gunzipSync(expected));
const report = {
  command:
    "PYTHONPATH=/tmp/statarena-archive-remat-pg/python bun docs/verification/aws-support-20261104/verify.mjs " +
    phase,
  fixtureSha256: createHash("sha256").update(expected).digest("hex"),
  byFamily: {},
  expectedKeys: rows.length,
};
let pg, admin, http;
try {
  const crt = scratch + "/ca.pem",
    key = scratch + "/key.pem";
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
      crt,
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
  pg = new EmbeddedPostgres({
    databaseDir: scratch + "/pg",
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
      "ssl_cert_file=" + crt,
      "-c",
      "ssl_key_file=" + key,
    ],
    onLog() {},
    onError() {},
  });
  await pg.initialise();
  await pg.start();
  const url = "postgresql://fixture:fixture@127.0.0.1:" + port + "/postgres",
    ca = await readFile(crt, "utf8");
  admin = new Client({
    connectionString: url,
    ssl: { ca, rejectUnauthorized: true },
  });
  await admin.connect();
  report.postgres = (
    await admin.query("show server_version")
  ).rows[0].server_version;
  await admin.query("create schema statarena_app");
  await admin.query(
    await readFile(
      root + "/dashboard/backend/migrations/005_supporting_models.sql",
      "utf8",
    ),
  );
  const u = new URL(url);
  u.searchParams.set("sslmode", "verify-full");
  u.searchParams.set("sslrootcert", crt);
  report.worker = JSON.parse(
    execFileSync("python3", [here + "/seed.py"], {
      env: { ...process.env, LOCAL_FIXTURE_DB: u.href },
      stdio: "pipe",
    }).toString(),
  );
  const cols = await admin.query(
    "select table_name,column_name,data_type from information_schema.columns where table_schema='statarena_app' and data_type in ('json','jsonb','bytea')",
  );
  assert.deepEqual(cols.rows, []);
  const reader = url.replace("fixture:fixture", "support_reader:fixture");
  Object.assign(process.env, {
    DATABASE_URL: reader,
    DATABASE_CA_PEM: ca,
    DATABASE_POOL_MAX: "1",
    STATARENA_DATA_PROVIDER: "aws",
    STATARENA_METRICS_SAMPLE_RATE: "0",
  });
  const {handleRequest}=await import(root+"/dashboard/backend/aws-app.js");
  http=Bun.serve({hostname:"127.0.0.1",port:0,fetch:handleRequest});
  report.entrypoint="dashboard/backend/aws-app.js";
  let why = "";
  const timings = [];
  for (const [name, params, body] of rows) {
    why = name + ":" + params;
    report.current = why;
    const route =
        "/api/" + name + "?" + new URLSearchParams(JSON.parse(params)),
      start = performance.now();
    const resp = await fetch(new URL(route, http.url));
    assert.equal(resp.status, 200, why);
    assert.deepEqual(await resp.json(), body, why);
    timings.push(performance.now() - start);
    report.byFamily[name] = (report.byFamily[name] || 0) + 1;
  }
  const first = rows[0],
    head = await fetch(
      new URL(
        "/api/" + first[0] + "?" + new URLSearchParams(JSON.parse(first[1])),
        http.url,
      ),
      { method: "HEAD" },
    );
  assert.equal(head.status, 200);
  assert.equal((await head.arrayBuffer()).byteLength, 0);
  for (const method of ["GET", "HEAD"])
    assert.equal(
      (
        await fetch(new URL("/api/standings?competition=l_ZZZZZZ", http.url), {
          method,
        })
      ).status,
      404,
    );
  const curatedDir = path.join(root, "docs/verification/aws-frontend-20261104");
  report.curatedWorker = JSON.parse(
    execFileSync("python3", [curatedDir + "/curated-seed.py"], {
      env: { ...process.env, LOCAL_FIXTURE_DB: u.href },
    }).toString(),
  );
  const expectedGroups = JSON.parse(
    await readFile(curatedDir + "/curated-before.json", "utf8"),
  ).expected;
  const published = await (
    await fetch(new URL("/api/player-honours?id=p_1mZO3B", http.url))
  ).json();
  const sourceMessi = rows.find(
    ([n, p]) => n === "player-honours" && JSON.parse(p).id === "p_1mZO3B",
  )[2];
  assert.deepEqual(published, {
    ...sourceMessi,
    displayGroups: expectedGroups,
  });
  report.curatedGroupCount = expectedGroups.length;
  delete report.current;
  timings.sort((a, b) => a - b);
  report.localHttpMs = {
    p50: timings[Math.floor(timings.length * 0.5)],
    p95: timings[Math.floor(timings.length * 0.95)],
  };
  report.passed = true;
} catch (e) {
  report.error = String(e.stack || e).slice(0, 3000);
  report.passed = false;
} finally {
  http?.stop(true);
  if (http)
    await (
      await import(root + "/dashboard/backend/services/postgres.js")
    ).closeDatabase();
  await admin?.end();
  await pg?.stop();
  await rm(scratch, { recursive: true, force: true });
  await writeFile(
    here + "/" + phase + ".json",
    JSON.stringify(report, null, 2) + "\n",
  );
}
console.log(JSON.stringify(report));
process.exitCode = report.passed ? 0 : 1;
