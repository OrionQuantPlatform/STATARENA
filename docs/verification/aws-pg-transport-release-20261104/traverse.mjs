import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync,writeFileSync} from 'node:fs';
const here=new URL('./',import.meta.url),api='https://d317dq37z1tacb.cloudfront.net';
process.env.NEXT_PUBLIC_API_ORIGIN=api;
const {loadSeason}=await import('../../../dashboard/frontend/src/season_data.js');
const previous=JSON.parse(readFileSync(new URL('../aws-wire-pages/after.json',here)));
const hash=obj=>createHash('sha256').update(JSON.stringify(obj,(_,v)=>v&&typeof v==='object'&&!Array.isArray(v)?Object.fromEntries(Object.entries(v).sort(([a],[b])=>a<b?-1:a>b?1:0)):v)).digest('hex');
const report={atUtc:new Date().toISOString(),rerun:'/tmp/statarena-node24-20261104 docs/verification/aws-pg-transport-release-20261104/traverse.mjs',setup:'Current deployed CloudFront→signed Lambda→RDS; actual production frontend season loader; complete traversal of both published partitions; prior canonical content hashes.',leagues:[],passed:false};
try{
 const manifest=await(await fetch(api+'/api/dashboard/manifest')).json();
 for(const before of previous.leagues){
  const rows=[];
  const trace=async(path,options)=>{
   const u=new URL(path,api);assert.equal(u.origin,api);assert.equal(u.pathname,'/api/seasons/partition');
   const response=await fetch(u,options),bytes=await response.clone().arrayBuffer();
   rows.push({status:response.status,format:u.searchParams.get('format'),limit:u.searchParams.get('limit'),decodedBytes:bytes.byteLength,etag:response.headers.get('etag'),cache:response.headers.get('cache-control')});
   assert.equal(response.status,200);return response;
  };
  const value=await loadSeason(manifest,'2026/2027',trace,new Set([before.league]));
  const digest=hash({...value,appearances:[...value.appearances].sort((a,b)=>a.matchId.localeCompare(b.matchId))});
  const actual={league:before.league,requests:rows,rowCounts:Object.fromEntries(['matches','fixtures','appearances','teams'].map(k=>[k,value[k].length])),digest,expectedDigest:before.digest};
  report.leagues.push(actual);assert.equal(digest,before.digest);assert.deepEqual(actual.rowCounts,before.rowCounts);
  assert.equal(rows.length,before.requests.length);assert.ok(rows.every(r=>r.format==='columns'&&r.limit==='100'&&r.cache==='no-store'&&r.decodedBytes<2097152));
 }
 report.passed=true;
}catch(e){report.error=e.stack;process.exitCode=1;}
finally{writeFileSync(new URL('traversal.json',here),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({passed:report.passed,leagues:report.leagues.map(x=>({league:x.league,requests:x.requests.length,counts:x.rowCounts,match:x.digest===x.expectedDigest})),error:report.error}));}
