// Source-free owned-loopback E2E adapter; not a production router.
import { AsyncLocalStorage } from "node:async_hooks";
import pg from "../../../dashboard/node_modules/pg/lib/index.js";
import {
  query,
  closeDatabase,
} from "../../../dashboard/backend/services/postgres.js";
import { handleRequest } from "../../../dashboard/backend/aws-app.js";
import { orionProEntityRoute } from "../../../dashboard/backend/services/orion-pro-entities.js";
const contexts = new AsyncLocalStorage(),
  traces = [];
let externalAttempts = 0;
const original = pg.Client.prototype.query;
pg.Client.prototype.query = function (...args) {
  const ctx = contexts.getStore();
  const entry = ctx
    ? {
        sql: typeof args[0] === "string" ? args[0] : args[0]?.text,
        values: Array.isArray(args[1]) ? args[1] : [],
      }
    : null;
  if (entry) ctx.sql.push(entry);
  const started = performance.now(),
    result = original.apply(this, args);
  return result?.then
    ? result.then(
        (value) => {
          if (entry) entry.elapsedMs = performance.now() - started;
          return value;
        },
        (error) => {
          if (entry) entry.error = error.code || error.name;
          throw error;
        },
      )
    : result;
};
globalThis.fetch = async () => {
  externalAttempts++;
  throw Error("External HTTP forbidden");
};
const identity = await query(
  "SELECT current_user AS role,current_setting('transaction_read_only') AS readonly",
);
const server = Bun.serve({
  hostname: "127.0.0.1",
  port: 0,
  async fetch(req) {
    const u = new URL(req.url);
    if (u.pathname === "/__e2e__/traces")
      return Response.json({ requests: traces, externalAttempts });
    const ctx = {
      id: req.headers.get("x-e2e-id"),
      path: u.pathname + u.search,
      method: req.method,
      sql: [],
    };
    return contexts.run(ctx, async () => {
      const response = await handleRequest(req);
      ctx.matched = response.status !== 501;
      ctx.status = response.status;
      traces.push(ctx);
      return response;
    });
  },
});
console.log(
  JSON.stringify({
    event: "ready",
    port: server.port,
    identity,
    entityRoutePresent: typeof orionProEntityRoute === "function",
    handler: "actual-aws-app.handleRequest",
  }),
);
const stop = async () => {
  server.stop(true);
  await closeDatabase();
  process.exit(0);
};
process.on("SIGTERM", stop);
process.on("SIGINT", stop);
