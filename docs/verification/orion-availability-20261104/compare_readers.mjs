// End-to-end semantic comparison on an isolated, disposable PostgreSQL database.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { cp, mkdir, mkdtemp, readFile, rm, symlink, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = resolve(fileURLToPath(new URL("../../../", import.meta.url)));
const out = resolve(root, "docs/verification/orion-availability-20261104");
const stamp = new Date().toISOString().replace(/[-:.]/g, "");
const command = "STATARENA_TEST_TOOLS=/tmp/statarena-cache-test-tools STATARENA_TEST_PYTHONPATH=/tmp/statarena-publication-test-python bun docs/verification/orion-availability-20261104/compare_readers.mjs";
const report = { command, atUtc: new Date().toISOString(),
  setup: "Real local disposable PostgreSQL18; synthetic publisher fixture; exact deployed b2ec973d reader and current uncommitted candidate loaded in separate copied backends against one database. Local fixture writes only; no cloud/provider calls.",
  expected: "The readers produce semantically equal JSON, pagination and validators for consistent partitions and both wire formats, including native scalars, zero/null/reserved metrics, schema fallback, and both pages. An intentionally inconsistent appearance retains the same membership as the deployed reader.", checks: [], passed: false };
const tmp = await mkdtemp(join(tmpdir(), "statarena-reader-pair-"));
const tools = process.env.STATARENA_TEST_TOOLS || "/tmp/statarena-cache-test-tools";
const { default: Postgres } = await import(pathToFileURL(join(tools, "node_modules/embedded-postgres/dist/index.js")));
const socket = Bun.listen({hostname:"127.0.0.1", port:0, socket:{data(){}}});
const port = socket.port; socket.stop(true);
const pg = new Postgres({databaseDir:join(tmp,"db"),user:"fixture",password:"local-only",port,persistent:false,autoRehydrateSymlinks:true,onLog(){},onError(){}});
let writer, servers = [], modules = [], restoreQuery;
const capturedSql = {};
const sha = (text) => createHash("sha256").update(text).digest("hex");
try {
  const baseline = execFileSync("git", ["show", "b2ec973d2d4aa9b25f66b58c32c9806d13e23a51:dashboard/backend/services/relational-core.js"], {cwd:root, encoding:"utf8"});
  const candidate = await readFile(join(root,"dashboard/backend/services/relational-core.js"), "utf8");
  report.source = { baselineCommit: "b2ec973d2d4aa9b25f66b58c32c9806d13e23a51", baselineSha256:sha(baseline), candidateSha256:sha(candidate) };
  assert.notEqual(report.source.baselineSha256, report.source.candidateSha256);
  await pg.initialise(); await pg.start(); await pg.createDatabase("relational_core_e2e");
  const dburl = `postgresql://fixture:local-only@127.0.0.1:${port}/relational_core_e2e`;
  const seed = Bun.spawnSync(["python3","docs/verification/aws-relational-core-20261104/workflow.py","--report",join(out,`compare-seed-${stamp}.json`)], {
    cwd:root, env:{...process.env, TEST_DATABASE_URL:dburl, PYTHONPATH:process.env.STATARENA_TEST_PYTHONPATH || "/tmp/statarena-publication-test-python", STATARENA_E2E_COMMAND:command}});
  await writeFile(join(out,`compare-seed-${stamp}.log`), seed.stdout.toString()+"\n"+seed.stderr.toString());
  assert.equal(seed.exitCode, 0, "Seed workflow failed");
  Object.assign(process.env, {DATABASE_URL:dburl+"?sslmode=disable", STATARENA_TEST_DATABASE:"1", STATARENA_DATA_PROVIDER:"aws", STATARENA_METRICS_SAMPLE_RATE:"0"});
  for (const [name, source] of [["baseline",baseline],["candidate",candidate]]) {
    const dashboard = join(tmp,name,"dashboard");
    await mkdir(dashboard,{recursive:true});
    await cp(join(root,"dashboard/backend"),join(dashboard,"backend"),{recursive:true});
    await writeFile(join(dashboard,"backend/services/relational-core.js"),source);
    await writeFile(join(dashboard,"package.json"),'{"type":"module"}\n');
    await symlink(join(root,"dashboard/node_modules"),join(dashboard,"node_modules"));
    const app = await import(pathToFileURL(join(dashboard,"backend/aws-app.js")));
    const db = await import(pathToFileURL(join(dashboard,"backend/services/postgres.js")));
    modules.push(db);
    servers.push(Bun.serve({hostname:"127.0.0.1",port:0,fetch:app.handleRequest}));
  }
  const { createRequire } = await import("node:module");
  const { Client } = createRequire(pathToFileURL(join(root,"dashboard/package.json")))("pg");
  const originalQuery = Client.prototype.query;
  Client.prototype.query = function(sql,...args) {
    if (typeof sql === "string" && sql.startsWith("WITH candidates AS") && Array.isArray(args[0]) && args[0][2] === 100 && args[0].length === 3) {
      const name = sql.includes("page_appearances AS MATERIALIZED") ? "candidate" : "baseline";
      capturedSql[name] ||= {sql, sha256:sha(sql), fixtureBinds:args[0]};
    }
    return originalQuery.call(this,sql,...args);
  };
  restoreQuery = () => { Client.prototype.query=originalQuery; };
  writer = new Client({connectionString:dburl}); await writer.connect();
  await writer.query(`INSERT INTO statarena_app.appearance_metrics(appearance_id,metric_key,value)
     SELECT id, k.key, CASE WHEN k.key='explicitNull' THEN NULL WHEN match_id='m_000001' THEN 0 ELSE 2 END
     FROM statarena_app.appearances CROSS JOIN (VALUES ('__proto__'),('constructor'),('explicitNull')) k(key)
     WHERE league_id='l_000001' ON CONFLICT (appearance_id,metric_key) DO UPDATE SET value=excluded.value`);
  const { decodePartition } = await import(pathToFileURL(join(root,"dashboard/frontend/src/season_data.js")));
  const base = "/api/seasons/partition?season=2026%2F2027&league=l_000001";
  async function get(server,path,headers={}) {
    const r = await fetch(new URL(path,server.url),{headers});
    const body = await r.text();
    return {status:r.status,etag:r.headers.get("etag"),body:body ? JSON.parse(body):null};
  }
  async function compare(label,path,options={}) {
    const a = await get(servers[0],path), b = await get(servers[1],path);
    assert.equal(a.status,200,label+" baseline status"); assert.equal(b.status,200,label+" candidate status");
    assert.equal(a.etag,b.etag,label+" ETag");
    if (options.columns) { a.body.data=decodePartition(a.body.data); b.body.data=decodePartition(b.body.data); }
    assert.deepEqual(b.body,a.body,label+" semantic body and pagination");
    report.checks.push({name:label,passed:true,appearanceCount:a.body.data.appearances.length,etagEqual:true,
      nextCursorPresent:Boolean(a.body.pagination.nextCursor)});
    return a.body.pagination.nextCursor;
  }
  const cursor = await compare("first page, native JSON",base+"&limit=1");
  assert.ok(cursor,"Expected second page");
  await compare("second page, native JSON",base+"&limit=1&cursor="+encodeURIComponent(cursor));
  await compare("complete fixture page, native JSON",base+"&limit=100");
  await compare("complete fixture page, decoded compact wire",base+"&limit=100&format=columns",{columns:true});
  await compare("other league remains isolated",base.replace("l_000001","l_100001")+"&limit=100");
  const first = await get(servers[0],base+"&limit=100");
  for (const server of servers) { const conditional=await get(server,base+"&limit=100",{"If-None-Match":first.etag}); assert.equal(conditional.status,304); assert.equal(conditional.body,null); }
  report.checks.push({name:"conditional GET",passed:true,status:304});
  await writer.query("ALTER TABLE statarena_app.appearances ADD COLUMN fixture_future_metric integer");
  await writer.query("UPDATE statarena_app.appearances SET fixture_future_metric=0 WHERE match_id='m_000001'");
  await compare("future schema named-record fallback",base+"&limit=100");
  await writer.query("ALTER TABLE statarena_app.appearances DROP COLUMN fixture_future_metric");
  await writer.query("UPDATE statarena_app.appearances SET season='2025/2026' WHERE match_id='m_000001'");
  const old = await get(servers[0],base+"&limit=100"), newer = await get(servers[1],base+"&limit=100");
  assert.equal(old.status,200); assert.equal(newer.status,200);
  const before = old.body.data.appearances.length, after = newer.body.data.appearances.length;
  assert.equal(before,2); assert.equal(after,2,"Candidate silently omitted an appearance with mismatched season");
  assert.deepEqual(newer.body,old.body,"Inconsistent-partition response changed");
  report.checks.push({name:"appearance with mismatched season retains deployed membership",passed:true,baselineAppearances:before,candidateAppearances:after});
  assert.ok(capturedSql.baseline && capturedSql.candidate,"Did not capture both exact handler statements");
  report.capturedSql = {baselineSha256:capturedSql.baseline.sha256,candidateSha256:capturedSql.candidate.sha256};
  report.passed = true;
} catch (e) {
  report.error = String(e?.stack || e);
} finally {
  for (const s of servers) s.stop(true);
  restoreQuery?.();
  for (const m of modules) await m.closeDatabase();
  if (writer) await writer.end();
  try { await pg.stop(); } catch (e) { report.cleanupError=String(e); report.passed=false; }
  await rm(tmp,{recursive:true,force:true});
  await writeFile(join(out,`reader-sql-${stamp}.json`),JSON.stringify(capturedSql,null,2)+"\n");
  await writeFile(join(out,`reader-comparison-${stamp}.json`),JSON.stringify(report,null,2)+"\n");
  console.log(JSON.stringify({passed:report.passed,error:report.error,checks:report.checks}));
}
process.exitCode = report.passed ? 0 : 1;
