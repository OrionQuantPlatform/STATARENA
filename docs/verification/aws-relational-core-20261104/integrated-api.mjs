import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {mkdtemp,rm,writeFile,readFile,readdir} from 'node:fs/promises';
import {tmpdir} from 'node:os';import path from 'node:path';import {gunzipSync} from 'node:zlib';import {createRequire} from 'node:module';
const here=import.meta.dir,root=path.resolve(here,'../../..'),tools=process.env.STATARENA_TEST_TOOLS||'/tmp/statarena-archive-remat-pg';
const {default:PG}=await import(tools+'/node_modules/embedded-postgres/dist/index.js'),{Client}=createRequire(root+'/dashboard/package.json')('pg');
const scratch=await mkdtemp(path.join(tmpdir(),'statarena-full-api-')),reserve=Bun.listen({hostname:'127.0.0.1',port:0,socket:{data(){}}}),port=reserve.port;reserve.stop(true);
const pg=new PG({databaseDir:scratch+'/db',user:'fixture',password:'fixture',port,persistent:false,autoRehydrateSymlinks:true,postgresFlags:['-c','listen_addresses=127.0.0.1'],onLog(){},onError(){}});
const report={command:'PYTHONPATH=/tmp/statarena-archive-remat-pg/python bun docs/verification/aws-relational-core-20261104/integrated-api.mjs',setup:'Fresh local PG18.6; actual 003–006 install, typed match and catalog source captures; runtime SELECT-only role. AWS FunctionURL v2 adapter + real HTTP Bun server, loopback only.',requests:[]};
let admin,http,close;
try{
 await pg.initialise();await pg.start();const url='postgresql://fixture:fixture@127.0.0.1:'+port+'/postgres';
 admin=new Client({connectionString:url});await admin.connect();
 for(const migration of ['003_relational_core.sql','004_match_details.sql','005_supporting_models.sql','006_catalog_models.sql']) await admin.query(await readFile(root+'/dashboard/backend/migrations/'+migration,'utf8'));
 for(const [folder,args] of [['relational-match-20261104',[]],['aws-catalog-20261104',[]],['aws-catalog-20261104',['supplemental']]]){
  execFileSync('python3',[path.resolve(here,'../'+folder+'/seed.py'),...args],{env:{...process.env,LOCAL_FIXTURE_DB:url},stdio:'pipe'});
 }
 await admin.query("INSERT INTO statarena_app.partitions(season,league_id,source_digest) VALUES('2026/2027','l_000001','fixture-digest'); INSERT INTO statarena_app.fixtures(id,season,league_id,day,status) VALUES('m_QQ0000','2026/2027','l_000001','2026-11-04','not_started'); INSERT INTO statarena_app.assets(url,path,content_type,size,sha256) VALUES('https://cdn.pitchapi.dev/logo','raw/assets/0123456789abcdef0123456789abcdef.webp','image/webp',1024,'0123456789abcdef0123456789abcdef')");
 await admin.query("CREATE ROLE web_reader LOGIN PASSWORD 'fixture';GRANT USAGE ON SCHEMA statarena_app TO web_reader;GRANT SELECT ON ALL TABLES IN SCHEMA statarena_app TO web_reader;");
 Object.assign(process.env,{DATABASE_URL:url.replace('fixture:fixture','web_reader:fixture')+'?sslmode=disable',STATARENA_TEST_DATABASE:'1',STATARENA_DATA_PROVIDER:'aws',STATARENA_METRICS_SAMPLE_RATE:'0',STATARENA_CLOUDFRONT_URL:'https://d1111111111.cloudfront.net'});
 const {handleRequest}=await import(root+'/dashboard/backend/aws-app.js'),{adapt}=await import(root+'/infra/aws-backend/transport.mjs');
 close=(await import(root+'/dashboard/backend/services/postgres.js')).closeDatabase;
 const lambda=adapt(handleRequest);http=Bun.serve({hostname:'127.0.0.1',port:0,fetch:async req=>{
  const u=new URL(req.url),r=await lambda({version:'2.0',rawPath:u.pathname,rawQueryString:u.search.slice(1),headers:Object.fromEntries(req.headers),requestContext:{http:{method:req.method}}});
  return new Response(req.method==='HEAD'||r.statusCode===304?null:Buffer.from(r.body||'',r.isBase64Encoded?'base64':'utf8'),{status:r.statusCode,headers:r.headers});
 }});
 async function check(route,expected,status=200){
  const url=new URL(route,http.url),get=await fetch(url),bytes=await get.arrayBuffer();
  report.requests.push({route,status:get.status,expectedStatus:status,bytes:bytes.byteLength,etag:get.headers.get('etag'),encoding:get.headers.get('content-encoding')});
  assert.equal(get.status,status,route);const body=JSON.parse(Buffer.from(bytes));if(expected!==undefined)assert.deepEqual(body,expected);
  const policy=get.headers.get('cache-control')||'';report.requests.at(-1).cacheControl=policy;
  if(status!==200){assert.match(policy,/no-store/,route);return;}
  assert.match(policy,/s-maxage=60(?:,|$)/,route);assert.match(policy,/max-age=0(?:,|$)/,route);assert.match(policy,/must-revalidate/,route);
  const etag=get.headers.get('etag');assert.ok(etag,route);
  const head=await fetch(url,{method:'HEAD'});assert.equal(head.status,200,route);assert.equal((await head.arrayBuffer()).byteLength,0);assert.equal(head.headers.get('etag').replace(/^W\//,''),etag.replace(/^W\//,''),route);
  assert.match(head.headers.get('cache-control'),/s-maxage=60(?:,|$)/,route);
  const cond=await fetch(url,{headers:{'if-none-match':etag}});assert.equal(cond.status,304,route);assert.equal((await cond.arrayBuffer()).byteLength,0);assert.match(cond.headers.get('cache-control'),/s-maxage=60(?:,|$)/,route);
 }
 for(const n of ['production-archive','browser-historical-archive','browser-upcoming-archive']){
  const a=JSON.parse(await readFile(root+'/dashboard/outputs/data-completeness/'+n+'.json','utf8')),mid=a.fixture.id;
  await check('/api/archive/matches/'+mid,a);
  for(const [family,v] of Object.entries(a.endpoints)){
   const suffix=({match:'',player_halves:'/players/halves',advanced_teams:'/advanced',advanced_players:'/advanced/players',pass_networks:'/advanced/network'})[family]??'/'+family;
   await check('/api/pitchapi/matches/'+mid+suffix,v.status===200?{data:v.data}:{ok:false,error:v.error},v.status);
  }
 }
 const capture=path.resolve(here,'../aws-catalog-20261104/captures');
 for(const f of await readdir(capture)){
  const k=f.slice(0,-3).replaceAll('__','/'),v=JSON.parse(gunzipSync(await readFile(path.join(capture,f))));
  const ranks=/^raw\/rankings\/(fifa-men|uefa-associations|uefa-clubs)\/([^/]+)\.json$/.exec(k);
  if(ranks)await check('/api/rankings/edition?'+new URLSearchParams({kind:ranks[1],edition:ranks[2]}),v);
  const arc=/^raw\/(openfootball|historical-goals)\/(?!index)([^/]+)\.json(?:\.gz)?$/.exec(k);
  if(arc)await check('/api/archives/season?'+new URLSearchParams({kind:arc[1]==='openfootball'?'results':'goals',season:v.season}),v);
  if(k.startsWith('profile/')){const [,kind,id]=k.split('/');if(id)await check('/api/archive/profiles/'+kind+'/'+id,v);await check('/api/pitchapi/'+kind+(id?'/'+id:''),v.status===200?{data:v.data}:{ok:false,error:v.error},v.status);}
 }
 await check('/api/supplemental');
 await check('/api/rankings/edition?kind=bad&edition=2026.uefa',undefined,400);
 await check('/data/raw/something.json',undefined,410);
 for(const method of ["GET","HEAD"]){
 const pending=await fetch(new URL('/api/matches/m_QQ0000/summary',http.url),{method});assert.equal(pending.status,200);assert.match(pending.headers.get('cache-control'),/no-store/);
 const p='/api/assets?url='+encodeURIComponent('https://cdn.pitchapi.dev/logo');
 const image=await fetch(new URL(p,http.url),{method,redirect:'manual'});assert.equal(image.status,307);assert.equal(image.headers.get('location'),'https://d1111111111.cloudfront.net/data/raw/assets/0123456789abcdef0123456789abcdef.webp');
 assert.match(image.headers.get('cache-control'),/s-maxage=(?:[1-5]?[0-9]|60)(?:,|$)/);
 report.requests.push({route:p,method,status:307,cacheControl:image.headers.get('cache-control')},{route:'/api/matches/m_QQ0000/summary',method,status:200,cacheControl:pending.headers.get('cache-control')});
 }
 report.passed=true;
}catch(error){report.error=String(error.stack||error).slice(0,2300);report.passed=false;}
finally{http?.stop(true);await close?.();await admin?.end();await pg.stop();await rm(scratch,{force:true,recursive:true});await writeFile(here+'/integrated-api.json',JSON.stringify(report,null,2)+'\n');}
console.log(JSON.stringify({passed:report.passed,count:report.requests.length,error:report.error}));process.exitCode=report.passed?0:1;
