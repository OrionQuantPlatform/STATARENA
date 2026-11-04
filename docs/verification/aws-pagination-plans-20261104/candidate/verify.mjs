import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {createRequire,registerHooks} from 'node:module';
import {execFileSync} from 'node:child_process';
import {createServer} from 'node:http';
import {createServer as reservePort} from 'node:net';
import {mkdtempSync,readFileSync,writeFileSync,rmSync} from 'node:fs';
import {join,resolve} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {tmpdir} from 'node:os';
const dir=fileURLToPath(new URL('./',import.meta.url)), source=resolve(dir,'../../../..');
const root=process.env.CANDIDATE_ROOT||source, phase=process.argv[2];
assert.ok(['before','after'].includes(phase));assert.equal(process.versions.node.split('.')[0],'24');
const scratch=mkdtempSync(join(tmpdir(),'statarena-paged-local-')),report={phase,node:process.version,checks:[],pages:{},runs:[]};
const hash=b=>createHash('sha256').update(b).digest('hex'),get=path=>pathToFileURL(join(root,path)).href;
const old=phase==='after'?JSON.parse(readFileSync(join(dir,'before.json'))):null;
const {default:Pg}=await import(pathToFileURL('/tmp/statarena-cache-test-tools/node_modules/embedded-postgres/dist/index.js'));
const sock=reservePort();await new Promise(r=>sock.listen(0,'127.0.0.1',r));const port=sock.address().port;await new Promise(r=>sock.close(r));
const pg=new Pg({databaseDir:join(scratch,'db'),user:'fixture',password:'local-only',port,persistent:false,initdbFlags:['--encoding=UTF8'],onLog(){},onError(){}});
let http,db,writer;
try{
 await pg.initialise();await pg.start();await pg.createDatabase('relational_core_e2e');
 const local='postgresql://fixture:local-only@127.0.0.1:'+port+'/relational_core_e2e';
 const env={...process.env,TEST_DATABASE_URL:local,CANDIDATE_ROOT:root,PYTHONPATH:'/tmp/statarena-publication-test-python',STATARENA_E2E_COMMAND:'/tmp/statarena-node24-20261104 '+process.argv[1]+' '+phase};
 execFileSync('python3',[join(root,'docs/verification/aws-relational-core-20261104/workflow.py'),'--report',join(dir,phase+'-seed.json')],{env});
 const tar=join(source,'docs/verification/aws-deferred-match-20261104/inputs/aws-replay.tar.gz');
 const pages=JSON.parse(execFileSync('python3',['-c',`import tarfile,sys,json
with tarfile.open(sys.argv[1]) as t:
 a=[]
 for m in t.getmembers():
  if m.name.startswith('api-cache/') and '/._' not in m.name and m.name.endswith('.json'):
   url=json.load(t.extractfile(m))['path']
   if '/seasons/partition?' in url and 'l_0ALvwF' in url:a.append([url,t.extractfile(m.name[:-5]+'.bin').read().decode()])
 print(json.dumps(a))`,tar],{maxBuffer:8e6}));
 const {decodePartition}=await import(get('dashboard/frontend/src/season_data.js'));
 const first=pages.find(x=>!x[0].includes('cursor='));
 assert.equal(hash(first[1]),'0d6bbe72588aa8df43b6d7933093a9d9cd8f028a1b53d61fc8c68bdc37f7d403');
 const firstPage=JSON.parse(first[1]);const data=decodePartition(firstPage.data);
 for(const [u,b] of pages)if(u!==first[0]){
    const next=decodePartition(JSON.parse(b).data);
    for(const k of ['fixtures','matches','appearances'])data[k].push(...next[k]);
 }
 writeFileSync(join(scratch,'dense.json'),JSON.stringify({data,generation:firstPage.pagination.generation}));
 execFileSync('python3',[join(dir,'seed.py'),join(scratch,'dense.json')],{env});
 Object.assign(process.env,{DATABASE_URL:local+'?sslmode=disable',STATARENA_DATA_PROVIDER:'aws',STATARENA_TEST_DATABASE:'1',STATARENA_METRICS_SAMPLE_RATE:'0'});
 const {Client}=createRequire(join(root,'dashboard/package.json'))('pg');writer=new Client({connectionString:local});await writer.connect();
 const original=Client.prototype.query;let intercept=null,shape=null,bodySelects=0,latestPageSql;
 Client.prototype.query=async function(sql,...args){
   if(typeof sql!=='string'||!sql.startsWith('WITH candidates AS'))return original.call(this,sql,...args);
   bodySelects++;latestPageSql={sql,values:args[0]};if(intercept?.row && intercept.sql===sql)return {rows:[intercept.row]};
   const result=await original.call(this,sql,...args),row=result.rows[0];
   shape=row.appearances.length?(Array.isArray(row.appearances[0])?'array':'object'):'empty';
   if(intercept)Object.assign(intercept,{row,sql});
   return result;
 };
 db=await import(get('dashboard/backend/services/postgres.js'));const {handleRequest}=await import(get('dashboard/backend/aws-app.js'));
 http=createServer(async(req,res)=>{
    const out=await handleRequest(new Request('http://localhost'+req.url,{method:req.method,headers:req.headers}));
    res.writeHead(out.status,Object.fromEntries(out.headers));res.end(Buffer.from(await out.arrayBuffer()));
 });await new Promise(r=>http.listen(0,'127.0.0.1',r));
 const serve='http://127.0.0.1:'+http.address().port;
 const url=(league,fmt)=>'/api/seasons/partition?season=2026%2F2027&league='+league+'&limit=100'+(fmt==='columns'?'&format=columns':'');
 for(const scenario of ['synthetic','empty','dense','drift']){
   if(scenario==='drift'){
     await writer.query('ALTER TABLE statarena_app.appearances ADD COLUMN future_typed_metric integer');
     await writer.query("UPDATE statarena_app.appearances SET future_typed_metric=0 WHERE match_id='m_000001'");
   }
   for(const fmt of ['ordinary','columns']){
      const path=url(({synthetic:'l_000001',empty:'l_000000',dense:'l_0ALvwF',drift:'l_000001'})[scenario],fmt);
      const res=await fetch(serve+path),raw=await res.text(),body=JSON.parse(raw),etag=res.headers.get('etag');
      // Dense ordinary rows exceed the public 2 MiB guard.
      assert.equal(res.status,scenario==='dense'&&fmt==='ordinary'?413:200);
      const name=scenario+'-'+fmt;
      report.pages[name]={sha:hash(raw),bytes:Buffer.byteLength(raw),etag,status:res.status,shape};
      if(old){ const {shape:_,...a}=report.pages[name],{shape:__,...b}=old.pages[name];assert.deepEqual(a,b);}
      if(res.status!==200)continue;
      const value=fmt==='columns'?decodePartition(body.data):body.data;
      if(scenario==='empty'){assert.equal(value.appearances.length,0);assert.equal(body.pagination.nextCursor,null);}
      if(scenario==='synthetic'||scenario==='drift'){
        const [a,b]=value.appearances;assert.deepEqual([a.positionId,b.positionId],[11,'11']);
        assert.equal(a.newObservedMetric,0);assert.equal(Object.hasOwn(b,'newObservedMetric'),false);assert.equal(b.passesAccurate,null);
        assert.equal(Object.hasOwn(a,'__proto__'),true);assert.equal(a.__proto__,0);assert.equal(a.constructor,0);
        if(scenario==='drift'){assert.equal(a.futureTypedMetric,0);assert.equal(Object.hasOwn(b,'futureTypedMetric'),true);assert.equal(b.futureTypedMetric,null);}
      }
      if(scenario==='dense'&&fmt==='columns'){
        report.captureSemanticEqual=JSON.stringify(body)===JSON.stringify(firstPage);
        report.denseSourceSha=hash(first[1]);report.corpusAppearances=value.appearances.length;
      }
      const pre=bodySelects;
      for(const [method,conditional,status] of [['HEAD',false,200],['HEAD',true,304],['GET',true,304]]){
        const cond=await fetch(serve+path,{method,headers:conditional?{'if-none-match':etag}:{}});
        assert.equal(cond.status,status);assert.equal(cond.headers.get('etag'),etag);assert.equal(await cond.text(),'');
      }
      assert.equal(bodySelects,pre,'HEAD and matching validators must skip body SQL');
   }
   if(scenario==='dense'){
      const path=url('l_0ALvwF','columns');intercept={};
      const referenceSrc=execFileSync('git',['-C',source,'show','e1771cc437:dashboard/backend/services/relational-core.js'],{encoding:'utf8'});
      registerHooks({load(u,c,next){if(u.endsWith('?reference=e1771cc437'))return {shortCircuit:true,format:'module',source:referenceSrc};return next(u,c)}});
      const modules={candidate:await import(get('dashboard/backend/services/relational-core.js')),reference:await import(get('dashboard/backend/services/relational-core.js')+'?reference=e1771cc437')};
      const caches={};
      const call=async(method)=>{
        const request=new Request('http://localhost'+path);
        const start=performance.now(),cpu=process.cpuUsage();
        const response=await modules[method].partitionPage(request,new URL(request.url).searchParams);
        const bytes=Buffer.from(await response.arrayBuffer()), ms=performance.now()-start,dt=process.cpuUsage(cpu);
        assert.equal(hash(bytes),report.pages['dense-columns'].sha);
        return {method,ms,cpuMs:(dt.user+dt.system)/1000};
      };
      for(const k of Object.keys(modules)){
        intercept={};await call(k);caches[k]=intercept;
      }
      intercept=null;
      const exp=await writer.query('explain (analyze,buffers,timing off,format json) '+caches.candidate.sql,['2026/2027','l_0ALvwF',100]);
      report.layoutScans=[];
      function walk(node){if(node['Relation Name']==='pg_attribute') report.layoutScans.push({loops:node['Actual Loops'],rows:node['Actual Rows']});for(const p of node.Plans||[])walk(p);}
      walk(exp.rows[0]['QUERY PLAN'][0].Plan);
      if(phase==='after')assert.deepEqual(report.layoutScans,[{loops:1,rows:87}]);
      for(let i=0;i<13;i++)for(const k of (i%2?['candidate','reference']:['reference','candidate'])){
        intercept=caches[k];const timing=await call(k);if(i)report.runs.push({round:i,...timing});
      }
      intercept=null;
   }
 }
 report.checks.push('All actual HTTP bytes, native values, empty pages, closed cursor, reserved extras and metadata-only GET/HEAD/304 checks passed');
 const ar=report.pages['synthetic-columns'].shape,dr=report.pages['drift-columns'].shape;
 report.hadCompactPgValues=ar==='array';assert.equal(dr,'object');assert.equal(ar,'array','normal typed database response must compact appearances');
 report.passed=true;
}catch(e){report.passed=false;report.failure=e.stack;process.exitCode=1}
finally{if(http)await new Promise(r=>http.close(r));await writer?.end();await db?.closeDatabase();await pg.stop();rmSync(scratch,{recursive:true,force:true});writeFileSync(join(dir,phase+'.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({phase,passed:report.passed,failure:report.failure,sourceMatch:report.captureSemanticEqual}));}
