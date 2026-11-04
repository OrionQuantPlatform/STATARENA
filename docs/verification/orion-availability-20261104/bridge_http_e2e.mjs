// E2E on the real saved Neon deployment through the proposed local compatibility HTTP layer.
import assert from "node:assert/strict";
import { gunzipSync, gzipSync } from "node:zlib";
import { writeFile } from "node:fs/promises";
import { fileURLToPath, pathToFileURL } from "node:url";
import { resolve } from "node:path";

const root=resolve(fileURLToPath(new URL("../../../",import.meta.url)));
const output=resolve(root,"docs/verification/orion-availability-20261104");
const stamp=new Date().toISOString().replace(/[-:.]/g,"");
const old="https://statarena-analytics-jumo9il0b-hlemonniers-projects.vercel.app";
const checks=[];
const report={atUtc:new Date().toISOString(),command:"bun docs/verification/orion-availability-20261104/bridge_http_e2e.mjs",
  setup:"Local Bun HTTP adapter; its legacy request and saved-object readers use only the immutable old Vercel/Neon deployment. Supplemental expansion alone uses two synthetic saved objects to bound external reads. No provider requests or writes.",
  expected:"Current frontend data contracts traverse the local bridge with current and historical saved data; pagination, scouting, match fallback, catalogs, missing paths and malformed parameters stay correct.",checks,passed:false};
