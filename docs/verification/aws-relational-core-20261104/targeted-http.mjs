import {mkdir,writeFile} from 'node:fs/promises';
import {FootballDataClient} from '../../../dashboard/frontend/src/services/football-client.js';
const out=process.argv[2]; if(!out)throw Error('evidence directory required');await mkdir(out,{recursive:true});
let status=200;const requests=[];
const server=Bun.serve({hostname:'127.0.0.1',port:0,fetch(req){const p=new URL(req.url).pathname;requests.push(p);if(p==='/api/status')return Response.json({configured:true});if(p.endsWith('/shots'))return Response.json(status===200?{data:{periods:[]}}:{error:{code:'ANALYTICS_UNAVAILABLE',message:'Stored unavailable'}},{status});return new Response('No archive fixture',{status:404});}});
const original=globalThis.fetch;globalThis.fetch=(url,init)=>original(new URL(url,`http://127.0.0.1:${server.port}`),init);
const report={setup:'Actual FootballDataClient + real loopback HTTP; exact targeted/aggregate path counts; no provider or production access.',command:`bun docs/verification/aws-relational-core-20261104/targeted-http.mjs ${out}`,expected:'Successful and deterministic missing selected-family requests make exactly one targeted HTTP call and zero aggregate-archive calls.',cases:[],status:'failed'};
try{for(const responseStatus of[200,404]){status=responseStatus;requests.length=0;const c=new FootballDataClient({data:{competitions:[],meta:{}}});await c.checkStatus();requests.length=0;await c.ensureEndpoint({id:'m_QA0001'},'shots');const actual=[...requests],passed=actual.length===1&&actual[0]==='/api/pitchapi/matches/m_QA0001/shots';report.cases.push({status:responseStatus,passed,requests:actual,payload:c.payloads.get('m_QA0001:shots')});}report.status=report.cases.every(c=>c.passed)?'passed':'failed';}
finally{globalThis.fetch=original;server.stop(true);await writeFile(`${out}/results.json`,JSON.stringify(report,null,2)+'\n');}
console.log(JSON.stringify(report));process.exitCode=report.status==='passed'?0:1;
