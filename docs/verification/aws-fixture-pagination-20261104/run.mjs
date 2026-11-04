import assert from 'node:assert/strict';
import {mkdtemp,readFile,readdir,rm,writeFile} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import {tmpdir} from 'node:os';import path from 'node:path';import {createRequire} from 'node:module';
const phase=process.argv[2];assert.ok(['before','after'].includes(phase));const here=import.meta.dir,root=path.resolve(here,'../../..'),require=createRequire(root+'/dashboard/package.json');
const {Client}=require('pg'),{default:PG}=await import((process.env.STATARENA_TEST_TOOLS||'/tmp/statarena-archive-remat-pg')+'/node_modules/embedded-postgres/dist/index.js');
const dir=await mkdtemp(path.join(tmpdir(),'football-fixtures-')),r=Bun.listen({hostname:'127.0.0.1',port:0,socket:{data(){}}}),port=r.port;r.stop(true);
const pg=new PG({databaseDir:dir+'/pg',user:'fixture',password:'fixture',port,persistent:false,autoRehydrateSymlinks:true,postgresFlags:['-c','listen_addresses=127.0.0.1'],onLog(){},onError(){}});
const report={command:'PYTHONPATH=/tmp/statarena-archive-remat-pg/python bun docs/verification/aws-fixture-pagination-20261104/run.mjs '+phase,cases:[],requests:[]};
let admin,http,close,mode,ready=false,interventions=0;
const league='l_0bfbkO',large='l_DENSE1',day='2026-05-14',season='2025/2026';
const ids=n=>Array.from({length:n},(_,i)=>'m_'+String(i).padStart(6,'0'));
async function test(name,fn){mode=name;interventions=0;const c={name};report.cases.push(c);try{await fn(c);c.passed=true;}catch(e){c.passed=false;c.error=String(e.message).slice(0,320);}}
try{
 await pg.initialise();await pg.start();const url='postgresql://fixture:fixture@127.0.0.1:'+port+'/postgres?sslmode=disable';
 admin=new Client({connectionString:url});await admin.connect();
 const migrations=root+'/dashboard/backend/migrations';for(const f of (await readdir(migrations)).filter(f=>/^\d+.*\.sql$/.test(f)&&Number(f.slice(0,3))>=3).sort())await admin.query(await readFile(path.join(migrations,f),'utf8'));
 execFileSync('python3',[here+'/seed.py'],{env:{...process.env,FIXTURE_DB:url,PYTHONDONTWRITEBYTECODE:'1'},stdio:'pipe'});
 const sql="insert into statarena_app.fixtures(id,season,native_season,league_id,league_name,day,status,home_team_id,away_team_id,home_name,away_name,score_home,score_away,round_name,has_playoff) select 'm_'||lpad((i+$1)::text,6,'0'),$2,$2,$3,'League',$4::date,'finished','t_000001','t_000002',case when $5 and i>=100 then repeat('A',30000) else 'A' end,'B',0,1,'Round '||i,i=122 from generate_series(0,$6::int-1) i";
 await admin.query(sql,[0,season,league,day,false,123]);await admin.query(sql,[800000,season,league,'2026-05-15',false,1]);await admin.query(sql,[800001,season,'l_OTHER1',day,false,1]);await admin.query(sql,[500000,season,large,'2026-04-01',true,210]);
 Object.assign(process.env,{DATABASE_URL:url,STATARENA_DATA_PROVIDER:'aws',STATARENA_TEST_DATABASE:'1',STATARENA_METRICS_SAMPLE_RATE:'0'});
 const {handleRequest}=await import(root+'/dashboard/backend/aws-app.js');close=(await import(root+'/dashboard/backend/services/postgres.js')).closeDatabase;
 http=Bun.serve({hostname:'127.0.0.1',port:0,fetch:async req=>{
   const u=new URL(req.url),res=await handleRequest(req);
   let next=null,count=null;if(res.status===200&&u.pathname==='/api/fixtures'){const v=await res.clone().json();count=v.data.matches.length;next=Boolean(v.pagination.nextCursor);}
   report.requests.push({mode,path:u.pathname,params:Object.fromEntries([...u.searchParams].map(([k,v])=>[k,k==='cursor'?'[cursor]':v])),status:res.status,count,hasNext:next});
   if(u.pathname==='/api/fixtures'&&!u.searchParams.has('cursor')&&next&&((mode==='one generation restart'&&interventions===0)||mode?.startsWith('repeat conflict'))){
     interventions++;await admin.query("with changed as (update statarena_app.fixtures set score_home=$1 where id='m_000000') update statarena_app.publications set generation=generation+1",[20+interventions]);
   }
   return res;
 }});
 process.env.NEXT_PUBLIC_API_ORIGIN=http.url.origin;
 const {FootballDataClient}=await import(root+'/dashboard/frontend/src/services/football-client.js'),{cupWorkerSnapshot}=await import(root+'/dashboard/frontend/src/services/cup-worker-client.js');
 const requested=()=>report.requests.filter(r=>r.mode===mode&&r.path==='/api/fixtures');
 async function schedule(scope,local=[]){
  const c=new FootballDataClient({data:{meta:{},competitions:[{id:scope.league||league,name:'League'}],fixtures:local},redraw(){}});
  Object.assign(c,{configured:true,season,browseMode:scope.day?'day':'catalog',day:scope.day,competitionId:scope.league||league});
  await c.loadFixtures();return {client:c,result:c.fixtures.get(scope.day?'date:'+scope.day:(scope.league||league)+':'+season)};
 }
 function exact(rows,keys){assert.equal(rows.length,keys.length);assert.deepEqual(new Set(rows.map(r=>r.id)),new Set(keys));}
 function complete(){const a=requested();assert.ok(a.length>1,'actual bounded multi-page HTTP required');assert.equal(a.at(-1).hasNext,false);}
 await test('busy date',async()=>{const {result}=await schedule({day});exact(result.matches,[...ids(123),'m_800001']);complete();});
 await test('league and season',async()=>{const {client,result}=await schedule({league});exact(result.matches,[...ids(123),'m_800000']);assert.equal(client.fixtureIndex.size,124);assert.equal(result.matches[0].score_home,0);complete();});
 await test('native cup union',async()=>{const v=await cupWorkerSnapshot('native',league,season);exact(v.matches,[...ids(123),'m_800000','m_KEEP01']);assert.equal(v.matches.find(m=>m.id==='m_000000').score_home,0);assert.deepEqual(v.rounds.m_000122,{name:'Round 122',playoff:true});assert.deepEqual(v.rounds.m_KEEP01,{name:'Saved final',playoff:true});complete();});
 await test('empty scope',async()=>{const {result}=await schedule({league:'l_EMPTY1'});assert.deepEqual(result.matches,[]);assert.equal(result.source,'api');assert.equal(requested().length,1);});
 await test('one generation restart',async()=>{const {result}=await schedule({league});exact(result.matches,[...ids(123),'m_800000']);assert.equal(result.matches.find(r=>r.id==='m_000000').score_home,21);assert.equal(requested().filter(r=>r.status===409).length,1);complete();});
 await test('dense mid-page 413',async()=>{const {result}=await schedule({league:large});assert.equal(result.matches.length,210);assert.equal(new Set(result.matches.map(r=>r.id)).size,210);assert.ok(requested().some(r=>r.status===413&&r.params.cursor),'expected real second-page 413');assert.ok(requested().some(r=>r.params.limit==='50'&&!r.params.cursor));complete();});
 await test('repeat conflict calendar fallback',async()=>{const single={id:'m_LOCAL1',season,league:{id:league}};const {client,result}=await schedule({league},[single]);assert.deepEqual(result.matches,[single]);assert.ok(result.error);assert.equal(client.fixtureIndex.size,1);assert.equal(requested().filter(r=>r.status===409).length,2);});
 await test('repeat conflict complete saved cup',async()=>{const v=await cupWorkerSnapshot('native',league,season);exact(v.matches,['m_000000','m_KEEP01']);assert.equal(v.matches[0].score_home,77);assert.equal(requested().filter(r=>r.status===409).length,2);});
 report.passed=report.cases.every(c=>c.passed);
}catch(e){report.passed=false;report.error=String(e.stack||e).slice(0,900);}
finally{http?.stop(true);await close?.();await admin?.end();await pg.stop();await rm(dir,{recursive:true,force:true});await writeFile(here+'/'+phase+'.json',JSON.stringify(report,null,2)+'\n');}
console.log(JSON.stringify({passed:report.passed,cases:report.cases,error:report.error}));if(!report.passed)process.exitCode=1;
