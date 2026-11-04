import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { readFile, writeFile, mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
const base = import.meta.dir,
  root = path.resolve(base, "../../.."),
  phase = process.argv[2];
assert.match(phase || "", /^(before|after|replay)$/);
const { Client } = createRequire(path.join(root, "dashboard/package.json"))(
  "pg",
);
const { default: PG } = await import(
  path.join(
    process.env.STATARENA_TEST_TOOLS || "/tmp/statarena-cache-test-tools",
    "node_modules/embedded-postgres/dist/index.js",
  )
);
const scratch = await mkdtemp(path.join(tmpdir(), "conditionally-")),
  listener = Bun.listen({
    hostname: "127.0.0.1",
    port: 0,
    socket: { data() {} },
  }),
  port = listener.port;
listener.stop(true);
const db = new PG({
  databaseDir: scratch,
  user: "fixture",
  password: "fixture",
  port,
  persistent: false,
  autoRehydrateSymlinks: true,
  onLog() {},
  onError() {},
});
const result = {
  command: "bun docs/verification/aws-conditional-20261104/verify.mjs " + phase,
  setup:
    "PROTOCOL.md; actual 004/006 DDL and local HTTP; isolated writer commits",
  cases: [],
};
let admin,
  http,
  forward,
  close,
  pause,
  queries = [],
  sent,
  reports = [],
  query = Client.prototype.query;
try {
  await db.initialise();
  await db.start();
  const url = "postgresql://fixture:fixture@127.0.0.1:" + port + "/postgres";
  admin = new Client({ connectionString: url });
  await admin.connect();
  result.pg = (await admin.query("show server_version")).rows[0].server_version;
  for (const file of [
    "004_match_details.sql",
    "006_catalog_models.sql",
    "007_match_source_fields.sql",
    "008_match_player_position.sql",
  ])
    await admin.query(
      await readFile(
        path.join(root, "dashboard/backend/migrations", file),
        "utf8",
      ),
    );
  Object.assign(process.env, {
    DATABASE_URL: url + "?sslmode=disable",
    STATARENA_TEST_DATABASE: "1",
    STATARENA_DATA_PROVIDER: "aws",
    STATARENA_METRICS_SAMPLE_RATE: "0",
  });
  const tag = (c) => 'W/"match-v1-' + c.repeat(64) + '"';
  for (let i = 1; i <= 7; i++) {
    const mid = "m_00000" + i;
    await admin.query(
      "INSERT INTO statarena_app.match_details(match_id) VALUES($1)",
      [mid],
    );
    const res = await admin.query(
      "INSERT INTO statarena_app.match_families(match_id,family,params,subject_id,status,has_data,has_error,error_object,error_code,error_message,error_has_code,error_has_message,source_digest) VALUES ($1,'match','{}','',$2,$3,$4,$4,'NO_ACCESS','Saved error',$4,$4,repeat('a',64)) RETURNING resource_id",
      [mid, i === 4 ? 404 : 200, i !== 4, i === 4],
    );
    await admin.query(
      "INSERT INTO statarena_app.match_summaries(resource_id,record_no,missing,null_groups,id,status) VALUES($1,0,'{}','{}',$2,'finished')",
      [res.rows[0].resource_id, mid],
    );
  }
  const cat = (
    await admin.query(
      "INSERT INTO statarena_app.catalog_editions(catalog,scope,edition,model,response_status,source_digest) VALUES('matchdays','l_000001','2026','matchdays',200,repeat('b',64)) RETURNING resource_id",
    )
  ).rows[0];
  await admin.query(
    "INSERT INTO statarena_app.cat_matchdays VALUES($1,0,'{}','{}')",
    [cat.resource_id],
  );
  const { handleRequest } =
    await import("../../../dashboard/backend/aws-app.js");
  ({ closeDatabase: close } =
    await import("../../../dashboard/backend/services/postgres.js"));
  http = Bun.serve({
    port: 0,
    hostname: "127.0.0.1",
    fetch: (req) => {
      sent = req.headers.get("if-none-match");
      return handleRequest(req);
    },
  });
  process.env.ORION_API_ORIGIN = "http://127.0.0.1:" + http.port;
  const { proxy } =
    await import("../../../dashboard/frontend/src/server/bun-proxy.js");
  forward = Bun.serve({ port: 0, hostname: "127.0.0.1", fetch: proxy });
  Client.prototype.query = function (sql, ...args) {
    const ret = query.call(this, sql, ...args);
    if (this === admin || typeof sql !== "string" || !ret?.then) return ret;
    const type =
      sql.includes("AS version FROM statarena_app.match_families") ||
      sql.includes("AS version FROM statarena_app.catalog_editions")
        ? "meta"
        : "body";
    queries.push(type);
    return ret.then(async (r) => {
      if (type === "meta" && pause) await pause();
      return r;
    });
  };
  const match = (i) => "/api/pitchapi/matches/m_00000" + i,
    catalog = "/api/matchdays?competition=l_000001&season=2026";
  async function get(route, { method = "GET", etag, proxy = false } = {}) {
    queries = [];
    const res = await fetch(
      "http://127.0.0.1:" + (proxy ? forward : http).port + route,
      { method, headers: etag ? { "if-none-match": etag } : {} },
    );
    const body = await res.text();
    const r = {
      route,
      method,
      sent,
      sql: [...queries],
      status: res.status,
      etag: res.headers.get("etag"),
      cache: res.headers.get("cache-control"),
      body,
    };
    reports.push(r);
    return r;
  }
  async function check(name, fn) {
    reports = [];
    try {
      await fn();
      result.cases.push({ name, passed: true, requests: reports });
    } catch (e) {
      result.cases.push({
        name,
        passed: false,
        reason: e.message,
        requests: reports,
      });
    } finally {
      pause = null;
    }
  }
  const old = '"old"',
    n = (r, len) => assert.equal(r.sql.length, len),
    ok = (r) => assert.equal(r.status, 200);
  let catTag;
  await check("cold match stale conditional", async () => {
    const r = await get(match(1), { etag: old });
    ok(r);
    assert.equal(JSON.parse(r.body).data.status, "finished");
    assert.equal(r.etag, tag("a"));
    n(r, 2);
  });
  await check("cold catalog stale conditional", async () => {
    const r = await get(catalog, { etag: old });
    ok(r);
    catTag = r.etag;
    assert.ok(JSON.parse(r.body));
    n(r, 2);
  });
  await check("warm catalog and match stale conditionals", async () => {
    for (const route of [catalog, match(1)]) {
      const r = await get(route, { etag: old });
      ok(r);
      assert.ok(r.body);
      n(r, 1);
    }
  });
  await check("weak list and HEAD", async () => {
    for (const [route, etag] of [
      [match(1), tag("a")],
      [catalog, catTag],
    ])
      for (const method of ["GET", "HEAD"]) {
        const r = await get(route, {
          method,
          etag: method === "GET" ? old + ", " + etag.replace(/^W\//, "") : null,
        });
        assert.equal(r.status, method === "GET" ? 304 : 200);
        assert.equal(r.body, "");
        n(r, 1);
      }
  });
  async function change(i, c) {
    await admin.query(
      "WITH h AS (UPDATE statarena_app.match_families SET source_digest=repeat($2,64) WHERE match_id=$1 RETURNING resource_id) UPDATE statarena_app.match_summaries SET status=$2 FROM h WHERE match_summaries.resource_id=h.resource_id",
      ["m_00000" + i, c],
    );
  }
  await check("committed change between SELECTs", async () => {
    pause = async () => {
      pause = null;
      await change(2, "b");
    };
    const r = await get(match(2), { etag: old });
    ok(r);
    assert.equal(r.etag, tag("b"));
    assert.equal(JSON.parse(r.body).data.status, "b");
    assert.ok(r.sql.length <= 4);
  });
  await check("concurrent catalog delete", async () => {
    await admin.query(
      "UPDATE statarena_app.catalog_editions SET source_digest=repeat('c',64)",
    );
    pause = async () => {
      pause = null;
      await admin.query("DELETE FROM statarena_app.catalog_editions");
    };
    const r = await get(catalog, { etag: old });
    assert.equal(r.status, 404);
    assert.equal(r.etag, null);
    assert.ok(r.sql.length <= 3);
  });
  await check("persistent publication churn", async () => {
    let c = 0;
    pause = () => change(3, (++c).toString());
    const r = await get(match(3), { etag: old });
    assert.equal(r.status, 503);
    assert.equal(r.etag, null);
    assert.equal(r.cache, "no-store");
    assert.ok(r.sql.length <= 4);
  });
  await check("wildcard on saved error preserves source error", async () => {
    const r = await get(match(4), { etag: "*" });
    assert.equal(r.status, 404);
    assert.equal(JSON.parse(r.body)?.error?.message, "Saved error");
    assert.equal(r.cache, "no-store");
    n(r, 2);
  });
  await check("missing match", async () => {
    const r = await get(match(9), { etag: "*" });
    assert.equal(r.status, 404);
    n(r, 1);
  });
  await check("proxy absent conditional stays absent", async () => {
    const r = await get(match(5), { proxy: true });
    ok(r);
    assert.equal(r.sent, null);
    n(r, 2);
  });
  await check("proxy forwards real validator", async () => {
    const r = await get(match(5), { proxy: true, etag: tag("a") });
    assert.equal(r.status, 304);
    assert.equal(r.sent, tag("a"));
    n(r, 1);
  });
} catch (e) {
  result.failure = e.stack;
} finally {
  Client.prototype.query = query;
  http?.stop(true);
  forward?.stop(true);
  if (close) await close();
  if (admin) await admin.end();
  await db.stop();
  await rm(scratch, { recursive: true, force: true });
  result.passed = result.cases.filter((c) => c.passed).length;
  result.total = result.cases.length;
  await writeFile(
    path.join(base, phase + ".json"),
    JSON.stringify(result, null, 2) + "\n",
  );
  console.log(
    result.passed + "/" + result.total,
    result.failure || "",
    result.cases.filter((x) => !x.passed).map((x) => [x.name, x.reason]),
  );
  process.exitCode = !result.failure && result.passed === 11 ? 0 : 1;
}
