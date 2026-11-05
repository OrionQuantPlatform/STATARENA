// Owned loopback actual AWS router; Node24 native HTTP, no external transports.
import { createServer } from 'node:http';
import { AsyncLocalStorage } from 'node:async_hooks';
import pg from '../../../dashboard/node_modules/pg/lib/index.js';
import { query, closeDatabase } from '../../../dashboard/backend/services/postgres.js';
import { handleRequest } from '../../../dashboard/backend/aws-app.js';
const contexts = new AsyncLocalStorage(), traces=[];
let externalAttempts=0;
const original=pg.Client.prototype.query;
pg.Client.prototype.query=function(...args){
 const ctx=contexts.getStore();
 const entry=ctx?{sql:typeof args[0]==='string'?args[0]:args[0]?.text,values:Array.isArray(args[1])?args[1]:[]}:null;
 if(entry)ctx.sql.push(entry);
 const result=original.apply(this,args);
 return result?.then?result.then(v=>v,e=>{if(entry)entry.error=e.code||e.name;throw e;}):result;
};
globalThis.fetch=async()=>{externalAttempts++;throw Error('External HTTP forbidden');};
const identity=await query("SELECT current_user AS role,current_setting('transaction_read_only') AS readonly,current_setting('statement_timeout') AS statement,current_setting('lock_timeout') AS lock");
const server=createServer(async(req,res)=>{
 try{
 const u=new URL(req.url,'http://127.0.0.1');
 if(u.pathname==='/__e2e__/traces'){res.setHeader('Content-Type','application/json');res.end(JSON.stringify({traces,externalAttempts}));return;}
 if(u.pathname==='/__e2e__/media-origin'){process.env.STATARENA_CLOUDFRONT_URL=u.searchParams.get('value');res.end('{}');return;}
 const ctx={id:req.headers['x-e2e-id'],method:req.method,path:u.pathname+u.search,sql:[]};
 await contexts.run(ctx,async()=>{
 const response=await handleRequest(new Request(u,{method:req.method,headers:req.headers}));
 ctx.status=response.status;traces.push(ctx);res.writeHead(response.status,Object.fromEntries(response.headers));
 res.end(Buffer.from(await response.arrayBuffer()));
 });
 }catch(e){res.writeHead(500);res.end('Test server: '+e.name);}
});
server.listen(0,'127.0.0.1',()=>console.log(JSON.stringify({event:'ready',port:server.address().port,identity,node:process.version,arch:process.arch,platform:process.platform})));
async function stop(){server.closeAllConnections();await new Promise(r=>server.close(r));await closeDatabase();process.exit(0);}
process.on('SIGTERM',stop);process.on('SIGINT',stop);
