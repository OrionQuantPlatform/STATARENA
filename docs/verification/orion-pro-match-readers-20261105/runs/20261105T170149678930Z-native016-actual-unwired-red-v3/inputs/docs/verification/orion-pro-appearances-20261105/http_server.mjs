// Owned Node24 actual-app E2E; no Bun-only server or production test controls.
import { AsyncLocalStorage } from "node:async_hooks";
import { createServer } from "node:http";
import pg from "../../../dashboard/node_modules/pg/lib/index.js";
import {
  query,
  closeDatabase,
} from "../../../dashboard/backend/services/postgres.js";
import { handleRequest } from "../../../dashboard/backend/aws-app.js";

const contexts = new AsyncLocalStorage(),
  traces = [];
let externalAttempts = 0;
const original = pg.Client.prototype.query;
pg.Client.prototype.query = function (...args) {
  const ctx = contexts.getStore();
  const record = ctx
    ? {
        sql: typeof args[0] === "string" ? args[0] : args[0]?.text,
        values: Array.isArray(args[1]) ? args[1] : [],
      }
    : null;
  if (record) ctx.sql.push(record);
  const start = performance.now(),
    result = original.apply(this, args);
  return result?.then
    ? result.then(
        (value) => {
          if (record) record.elapsedMs = performance.now() - start;
          return value;
        },
        (error) => {
          if (record) record.error = error.code || error.name;
          throw error;
        },
      )
    : result;
};
globalThis.fetch = async () => {
  externalAttempts++;
  throw Error("External HTTP forbidden in appearance E2E");
};
const identity = await query(
  "SELECT current_user AS role,current_setting('transaction_read_only') AS readonly",
);
const server = createServer(async (incoming, outgoing) => {
  const origin = `http://127.0.0.1:${server.address().port}`;
  const u = new URL(incoming.url, origin);
  if (u.pathname === "/__e2e__/traces") {
    outgoing.writeHead(200, { "Content-Type": "application/json" });
    outgoing.end(JSON.stringify({ requests: traces, externalAttempts }));
    return;
  }
  const ctx = {
    id: incoming.headers["x-e2e-id"],
    method: incoming.method,
    path: u.pathname + u.search,
    sql: [],
  };
  try {
    await contexts.run(ctx, async () => {
      const request = new Request(u, {
        method: incoming.method,
        headers: incoming.headers,
      });
      const response = await handleRequest(request);
      ctx.status = response.status;
      traces.push(ctx);
      outgoing.writeHead(response.status, Object.fromEntries(response.headers));
      outgoing.end(Buffer.from(await response.arrayBuffer()));
    });
  } catch (error) {
    ctx.error = error.code || error.name;
    traces.push(ctx);
    outgoing.writeHead(500, { "Content-Type": "application/json" });
    outgoing.end(JSON.stringify({ error: { code: "E2E_SERVER_FAILURE" } }));
  }
});
await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
console.log(
  JSON.stringify({
    event: "ready",
    port: server.address().port,
    identity,
    runtime: {
      version: process.version,
      platform: process.platform,
      arch: process.arch,
      rawJSON: typeof JSON.rawJSON,
    },
    handler: "actual-aws-app.handleRequest",
  }),
);
const stop = async () => {
  server.closeAllConnections();
  server.close();
  await closeDatabase();
  process.exit(0);
};
process.on("SIGTERM", stop);
process.on("SIGINT", stop);
