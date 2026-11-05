// Owned-loopback E2E only. Real PostgreSQL readers; no football response mocks.
import { AsyncLocalStorage } from "node:async_hooks";
import fs from "node:fs";
import fsp from "node:fs/promises";
import { pathToFileURL } from "node:url";
import pg from "../../../dashboard/node_modules/pg/lib/index.js";

const contexts = new AsyncLocalStorage(), traces = [];
const runtime = process.env.ORION_GUARD_RUNTIME;
if (!runtime || !runtime.includes("/orion-pro-api-coverage-20261105/runs/"))
  throw Error("Owned E2E runtime is required");
const originalQuery = pg.Client.prototype.query;
pg.Client.prototype.query = function (...args) {
  const context = contexts.getStore();
  const entry = context ? {sql:typeof args[0] === "string" ? args[0] : args[0]?.text,
    values:Array.isArray(args[1]) ? args[1] : []} : null;
  if (entry) context.sql.push(entry);
  const start = performance.now(), result = originalQuery.apply(this,args);
  return result?.then ? result.then(value => {
    if (entry) entry.elapsedMs=performance.now()-start;
    return value;
  }, error => { if(entry)entry.error=error.code||error.name;throw error; }) : result;
};
globalThis.__orionGuardCall = async (name, fn, args) => {
  const c=contexts.getStore();
  if(c)c.legacyEntries.push(name);
  const result=await fn(...args);
  if(c && ((result instanceof Response && result.body !== null) || result?.value !== undefined))
    c.legacyMaterializations.push(name);
  if(result && typeof result.readBody === "function") {
    const original=result.readBody;
    result.readBody=async (...a)=>{const context=contexts.getStore();if(context)context.legacyMaterializations.push(name+".readBody");return original(...a);};
  }
  return result;
};
const {handleRequest}=await import(pathToFileURL(runtime+"/dashboard/backend/aws-app.js").href);
const {query,closeDatabase}=await import(pathToFileURL(runtime+"/dashboard/backend/services/postgres.js").href);
const identity=await query("SELECT current_user AS role,current_setting('transaction_read_only') AS readonly");
let probeMode=false;
const calibrations=[];
function forbidden(kind) {
  const context=contexts.getStore();
  if(context)context.sourceAccess.push(kind);
  if(probeMode)calibrations.push(kind);
  throw Error("Source/file/object/provider access forbidden in guard E2E: "+kind);
}
globalThis.fetch=async()=>forbidden("provider_or_object_fetch");
Bun.file=()=>forbidden("Bun.file");
fs.readFileSync=()=>forbidden("fs.readFileSync");
fs.readFile=()=>forbidden("fs.readFile");
fs.createReadStream=()=>forbidden("fs.createReadStream");
fsp.readFile=async()=>forbidden("fsp.readFile");
probeMode=true;
for(const fn of [()=>globalThis.fetch("https://forbidden.invalid/"),()=>Bun.file("/forbidden-source"),
  ()=>fs.readFileSync("/forbidden-source"),()=>fs.readFile("/forbidden-source"),
  ()=>fs.createReadStream("/forbidden-source"),()=>fsp.readFile("/forbidden-source")]) {
  try {await fn();throw Error("Tripwire did not reject");} catch(error) {
    if(!String(error).includes("Source/file/object/provider access forbidden"))throw error;
  }
}
probeMode=false;
const server=Bun.serve({hostname:"127.0.0.1",port:0,async fetch(req){
  const u=new URL(req.url);
  if(u.pathname==="/__e2e__/trace")return Response.json(traces.find(t=>t.id===u.searchParams.get("id"))||null);
  if(u.pathname==="/__e2e__/all")return Response.json({traces,calibrations});
  if(u.pathname==="/__e2e__/flag"){
    process.env.STATARENA_PRO_API=u.searchParams.get("value")==="1"?"1":"0";
    return Response.json({flag:process.env.STATARENA_PRO_API});
  }
  const context={id:req.headers.get("x-e2e-id"),method:req.method,path:u.pathname+u.search,
    sql:[],legacyEntries:[],legacyMaterializations:[],sourceAccess:[]};
  return contexts.run(context,async()=>{const response=await handleRequest(req);context.status=response.status;traces.push(context);return response;});
}});
console.log(JSON.stringify({event:"ready",port:server.port,identity,calibrations,runtimeLabel:process.env.ORION_GUARD_RUNTIME_LABEL}));
const stop=async()=>{server.stop(true);await closeDatabase();process.exit(0);};
process.on("SIGTERM",stop);process.on("SIGINT",stop);
