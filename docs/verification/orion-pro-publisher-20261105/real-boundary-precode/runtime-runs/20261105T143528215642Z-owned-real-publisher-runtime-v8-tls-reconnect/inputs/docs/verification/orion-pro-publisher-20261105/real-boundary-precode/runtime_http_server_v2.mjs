// Owned-local publisher E2E API; real readers and shared operation reservations.
import fs from "node:fs";
import { pathToFileURL } from "node:url";
import { AsyncLocalStorage } from "node:async_hooks";
import pg from "../../../../dashboard/node_modules/pg/lib/index.js";
import { createHash } from "node:crypto";
import net from "node:net";

const run = process.env.ORION_PUBLISHER_TEST_RUN,
  runtime = process.env.ORION_PUBLISHER_API_RUNTIME;
if (
  !run?.includes("/orion-pro-publisher-20261105/product-campaign/runs/") ||
  !runtime?.startsWith(run + "/")
)
  throw Error("Owned runtime required");
const budgetPath = run + "/budget.json",
  lock = run + "/budget.lock",
  tracePath = run + "/api-sql.jsonl";
const contexts = new AsyncLocalStorage();
const originalRead = fs.readFileSync,
  originalWrite = fs.writeFileSync,
  originalAppend = fs.appendFileSync;
const sleep = () =>
  Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 5);
function reserve(kind) {
  const start = Date.now();
  for (;;) {
    try {
      fs.mkdirSync(lock);
      break;
    } catch (e) {
      if (e.code !== "EEXIST" || Date.now() - start > 1000)
        throw Error("Shared budget lock/deadline");
      sleep();
    }
  }
  try {
    const b = JSON.parse(originalRead(budgetPath, "utf8"));
    if (
      Date.now() / 1000 > b.deadlineEpoch ||
      b.counts[kind] + 1 > b.limits[kind]
    )
      throw Error("Budget exceeded: " + kind);
    b.counts[kind]++;
    const tmp = budgetPath + "." + process.pid + ".tmp";
    originalWrite(tmp, JSON.stringify(b) + "\n");
    fs.renameSync(tmp, budgetPath);
  } finally {
    fs.rmdirSync(lock);
  }
}
const originalQuery = pg.Client.prototype.query;
pg.Client.prototype.query = function (...args) {
  reserve("sql");
  const c = contexts.getStore(),
    sql = typeof args[0] === "string" ? args[0] : args[0]?.text;
  const item = {
    requestId: c?.id || "startup",
    sql,
    parameterTypes: Array.isArray(args[1]) ? args[1].map((x) => typeof x) : [],
    parametersSha256: createHash("sha256")
      .update(JSON.stringify(args[1] || []))
      .digest("hex"),
  };
  if (c) c.sql.push(item);
  const result = originalQuery.apply(this, args);
  if (result?.then)
    return result.then(
      (value) => {
        item.resultRows = value.rows?.length ?? null;
        originalAppend(tracePath, JSON.stringify(item) + "\n");
        return value;
      },
      (error) => {
        item.errorCode = error.code || error.name;
        originalAppend(tracePath, JSON.stringify(item) + "\n");
        throw error;
      },
    );
  originalAppend(tracePath, JSON.stringify(item) + "\n");
  return result;
};
const { handleRequest } = await import(
  pathToFileURL(runtime + "/dashboard/backend/aws-app.js").href
);
const { query, closeDatabase } = await import(
  pathToFileURL(runtime + "/dashboard/backend/services/postgres.js").href
);
const identity = await query(
  "SELECT current_user AS role,current_setting('transaction_read_only') AS readonly,current_setting('statement_timeout') AS statement_timeout,current_setting('lock_timeout') AS lock_timeout",
);
const calibration = [];
let calibrating = true;
function denied(kind, details = undefined) {
  if (calibrating) calibration.push(kind);
  else
    originalAppend(
      run + "/api-source-access.jsonl",
      JSON.stringify({ kind, details }) + "\n",
    );
  throw Error("Forbidden source access: " + kind);
}
const pgPort = Number(new URL(process.env.DATABASE_URL).port),
  originalConnect = net.Socket.prototype.connect;
