import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {createRequire,registerHooks} from 'node:module';
import {readFileSync,writeFileSync} from 'node:fs';
import {isDeepStrictEqual} from 'node:util';

const folder=new URL('./',import.meta.url),root=new URL('../../../',folder);
const baseline=JSON.parse(readFileSync(new URL('measurements.json',folder))),dense=baseline.routes[0];
const credential=JSON.parse(JSON.parse(execFileSync('aws',['--profile','statarena','--region','us-east-2','ssm','get-parameter','--name','/statarena/app/rds-runtime','--with-decryption','--output','json'],{encoding:'utf8'})).Parameter.Value);
if(credential.host!=='statarena-postgres.clcy2iqyajbl.us-east-2.rds.amazonaws.com' || credential.database!=='statarena_prod')throw Error('Unexpected target');
const url=new URL('postgresql://'+credential.host+'/'+credential.database);url.username=credential.username;url.password=credential.password;
Object.assign(process.env,{DATABASE_URL:url.href,STATARENA_DATA_PROVIDER:'aws',STATARENA_METRICS_SAMPLE_RATE:'0'});
const req=createRequire(new URL('dashboard/package.json',root));
const pg=req('pg'), result=createRequire(req.resolve('pg'))('./result.js'),parse=result.prototype.parseRow;
let fields=null;
result.prototype.parseRow=function(raw){
 if(fields && raw.length>1)for(let i=0;i<raw.length;i++)fields[this.fields[i].name]=raw[i]==null?0:Buffer.byteLength(raw[i]);
 return parse.call(this,raw);
};
const point={};
let row,changed;
const savedQuery=pg.Client.prototype.query;
registerHooks({load(url,context,next){
 const o=next(url,context);
 if(!url.includes('/relational-core.js?profile='))return o;
 const from='const camelRow = (row) =>\n  Object.fromEntries(Object.entries(row).map(([k, v]) => [camel(k), v]));';
 const memo='const renamed = new Map(); function convert(row){ const out=Object.create(null); for (const k of Object.keys(row)){let key=renamed.get(k); if(key===undefined){key=camel(k);renamed.set(k,key)} out[key]=row[k];} return out;}';
 const normal=from.replace('const camelRow','const convert');
 const name=url.endsWith('profile=memo')?memo:normal;
 const instrumented='\nfunction camelRow(row){ const t=performance.now(); try{return convert(row)} finally{globalThis.keyElapsed+=performance.now()-t;} }';
 const src=Buffer.from(o.source).toString();
 if(!src.includes(from))throw Error('Source mismatch');
 return {...o,source:src.replace(from,name+instrumented)};
}});
const db=await import(new URL('dashboard/backend/services/postgres.js',root));
const modes={};
for(const key of ['applied','memo'])modes[key]=await import(new URL('dashboard/backend/services/relational-core.js?profile='+key,root));
const run=async(mode)=>{
 globalThis.keyElapsed=0;
 const t=performance.now(), request=new Request(dense.url);
 const res=await modes[mode].partitionPage(request,new URL(request.url).searchParams);
 const bytes=Buffer.from(await res.arrayBuffer()),ms=performance.now()-t;
 const hash=createHash('sha256').update(bytes).digest('hex');
 if(hash!==dense.hash||res.status!==200)throw Error('Complete response mismatch');
 return {mode,ms,keyMs:globalThis.keyElapsed,bytes:bytes.length,hash};
};
const output={source:baseline.source,at:new Date().toISOString(),node:process.version,records:[]};
try{
 fields={}; [row]=await db.query(dense.statement.sql,dense.statement.values);
 if(row.source_digest!==dense.pagination.generation)throw Error('Publication changed');
 output.baselineFields=fields;
 const prefix='SELECT coalesce(json_agg(r)',start=dense.statement.sql.lastIndexOf(prefix,dense.statement.sql.indexOf('SELECT a.*,p.name'));
 const keys=Object.keys(row.appearances[0]); 
 if(!keys.every(k=>/^[a-z_][a-z0-9_]*$/.test(k))||keys.length>100)throw Error('Unexpected column names');
 const q=dense.statement.sql.slice(0,start)+dense.statement.sql.slice(start).replace('json_agg(r)', 'json_agg(json_build_array('+keys.map(k=>'r.'+k).join(',')+'))');
 if(q===dense.statement.sql)throw Error('Failed query substitution');
 fields={}; [changed]=await db.query(q,dense.statement.values);
 output.candidateFields=fields;output.appearanceKeys=keys;output.candidateSQL=q;output.candidateArgs=dense.statement.values;
 fields=null;
 const decoded=changed.appearances.map(a=>Object.fromEntries(keys.map((k,j)=>[k,a[j]])));
 if(!isDeepStrictEqual({...changed,appearances:decoded},row))throw Error('SQL field or order difference');
 const [exp]=await db.query('EXPLAIN (ANALYZE,BUFFERS,TIMING OFF,FORMAT JSON) '+q,dense.statement.values);
 output.candidatePlan=exp['QUERY PLAN'][0];
 pg.Client.prototype.query=async function(sql,...rest){
  if(sql!==dense.statement.sql)throw Error('Unexpected offline query');return {rows:[row]};
 };
 for(const mode of Object.keys(modes))await run(mode);
 for(let round=0;round<12;round++)for(const mode of round%2?['memo','applied']:['applied','memo'])output.records.push({round,...await run(mode)});
 const med=arr=>{const a=arr.toSorted((x,y)=>x-y);return (a[5]+a[6])/2};
 output.summary={};
 for(const mode of Object.keys(modes)){
  const r=output.records.filter(x=>x.mode===mode);output.summary[mode]={ms:med(r.map(x=>x.ms)),keyMs:med(r.map(x=>x.keyMs))};
 }
 row={...changed,appearances:decoded};output.arrayReplay=await run('applied');
 output.passed=true;
}catch(e){output.passed=false;output.error=String(e);process.exitCode=1;}
finally{
 pg.Client.prototype.query=savedQuery;writeFileSync(new URL('replay.json',folder),JSON.stringify(output,null,2)+'\n');
 console.log(JSON.stringify({passed:output.passed,error:output.error,summary:output.summary,sqlMs:output.candidatePlan?.['Execution Time']}));await db.closeDatabase();
}
