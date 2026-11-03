import { mkdtemp, mkdir, writeFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
const root = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../..",
);
const tools =
  process.env.STATARENA_TEST_TOOLS || "/tmp/statarena-cache-test-tools";
const daily = process.argv.includes("--daily");
const output = path.resolve(
  root,
  process.env.STATARENA_SUMMARY_EVIDENCE ||
    "docs/verification/backend-p1-20261103/materializer-after",
);
const rerunCommand = `STATARENA_TEST_TOOLS=${tools}${process.env.STATARENA_MATERIALIZER_MODULE ? ` STATARENA_MATERIALIZER_MODULE=${process.env.STATARENA_MATERIALIZER_MODULE}` : ""} STATARENA_SUMMARY_EVIDENCE=${path.relative(root, output)} bun dashboard/scripts/verify_match_summary_materializer.mjs${daily ? " --daily" : ""}`;
await mkdir(output, { recursive: true });
const dir = await mkdtemp(path.join(tmpdir(), "statarena-summary-pg-")),
  logs = [];
const { default: Postgres } = await import(
  pathToFileURL(
    path.join(tools, "node_modules/embedded-postgres/dist/index.js"),
  ).href
);
const socket = Bun.listen({
  hostname: "127.0.0.1",
  port: 0,
  socket: { data() {} },
});
const port = socket.port;
socket.stop(true);
const pg = new Postgres({
  databaseDir: path.join(dir, "db"),
  user: "fixture",
  password: "local-e2e-only",
  port,
  persistent: false,
  autoRehydrateSymlinks: true,
  onLog: (s) => logs.push(String(s)),
  onError: (s) => logs.push(String(s)),
});
let code = 1;
try {
  await pg.initialise();
  await pg.start();
  await pg.createDatabase("archive_materialization_e2e");
  const child = Bun.spawn(
    daily
      ? ["python3", "tests/daily_refresh_postgres.py"]
      : [
          "python3",
          "tests/rematerialize_archive_postgres.py",
          "--report",
          path.join(output, "results.json"),
        ],
    {
      cwd: root,
      env: {
        ...process.env,
        TEST_DATABASE_URL: `postgresql://fixture:local-e2e-only@127.0.0.1:${port}/archive_materialization_e2e`,
        PYTHONPATH:
          process.env.STATARENA_TEST_PYTHONPATH ||
          "/tmp/statarena-archive-remat-pg/python",
        STATARENA_SUMMARY_CHECKS: "1",
        STATARENA_E2E_COMMAND: rerunCommand,
      },
      stdout: "pipe",
      stderr: "pipe",
    },
  );
  const content = await Promise.all([
    new Response(child.stdout).text(),
    new Response(child.stderr).text(),
  ]);
  code = await child.exited;
  await writeFile(path.join(output, "python.log"), content.join("\n"));
  console.log(content.join("\n"));
} finally {
  await pg.stop();
  await writeFile(path.join(output, "postgres.log"), logs.join("\n"));
  await writeFile(
    path.join(output, "RUN.json"),
    JSON.stringify(
      {
        command: rerunCommand,
        setup:
          "Temporary PostgreSQL18, real Python normalizer/materializer, stored-archive fixtures. No production/provider requests.",
        expected: daily
          ? "Daily and pulse publication preserve civil/split-year seasons and publish changed saved match data."
          : "All archive scenarios also publish exact bounded summaries and acknowledge their dirty queue atomically.",
        exitCode: code,
      },
      null,
      2,
    ) + "\n",
  );
  await rm(dir, { recursive: true, force: true });
}
process.exitCode = code;
