// Local E2E-only proxy for the old immutable saved-data deployment.
import { gunzipSync } from "node:zlib";
import { legacyCompatibility } from "../../../dashboard/frontend/src/server/legacy-compat.js";
const old="https://statarena-analytics-jumo9il0b-hlemonniers-projects.vercel.app";
const cache=new Map();
async function readJson(path) {
  if(!/^(raw|computed)\/[A-Za-z0-9_./-]+$/.test(path)||path.split("/").some(x=>x.startsWith("."))) throw Error("invalid saved path");
  if(!cache.has(path)) cache.set(path,(async()=>{const r=await fetch(old+"/data/"+path,{headers:{"accept-encoding":"identity"}});if(!r.ok){const e=Error("saved object unavailable");e.code=r.status===404?"ENOENT":"UPSTREAM";throw e;}const b=Buffer.from(await r.arrayBuffer());return JSON.parse(path.endsWith(".gz")?gunzipSync(b).toString():b.toString());})().catch(e=>{cache.delete(path);throw e;}));
  return cache.get(path);
}
async function handleLegacy(request) {
  const u=new URL(request.url), target=new URL(u.pathname+u.search,old), headers={"accept-encoding":"identity"};
  if(request.headers.has("if-none-match"))headers["if-none-match"]=request.headers.get("if-none-match");
  const r=await fetch(target,{method:request.method,headers,redirect:"manual"});
  const h=new Headers(r.headers);
  // Fetch decodes an HTTP content coding, but a stored .gz with no such header
  // still carries its original bytes and requires its real encoded length.
  if(h.has("content-encoding"))h.delete("content-length");
  h.delete("content-encoding");
  // The test-only Bun relay drops a supplied Content-Length on streamed GETs.
  // Buffer this bounded public response so the next local hop sees the same
  // encoded length as the real in-process legacy reader.
  const body=request.method==="HEAD"||[204,304].includes(r.status)?null:await r.arrayBuffer();
  return new Response(body,{status:r.status,headers:h});
}
const server=Bun.serve({hostname:"127.0.0.1",port:Number(process.env.ORION_BRIDGE_TEST_PORT),fetch:async req=>{
  const url=new URL(req.url);
  if(url.pathname==="/__legacy") {
    const path=url.searchParams.get("path");
    if(!path||!/^\/(?:api|data)\//.test(path))return new Response(null,{status:400});
    return handleLegacy(new Request(new URL(path,url),{method:req.method,headers:req.headers}));
  }
  if(url.pathname==="/__object") {
    try {return Response.json(await readJson(url.searchParams.get("path")));}
    catch(e) {return new Response(null,{status:e.code==="ENOENT"?404:503});}
  }
  return legacyCompatibility(req,{handleLegacy,readJson});
}});
console.log(JSON.stringify({listening:server.url.href,source:"old saved Neon deployment"}));
