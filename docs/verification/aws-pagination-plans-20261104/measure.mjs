import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {createRequire,registerHooks} from 'node:module';
import {readFileSync,writeFileSync} from 'node:fs';

const folder=new URL('./',import.meta.url), root=new URL('../../../',folder);
const require=createRequire(new URL('dashboard/package.json',root));
const caps=JSON.parse(JSON.parse(execFileSync('aws',['--profile','statarena','--region','us-east-2','ssm','get-parameter','--name','/statarena/app/rds-runtime','--with-decryption','--output','json'],{encoding:'utf8'})).Parameter.Value);
if(caps.host!=='statarena-postgres.clcy2iqyajbl.us-east-2.rds.amazonaws.com'||caps.database!=='statarena_prod')throw Error('Wrong database');
const url=new URL('postgresql://'+caps.host+'/'+caps.database);
url.username=caps.username;url.password=caps.password;
Object.assign(process.env,{DATABASE_URL:url.href,STATARENA_DATA_PROVIDER:'aws',STATARENA_METRICS_SAMPLE_RATE:'1',STATARENA_SERVER_TIMING:'1'});
const pg=require('pg'), hash=b=>createHash('sha256').update(b).digest('hex');
let obs,statement;
const requirePg=createRequire(require.resolve('pg')), Result=requirePg('./result.js');
const parse=Result.prototype.parseRow;
Result.prototype.parseRow=function(fields){
  if(!obs)return parse.call(this,fields);
  const t=performance.now(), result=parse.call(this,fields); obs.parseMs+=performance.now()-t;
  if(fields.length>1)for(let i=0;i<fields.length;i++){
    const val=fields[i],name=this.fields[i].name;
    obs.fieldBytes[name]=(obs.fieldBytes[name]||0)+(val==null?0:Buffer.byteLength(val));
  }
  return result;
};
const original=pg.Client.prototype.query;
pg.Client.prototype.query=function(sql,...rest){
  if(obs && typeof sql==='string')statement={sql,values:rest[0]};
  return original.call(this,sql,...rest);
};
registerHooks({load(url,context,next){
  const r=next(url,context);
  if(url.endsWith('/services/partition-wire.js')){
    const src=Buffer.from(r.source).toString().replace('export function packPartition(', 'function originalPack(');
    return {...r,source:src+'\nexport function packPartition(value){const t=performance.now();try{return originalPack(value)}finally{globalThis.measurePack(performance.now()-t)}}\n'};
  }
  return r;
}});
globalThis.measurePack=ms=>{obs.packMs+=ms};
const database=await import(new URL('dashboard/backend/services/postgres.js',root));
const app=await import(new URL('dashboard/backend/aws-app.js',root));
const output={when:new Date().toISOString(),source:execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),runtime:process.version,routes:[]};
const save=()=>writeFileSync(new URL('measurements.json',folder),JSON.stringify(output,null,2)+'\n');
const logger=console.log;
console.log=(...args)=>{if(obs && typeof args[0]==='string' && args[0].includes('"event":"statarena.request"')) obs.internal=JSON.parse(args[0]);else logger(...args)};
try{
  [output.identity]=await database.query("SELECT current_database() db,current_setting('transaction_read_only') read_only,current_setting('statement_timeout') timeout");
  if(output.identity.read_only!=='on') throw Error('write connection');
  let cursor,partitionVersion,ids=[];
  for(const [label,path] of [['dense100','/api/seasons/partition'],['dense50','/api/seasons/partition'],['fixturesFirst','/api/fixtures'],['fixturesNext','/api/fixtures']]){
    const query=new URLSearchParams({season:'2026/2027',league:'l_0ALvwF',limit:label==='dense100'?'100':'50'});
    if(label.startsWith('dense'))query.set('format','columns');
    if(label==='fixturesNext')query.set('cursor',cursor);
    const request=new Request('https://d317dq37z1tacb.cloudfront.net'+path+'?'+query);
    const record={label,url:request.url,fieldBytes:{},parseMs:0,packMs:0};
    output.routes.push(record);
    obs=record;statement=null;
    const response=await app.handleRequest(request);
    obs=null;
    const bytes=Buffer.from(await response.arrayBuffer()),body=JSON.parse(bytes);
    Object.assign(record,{status:response.status,bytes:bytes.length,hash:hash(bytes),etag:response.headers.get('etag'),pagination:body.pagination,statement});
    if(response.status!==200)throw Error(label+' '+response.status+' '+JSON.stringify(body.error));
    if(label==='dense100'){
      if(record.hash!=='0d6bbe72588aa8df43b6d7933093a9d9cd8f028a1b53d61fc8c68bdc37f7d403')throw Error('dense-100 changed');
      partitionVersion=body.pagination.generation;
    }
    if(label==='dense50' && partitionVersion!==body.pagination.generation) throw Error('Partition changed');
    if(label.startsWith('fixtures')){
      const found=body.data.matches.map(m=>m.id);
      if(!body.pagination.nextCursor||found.length!==50||found.some(i=>ids.includes(i)))throw Error('fixture page continuity');
      ids.push(...found); cursor=body.pagination.nextCursor;
      if(new Set(ids).size!==ids.length)throw Error('duplicate fixtures');
      record.fixtureEndpoints=[found[0],found.at(-1)];
    }
    const [res]=await database.query('EXPLAIN (ANALYZE,BUFFERS,TIMING OFF,FORMAT JSON) '+statement.sql,statement.values);
    record.plan=res['QUERY PLAN'][0];
    save(); logger(label,record.plan['Execution Time'],record.bytes,record.internal?.metrics?.sql_ms);
  }
  output.passed=true;
}catch(e){output.passed=false;output.error=String(e);process.exitCode=1}
finally{save();await database.closeDatabase();}
