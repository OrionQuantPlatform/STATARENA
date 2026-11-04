// Exact runtime body SQL on real RDS, measured server-side independently of CDN/TLS.
import { execFileSync } from "node:child_process";
import { createRequire } from "node:module";
import { createHash } from "node:crypto";
import { writeFile } from "node:fs/promises";
const root = new URL("../../../", import.meta.url);
const phase = process.argv[2];
if (!/^[a-z0-9-]+$/.test(phase || "")) throw Error("Supply a receipt phase");
const c = JSON.parse(JSON.parse(execFileSync("aws", ["--profile", "statarena", "--region", "us-east-2", "ssm", "get-parameter", "--name", "/statarena/app/rds-runtime", "--with-decryption", "--output", "json"], {encoding:"utf8", stdio:["ignore","pipe","pipe"]})).Parameter.Value);
if(c.host!=="statarena-postgres.clcy2iqyajbl.us-east-2.rds.amazonaws.com" || c.database!=="statarena_prod") throw Error("Unexpected target");
const url = new URL("postgresql://" + c.host + "/" + c.database);
url.username=c.username;url.password=c.password;
Object.assign(process.env,{DATABASE_URL:url.href,STATARENA_DATA_PROVIDER:"aws",DATABASE_POOL_MAX:"1",STATARENA_METRICS_SAMPLE_RATE:"0"});
const {Client}=createRequire(new URL("dashboard/package.json",root))("pg");
const original=Client.prototype.query;
let captured;
Client.prototype.query=function(sql,...rest){
  if(typeof sql==="string" && /\sAS body\b/i.test(sql) && !sql.startsWith("EXPLAIN")) captured={sql,values:rest[0]};
  return original.call(this,sql,...rest);
};
const pg=await import(new URL("dashboard/backend/services/postgres.js",root));
const match=await import(new URL("dashboard/backend/services/relational-match.js",root));
const report={phase,at:new Date().toISOString(),command:`bun docs/verification/aws-live-performance-20261104/body-query.mjs ${phase}`,setup:"Same actual runtime SELECT statements, verified Ohio RDS TLS, read-only startup; 5 server EXPLAIN ANALYZE repetitions after one representation load per route; no writes",routes:[]};
try{
 const [identity]=await pg.query("SELECT current_database() AS database,current_setting('transaction_read_only') AS read_only");
 if(identity.database!=="statarena_prod" || identity.read_only!=="on") throw Error("Read-only identity mismatch");
 report.identity=identity;
 const [schema]=await pg.query("SELECT array_agg(version ORDER BY version) AS versions FROM statarena_app.worker_schema");report.schema=schema;
 const mid="m_02vUAH";
 for(const [label,read] of [["archive",()=>match.relationalMatchObservation(mid,{withMeta:true})],["players",()=>match.relationalResource(`/matches/${mid}/players`,{},{withMeta:true})],["halves",()=>match.relationalResource(`/matches/${mid}/players/halves`,{},{withMeta:true})]]){
  captured=undefined;
  const value=await read();
  if(!value || !captured) throw Error("Missing actual body SQL");
  const body=JSON.stringify(value.value), plans=[];
  const statement={...captured};
  for(let i=0;i<5;i++){
   const [row]=await pg.query("EXPLAIN (ANALYZE,BUFFERS,TIMING OFF,FORMAT JSON) "+statement.sql,statement.values);
   plans.push(row["QUERY PLAN"][0]);
  }
  const times=plans.map(p=>p["Execution Time"]).sort((a,b)=>a-b);
  report.routes.push({label,match:mid,etag:value.etag,bodyBytes:Buffer.byteLength(body),bodySha256:createHash("sha256").update(body).digest("hex"),sql:statement,executionMs:times,medianMs:times[2],plans});
 }
 report.passed=true;
}catch(error){report.passed=false;report.error={name:error.name,code:error.code};}
finally{
 Client.prototype.query=original;
 await pg.closeDatabase();
 await writeFile(new URL(`body-query-${phase}.json`,import.meta.url),JSON.stringify(report,null,2)+"\n");
}
console.log(JSON.stringify({phase,passed:report.passed,routes:report.routes.map(r=>({label:r.label,medianMs:r.medianMs,bytes:r.bodyBytes}))}));
if(!report.passed)process.exitCode=1;
