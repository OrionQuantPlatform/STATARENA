import { mkdir, mkdtemp, writeFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL, fileURLToPath } from "node:url";
import assert from "node:assert/strict";
const here = fileURLToPath(new URL("./", import.meta.url)),
  root = fileURLToPath(new URL("../../../", import.meta.url));
const ci = process.argv.includes("--ci");
if (
  ci &&
  (!process.env.STATARENA_CI_EVIDENCE ||
    !process.env.STATARENA_TEST_TOOLS ||
    !process.env.STATARENA_TEST_PYTHONPATH)
)
  throw Error("Missing isolated CI fixture paths");
const evidence = ci
  ? join(root, process.env.STATARENA_CI_EVIDENCE, "season-wire")
  : here;
await mkdir(evidence, { recursive: true });
const command =
  "bun docs/verification/aws-wire-pages/disposable.mjs" + (ci ? " --ci" : "");
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
  initdbFlags: ["--encoding=UTF8"],
  autoRehydrateSymlinks: true,
  onLog() {},
  onError() {},
});
const report = {
  command,
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
      join(evidence, "disposable-seed.json"),
    ],
    {
      cwd: root,
      env: {
        ...process.env,
        TEST_DATABASE_URL: local,
        STATARENA_E2E_COMMAND: command,
        PYTHONPATH:
          process.env.STATARENA_TEST_PYTHONPATH ?? process.env.PYTHONPATH ?? "",
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
  const formats = [base, base + "&format=columns"];
  const contents = [];
  for (const target of formats) {
    const get = await fetch(target);
    assert.equal(get.status, 200);
    const etag = get.headers.get("etag");
    assert.ok(etag);
    contents.push(await get.json());
    for (const [method, headers, status] of [
      ["HEAD", {}, 200],
      ["GET", { "if-none-match": etag }, 304],
      ["HEAD", { "if-none-match": etag }, 304],
    ]) {
      const response = await fetch(target, { method, headers });
      assert.equal(response.status, status);
      assert.equal(response.headers.get("etag"), etag);
      assert.equal(await response.text(), "");
    }
  }
  assert.equal((await fetch(base + "&format=unknown")).status, 400);
  report.checks.push(
    "Default and compact HEAD and conditional 304 preserve validators and empty bodies; unknown format returns 400",
  );
  const [raw, packed] = contents;
  assert.equal(packed.data.format, "orion-packed-tables-v1");
  const hydrated = decodePartition(packed.data);
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
  assert.ok(absent.includes("newObservedMetric"));
  assert.equal(apps[0].newObservedMetric, 0);
  assert.ok(Object.hasOwn(apps[1], "passesAccurate"));
  assert.equal(apps[1].passesAccurate, null);
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

    const originalQuery = Client.prototype.query;
    const pgShapes = [];
    Client.prototype.query = async function (sql, ...args) {
      const result = await originalQuery.call(this, sql, ...args);
      if (typeof sql === "string" && sql.startsWith("WITH candidates AS")) {
        const row = result.rows[0]?.appearances?.[0];
        pgShapes.push(Array.isArray(row) ? "array" : "object");
      }
      return result;
    };
    try {
      await fetch(base);
      assert.equal(pgShapes.at(-1), "array");
      await writer.query(
        "ALTER TABLE statarena_app.appearances ADD COLUMN future_typed_metric integer",
      );
      await writer.query(
        "UPDATE statarena_app.appearances SET future_typed_metric=0 WHERE match_id='m_000001'",
      );
      const named = await (await fetch(base)).json();
      const compact = await (await fetch(base + "&format=columns")).json();
      assert.deepEqual(decodePartition(compact.data), named.data);
      assert.equal(pgShapes.at(-1), "object");
      const [first, second] = named.data.appearances;
      assert.equal(first.futureTypedMetric, 0);
      assert.ok(Object.hasOwn(second, "futureTypedMetric"));
      assert.equal(second.futureTypedMetric, null);
      await writer.query(
        "ALTER TABLE statarena_app.appearances DROP COLUMN future_typed_metric",
      );
      const restored = await (await fetch(base)).json();
      assert.equal(pgShapes.at(-1), "array");
      assert.ok(
        !Object.hasOwn(restored.data.appearances[0], "futureTypedMetric"),
      );
      report.checks.push({
        pgAppearanceProtocol: pgShapes,
        expected: ["array", "object", "object", "array"],
        futureField: "zero/null preserved; dropped catalog slot ignored",
      });
      assert.deepEqual(pgShapes, ["array", "object", "object", "array"]);
    } finally {
      Client.prototype.query = originalQuery;
    }
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
    join(evidence, "disposable.json"),
    JSON.stringify(report, null, 2) + "\n",
  );
  console.log(JSON.stringify(report));
  process.exitCode = report.passed ? 0 : 1;
}
