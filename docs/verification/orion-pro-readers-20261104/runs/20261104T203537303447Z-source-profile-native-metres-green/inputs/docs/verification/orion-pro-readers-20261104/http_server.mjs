// Owned-loopback HTTP E2E server. This file is never a production route.
import { AsyncLocalStorage } from "node:async_hooks";
import pg from "../../../dashboard/node_modules/pg/lib/index.js";
import { handleRequest } from "../../../dashboard/backend/aws-app.js";
import {
  closeDatabase,
  query,
} from "../../../dashboard/backend/services/postgres.js";

const contexts = new AsyncLocalStorage(),
  traces = [];
let externalAttempts = 0;
const original = pg.Client.prototype.query;
pg.Client.prototype.query = function (...args) {
  const context = contexts.getStore(),
    start = performance.now();
  const text = typeof args[0] === "string" ? args[0] : args[0]?.text;
  const entry = context
    ? { sql: text, values: Array.isArray(args[1]) ? args[1] : [] }
    : null;
  if (entry) context.sql.push(entry);
  const result = original.apply(this, args);
  return result?.then
    ? result.then(
        (value) => {
          if (entry) entry.elapsedMs = performance.now() - start;
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
  throw Error("External/provider HTTP is forbidden in the local reader E2E");
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
    if (u.pathname === "/__e2e__/flag") {
      process.env.STATARENA_PRO_API = u.searchParams.get("value") || "0";
      return Response.json({ flag: process.env.STATARENA_PRO_API });
    }
    const context = {
      id: req.headers.get("x-e2e-id"),
      path: u.pathname + u.search,
      method: req.method,
      sql: [],
    };
    return contexts.run(context, async () => {
      const response = await handleRequest(req);
      context.status = response.status;
      traces.push(context);
      return response;
    });
  },
});
console.log(JSON.stringify({ event: "ready", port: server.port, identity }));
const stop = async () => {
  server.stop(true);
  await closeDatabase();
  process.exit(0);
};
process.on("SIGTERM", stop);
process.on("SIGINT", stop);