net.Socket.prototype.connect = function (...args) {
  // Bun normalizes Socket.connect to a single [options, callback] argument.
  // TLS wraps its already-connected socket without a second host/port pair.
  const values = Array.isArray(args[0]) ? args[0] : args,
    first = values[0],
    options = first && typeof first === "object"
      ? first : { port: first, host: values[1] },
    loopback = (host) => ["127.0.0.1", "localhost", "::1"].includes(host),
    socket = options.socket,
    tcp = !socket && loopback(options.host) && Number(options.port) === pgPort,
    tlsUpgrade = socket instanceof net.Socket &&
      loopback(socket.remoteAddress) && Number(socket.remotePort) === pgPort &&
      (options.host === undefined || loopback(options.host)) &&
      (options.port === undefined || Number(options.port) === pgPort) &&
      (options.servername === undefined || loopback(options.servername));
  const details = { normalizedArray: Array.isArray(args[0]),
    host: options.host, port: options.port,
    peerHost: socket?.remoteAddress, peerPort: socket?.remotePort,
    kind: tcp ? "owned_tcp" : tlsUpgrade ? "owned_tls_upgrade" : "rejected" };
  if (!tcp && !tlsUpgrade)
    return denied("non_owned_network_connect", details);
  originalAppend(run + "/api-owned-connects.jsonl", JSON.stringify(details) + "\n");
  return originalConnect.apply(this, args);
};
globalThis.fetch = async () => denied("provider_or_object_fetch");
Bun.file = () => denied("Bun.file");
fs.readFileSync = (...args) => {
  if (args[0] === budgetPath) return originalRead(...args);
  return denied("fs.readFileSync");
};
fs.readFile = () => denied("fs.readFile");
fs.createReadStream = () => denied("fs.createReadStream");
for (const fn of [
  () => globalThis.fetch("https://forbidden.invalid"),
  () => Bun.file("/forbidden-source"),
  () => fs.readFileSync("/forbidden-source"),
  () => net.connect({ host: "192.0.2.1", port: 443 }),
  () => net.connect({ host: "127.0.0.1", port: pgPort + 1 }),
  () => net.Socket.prototype.connect.call({}, [{ host: "192.0.2.1", port: pgPort }]),
  () => net.Socket.prototype.connect.call({}, [{ socket: { remoteAddress: "127.0.0.1", remotePort: pgPort } }]),
  () => net.Socket.prototype.connect.call({}, [{ socket: { remoteAddress: "192.0.2.1", remotePort: pgPort } }]),
]) {
  try {
    await fn();
    throw Error("Tripwire did not reject");
  } catch (e) {
    if (!String(e).includes("Forbidden source access")) throw e;
  }
}
await closeDatabase();
const reconnectIdentity = await query(
  "SELECT current_user AS role,current_setting('transaction_read_only') AS readonly,current_setting('statement_timeout') AS statement_timeout,current_setting('lock_timeout') AS lock_timeout",
);
if (JSON.stringify(reconnectIdentity) !== JSON.stringify(identity))
  throw Error("Owned reconnect changed native identity or deadlines");
const reconnectTls = await query("SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()");
if (reconnectTls.length !== 1 || reconnectTls[0].ssl !== true)
  throw Error("Owned reconnect requires actual native TLS");
calibrating = false;
const server = Bun.serve({
  hostname: "127.0.0.1",
  port: 0,
  async fetch(req) {
    reserve("http");
    const u = new URL(req.url),
      context = {
        id: req.headers.get("x-e2e-id"),
        method: req.method,
        path: u.pathname + u.search,
        sql: [],
      };
    return contexts.run(context, async () => {
      const response = await handleRequest(req);
      context.status = response.status;
      originalAppend(
        run + "/api-requests.jsonl",
        JSON.stringify(context) + "\n",
      );
      return response;
    });
  },
});
console.log(
  JSON.stringify({ event: "ready", port: server.port, identity, calibration,
    reconnectIdentity, reconnectTls }),
);
const stop = async () => {
  server.stop(true);
  await closeDatabase();
  process.exit(0);
};
process.on("SIGTERM", stop);
process.on("SIGINT", stop);
