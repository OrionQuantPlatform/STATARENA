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
  const { createRequire } = await import("node:module");
  const { Client } = createRequire(
    new URL("../../../dashboard/package.json", import.meta.url),
  )("pg");
  const writer = new Client({ connectionString: local });
  await writer.connect();
  try {
    const propertyChecks = [];
    for (const kind of ["constant", "varying", "missing"]) {
      await writer.query(
        "DELETE FROM statarena_app.appearance_metrics WHERE metric_key IN ('__proto__','constructor')",
      );
      await writer.query(
        `INSERT INTO statarena_app.appearance_metrics (appearance_id,metric_key,value)
        SELECT a.id,k.key,CASE WHEN $1::text='varying' AND a.match_id='m_000002' THEN 22 ELSE 11 END
        FROM statarena_app.appearances a CROSS JOIN (VALUES ('__proto__'),('constructor')) k(key)
        WHERE a.league_id='l_000001' AND ($1<>'missing' OR a.match_id='m_000001')`,
        [kind],
      );
      const record = await (await fetch(base)).json(),
        compact = await (await fetch(base + "&format=columns")).json();
      for (const csp of [false, true]) {
        const original = globalThis.Function;
        let output;
        try {
          if (csp)
            globalThis.Function = () => {
              throw Error("Eval blocked");
            };
          output = decodePartition(compact.data);
        } finally {
          globalThis.Function = original;
        }
        const props = (rows) =>
          rows.map((r) => ({
            plain: Object.getPrototypeOf(r) === Object.prototype,
            fields: Object.fromEntries(
              ["__proto__", "constructor"].map((k) => [
                k,
                Object.hasOwn(r, k) ? r[k] : "absent",
              ]),
            ),
          }));
        const expected = props(record.data.appearances),
          actual = props(output.appearances);
        assert.equal(expected[0].fields["__proto__"], 11);
        propertyChecks.push({
          kind,
          csp,
          expected,
          actual,
          ok: JSON.stringify(expected) === JSON.stringify(actual),
        });
      }
    }
    report.checks.push({ propertyChecks });
    assert.ok(
      propertyChecks.every((c) => c.ok),
      "Dynamic SQL metric own-property parity failed",
    );
  } finally {
    await writer.end();
  }
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