const fetched=new Map();
const syntheticIndex={meta:{fixture:true},competitions:[{folder:"FIXTURE",season:"2026/2027",tables:{results:{path:"raw/fixture-results.json.gz"},fixtures:{path:"raw/fixture-fixtures.json.gz"}}}]};
async function readJson(path) {
  if(path==="raw/supplemental-index.json") return syntheticIndex;
  if(path==="raw/fixture-results.json.gz") return [{id:"saved-result"}];
  if(path==="raw/fixture-fixtures.json.gz") return [{id:"saved-fixture"}];
  assert.match(path,/^(raw|computed)\/[A-Za-z0-9_./-]+$/); assert.ok(!path.split("/").some(p=>p.startsWith(".")));
  if(!fetched.has(path)) fetched.set(path,(async()=>{const r=await fetch(old+"/data/"+path,{headers:{"accept-encoding":"identity"}});if(!r.ok){const e=Error("saved object HTTP "+r.status);e.code=r.status===404?"ENOENT":"UPSTREAM";throw e;}const b=Buffer.from(await r.arrayBuffer());return JSON.parse(path.endsWith(".gz")?gunzipSync(b).toString():b.toString());})());
  return fetched.get(path);
}
async function legacy(request) {
  const url=new URL(request.url); const target=new URL(url.pathname+url.search,old);
  if(url.pathname==="/data/raw/supplemental-index.json")return Response.json(syntheticIndex);
  if(url.pathname==="/data/raw/fixture-results.json.gz")return new Response(gzipSync(JSON.stringify([{id:"saved-result"}])));
  if(url.pathname==="/data/raw/fixture-fixtures.json.gz")return new Response(gzipSync(JSON.stringify([{id:"saved-fixture"}])));
  const headers={"accept-encoding":"identity"};if(request.headers.has("if-none-match"))headers["if-none-match"]=request.headers.get("if-none-match");
  const response=await fetch(target,{method:request.method,redirect:"manual",headers});
  const copy=new Headers(response.headers);
  if(copy.has("content-encoding"))copy.delete("content-length");
  copy.delete("content-encoding");
  return new Response(response.body,{status:response.status,headers:copy});
}
let adapter;
try { adapter=(await import(pathToFileURL(resolve(root,"dashboard/frontend/src/server/legacy-compat.js")))).legacyCompatibility; }
catch { adapter=async(request,deps)=>deps.handleLegacy(request); }
const server=Bun.serve({hostname:"127.0.0.1",port:0,fetch:request=>adapter(request,{handleLegacy:legacy,readJson})});
const request=(path,init)=>fetch(new URL(path,server.url),init);
const fetcher=(path,init)=>request(path,init);
const check=async(name,fn)=>{try{const details=await fn();checks.push({name,passed:true,details});}catch(e){checks.push({name,passed:false,error:String(e?.message||e)});}};
let manifest,index,player,team;
try {
  manifest=await readJson("computed/dashboard/index.json");
  index=await readJson(manifest.scouting.playerRoutes.path);
  player=Object.keys(index.routes).find(k=>/^p_[A-Za-z0-9]{6}$/.test(k));
  team=Object.keys(index.clubRoutes).find(k=>/^t_[A-Za-z0-9]{6}$/.test(k));
  await check("manifest exposes six saved seasons",async()=>{const r=await request("/api/dashboard/manifest");assert.equal(r.status,200);const m=await r.json();assert.equal(m.storage,"json-packed");assert.equal(m.seasons.length,6);return {seasons:m.seasons.length};});
  const {loadSeason,readPages}=await import(pathToFileURL(resolve(root,"dashboard/frontend/src/season_data.js")));
  for(const [season,count] of [["2026/2027",81],["2025/2026",306]]) await check("load saved season "+season,async()=>{const x=await loadSeason(manifest,season,fetcher,new Set(["l_3FJFUl"]));assert.equal(x.matches.length,count);assert.ok(x.appearances.length>0);assert.ok(x.fixtures.length>0);return {matches:x.matches.length,appearances:x.appearances.length,fixtures:x.fixtures.length};});
  await check("fixture cursor traversal",async()=>{const pages=await readPages("/api/fixtures",{league:"l_3FJFUl",season:"2025/2026",status:"all"},fetcher);const matches=pages.flatMap(p=>p.matches);assert.equal(matches.length,306);assert.equal(new Set(matches.map(x=>x.id)).size,306);return {pages:pages.length,matches:matches.length};});
  await check("fixture HEAD and invalid calendar date",async()=>{const head=await request("/api/fixtures?league=l_3FJFUl&season=2025%2F2026&limit=1",{method:"HEAD"});assert.equal(head.status,200);assert.equal((await head.text()).length,0);const invalid=await request("/api/fixtures?from=2025-02-30&to=2025-02-30");assert.equal(invalid.status,400);return {};});
  await check("fixture stale cursor is rejected",async()=>{const first=await request("/api/fixtures?league=l_3FJFUl&season=2025%2F2026&limit=1");assert.equal(first.status,200);const x=await first.json();const cursor=JSON.parse(Buffer.from(x.pagination.nextCursor,"base64url").toString());cursor.generation="changed";const encoded=Buffer.from(JSON.stringify(cursor)).toString("base64url");const r=await request("/api/fixtures?league=l_3FJFUl&season=2025%2F2026&limit=1&cursor="+encoded);assert.equal(r.status,409);return {};});
  await check("player and team scouting routes",async()=>{assert.ok(player&&team);const r=await request("/api/scouting/routes?"+new URLSearchParams({player,team}));assert.equal(r.status,200);const x=await r.json();assert.deepEqual(x.routes[player],index.routes[player]);assert.deepEqual(x.clubRoutes[team],index.clubRoutes[team]);return {playerSeasons:Object.keys(x.routes[player]).length,teamSeasons:Object.keys(x.clubRoutes[team]).length};});
  await check("match summary retains saved leaders",async()=>{const r=await request("/api/matches/m_18Uw0k/summary");assert.equal(r.status,200);const x=await r.json();assert.equal(x.data.match.id,"m_18Uw0k");assert.ok(x.data.match.leadingPlayers.length>0);assert.ok(x.data.match.leadingPlayers.every(p=>p.matchId==="m_18Uw0k"));return {leaders:x.data.match.leadingPlayers.length};});
  await check("match summary fallback through real client",async()=>{const {loadRemoteMatch}=await import(pathToFileURL(resolve(root,"dashboard/frontend/src/services/remote-match.js")));const client={normalizedRemote:x=>x,request:()=>{throw Error("unexpected fallback")}};const x=await loadRemoteMatch("m_18Uw0k",client,async path=>{const r=await request(path);if(!r.ok)throw Error("HTTP "+r.status);return r.json();});assert.equal(x.id,"m_18Uw0k");return {id:x.id};});
  await check("archive index and season",async()=>{const r=await request("/api/archives/index?kind=results");assert.equal(r.status,200);const x=await r.json();assert.ok(x.seasons.length);const id=x.seasons[0].id;const q=await request("/api/archives/season?"+new URLSearchParams({kind:"results",season:id}));assert.equal(q.status,200);return {seasons:x.seasons.length,chosen:id};});
  await check("association ranking",async()=>{const r=await request("/api/rankings/associations?year=2025");assert.equal(r.status,200);const x=await r.json();assert.ok(Array.isArray(x.rows));return {rows:x.rows.length};});
  await check("club links and ranking",async()=>{const links=await request("/api/club-links?club=t_41iFW3");assert.equal(links.status,200);const l=await links.json();assert.ok(l.links&&typeof l.links==="object");const ranking=await request("/api/rankings/club?club=t_41iFW3");assert.equal(ranking.status,200);const x=await ranking.json();assert.ok(x.rows===null||Array.isArray(x.rows));return {linkCount:Object.keys(l.links).length,rankingRows:x.rows?.length??null};});
  await check("cup catalog and table",async()=>{const idx=await request("/api/cup-index?kind=worker");assert.equal(idx.status,200);const x=await idx.json();const c=x.competitions.find(v=>v.tables?.results?.rows>0);assert.ok(c);const r=await request("/api/cup-table?"+new URLSearchParams({competition:c.folder,season:c.season,kind:"results"}));assert.equal(r.status,200);assert.ok(Array.isArray(await r.json()));return {folder:c.folder,season:c.season};});
  await check("historical cup edition uses its saved table",async()=>{const deps={handleLegacy:legacy,readJson:async path=>path==="raw/cup-worker/index.json"?{competitions:[{folder:"TEST_CUP",season:"2026/2027",editions:{"2025/2026":{results:{path:"raw/test-cup.json"}}}}]}:path==="raw/supplemental-index.json"?{competitions:[]}:path==="raw/test-cup.json"?[{id:"historical"}]:(()=>{throw Error("Unexpected path")})()};const local=Bun.serve({hostname:"127.0.0.1",port:0,fetch:r=>adapter(r,deps)});try{const r=await fetch(new URL("/api/cup-table?competition=TEST_CUP&season=2025%2F2026&kind=results",local.url));assert.equal(r.status,200);assert.equal((await r.json())[0].id,"historical");return {fixture:"synthetic historic edition"};}finally{local.stop(true);}});
  await check("saved cup snapshot and matchdays",async()=>{const cup=await request("/api/cup-snapshot?kind=open-cups&competition=world-cup-history&season=2022");assert.equal(cup.status,200);assert.ok(Array.isArray((await cup.json()).matches));const days=await request("/api/matchdays?competition=l_0bfbkO&season=2026%2F2027");assert.equal(days.status,200);assert.ok((await days.json()).matches);return {};});
  await check("legacy read routes retain upstream statuses",async()=>{const paths=["/api/status","/api/pitchapi/leagues","/api/standings?competition=l_3FJFUl&season=2025%2F2026","/api/open-cups?competition=world-cup-history&season=2022","/api/openligadb?competition=germany-cup&season=2025%2F2026","/api/nations-results?season=2026%2F2027","/api/stadium?id=Q1","/api/player-honours?id="+player,"/api/club-wikidata?name=Paris&country=FRA","/api/coach-portrait?name=Test"];const rows=[];for(const path of paths){const [a,b]=await Promise.all([request(path),legacy(new Request("http://fixture"+path))]);assert.equal(a.status,b.status,path);rows.push({path,status:a.status});}return rows;});
  await check("supplemental references expand",async()=>{const r=await request("/api/supplemental");assert.equal(r.status,200);const x=await r.json();assert.equal(x.competitions[0].results[0].id,"saved-result");assert.equal(x.competitions[0].fixtures[0].id,"saved-fixture");return {fixture:"synthetic bounded sample"};});
  await check("legacy client loads supplemental in bounded objects",async()=>{const {FootballDataClient}=await import(pathToFileURL(resolve(root,"dashboard/frontend/src/services/football-client.js")));const original=globalThis.fetch,paths=[];globalThis.fetch=(path,init)=>{if(typeof path==="string"&&path.startsWith("/")){paths.push(path);return original(new URL(path,server.url),init);}return original(path,init);};try{const client=new FootballDataClient({data:{meta:{storage:"json-packed"},competitions:[]}});await client.loadSupplemental();assert.equal(client.supplementalError,null);assert.equal(client.supplementalData.competitions[0].results[0].id,"saved-result");assert.ok(paths.includes("/data/raw/supplemental-index.json"));assert.ok(!paths.includes("/api/supplemental"));return {paths};}finally{globalThis.fetch=original;}});
  await check("missing route and invalid parameter fail",async()=>{assert.equal((await request("/api/definitely-not-a-route")).status,404);assert.equal((await request("/api/archives/index?kind=invalid")).status,400);return {};});
  await check("HEAD manifest has no response body",async()=>{const r=await request("/api/dashboard/manifest",{method:"HEAD"});assert.equal(r.status,200);assert.equal((await r.text()).length,0);return {};});
  report.passed=checks.every(c=>c.passed);
} catch(e){report.error=String(e?.stack||e);}
finally {server.stop(true);const file=resolve(output,`bridge-http-${stamp}.json`);await writeFile(file,JSON.stringify(report,null,2)+"\n");console.log(JSON.stringify({passed:report.passed,artifact:file,checks}));}
process.exitCode=report.passed?0:1;
