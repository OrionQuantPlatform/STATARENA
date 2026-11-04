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
    "PYTHONPATH=/tmp/statarena-archive-remat-pg/python bun docs/verification/aws-match-publish-20261104/run.mjs " +
    phase,
  setup:
    "PROTOCOL.md; PostgreSQL 18, verified local TLS, migration 004; measure.py clones production-archive.json",
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
  await admin.query("CREATE SCHEMA statarena_app");
  await admin.query(
    await readFile(
      path.join(root, "dashboard/backend/migrations/004_match_details.sql"),
      "utf8",
    ),
  );
  await admin.query(
    await readFile(
      path.join(
        root,
        "dashboard/backend/migrations/007_match_source_fields.sql",
      ),
      "utf8",
    ),
  );
  await admin.query(
    await readFile(
      path.join(
        root,
        "dashboard/backend/migrations/008_match_player_position.sql",
      ),
      "utf8",
    ),
  );
  await admin.query(
    await readFile(
      path.join(
        root,
        "dashboard/backend/migrations/009_compact_player_metrics.sql",
      ),
      "utf8",
    ),
  );
  const conn = new URL(url);
  conn.searchParams.set("sslmode", "verify-full");
  conn.searchParams.set("sslrootcert", cert);
  const output = execFileSync(
    process.env.PYTHON || "python3",
    [path.join(import.meta.dir, "measure.py"), phase],
    {
      env: { ...process.env, LOCAL_FIXTURE_DB: conn.href },
      stdio: "pipe",
      maxBuffer: 2000000,
    },
  );
  report.benchmark = JSON.parse(output.toString());
  report.passed = report.benchmark.passed;
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
    path.join(
      import.meta.dir,
      phase +
        (process.env.STATARENA_BENCH_SUFFIX || "") +
        (process.env.STATARENA_SIMULATED_RTT_MS
          ? "-simulated-" + process.env.STATARENA_SIMULATED_RTT_MS + "ms"
          : "") +
        ".json",
    ),
    JSON.stringify(report, null, 2) + "\n",
  );
}
console.log(
  report.passed ? "PASS" : "FAIL",
  report.benchmark?.cases?.length,
  report.error || "",
);
process.exitCode = report.passed ? 0 : 1;
