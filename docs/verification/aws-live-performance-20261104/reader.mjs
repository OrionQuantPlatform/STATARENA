/** One fresh process. The DataRow counter observes incoming frame lengths without changing query or result handling. */
import { createRequire } from "node:module";
import { createHash } from "node:crypto";
import { writeFileSync } from "node:fs";
import path from "node:path";
const [snapshot, reader, route, additional, out, allowance, bound] =
  process.argv.slice(2);
if (
  !["legacy-app", "aws-app"].includes(reader) ||
  !/^\/api\/(archive|pitchapi)\//.test(route)
)
  throw Error("Invalid comparison target");
const parsed = new URL(process.env.DATABASE_URL);
if (
  !parsed.hostname.endsWith(".rds.amazonaws.com") ||
  parsed.pathname !== "/statarena_prod" ||
  !parsed.searchParams
    .get("options")
    ?.includes("default_transaction_read_only=on")
)
  throw Error("Expected read-only RDS");
const require = createRequire(path.join(snapshot, "dashboard/package.json"));
const { Client } = require("pg");
const connect = Client.prototype.connect;
let verifiedConnections = 0;
Client.prototype.connect = function (...args) {
  const props = this.connectionParameters;
  if (
    !props.host.endsWith(".rds.amazonaws.com") ||
    props.database !== "statarena_prod" ||
    !props.options?.includes("default_transaction_read_only=on")
  )
    throw Error("Database startup guard failed");
  verifiedConnections++;
  return connect.apply(this, args);
};
let pgFrames = 0,
  pgBytes = 0,
  pgFields = 0;
const original = Client.prototype._handleDataRow;
Client.prototype._handleDataRow = function (msg) {
  pgFrames++;
  pgBytes += msg.length + 1;
  pgFields += msg.length - 6 - 4 * msg.fields.length;
  return original.call(this, msg);
};
const logs = [];
const logger = console.log;
console.log = (...args) => {
  try {
    const row = JSON.parse(args[0]);
    if (row.event === "statarena.request") logs.push(row);
  } catch {}
};
const { handleRequest } = await import(
  path.join(snapshot, "dashboard/backend", reader + ".js")
);
const server = Bun.serve({
  hostname: "127.0.0.1",
  port: 0,
  idleTimeout: 30,
  fetch: handleRequest,
});
const digest = (b) => createHash("sha256").update(b).digest("hex");
function ordered(x) {
  if (Array.isArray(x)) return x.map(ordered);
  if (x && typeof x === "object")
    return Object.fromEntries(
      Object.keys(x)
        .sort()
        .map((k) => [k, ordered(x[k])]),
    );
  return x;
}
const requests = [];
let readBytes = 0;
try {
  for (let n = 0; n <= Number(additional); n++) {
    if (
      reader === "legacy-app" &&
      readBytes + Number(bound) > Number(allowance)
    )
      break;
    const start = performance.now(),
      before = [pgFrames, pgBytes, pgFields],
      from = logs.length;
    const res = await fetch(new URL(route, server.url), {
      headers: { "accept-encoding": "identity" },
      signal: AbortSignal.timeout(20000),
    });
    const bytes = Buffer.from(await res.arrayBuffer()),
      ms = performance.now() - start;
    let body;
    try {
      body = JSON.parse(bytes);
    } catch {
      body = bytes.toString("utf8");
    }
    if (out !== "-" && n === 0)
      writeFileSync(out, JSON.stringify(body), { mode: 0o600 });
    const engine = logs.slice(from).at(-1),
      metrics = engine?.metrics || {};
    const sample = {
      n,
      status: res.status,
      rawSha256: digest(bytes),
      canonicalSha256: digest(JSON.stringify(ordered(body))),
      httpBytes: bytes.length,
      elapsedMs: Number(ms.toFixed(3)),
      handlerMs: engine?.duration_ms,
      pgDataRows: pgFrames - before[0],
      pgDataRowFrameBytes: pgBytes - before[1],
      pgFieldPayloadBytes: pgFields - before[2],
      etag: res.headers.get("etag"),
      dataSource: res.headers.get("x-data-source"),
      metrics,
    };
    requests.push(sample);
    readBytes += metrics.object_bytes || 0;
    if (!engine || res.status !== 200) break;
  }
} finally {
  server.stop(true);
}
logger(JSON.stringify({ reader, route, verifiedConnections, requests }));
process.exit(0);
