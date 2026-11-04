import { mkdtemp, writeFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL, fileURLToPath } from "node:url";
import assert from "node:assert/strict";
const here = fileURLToPath(new URL("./", import.meta.url)),
  root = fileURLToPath(new URL("../../../", import.meta.url));
const tools =
  process.env.STATARENA_TEST_TOOLS || "/tmp/statarena-cache-test-tools";
const { default: Postgres } = await import(
  pathToFileURL(join(tools, "node_modules/embedded-postgres/dist/index.js"))
);
const dir = await mkdtemp(join(tmpdir(), "statarena-wire-"));
const sock = Bun.listen({
    hostname: "127.0.0.1",
    port: 0,
    socket: { data() {} },
  }),
  port = sock.port;
sock.stop(true);
const pg = new Postgres({
  databaseDir: dir,
  user: "fixture",
  password: "local-only",
  port,
  persistent: false,
  autoRehydrateSymlinks: true,
  onLog() {},
  onError() {},
});
const report = {
  command: "bun docs/verification/aws-wire-pages/disposable.mjs",
  checks: [],
};
let srv;
try {
  await pg.initialise();
  await pg.start();
  await pg.createDatabase("relational_core_e2e");
  const local =
    "postgresql://fixture:local-only@127.0.0.1:" +
    port +
    "/relational_core_e2e";
  const seed = Bun.spawnSync(
    [
      "python3",
      "docs/verification/aws-relational-core-20261104/workflow.py",
      "--report",
      join(here, "disposable-seed.json"),
    ],
    {
      cwd: root,
      env: {
        ...process.env,
        TEST_DATABASE_URL: local,
        STATARENA_E2E_COMMAND:
          "bun docs/verification/aws-wire-pages/disposable.mjs",
        PYTHONPATH: "/tmp/statarena-archive-remat-pg/python",
      },
    },
  );
  assert.equal(seed.exitCode, 0, seed.stderr.toString().slice(-1000));
  Object.assign(process.env, {
    DATABASE_URL: local + "?sslmode=disable",
    STATARENA_TEST_DATABASE: "1",
    STATARENA_DATA_PROVIDER: "aws",
    STATARENA_METRICS_SAMPLE_RATE: "0",
  });
  const { handleRequest } =
    await import("../../../dashboard/backend/aws-app.js");
  const { decodePartition } =
    await import("../../../dashboard/frontend/src/season_data.js");
  srv = Bun.serve({ hostname: "127.0.0.1", port: 0, fetch: handleRequest });
  const base = new URL(
    "/api/seasons/partition?season=2026%2F2027&league=l_000001&limit=100",
    srv.url,
  ).href;
  const raw = await (await fetch(base)).json(),
    packed = await (await fetch(base + "&format=columns")).json(),
    hydrated = decodePartition(packed.data);
  assert.deepEqual(hydrated, raw.data);
  report.checks.push(
    "All fixture, appearance, match membership, geometry, stats and missing fields identical",
  );
  const apps = hydrated.appearances;
  assert.deepEqual(
    apps.map((a) => a.positionId),
    [11, "11"],
  );
  report.checks.push(
    "SQL integer 11 and SQL string 11 retain exact native types",
  );
  const absent = Object.keys(apps[0]).filter((k) => !Object.hasOwn(apps[1], k));
  assert.ok(absent.length);
  report.checks.push({ sourceAbsentFields: absent });
  report.passed = true;
} catch (e) {
  report.passed = false;
  report.error = e.message;
} finally {
  srv?.stop(true);
  const { closeDatabase } =
    await import("../../../dashboard/backend/services/postgres.js");
  await closeDatabase();
  await pg.stop();
  await rm(dir, { recursive: true, force: true });
  await writeFile(
    join(here, "disposable.json"),
    JSON.stringify(report, null, 2) + "\n",
  );
  console.log(JSON.stringify(report));
  process.exitCode = report.passed ? 0 : 1;
}
