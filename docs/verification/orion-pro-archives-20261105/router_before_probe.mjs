// Observe the exact original Pro dispatch before ROOT wires the new module.
import net from "node:net";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
const app = new URL("../../../dashboard/backend/aws-app.js", import.meta.url);
const expected = process.argv[2];
const hash = () => createHash("sha256").update(readFileSync(app)).digest("hex");
if (hash() !== expected) throw Error("Original app input drift");
if (process.env.DATABASE_URL || process.env.NEON_DATABASE_URL) throw Error("No DB configured for this probe");
process.env.STATARENA_PRO_API = "1";
const attempts = [];
globalThis.fetch = () => {attempts.push("fetch");throw Error("Network disabled");};
net.Socket.prototype.connect = () => {attempts.push("socket");throw Error("Network disabled");};
const {handleRequest} = await import(app);
const records = [];
for (const path of ["/api/archives/index?kind=results","/api/archives/season?kind=goals&season=2026%2F2027","/api/supplemental","/api/archive/matches/m_000001"]) {
  const r = await handleRequest(new Request("http://fixture.invalid"+path));
  records.push({path,status:r.status,cacheControl:r.headers.get("cache-control"),body:await r.json()});
}
if (hash() !== expected || attempts.length || records.some((r) => r.status!==501||r.cacheControl!=="no-store"||r.body.error?.code!=="PRO_ROUTE_NOT_IMPLEMENTED"))
  throw Error("Unexpected original dispatch result");
console.log(JSON.stringify({kind:"archive_actual_app_before_wiring_v1",appSha256:expected,node:process.version,records,networkAttempts:attempts,pgConnections:0}));
