/** Additive HTTP workflows; expected behavior was specified before read code. */
import assert from "node:assert/strict";
import { readFile, readdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { gzipSync } from "node:zlib";

export async function run({
  check,
  get,
  telemetry,
  admin,
  root,
  evidence,
  hash,
  put,
  objects,
}) {
  const migrationDir = path.join(root, "dashboard/backend/migrations");
  for (const file of (await readdir(migrationDir))
    .filter((f) => /^00[23]_/.test(f))
    .sort())
    await admin.query(await readFile(path.join(migrationDir, file), "utf8"));
  const rows = Array.from({ length: 123 }, (_, i) => ({
    id: `m_${100000 + i}`,
    date:
      i >= 119
        ? null
        : `2026-11-${String(1 + Math.floor(i / 20)).padStart(2, "0")}`,
    time_utc: null,
    status: i % 3 ? "finished" : "not_started",
    season: "2026/2027",
    league: { id: "l_100001", name: "Example League" },
    home_team: { id: "t_100001", name: "Paris Example", image_url: null },
    away_team: { id: "t_100002", name: "Away Example", image_url: null },
    score_home: i % 3 ? 0 : null,
    score_away: i % 3 ? 1 : null,
    heavy_detail: "x".repeat(8192),
  }));
  for (const r of rows)
    await admin.query(
      "INSERT INTO statarena.fixtures(id,league_id,season,day,status,body) VALUES($1,$2,$3,$4,$5,$6)",
      [r.id, r.league.id, r.season, r.date, r.status, r],
    );
  const base = "/api/fixtures?league=l_100001&season=2026%2F2027&status=all";
  const tally = (entries, key) =>
    entries.reduce((n, r) => n + (r.metrics?.[key] || 0), 0);
  await telemetry();
  await check(
    "P1 pagination versus legacy bytes",
    "legacy returns123 complete; default page50 excludes heavy fields with smaller bytes",
    async () => {
      const legacy = await get(
        "/api/pitchapi/leagues/l_100001/matches?season=2026%2F2027&status=all",
      );
      const page = await get(base);
      const measured = {
        legacyStatus: legacy.status,
        legacyBytes: legacy.bytes.length,
        pageStatus: page.status,
        pageBytes: page.bytes.length,
        legacyGzipBytes: gzipSync(legacy.bytes).length,
        pageGzipBytes: gzipSync(page.bytes).length,
      };
      await writeFile(
        path.join(evidence, "p1-payload-comparison.json"),
        JSON.stringify(measured, null, 2) + "\n",
      );
      assert.equal(legacy.status, 200);
      assert.equal(legacy.json().data.matches.length, 123);
      assert.equal(page.status, 200);
      assert.equal(page.json().data.matches.length, 50);
      assert.ok(page.bytes.length < legacy.bytes.length / 5);
      assert.ok(
        page
          .json()
          .data.matches.every((m) => !Object.hasOwn(m, "heavy_detail")),
      );
    },
  );
  await check(
    "P1 cursor traversal and null/tie ordering",
    "three stable pages, no omissions or duplicates; null dates last",
    async () => {
      const seen = [],
        cursors = new Set();
      let url = base;
      while (url) {
        const r = await get(url);
        assert.equal(r.status, 200);
        const value = r.json();
        assert.ok(value.data.matches.length <= 50);
        seen.push(...value.data.matches.map((m) => m.id));
        const next = value.pagination.nextCursor;
        if (next) {
          assert.ok(!cursors.has(next));
          cursors.add(next);
        }
        url = next ? base + "&cursor=" + encodeURIComponent(next) : null;
      }
      assert.deepEqual(
        seen,
        rows.map((m) => m.id),
      );
      assert.equal(new Set(seen).size, 123);
    },
  );
  await check(
    "P1 filters, ceilings and errors",
    "explicit upcoming semantics,50/100 bounds, invalid parameters400 and filter-bound cursor",
    async () => {
      const first = await get(base);
      assert.equal(first.status, 200);
      const cursor = first.json().pagination.nextCursor;
      const max = await get(base + "&limit=100");
      assert.equal(max.status, 200);
      assert.equal(max.json().data.matches.length, 100);
      const upcoming = await get(
        "/api/fixtures?league=l_100001&season=2026%2F2027&status=upcoming&limit=100",
      );
      assert.equal(upcoming.status, 200);
      assert.equal(upcoming.json().data.matches.length, 41);
      assert.ok(
        upcoming.json().data.matches.every((m) => m.status === "not_started"),
      );
      for (const suffix of [
        "&limit=0",
        "&limit=101",
        "&limit=2&limit=3",
        "&cursor=garbage",
        "&unknown=1",
        "&from=2026-02-30",
      ])
        assert.equal((await get(base + suffix)).status, 400, suffix);
      assert.equal(
        (
          await get(
            base.replace("l_100001", "l_100002") +
              "&cursor=" +
              encodeURIComponent(cursor),
          )
        ).status,
        400,
      );
      const empty = await get(base.replace("l_100001", "l_999999"));
      assert.equal(empty.status, 200);
      assert.deepEqual(empty.json().data.matches, []);
      assert.equal(empty.json().pagination.nextCursor, null);
    },
  );
  await check(
    "P1 publication invalidates cursor",
    "a changed fixture generation returns409 rather than mixing pages",
    async () => {
      const first = await get(base);
      assert.equal(first.status, 200);
      const cursor = first.json().pagination.nextCursor;
      await admin.query(
        "UPDATE statarena.fixtures SET body=body||'{\"score_home\":2}'::jsonb,updated_at=now() WHERE id='m_100001'",
      );
      assert.equal(
        (await get(base + "&cursor=" + encodeURIComponent(cursor))).status,
        409,
      );
    },
  );
  await check(
    "P1 null cursor pages and literal search",
    "null day branch, case-sensitive ties, escaped%/_ and accent normalization",
    async () => {
      const ids = ["m_A10000", "m_a10000", "m_Z10000"];
      for (const id of ids)
        await admin.query(
          "INSERT INTO statarena.fixtures(id,league_id,season,day,status,body) VALUES($1,'l_100003','2026',NULL,'not_started',$2)",
          [
            id,
            {
              id,
              season: "2026",
              status: "not_started",
              home_team: {
                id: "t_100003",
                name: id === "m_A10000" ? "Équipe%_test" : "Other",
              },
              away_team: { id: "t_100004", name: "Away" },
              league: { id: "l_100003" },
            },
          ],
        );
      const route = "/api/fixtures?league=l_100003&season=2026&limit=1";
      let url = route;
      const got = [];
      while (url) {
        const r = await get(url);
        assert.equal(r.status, 200);
        const p = r.json();
        got.push(...p.data.matches.map((m) => m.id));
        url = p.pagination.nextCursor
          ? route + "&cursor=" + encodeURIComponent(p.pagination.nextCursor)
          : null;
      }
      assert.equal(new Set(got).size, 3);
      assert.deepEqual([...got].sort(), [...ids].sort());
      const search = await get(
        route.replace("limit=1", "limit=100") +
          "&q=" +
          encodeURIComponent("equipe%_"),
      );
      assert.equal(search.status, 200);
      assert.deepEqual(
        search.json().data.matches.map((m) => m.id),
        ["m_A10000"],
      );
      assert.equal((await get(base + "&from=0000-01-01")).status, 400);
    },
  );
  await check(
    "P1 complete-season consumer traverses pages",
    "a consumer opting into all pages still receives all123fixtures",
    async () => {
      const { allFixturePages } =
        await import("../frontend/src/services/fixture-pages.js");
      const result = await allFixturePages(
        { league: "l_100001", season: "2026/2027", status: "all" },
        async (url) => {
          const r = await get(url);
          return new Response(r.bytes, {
            status: r.status,
            headers: r.headers,
          });
        },
      );
      assert.equal(result.data.matches.length, 123);
      assert.equal(new Set(result.data.matches.map((m) => m.id)).size, 123);
    },
  );
  await check(
    "P1 immutable reader handoff",
    "cached old metadata returns exact old immutable bytes after inline alias changes",
    async () => {
      const p = "raw/p1-immutable-handoff.json",
        old = Buffer.from('{"handoff":"old"}'),
        next = Buffer.from('{"handoff":"new"}');
      const key = "data/versions/" + hash(old);
      objects.set(key, old);
      await put(p, old);
      await admin.query(
        "UPDATE statarena.objects SET storage_key=$1 WHERE path=$2",
        [key, p],
      );
      assert.equal((await get("/data/" + p, { method: "HEAD" })).status, 200);
      await put(p, next);
      const r = await get("/data/" + p);
      assert.equal(r.status, 200);
      assert.deepEqual(r.bytes, old);
      assert.equal(r.headers.etag, `"${hash(old)}"`);
    },
  );
  await check(
    "P1 no-op write preserves cursor",
    "zero affected rows do not change data generation",
    async () => {
      const r = await get(base);
      assert.equal(r.status, 200);
      const cursor = r.json().pagination.nextCursor;
      await admin.query(
        "UPDATE statarena.fixtures SET status=status WHERE false",
      );
      assert.equal(
        (await get(base + "&cursor=" + encodeURIComponent(cursor))).status,
        200,
      );
    },
  );
  for (const family of [
    "match",
    "shots",
    "momentum",
    "events",
    "players",
    "players/halves",
    "lineups",
    "h2h",
    "stats",
    "advanced",
    "advanced/players",
    "advanced/network",
    "heatmaps",
  ]) {
    const p = "raw/summary-compare-" + family.replaceAll("/", "-") + ".json";
    const data =
      family === "match"
        ? { ...rows[1], score_home: 2 }
        : { family, unavailable: null, value: 0, detail: "x".repeat(8192) };
    await put(p, Buffer.from(JSON.stringify({ data })));
    await admin.query(
      "INSERT INTO statarena.resources(endpoint,status,ref) VALUES($1,200,$2)",
      [
        "/matches/m_100001" + (family === "match" ? "" : "/" + family),
        { path: p },
      ],
    );
  }
  const summary = {
    data: {
      version: 1,
      state: "ready",
      match: {
        id: "m_100001",
        season: "2026/2027",
        status: "finished",
        home: { id: "t_100001", name: "Paris Example", score: 2 },
        away: { id: "t_100002", name: "Away Example", score: 1 },
        shots: [],
        stats: [],
        warnings: [],
        coverage: { players: false },
        leadingPlayers: [],
      },
    },
  };
  const bytes = Buffer.from(JSON.stringify(summary));
  const exists = (
    await admin.query(
      "SELECT to_regclass('statarena.match_summaries') IS NOT NULL AS present",
    )
  ).rows[0].present;
  if (exists) {
    await admin.query(
      "INSERT INTO statarena.match_summaries(match_id,body,sha256,size,source_digest) VALUES($1,$2,decode($3,'hex'),$4,$3)",
      ["m_100001", bytes, hash(bytes), bytes.length],
    );
    await admin.query(
      "DELETE FROM statarena.dirty_match_summaries WHERE match_id='m_100001'",
    );
  }
  await check(
    "P1 precomputed summary bounded GET",
    "one SQL, exact small body, no archive/object/parse",
    async () => {
      await telemetry();
      const legacy = await get("/api/archive/matches/m_100001");
      const oldMetrics = await telemetry();
      const r = await get("/api/matches/m_100001/summary");
      const metrics = await telemetry();
      await writeFile(
        path.join(evidence, "p1-summary-comparison.json"),
        JSON.stringify(
          {
            legacy: {
              status: legacy.status,
              bytes: legacy.bytes.length,
              gzipBytes: gzipSync(legacy.bytes).length,
              sql: tally(oldMetrics, "sql_count"),
              sourceBytes: tally(oldMetrics, "sql_body_bytes"),
            },
            summary: {
              status: r.status,
              bytes: r.bytes.length,
              gzipBytes: gzipSync(r.bytes).length,
              sql: tally(metrics, "sql_count"),
              sourceBytes: tally(metrics, "sql_body_bytes"),
            },
          },
          null,
          2,
        ) + "\n",
      );
      assert.equal(r.status, 200);
      assert.deepEqual(r.bytes, bytes);
      assert.equal(r.headers.etag, `"${hash(bytes)}"`);
      assert.equal(tally(metrics, "sql_count"), 1);
      assert.equal(tally(metrics, "object_bytes"), 0);
      assert.equal(tally(metrics, "parse_bytes"), 0);
    },
  );
  await check(
    "P1 summary HEAD and validators",
    "metadata-only HEAD/304 with exact size/hash and zero SQLbody",
    async () => {
      await telemetry();
      const h = await get("/api/matches/m_100001/summary", { method: "HEAD" });
      assert.equal(h.status, 200);
      assert.equal(Number(h.headers["content-length"]), bytes.length);
      assert.equal(h.bytes.length, 0);
      for (const tag of [
        `"${hash(bytes)}"`,
        `W/"${hash(bytes)}"`,
        `"other", W/"${hash(bytes)}"`,
        "*",
      ])
        assert.equal(
          (
            await get("/api/matches/m_100001/summary", {
              headers: { "If-None-Match": tag },
            })
          ).status,
          304,
        );
      const metrics = await telemetry();
      assert.equal(tally(metrics, "sql_body_bytes"), 0);
      assert.equal(tally(metrics, "object_bytes"), 0);
      assert.equal(tally(metrics, "parse_bytes"), 0);
    },
  );
  await check(
    "P1 conditional summary publication race",
    "a replacement between metadata/body cannot emit new bytes with the old ETag",
    async () => {
      if (!exists) throw new Error("Summary schema missing");
      const replacement = Buffer.from(
        JSON.stringify({
          ...summary,
          data: {
            ...summary.data,
            match: {
              ...summary.data.match,
              home: { ...summary.data.match.home, score: 7 },
            },
          },
        }),
      );
      await admin.query(
        "ALTER TABLE statarena.match_summaries RENAME TO fixture_summary_rows",
      );
      try {
        await admin.query(
          `CREATE FUNCTION statarena.fixture_summary_race(identity text,incoming integer) RETURNS integer LANGUAGE plpgsql VOLATILE AS $$ BEGIN UPDATE statarena.fixture_summary_rows SET body=decode('${replacement.toString("hex")}','hex'),sha256=sha256(decode('${replacement.toString("hex")}','hex')),size=${replacement.length} WHERE match_id=identity AND sha256<>sha256(decode('${replacement.toString("hex")}','hex')); RETURN incoming; END $$`,
        );
        await admin.query(
          "CREATE VIEW statarena.match_summaries AS SELECT match_id,body,sha256,statarena.fixture_summary_race(match_id,size) AS size,source_digest,updated_at FROM statarena.fixture_summary_rows",
        );
        const r = await get("/api/matches/m_100001/summary", {
          headers: { "If-None-Match": '"different"' },
        });
        assert.equal(r.status, 200);
        assert.equal(r.json().data.state, "pending");
        assert.equal(r.headers.etag, undefined);
        assert.equal(r.headers["cache-control"], "no-store");
      } finally {
        await admin.query("DROP VIEW IF EXISTS statarena.match_summaries");
        await admin.query(
          "ALTER TABLE statarena.fixture_summary_rows RENAME TO match_summaries",
        );
        await admin.query(
          "DROP FUNCTION IF EXISTS statarena.fixture_summary_race(text,integer)",
        );
      }
      await telemetry();
    },
  );
  await check(
    "P1 dirty/missing summary stays truthful",
    "source change gives pending fixture, null preserved; absent fixture404; stale ETag never304",
    async () => {
      await admin.query(
        "UPDATE statarena.fixtures SET body=body||'{\"score_home\":null}'::jsonb,updated_at=now() WHERE id='m_100001'",
      );
      const r = await get("/api/matches/m_100001/summary", {
        headers: { "If-None-Match": `"${hash(bytes)}"` },
      });
      assert.equal(r.status, 200);
      assert.equal(r.json().data.state, "pending");
      assert.equal(r.json().data.match.home.score, null);
      assert.equal(r.headers["cache-control"], "no-store");
      await telemetry();
      assert.equal(
        (await get("/api/matches/m_100001/summary", { method: "HEAD" })).status,
        200,
      );
      assert.equal(
        (
          await get("/api/matches/m_100001/summary", {
            headers: { "If-None-Match": "*" },
          })
        ).status,
        304,
      );
      assert.equal(tally(await telemetry(), "sql_json_rows"), 0);
      assert.equal(
        (
          await get("/api/matches/m_999999/summary", {
            headers: { "If-None-Match": "*" },
          })
        ).status,
        404,
      );
    },
  );
  await check(
    "P1 target detail precedes full archive",
    "client requests one selected section without a preceding whole-shard request",
    async () => {
      const { FootballDataClient } =
        await import("../frontend/src/services/football-client.js");
      const client = new FootballDataClient({
        data: {
          competitions: [],
          meta: { endDate: "2026-11-03" },
          matches: [],
          fixtures: [],
        },
      });
      client.configured = true;
      const calls = [];
      client.loadShard = async () => {
        calls.push("archive");
        return { stats: { data: { fixture: true } } };
      };
      client.request = async (p) => {
        calls.push(p);
        return { data: { fixture: true } };
      };
      await client.ensureEndpoint({ id: "m_100001" }, "stats");
      assert.deepEqual(calls, ["matches/m_100001/stats"]);
    },
  );
}
