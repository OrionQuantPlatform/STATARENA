import { mkdtemp, mkdir, appendFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve, dirname } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createServer } from "node:net";
import { spawn } from "node:child_process";

const folder = dirname(fileURLToPath(import.meta.url));
const root = resolve(folder, "../../../..");
const phase = process.argv[2] || "after";
if (!/^[a-z0-9-]+$/.test(phase)) throw new Error("Invalid evidence phase");
const out = join(folder, phase);
await mkdir(out, { recursive: true });
const { default: EmbeddedPostgres } = await import(pathToFileURL(join(
  process.env.STATARENA_TEST_TOOLS || "/tmp/statarena-cache-test-tools",
  "node_modules/embedded-postgres/dist/index.js",
)));
const socket = createServer();
await new Promise((r) => socket.listen(0, "127.0.0.1", r));
const port = socket.address().port;
await new Promise((r) => socket.close(r));
const scratch = await mkdtemp(join(tmpdir(), "statarena-publication-"));
const logs = [];
const pg = new EmbeddedPostgres({
  databaseDir: join(scratch, "data"), user: "fixture", password: "fixture-only",
  port, persistent: false,
  postgresFlags: ["-c", "listen_addresses=127.0.0.1", "-c", "log_statement=all"],
  onLog: (s) => logs.push(String(s)), onError: (s) => logs.push(String(s)),
});
let code = 1;
try {
  await pg.initialise(); await pg.start(); await pg.createDatabase("publication_e2e");
  const child = spawn("python3", [join(folder, "scenario.py"), "--report", join(out, "results.json"), "--phase", phase], {
    cwd: root,
    env: {
      PATH: process.env.PATH, HOME: process.env.HOME,
      PYTHONDONTWRITEBYTECODE: "1",
      PYTHONPATH: process.env.STATARENA_TEST_PYTHON || "/tmp/statarena-publication-test-python",
      STATARENA_PUBLICATION_BASELINE: phase.startsWith("baseline") ? "1" : "0",
      STATARENA_PUBLICATION_SOURCE: phase.startsWith("admission-baseline") ? join(folder,"before-admission") : phase.startsWith("sql-dedup-baseline") ? join(folder,"before-sql-dedup") : "",
      TEST_DATABASE_URL: `postgresql://fixture:fixture-only@127.0.0.1:${port}/publication_e2e`,
    },
    stdio: ["ignore", "pipe", "pipe"],
  });
  let output = "";
  for (const stream of [child.stdout, child.stderr]) stream.on("data", (b) => { output += b; process.stdout.write(b); });
  code = await new Promise((r) => child.on("exit", r));
  await appendFile(join(out, "python.log"), output);
} finally {
  await pg.stop();
  await appendFile(join(out, "postgres.log"), logs.join("\n"));
  await rm(scratch, { recursive: true, force: true });
}
process.exitCode = code;
