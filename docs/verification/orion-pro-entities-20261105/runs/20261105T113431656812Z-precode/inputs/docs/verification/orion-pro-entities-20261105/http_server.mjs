// Source-free owned-loopback E2E adapter; not a production router.
import { AsyncLocalStorage } from "node:async_hooks";
import pg from "../../../dashboard/node_modules/pg/lib/index.js";
import { query, closeDatabase } from "../../../dashboard/backend/services/postgres.js";
import { send } from "../../../dashboard/backend/services/relational-core.js";
import { orionProRoute } from "../../../dashboard/backend/services/orion-pro.js";

let entityRoute;
try {
  ({ orionProEntityRoute: entityRoute } = await import("../../../dashboard/backend/services/orion-pro-entities.js"));
} catch (error) {
  if (error.code !== "ERR_MODULE_NOT_FOUND") throw error;
}
const contexts = new AsyncLocalStorage(), traces = [];
let externalAttempts = 0;
const original = pg.Client.prototype.query;
pg.Client.prototype.query = function (...args) {
  const ctx = contexts.getStore();
  const entry = ctx ? {sql:typeof args[0] === "string" ? args[0] : args[0]?.text, values:Array.isArray(args[1]) ? args[1] : []} : null;
  if (entry) ctx.sql.push(entry);
  const started = performance.now(), result = original.apply(this, args);
  return result?.then ? result.then(value => {if (entry) entry.elapsedMs=performance.now()-started; return value;}, error => {if (entry) entry.error=error.code||error.name; throw error;}) : result;
};
globalThis.fetch = async () => {externalAttempts++; throw Error("External HTTP forbidden");};
const identity = await query("SELECT current_user AS role,current_setting('transaction_read_only') AS readonly");
const server = Bun.serve({hostname:"127.0.0.1",port:0,async fetch(req) {
  const u=new URL(req.url);
  if (u.pathname === "/__e2e__/traces") return Response.json({requests:traces,externalAttempts});
  const ctx={id:req.headers.get("x-e2e-id"),path:u.pathname+u.search,method:req.method,sql:[]};
  return contexts.run(ctx,async()=>{
    let response;
    try {
      if (u.pathname === "/api/dashboard/manifest") response=await orionProRoute(req,u.pathname,u.searchParams);
      else response=entityRoute ? await entityRoute(req,u.pathname,u.searchParams,{mediaBase:"https://fixture.invalid/"}) : null;
      ctx.matched=Boolean(response);
      response ??= send(req,{error:{code:"PRO_ROUTE_NOT_IMPLEMENTED"}},501);
    } catch (error) {
      const status=error.status>=400&&error.status<=599?error.status:503;
      response=send(req,{ok:false,available:false,error:{code:({400:"INVALID_PARAMETER",404:"RESOURCE_NOT_FOUND",409:"PUBLICATION_CHANGED"})[status]||"DATA_UNAVAILABLE",message:status===503?"Données indisponibles.":error.message}},status);
      ctx.error=error.code||error.name;
    }
    ctx.status=response.status; traces.push(ctx); return response;
  });
}});
console.log(JSON.stringify({event:"ready",port:server.port,identity,entityRoutePresent:Boolean(entityRoute)}));
const stop=async()=>{server.stop(true);await closeDatabase();process.exit(0);};
process.on("SIGTERM",stop);process.on("SIGINT",stop);
