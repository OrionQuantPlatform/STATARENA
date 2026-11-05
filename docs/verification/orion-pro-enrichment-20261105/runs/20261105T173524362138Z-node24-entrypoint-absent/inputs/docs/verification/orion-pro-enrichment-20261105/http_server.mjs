// Node24 owned HTTP boundary. The independent module and actual-app integration
// are distinct modes; neither is deployed or wired by this test server.
import fs from "node:fs";
import net from "node:net";
import dns from "node:dns";
import http from "node:http";
import https from "node:https";
import { AsyncLocalStorage } from "node:async_hooks";

const pgPort = Number(process.env.COMPETITION_OWNED_PG_PORT);
const run = process.env.COMPETITION_EVIDENCE_ROOT;
if (!Number.isInteger(pgPort) || pgPort < 1024 || !run?.startsWith("/"))
  throw Error("Explicit owned fixture endpoint and evidence required");
const opts = new URL(process.env.DATABASE_URL);
if (opts.hostname !== "127.0.0.1" || Number(opts.port) !== pgPort ||
    opts.username !== "statarena_runtime" || opts.password || opts.pathname !== "/postgres")
  throw Error("Owned DB mismatch");
const book = run + "/budget.json", lock = run + "/budget.lock";
function reserveSql() {
  const stop = performance.now() + 1000;
  for (;;) {
    try { fs.mkdirSync(lock); break; }
    catch (error) { if (error.code !== "EEXIST" || performance.now() > stop) throw error; }
  }
  try {
    const b = JSON.parse(fs.readFileSync(book, "utf8"));
    if (Date.now() > b.deadlineEpoch * 1000 || b.counts.sql >= b.limits.sql)
      throw Error("SQL or global deadline budget");
    b.counts.sql++;
    const temp = book + "." + process.pid + ".tmp";
    fs.writeFileSync(temp, JSON.stringify(b) + "\n");fs.renameSync(temp, book);
  } finally { fs.rmdirSync(lock); }
}

const attempts = [], calibration = [];
let calibrating = true;
function blocked(kind) {
  (calibrating ? calibration : attempts).push(kind);
  throw Error("Owned network tripwire: " + kind);
}
globalThis.fetch = async () => blocked("fetch");
const connect = net.Socket.prototype.connect;
net.Socket.prototype.connect = function (...args) {
  const first = Array.isArray(args[0]) ? args[0][0] : args[0];
  const endpoint = typeof first === "object" && first !== null ? first : {port:first,host:args[1]};
  const socket = endpoint.socket;
  const owned = endpoint.host === "127.0.0.1" && Number(endpoint.port) === pgPort && !endpoint.path;
  const ownedTls = socket instanceof net.Socket && socket.remoteAddress === "127.0.0.1" && socket.remotePort === pgPort && !socket.destroyed;
  if (!owned && !ownedTls) return blocked("socket");
  return connect.apply(this,args);
};
const nativeLookup = dns.lookup;
dns.lookup = (host, ...args) => host === "127.0.0.1" ? nativeLookup.call(dns, host, ...args) : blocked("dns.lookup");
dns.resolve = () => blocked("dns.resolve");
dns.promises.lookup = async () => blocked("dns.promises.lookup");
http.request = () => blocked("http.request");
https.request = () => blocked("https.request");
https.get = () => blocked("https.get");
for (const check of [() => fetch("https://provider.invalid"),() => net.connect(80,"203.0.113.1"),
  () => dns.lookup("provider.invalid"),() => dns.resolve("provider.invalid"),() => dns.promises.lookup("provider.invalid"),
  () => http.request("http://provider.invalid"),() => https.request("https://provider.invalid"),() => https.get("https://provider.invalid")]) {
  try { await check();throw Error("Tripwire bypassed"); }
  catch (error) { if (!error.message.startsWith("Owned network tripwire:")) throw error; }
}
if (calibration.length !== 8) throw Error("Tripwire calibration incomplete");
calibrating = false;

const pg = (await import("../../../dashboard/node_modules/pg/lib/index.js")).default;
const contexts = new AsyncLocalStorage(), requests = [];
const queryOriginal = pg.Client.prototype.query;
pg.Client.prototype.query = function (...args) {
  reserveSql();
  const ctx = contexts.getStore();
  const sql = typeof args[0] === "string" ? args[0] : args[0]?.text;
  const entry = ctx ? {sql} : null;
  if (entry) ctx.sql.push(entry);
  const before=performance.now(),result=queryOriginal.apply(this,args);
  return result?.then ? result.then((value) => {
    if (entry) entry.elapsedMs=performance.now()-before;
    return value;
  }, (error) => { if (entry) entry.error=error.code || error.name;throw error; }) : result;
};
const {query,closeDatabase} = await import("../../../dashboard/backend/services/postgres.js");
const {send} = await import("../../../dashboard/backend/services/relational-core.js");
const {handleRequest} = await import("../../../dashboard/backend/aws-app.js");
const {orionProEnrichmentRoute} = await import("../../../dashboard/backend/services/orion-pro-enrichment.js");
const [identity] = await query(`SELECT current_user AS role,current_setting('transaction_read_only') AS readonly,
 current_setting('statement_timeout') AS statement,current_setting('lock_timeout') AS locks,
 current_setting('idle_in_transaction_session_timeout') AS idle,(SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()) AS ssl`);
const actualApp = process.env.COMPETITION_ACTUAL_APP === "1";
async function independent(request,url) {
  try {
    if (!["GET","HEAD"].includes(request.method)) return send(request,{error:{code:"METHOD_NOT_ALLOWED"}},405,{headers:{Allow:"GET, HEAD"}});
    return await orionProEnrichmentRoute(request,url.pathname,url.searchParams,{mediaBase:process.env.STATARENA_CLOUDFRONT_URL}) || await handleRequest(request);
  } catch(error) {
    const status = Number.isInteger(error.status) ? error.status : 503;
    return send(request,{ok:false,available:false,error:{code:status===400?"INVALID_PARAMETER":status===404?"RESOURCE_NOT_FOUND":"DATA_UNAVAILABLE",message:status===503?"Données indisponibles.":error.message}},status);
  }
}
const server = http.createServer(async (incoming,outgoing) => {
  const u = new URL(incoming.url, `http://127.0.0.1:${server.address().port}`);
  if (u.pathname === "/__e2e__/traces") {
    outgoing.writeHead(200,{"Content-Type":"application/json"});outgoing.end(JSON.stringify({requests,attempts,calibration}));return;
  }
  const ctx={id:incoming.headers["x-e2e-id"],method:incoming.method,path:u.pathname+u.search,sql:[]};
  await contexts.run(ctx,async () => {
    try {
      const req=new Request(u,{method:incoming.method,headers:incoming.headers});
      const res=actualApp ? await handleRequest(req) : await independent(req,u);
      ctx.status=res.status;requests.push(ctx);outgoing.writeHead(res.status,Object.fromEntries(res.headers));outgoing.end(Buffer.from(await res.arrayBuffer()));
    } catch(error) {ctx.error=error.code||error.name;requests.push(ctx);outgoing.writeHead(500);outgoing.end("Owned HTTP failure");}
  });
});
await new Promise((r)=>server.listen(0,"127.0.0.1",r));
console.log(JSON.stringify({event:"ready",port:server.address().port,identity,calibration,node:process.version,handler:actualApp?"actual-aws-app":"independent-adapter-with-actual-app-controls"}));
async function stop(){server.closeAllConnections();server.close();await closeDatabase();process.exit(0);}
process.on("SIGTERM",stop);process.on("SIGINT",stop);
