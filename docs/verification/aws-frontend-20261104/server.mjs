import path from "node:path";
const trace = [],
  bad = [],
  requests = {};
let starts = 0;
const api = Bun.serve({
  hostname: "127.0.0.1",
  port: 0,
  fetch(r) {
    const u = new URL(r.url),
      p = u.searchParams,
      path = u.pathname;
    trace.push(path + u.search);
    requests[path] = (requests[path] || 0) + 1;
    let value,
      status = 200;
    if(path==="/api/seasons/partition" && p.get("league")==="l_CCCCCC"){
      const limit=Number(p.get("limit")),cursor=p.get("cursor");
      if(limit===100 || (limit===50 && cursor)){status=413;value={error:"page too large"};}
      else {
        const ids=Array.from({length:cursor?1:25},(_,i)=>limit===50?"discard"+i:"dense"+((cursor?25:0)+i));
        value={data:{meta:{shotCount:26},metrics:[],competitions:[],teams:[],fixtures:ids.map(id=>({id})),matches:ids.map(id=>({id})),appearances:ids.map(matchId=>({matchId}))},pagination:{generation:"1",nextCursor:cursor?null:"dense-next"}};
      }
    }else if (path === "/api/seasons/partition") {
      const a = p.get("league") === "l_AAAAAA",
        cursor = p.get("cursor");
      if (a && !cursor) starts++;
      if (a && cursor && starts === 1) {
        status = 409;
        value = { error: "new generation" };
      } else {
        const count = a ? (cursor ? 1 : 100) : 1,
          id = a ? "A" : "B",
          total = a ? 101 : 1,
          begin = cursor ? 100 : 0;
        const ids = Array.from(
          { length: count },
          (_, i) => id + (a && starts === 1 ? "retired" : "") + (i + begin),
        );
        value = {
          data: {
            meta: { shotCount: total },
            metrics: [],
            fixtures: ids.map((id) => ({ id })),
            matches: ids.map((id) => ({ id })),
            appearances: ids.map((id) => ({ matchId: id, playerId: id })),
            teams: [{ id, name: id, sampleMatches: total }],
            competitions: [{ id, name: id, sampleMatches: total }],
          },
          pagination: {
            generation: String(a ? starts : 1),
            nextCursor: a && !cursor ? "next" : null,
          },
        };
      }
    } else if (path === "/api/fixtures") {
      const more = p.has("cursor");
      value = {
        data: {
          matches: Array.from({ length: more ? 3 : 100 }, (_, i) => ({
            id: "f" + ((more ? 100 : 0) + i),
          })),
        },
        pagination: { generation: "12", nextCursor: more ? null : "second" },
      };
    } else if (
      path === "/api/scouting/routes" &&
      p.get("player") === "p_AAAAAA" &&
      p.get("team") === "t_BBBBBB"
    )
      value = {
        routes: { p_AAAAAA: { "2026/2027": ["l_AAAAAA"] } },
        clubRoutes: { t_BBBBBB: {} },
      };
    else if (path === "/api/club-links" && p.get("club") === "t_BBBBBB")
      value = { links: { t_BBBBBB: { entityId: "uefa:21" } } };
    else if (path === "/api/club-wikidata" && p.get("uefa") === "21")
      value = { founded: "1900" };
    else if (path === "/api/supplemental")
      value = { meta: { v: 1 }, competitions: [] };
    else if (path === "/api/cup-snapshot" && p.get("kind") === "open-cups")
      value = { matches: [{ id: "cup1" }] };
    else if (path === "/api/archives/index")
      value = { seasons: [{ id: "2020/2021" }] };
    else if (path === "/api/archives/season")
      value = { season: p.get("season"), competitions:p.get("kind")==="results"?[{id:"l_AAAAAA",name:"Fixture Cup",country:"FRA",matches:[{team1:"Test Athletic",team2:"Blue United",date:"2020-11-03",score:{ft:[2,0]}}]}]:[] };
    else if (path === "/api/dashboard/manifest") value={schemaVersion:4,storage:"aws-relational",defaultSeason:"2020/2021",seasons:[{id:"2020/2021",chunks:[]}],competitions:[],clubCountries:{},scouting:{version:2}};
    else if(path==="/api/status")value={configured:false};
    else if (path === "/api/rankings/club")
      value = {
        rows: [
          { edition: { edition: "2020.uefa" }, row: null },
          { edition: { edition: "2021.uefa" }, row: { points: 12 } },
        ],
      };
    else if (path === "/api/rankings/associations")
      value = { rows: [{ rank: 2 }] };
    else if (path === "/api/cup-index")
      value = { competitions: p.get("kind") === "worker" ? [{}] : [{}, {}] };
    else if (
      path === "/api/cup-table" &&
      p.get("competition") === "FRA_CUP_demo"
    )
      value = [{ score: 0 }];
    else if (path === "/api/player-honours" && p.get("id") === "p_AAAAAA")
      value = {
        available: true,
        honours: [
          { name: "Cup", category: "team", team: "Team", seasons: ["2020"] },
        ],
      };
    else if (path === "/api/player-honours" && p.get("id") === "p_000000") {
      status = 404;
      value = { available: false };
    } else {
      bad.push(u.pathname);
      value = { error: "unexpected" };
      status = 404;
    }
    return Response.json(value, {
      status,
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Cache-Control": "no-store",
      },
    });
  },
});
const bundle = await Bun.build({
  entrypoints: [path.join(import.meta.dir, "browser.mjs")],
  target: "browser",
  format: "esm",
  define: {
    "process.env.NEXT_PUBLIC_API_ORIGIN": JSON.stringify(api.url.origin),
  },
});
if (!bundle.success) throw Error(bundle.logs.join("\n"));
const js = await bundle.outputs[0].text();
const page = Bun.serve({
  hostname: "127.0.0.1",
  port: 0,
  fetch(r) {
    const p = new URL(r.url).pathname;
    if (p === "/")
      return new Response(
        '<html><body>Loading<script type="module" src="/app.js"></script></body></html>',
        { headers: { "content-type": "text/html" } },
      );
    if (p === "/app.js")
      return new Response(js, {
        headers: { "content-type": "application/javascript" },
      });
    if (p === "/config") return Response.json({api:api.url.origin});
    if (p === "/trace") return Response.json({ trace, bad, requests, starts });
    if (p !== "/favicon.ico") bad.push("frontend:" + p);
    return new Response(null, { status: 404 });
  },
});
console.log(page.url.origin);
