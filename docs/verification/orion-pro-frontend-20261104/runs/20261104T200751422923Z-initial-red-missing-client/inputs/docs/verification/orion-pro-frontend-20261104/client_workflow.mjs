import fs from 'node:fs';
import readline from 'node:readline';
const argument=name=>process.argv[process.argv.indexOf(name)+1];
const origin=argument('--origin'),evidence=argument('--evidence');
const {ProMatchClient,loadProManifest,createProMatchCache}=await import('../../../dashboard/frontend/src/services/pro-match-data.js');
const report={setup:'Actual owned-local Pro API and SQL publication fixture; no mocked football responses',cases:[],requests:[]};
let serial=0;
const fetcher=async(url,options={})=>{
 const id=`frontend-${++serial}`,response=await fetch(url,{...options,headers:{...options.headers,'x-e2e-id':id}});
 const body=await response.clone().text();
 report.requests.push({id,url,status:response.status,bytes:Buffer.byteLength(body),bodySha256:new Bun.CryptoHasher('sha256').update(body).digest('hex')});
 return response;
};
const assert=(ok,message)=>{if(!ok)throw Error(message);};
async function check(name,action){try{const actual=await action();report.cases.push({case:name,status:'pass',actual});}catch(error){report.cases.push({case:name,status:'fail',error:error.message});throw error;}}
const input=readline.createInterface({input:process.stdin});let resume;input.on('line',()=>resume?.());
try{
 const manifest=await loadProManifest(fetcher),make=(m,season,cache)=>new ProMatchClient({manifest:m,leagueId:'l_000001',season,fetcher,...(cache?{cache}:{})});
 const a=make(manifest,'2024/2025'),c=make(manifest,'2026/2027');let first,oldSummary,oldC;
 await check('manifest_edition_validation',async()=>{
  let rejected=false;try{make({...manifest,storage:'json-packed'},'2024/2025');}catch{rejected=true;}assert(rejected,'Legacy manifest must be rejected by explicit Pro client');
  return {token:a.representationToken};
 });
 await check('one_page_then_explicit_next',async()=>{
  const before=report.requests.length;first=await a.page({limit:2});assert(report.requests.length===before+1,'Must request exactly one page');
  assert(first.data.matches.length===2&&first.pagination.nextCursor,'Expected first two matches');
  const second=await a.page({limit:2,cursor:first.pagination.nextCursor});const ids=[...first.data.matches,...second.data.matches].map(x=>x.id);
  assert(JSON.stringify(ids)===JSON.stringify(['m_000001','m_000002','m_000003']),'Complete unique page traversal');
  assert(!report.requests.some(r=>r.url.includes('/shots')),'Shots requested before intent');return {ids,listRequests:2};
 });
 await check('summary_coalescing_and_cache_isolation',async()=>{
  const before=report.requests.length;const summaries=await Promise.all([a.summary('m_000001'),a.summary('m_000001'),a.summary('m_000001')]);
  assert(report.requests.length===before+1,'Concurrent summary must coalesce');oldSummary=structuredClone(summaries[0]);
  assert(oldSummary.summaryVersion===1&&oldSummary.representationToken===a.representationToken,'Summary token/version missing');
  summaries[0].home.name='caller mutation';assert((await a.summary('m_000001')).home.name===oldSummary.home.name,'Caller poisoned cache');
  oldC=await c.summary('m_000005');return {httpRequests:1,shotsBeforeIntent:0};
 });
 await check('lazy_shots_and_native_empty_unknown',async()=>{
  const shots=await a.shots('m_000001');assert(shots.collectionState==='present','Present collection state missing');
  assert(shots.periods[0].shots[0].expected_goals_on_target===0,'Native zero lost');
  const empty=await a.shots('m_000002');assert(empty.collectionState==='empty'&&empty.periods.length===0,'Explicit empty collection lost');
  let unavailable;try{await a.shots('m_000003');}catch(error){unavailable=error;}
  assert(unavailable?.status===404&&unavailable?.code==='NOT_COLLECTED','Unavailable must be an error, not empty');
  return {present:true,empty:true,unavailableStatus:unavailable.status};
 });
 await check('oversized_response_preserves_small_entry',async()=>{
  const cache=createProMatchCache({maxBytes:512,maxEntries:4}),bounded=make(manifest,'2024/2025',cache);
  const start=report.requests.length;await bounded.shots('m_000002');const small=report.requests.at(-1).bytes;
  await bounded.summary('m_000001');const large=report.requests.at(-1).bytes;
  await bounded.shots('m_000002');assert(small<=512&&large>512,'Fixture must straddle cache byte bound');
  assert(report.requests.length===start+2,'Oversized object evicted the small entry');return {smallBytes:small,largeBytes:large,budget:512};
 });
 console.log(JSON.stringify({event:'publish'}));await new Promise(resolve=>{resume=resolve;});resume=null;
 const corrected=await loadProManifest(fetcher),nextA=make(corrected,'2024/2025'),nextC=make(corrected,'2026/2027');
 await check('correction_keeps_frozen_and_independent_caches',async()=>{
  assert(nextA.representationToken!==a.representationToken,'Affected token did not change');
  assert(nextC.representationToken===c.representationToken,'Independent C token changed');
  const newSummary=await nextA.summary('m_000001');assert(newSummary.home.score===2&&newSummary.home.name==='Shared team corrected','New dataset/catalogue missing');
  const before=report.requests.length;assert(JSON.stringify(await a.summary('m_000001'))===JSON.stringify(oldSummary),'Old frozen summary changed');
  assert(JSON.stringify(await nextC.summary('m_000005'))===JSON.stringify(oldC),'Independent cache changed');
  assert(report.requests.length===before,'Frozen and independent data should reuse cache');return {affectedChanged:true,oldAndCExtraRequests:0};
 });
 await check('resource_keys_include_version',async()=>{
  assert(a.resourceKey('summary','m_000001')!==nextA.resourceKey('summary','m_000001'),'Versions share resource key');
  assert(c.resourceKey('summary','m_000005')===nextC.resourceKey('summary','m_000005'),'Same token has unstable resource key');return {distinctAffected:true,stableIndependent:true};
 });
 report.status='pass';
}catch(error){report.status='fail';report.error={type:error.name,message:error.message};}
finally{input.close();fs.writeFileSync(evidence+'/client-result.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({event:'done',status:report.status}));}
process.exitCode=report.status==='pass'?0:1;
