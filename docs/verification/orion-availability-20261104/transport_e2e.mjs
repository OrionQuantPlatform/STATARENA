import assert from "node:assert/strict";
import { writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
const out=new URL("./",import.meta.url), stamp=new Date().toISOString().replace(/[-:.]/g,"");
const report={atUtc:new Date().toISOString(),command:"bun docs/verification/orion-availability-20261104/transport_e2e.mjs",setup:"Actual Next transport functions, a local HTTP fixture and an AWS-origin redirect checked without contacting AWS or any provider.",expected:"Local proxy works; configured AWS preview wins; its retired /data route remains 410; legacy without credentials fails closed.",checks:[],passed:false};
let server;
try {
  delete process.env.VERCEL;delete process.env.NEXT_PUBLIC_API_ORIGIN;
  server=Bun.serve({hostname:"127.0.0.1",port:0,fetch:r=>Response.json({path:new URL(r.url).pathname})});
  process.env.ORION_API_ORIGIN=server.url.origin;
  const {proxy}=await import("../../../dashboard/frontend/src/server/bun-proxy.js");
  const data=await import("../../../dashboard/frontend/app/data/[...path]/route.js");
  let r=await proxy(new Request("http://local/api/health"));assert.equal(r.status,200);assert.equal((await r.json()).path,"/api/health");
  r=await data.GET(new Request("http://local/data/computed/test.json"));assert.equal(r.status,200);assert.equal((await r.json()).path,"/data/computed/test.json");
  report.checks.push({name:"local upstream API and data proxy",passed:true});
  process.env.VERCEL="1";process.env.NEXT_PUBLIC_API_ORIGIN="https://d317dq37z1tacb.cloudfront.net";
  r=await proxy(new Request("https://frontend.invalid/api/health?q=1"));assert.equal(r.status,307);assert.equal(r.headers.get("location"),"https://d317dq37z1tacb.cloudfront.net/api/health?q=1");
  r=await data.GET(new Request("https://frontend.invalid/data/computed/test.json"));assert.equal(r.status,410);
  report.checks.push({name:"AWS preview wins and data stays retired",passed:true});
  delete process.env.NEXT_PUBLIC_API_ORIGIN;delete process.env.NEON_DATABASE_URL;delete process.env.NEON_STORAGE_ENDPOINT;
  r=await proxy(new Request("https://frontend.invalid/api/dashboard/manifest"));assert.equal(r.status,503);
  report.checks.push({name:"legacy mode without Neon configuration fails closed",passed:true});
  report.passed=true;
} catch(e) {report.error=String(e?.stack||e);}
finally {server?.stop(true);const file=new URL(`transport-${stamp}.json`,out);await writeFile(file,JSON.stringify(report,null,2)+"\n");console.log(JSON.stringify({passed:report.passed,error:report.error,artifact:fileURLToPath(file),checks:report.checks}));}
process.exitCode=report.passed?0:1;
