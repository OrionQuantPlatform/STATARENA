import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { createHash } from "node:crypto";
import { gzipSync } from "node:zlib";
import assert from "node:assert/strict";
const dir = new URL("./", import.meta.url),
  root = new URL("../../../", dir),
  phase = process.argv[2];
if (!["before", "after"].includes(phase)) throw Error("Choose before or after");
const c = JSON.parse(readFileSync("/tmp/statarena-aws-runtime-20261104.json"));
assert.equal(
  c.host,
  "statarena-postgres.clcy2iqyajbl.us-east-2.rds.amazonaws.com",
);
assert.equal(c.database, "statarena_prod");
const url = new URL("postgresql://" + c.host + "/" + c.database);
url.username = c.username;
url.password = c.password;
Object.assign(process.env, {
  DATABASE_URL: url.href,
  STATARENA_DATA_PROVIDER: "aws",
  DATABASE_POOL_MAX: "1",
  STATARENA_METRICS_SAMPLE_RATE: "0",
});
const { handleRequest } = await import(
  new URL("dashboard/backend/aws-app.js", root)
);
const { query, closeDatabase } = await import(
  new URL("dashboard/backend/services/postgres.js", root)
);
const { loadSeason, readPages } = await import(
  new URL("dashboard/frontend/src/season_data.js", root)
);
const srv = Bun.serve({
  hostname: "127.0.0.1",
  port: 0,
  idleTimeout: 120,
  fetch: handleRequest,
});
const report = {
  phase,
  at: new Date(),
  command: "bun docs/verification/aws-wire-pages/verify.mjs " + phase,
  checks: [],
  leagues: [],
};
const get = (path, options) => fetch(new URL(path, srv.url), options);
const test = (label, ok, detail) => report.checks.push({ label, ok, detail });
const hash = (obj) =>
  createHash("sha256")
    .update(
      JSON.stringify(obj, (_, v) =>
        v && typeof v === "object" && !Array.isArray(v)
          ? Object.fromEntries(
              Object.entries(v).sort(([a], [b]) =>
                a < b ? -1 : a > b ? 1 : 0,
              ),
            )
          : v,
      ),
    )
    .digest("hex");
try {
  assert.equal(
    (await query("SELECT current_setting('transaction_read_only') AS r"))[0].r,
    "on",
  );
  const manifest = await (await get("/api/dashboard/manifest")).json(),
    season = "2026/2027",
    path = "/api/seasons/partition",
    baseline = new URL("before.json", dir);
  for (const league of ["l_0275VP", "l_0ALvwF"]) {
    const params = new URLSearchParams({ season, league, limit: "1" }),
      base = path + "?" + params,
      plain = await (await get(base)).json();
    const sample = await get(base + "&format=columns"),
      first = await sample.json();
    test(
      "compact opt-in selected",
      sample.ok && first.data?.format === "orion-packed-tables-v1",
      { league, status: sample.status },
    );
    const summary = {
      league,
      generation: plain.pagination.generation,
      firstRecordPageBytesByTable: Object.fromEntries(
        Object.entries(plain.data).map(([k, v]) => [
          k,
          Buffer.byteLength(JSON.stringify(v)),
        ]),
      ),
      requests: [],
    };
    report.leagues.push(summary);
    const trace = async (p) => {
      const t = performance.now(),
        res = await get(p),
        buf = Buffer.from(await res.clone().arrayBuffer()),
        par = new URL(p, srv.url).searchParams;
      summary.requests.push({
        status: res.status,
        limit: Number(par.get("limit")),
        columns: par.get("format") === "columns",
        cursor: par.has("cursor"),
        ms: Math.round(performance.now() - t),
        bytes: buf.length,
        gzipBytes: gzipSync(buf).length,
      });
      return res;
    };
    const [a, b] = await Promise.all([
      loadSeason(manifest, season, trace, new Set([league])),
      loadSeason(manifest, season, trace, new Set([league])),
    ]);
    assert.deepEqual(a, b);
    summary.rowCounts = Object.fromEntries(
      ["matches", "fixtures", "appearances", "teams"].map((k) => [
        k,
        a[k].length,
      ]),
    );
    summary.shots = a.matches.reduce((n, m) => n + m.shots.length, 0);
    summary.digest = hash({
      ...a,
      appearances: [...a.appearances].sort((a, b) =>
        a.matchId.localeCompare(b.matchId),
      ),
    });
    const n = summary.requests.length;
    await loadSeason(manifest, season, trace, new Set([league]));
    test("cached traversal reused", n === summary.requests.length, {
      league,
      n,
    });
    test(
      "all compact windows fit at limit 100",
      summary.requests.every(
        (r) =>
          r.status === 200 &&
          r.limit === 100 &&
          r.columns &&
          r.bytes <= 2 * 1024 * 1024,
      ),
      { league, n },
    );
    if (phase === "after") {
      const saved = JSON.parse(readFileSync(baseline)).leagues.find(
        (l) => l.league === league,
      );
      test(
        "complete decoded contents and within-match ordering match prior SHA",
        saved.digest === summary.digest &&
          saved.generation === summary.generation,
        { league, digest: summary.digest },
      );
      const module = await import(
        new URL("dashboard/frontend/src/season_data.js", root)
      );
      const decoded = module.decodePartition(first.data);
      test(
        "one fixture default page matches decoded opt-in exactly",
        hash(decoded) === hash(plain.data),
        { league },
      );
      const head = await get(base + "&format=columns", { method: "HEAD" }),
        cond = await get(base + "&format=columns", {
          headers: { "if-none-match": sample.headers.get("etag") },
        });
      test(
        "metadata parity",
        head.status === 200 &&
          head.headers.get("etag") === sample.headers.get("etag") &&
          cond.status === 304,
        { league },
      );
      const bad = await get(base + "&format=xml");
      test("unknown format rejected", bad.status === 400, { league });
      const cursor = first.pagination.nextCursor,
        stale = JSON.parse(Buffer.from(cursor, "base64url"));
      stale.generation = "obsolete";
      const conflict = await get(
        base +
          "&format=columns&cursor=" +
          Buffer.from(JSON.stringify(stale)).toString("base64url"),
      );
      const mixed = await get(base + "&cursor=" + cursor);
      test(
        "stale and mixed format cursors rejected",
        conflict.status === 409 && mixed.status === 400,
        { league },
      );
    }
    writeFileSync(
      new URL(phase + ".json", dir),
      JSON.stringify(report, null, 2) + "\n",
    );
  }
} catch (e) {
  report.error = { name: e.name, message: String(e.message).slice(0, 140) };
} finally {
  srv.stop(true);
  await closeDatabase();
  report.passed = !report.error && report.checks.every((c) => c.ok);
  writeFileSync(
    new URL(phase + ".json", dir),
    JSON.stringify(report, null, 2) + "\n",
  );
  console.log(
    JSON.stringify({
      passed: report.passed,
      checks: report.checks,
      error: report.error,
    }),
  );
  process.exitCode = report.passed ? 0 : 1;
}
