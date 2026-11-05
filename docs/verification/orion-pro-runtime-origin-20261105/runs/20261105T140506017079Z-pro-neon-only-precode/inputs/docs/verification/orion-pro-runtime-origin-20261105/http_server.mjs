import { createServer } from 'node:http';
import { AsyncLocalStorage } from 'node:async_hooks';
import pg from '../../../dashboard/node_modules/pg/lib/index.js';
import { closeDatabase } from '../../../dashboard/backend/services/postgres.js';
import { handleRequest } from '../../../dashboard/backend/aws-app.js';
const contexts=new AsyncLocalStorage(),traces=[];
let driverAttempts=0,externalAttempts=0;
pg.Client.prototype.connect=function(){driverAttempts++;throw Error('Database driver forbidden in unconfigured-origin E2E');};
const original=pg.Client.prototype.query;
pg.Client.prototype.query=function(...args){const ctx=contexts.getStore();if(ctx)ctx.sql.push(typeof args[0]==='string'?args[0]:args[0]?.text);return original.apply(this,args);};
globalThis.fetch=async()=>{externalAttempts++;throw Error('External transport forbidden');};
const server=createServer(async(req,res)=>{
 const u=new URL(req.url,'http://127.0.0.1');
 if(u.pathname==='/__e2e__/traces'){res.setHeader('Content-Type','application/json');res.end(JSON.stringify({traces,driverAttempts,externalAttempts,node:process.version}));return;}
 const ctx={id:req.headers['x-e2e-id'],sql:[]};
 await contexts.run(ctx,async()=>{const r=await handleRequest(new Request(u,{method:req.method,headers:req.headers}));ctx.status=r.status;traces.push(ctx);res.writeHead(r.status,Object.fromEntries(r.headers));res.end(Buffer.from(await r.arrayBuffer()));});
});
server.listen(0,'127.0.0.1',()=>console.log(JSON.stringify({event:'ready',port:server.address().port,node:process.version})));
async function stop(){server.closeAllConnections();await new Promise(r=>server.close(r));await closeDatabase();process.exit(0);}
process.on('SIGTERM',stop);process.on('SIGINT',stop);
