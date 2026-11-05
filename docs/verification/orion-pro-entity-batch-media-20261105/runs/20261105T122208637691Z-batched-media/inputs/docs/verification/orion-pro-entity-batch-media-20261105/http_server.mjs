// Actual AWS handler, owned-loopback SQL/media E2E; no production test controls.
import { AsyncLocalStorage } from "node:async_hooks";
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
  const c = contexts.getStore(),
    q = c
      ? {
          sql: typeof args[0] === "string" ? args[0] : args[0]?.text,
          values: Array.isArray(args[1]) ? args[1] : [],
        }
      : null;
  if (q) c.sql.push(q);
  const start = performance.now(),
    result = original.apply(this, args);
  return result?.then
    ? result.then(
        (r) => {
          if (q) q.elapsedMs = performance.now() - start;
          return r;
        },
        (e) => {
          if (q) q.error = e.code || e.name;
          throw e;
        },
      )
    : result;
};
globalThis.fetch = async () => {
  externalAttempts++;
  throw Error("External HTTP forbidden in source-free E2E");
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
    if (u.pathname === "/__e2e__/media-origin") {
      process.env.STATARENA_CLOUDFRONT_URL = u.searchParams.get("value");
      return Response.json({ origin: process.env.STATARENA_CLOUDFRONT_URL });
    }
    const c = {
      id: req.headers.get("x-e2e-id"),
      method: req.method,
      path: u.pathname + u.search,
      sql: [],
    };
    return contexts.run(c, async () => {
      const r = await handleRequest(req);
      c.status = r.status;
      traces.push(c);
      return r;
    });
  },
});
console.log(
  JSON.stringify({
    event: "ready",
    port: server.port,
    identity,
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
