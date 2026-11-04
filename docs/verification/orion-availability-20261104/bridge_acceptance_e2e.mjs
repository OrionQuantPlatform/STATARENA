// Real saved-object HTTP acceptance; bounded reads are specified in ACCEPTANCE_PROTOCOL.md.
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { gunzipSync } from "node:zlib";
import { readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { legacyCompatibility } from "../../../dashboard/frontend/src/server/legacy-compat.js";
import { loadSeason, readPages } from "../../../dashboard/frontend/src/season_data.js";
import { FootballDataClient } from "../../../dashboard/frontend/src/services/football-client.js";
import { historicalFixtures, loadPlayerHistory } from "../../../dashboard/frontend/src/services/scouting-history.js";
import { loadPlayerHonours } from "../../../dashboard/frontend/src/services/player-honours.js";

const OLD = "https://statarena-analytics-jumo9il0b-hlemonniers-projects.vercel.app";
const directory = fileURLToPath(new URL("./", import.meta.url));
const stamp = new Date().toISOString().replace(/[-:.]/g, "");
const sha = (body) => createHash("sha256").update(body).digest("hex");
const canonical = (value) => JSON.stringify(value, (_, item) => item && typeof item === "object" && !Array.isArray(item) ? Object.fromEntries(Object.entries(item).sort(([a], [b]) => a.localeCompare(b))) : item);
const hash = (value) => sha(canonical(value));
const rowHash = (rows) => hash([...rows].sort((a, b) => String(a.id).localeCompare(String(b.id))));
const checks = [], network = [], localRequests = [], limits = { maxUniqueRequests: 300, maxResponseBytes: 64 * 1024 * 1024, maxConcurrent: 4, requestTimeoutMs: 30000 };
const report = {
  atUtc: new Date().toISOString(), command: "bun docs/verification/orion-availability-20261104/bridge_acceptance_e2e.mjs",
  setup: "Actual compatibility handler on ephemeral localhost Bun HTTP server. Only immutable previous Vercel saved routes/objects may be read; duplicate external GETs are cached in memory for a stable bounded comparison. No payload files, provider APIs, database credentials or writes. This does not exercise the real Next/Neon SDK path or Vercel runtime.",
  expected: "All 65 real supplemental competitions expand through the current bounded-object client with exact saved-table values; six scoped seasons, fixture/history filters and every current data route family preserve saved-source identities, dates, statuses and errors.",
  externalSource: OLD, limits, sourceSha256: {}, checks, network, passed: false,
};
for (const path of ["dashboard/frontend/src/server/legacy-compat.js", "dashboard/frontend/src/services/football-client.js", "dashboard/frontend/src/season_data.js"]) report.sourceSha256[path] = sha(await readFile(new URL("../../../" + path, import.meta.url)));
const originalFetch = globalThis.fetch, cache = new Map(), pending = [];
let running = 0, maximumRunning = 0, totalBytes = 0, remoteCount = 0;
async function limited(work) {
  if (running >= limits.maxConcurrent) await new Promise((resolve) => pending.push(resolve));
  running++; maximumRunning = Math.max(maximumRunning, running);
  try { return await work(); } finally { running--; pending.shift()?.(); }
}
async function remote(path, { method = "GET", headers = {} } = {}) {
  const url = new URL(path, OLD);
  assert.equal(url.origin, OLD); assert.ok(/^\/(data|api)\//.test(url.pathname));
  const key = method + " " + path + " " + canonical(headers);
  if (!cache.has(key)) {
    assert.ok(++remoteCount <= limits.maxUniqueRequests, "External request budget exceeded");
    cache.set(key, limited(async () => {
      const started = performance.now();
      const response = await originalFetch(url, { method, headers: { "accept-encoding": "identity", ...headers }, redirect: "manual", signal: AbortSignal.timeout(limits.requestTimeoutMs) });
      const bytes = Buffer.from(await response.arrayBuffer()); totalBytes += bytes.length;
      assert.ok(totalBytes <= limits.maxResponseBytes, "External response byte budget exceeded");
      const copied = new Headers(response.headers);
      if (copied.has("content-encoding")) copied.delete("content-length");
      copied.delete("content-encoding");
      network.push({ path, method, status: response.status, bytes: bytes.length, sha256: sha(bytes), elapsedMs: Math.round((performance.now() - started) * 1000) / 1000 });
      return { bytes, status: response.status, headers: copied };
    }));
  }
  return cache.get(key);
}
async function readJson(path) {
  assert.match(path, /^(raw|computed)\/[A-Za-z0-9_./-]+$/); assert.ok(!path.split("/").some((part) => part.startsWith(".")));
  const response = await remote("/data/" + path);
  if (response.status !== 200) { const error = Error("Saved object HTTP " + response.status); error.code = response.status === 404 ? "ENOENT" : "UPSTREAM"; throw error; }
  return JSON.parse(path.endsWith(".gz") ? gunzipSync(response.bytes).toString() : response.bytes.toString());
}
async function legacy(request) {
  const url = new URL(request.url), headers = {};
  for (const name of ["if-none-match", "if-modified-since"]) if (request.headers.has(name)) headers[name] = request.headers.get(name);
  const value = await remote(url.pathname + url.search, { method: request.method, headers });
  return new Response(request.method === "HEAD" || [204, 304].includes(value.status) ? null : value.bytes, { status: value.status, headers: value.headers });
}
const server = Bun.serve({ hostname: "127.0.0.1", port: 0, fetch: (request) => { const url = new URL(request.url); localRequests.push(url.pathname + url.search); return legacyCompatibility(request, { handleLegacy: legacy, readJson }); } });
const request = (path, init) => originalFetch(new URL(path, server.url), init);
globalThis.fetch = (path, init) => typeof path === "string" && path.startsWith("/") ? request(path, init) : originalFetch(path, init);
async function check(name, inputs, workflow) {
  const start = performance.now();
  try { const actual = await workflow(); checks.push({ name, inputs, passed: true, elapsedMs: Math.round(performance.now() - start), actual }); }
  catch (error) { checks.push({ name, inputs, passed: false, error: String(error.stack || error) }); }
}
async function json(path) { const response = await request(path); assert.equal(response.status, 200, path); return response.json(); }
async function parity(path) {
  const [bridged, source] = await Promise.all([request(path), legacy(new Request("http://saved" + path))]);
  const [actual, expected] = await Promise.all([bridged.arrayBuffer(), source.arrayBuffer()]);
  assert.equal(bridged.status, source.status, path); assert.equal(sha(Buffer.from(actual)), sha(Buffer.from(expected)), path);
  for (const header of ["cache-control", "etag", "x-data-source", "allow"]) assert.equal(bridged.headers.get(header), source.headers.get(header), path + " " + header);
  return { path, status: bridged.status, bytes: actual.byteLength, sha256: sha(Buffer.from(actual)), cacheControl: bridged.headers.get("cache-control") };
}
try {
  const manifest = await readJson("computed/dashboard/index.json"), raw = await readJson("raw/index.json");
  await check("manifest preserves all six saved seasons and 230 references", {}, async () => {
    const value = await json("/api/dashboard/manifest"); assert.equal(hash(value), hash(manifest)); assert.equal(value.seasons.length, 6); assert.equal(value.seasons.reduce((n, season) => n + season.chunks.length, 0), 230);
    return { seasons: value.seasons.map((season) => ({ id: season.id, chunks: season.chunks.length })) };
  });
  let current;
  for (const season of manifest.seasons) await check("scoped season load " + season.id, { league: "l_3FJFUl", season: season.id }, async () => {
    const value = await loadSeason(manifest, season.id, request, new Set(["l_3FJFUl"]));
    assert.ok(value.matches.length); assert.ok(value.appearances.length); assert.ok(value.matches.every((match) => match.season === season.id));
    if (season.id === manifest.defaultSeason) current = value;
    return { matches: value.matches.length, fixtures: value.fixtures.length, appearances: value.appearances.length, matchHash: rowHash(value.matches), appearanceHash: rowHash(value.appearances) };
  });
  const sourceFixtures = [];
  for (const season of raw.seasons.filter((season) => season.chunks.some((chunk) => chunk.leagueId === "l_3FJFUl"))) {
    const path = "/api/pitchapi/leagues/l_3FJFUl/matches?" + new URLSearchParams({ season: season.id, status: "all" });
    const saved = JSON.parse((await remote(path)).bytes); assert.ok(Array.isArray(saved.data.matches)); sourceFixtures.push(...saved.data.matches);
  }
  const unique = [...new Map(sourceFixtures.map((row) => [row.id, row])).values()];
  for (const [status, expected] of [["all", unique], ["played", unique.filter((row) => row.status === "finished")], ["upcoming", unique.filter((row) => row.status === "not_started")]]) {
    await check("all-season fixture traversal " + status, { league: "l_3FJFUl", status }, async () => {
      const pages = await readPages("/api/fixtures", { league: "l_3FJFUl", status }, request), matches = pages.flatMap((page) => page.matches);
      assert.equal(matches.length, expected.length); assert.equal(rowHash(matches), rowHash(expected));
      return { pages: pages.length, matches: matches.length, semanticHash: rowHash(matches) };
    });
  }
  await check("actual historicalFixtures client enumerates every saved league season", { league: "l_3FJFUl" }, async () => {
    const matches = await historicalFixtures(manifest, "l_3FJFUl"); assert.equal(rowHash(matches), rowHash(unique));
    return { matches: matches.length, seasons: [...new Set(matches.map((match) => match.season))].sort(), semanticHash: rowHash(matches) };
  });
  const day = unique.find((row) => /^\d{4}-\d{2}-\d{2}$/.test(row.date || ""))?.date;
  await check("calendar day and status filters", { day }, async () => {
    assert.ok(day); const source = JSON.parse((await remote("/api/pitchapi/date/" + day + "?status=all")).bytes).data.matches;
    const output = [];
    for (const status of ["all", "played", "upcoming"]) {
      const expected = [...new Map(source.map((row) => [row.id, row])).values()].filter((row) => status === "all" || row.status === (status === "played" ? "finished" : "not_started"));
      const pages = await readPages("/api/fixtures", { from: day, to: day, status }, request), actual = pages.flatMap((page) => page.matches);
      assert.equal(rowHash(actual), rowHash(expected)); output.push({ status, matches: actual.length });
    }
    return output;
  });
  const routing = await readJson(manifest.scouting.playerRoutes.path), player = "p_3chd12", team = "t_0LMnwp";
  await check("player/team multi-season scouting route values", { player, team }, async () => {
    const value = await json("/api/scouting/routes?" + new URLSearchParams({ player, team }));
    assert.deepEqual(value.routes[player], routing.routes[player]); assert.deepEqual(value.clubRoutes[team], routing.clubRoutes[team]);
    return { playerSeasons: Object.keys(value.routes[player] || {}), teamSeasons: Object.keys(value.clubRoutes[team] || {}) };
  });
  await check("real player history loads every indexed season", { player }, async () => {
    const rows = await loadPlayerHistory(manifest, player), expected = Object.keys(routing.routes[player]); assert.equal(rows.length, expected.length);
    assert.ok(rows.every((row) => row.data?.appearances.some((appearance) => appearance.playerId === player)));
    return rows.map((row) => ({ season: row.season, competitions: routing.routes[player][row.season], appearances: row.data.appearances.filter((appearance) => appearance.playerId === player).length }));
  });
  await check("browser honours 404 classification preserves exact source and client semantics", { player }, async () => {
    const value = await parity("/api/player-honours?id=" + player); assert.equal(value.status, 404);
    const result = await loadPlayerHonours(player, "", request); assert.deepEqual(result, { groups: [], partial: true });
    return { ...value, classification: "Saved projection absent at source; bridge parity; existing UI contract treats 404 as partial honours.", client: result };
  });
  const supplemental = await readJson("raw/supplemental-index.json");
  await check("full real supplemental client expansion with concurrency at most four", { competitions: supplemental.competitions.length }, async () => {
    assert.equal(supplemental.competitions.length, 65); const start = localRequests.length;
    const client = new FootballDataClient({ data: { meta: { storage: "json-packed" }, competitions: [] } }); await client.loadSupplemental();
    assert.equal(client.supplementalError, null); assert.equal(client.supplementalLoading, false); assert.equal(client.supplementalData.competitions.length, 65);
    const decoded = [], rowCounts = {};
    for (let i = 0; i < supplemental.competitions.length; i++) {
      const saved = supplemental.competitions[i], { tables, ...entry } = saved; const actual = client.supplementalData.competitions[i];
      for (const [kind, reference] of Object.entries(tables)) {
        const rows = await readJson(reference.path); assert.ok(Array.isArray(rows)); assert.equal(hash(actual[kind]), hash(rows));
        assert.equal(rows.length, reference.rows); entry[kind] = rows; rowCounts[kind] = (rowCounts[kind] || 0) + rows.length;
      }
      assert.equal(hash(actual), hash(entry)); decoded.push(entry);
    }
    const used = localRequests.slice(start); assert.ok(used.includes("/data/raw/supplemental-index.json")); assert.ok(!used.includes("/api/supplemental"));
    report.supplementalExpandedBytes = Buffer.byteLength(JSON.stringify({ meta: supplemental.meta, competitions: decoded }));
    report.supplementalSemanticHash = hash(client.supplementalData);
    return { competitions: decoded.length, tableReferences: supplemental.competitions.reduce((n, row) => n + Object.keys(row.tables).length, 0), localRequests: used.length, rowCounts, expandedBytes: report.supplementalExpandedBytes, semanticHash: report.supplementalSemanticHash };
  });
  await check("whole supplemental endpoint respects compatibility response cap", {}, async () => {
    const response = await request("/api/supplemental"), body = await response.json();
    if (report.supplementalExpandedBytes > 2 * 1024 * 1024) { assert.equal(response.status, 413); assert.equal(body.error.code, "PAGE_TOO_LARGE"); }
    else { assert.equal(response.status, 200); assert.equal(hash(body), report.supplementalSemanticHash); }
    return { status: response.status, expandedBytes: report.supplementalExpandedBytes, capBytes: 2 * 1024 * 1024 };
  });
  for (const kind of ["results", "goals"]) await check("historical archive " + kind + " index and boundary seasons", { kind }, async () => {
    const index = await json("/api/archives/index?kind=" + kind), source = await readJson(kind === "results" ? "raw/openfootball/index.json" : "raw/historical-goals/index.json");
    assert.equal(index.seasons.length, source.seasons.length); assert.ok(index.seasons.every((entry) => !Object.hasOwn(entry, "path")));
    const samples = [];
    for (const entry of [source.seasons[0], source.seasons.at(-1)]) {
      const path = "/api/archives/season?" + new URLSearchParams({ kind, season: entry.id }), response = await request(path), value = await response.json(), saved = await readJson(entry.path);
      const bytes = Buffer.byteLength(JSON.stringify(saved));
      if (bytes > 2 * 1024 * 1024) assert.equal(response.status, 413); else { assert.equal(response.status, 200); assert.equal(hash(value), hash(saved)); }
      samples.push({ season: entry.id, status: response.status, bytes, keys: Object.keys(saved), semanticHash: hash(saved) });
    }
    return { seasons: source.seasons.length, samples };
  });
  const worker = await readJson("raw/cup-worker/index.json");
  for (const kind of ["worker", "supplemental"]) await check("cup catalog " + kind, { kind }, async () => {
    const value = await json("/api/cup-index?kind=" + kind); assert.equal(value.competitions.length, (kind === "worker" ? worker : supplemental).competitions.length);
    return { competitions: value.competitions.length, bytes: Buffer.byteLength(JSON.stringify(value)) };
  });
  await check("worker and supplemental cup tables preserve real saved rows", {}, async () => {
    const output = [];
    for (const index of [worker, supplemental]) {
      const entry = index.competitions.find((entry) => entry.tables?.results?.rows > 0), season = entry.season || entry.tables.results.path.match(/seasons\/(\d{4})-(\d{4})\//)?.slice(1).join("/");
      assert.ok(season);
      for (const kind of ["results", "fixtures"]) {
        if (!entry.tables[kind]) continue;
        const value = await json("/api/cup-table?" + new URLSearchParams({ competition: entry.folder, season, kind })), saved = await readJson(entry.tables[kind].path);
        assert.equal(hash(value), hash(saved)); output.push({ competition: entry.folder, season, kind, rows: value.length, semanticHash: hash(value) });
      }
    }
    return output;
  });
  for (const [kind, competition, season] of [["open-cups", "world-cup-history", "2022"], ["openligadb", "germany-cup", "2025/2026"], ["openligadb", "nations-league", "2026/2027"], ["nations-results", "nations-league", "2026/2027"], ["native", "l_0bfbkO", "2026/2027"], ["standings", "l_3FJFUl", "2025/2026"]]) await check("cup snapshot " + kind + "/" + competition, { kind, competition, season }, async () => {
    const sourcePath = "raw/cup-worker/" + kind + "/" + competition + "/" + season.replace("/", "-") + ".json", saved = await remote("/data/" + sourcePath), response = await request("/api/cup-snapshot?" + new URLSearchParams({ kind, competition, season }));
    assert.equal(response.status, saved.status); if (saved.status === 200) { const value = await response.json(); assert.equal(hash(value), hash(JSON.parse(saved.bytes))); return { status: 200, matches: value.matches?.length ?? null, tables: value.tables?.length ?? null, bytes: saved.bytes.length }; }
    return { status: response.status, classification: "Saved snapshot absent; existing fresh-source client fallback remains necessary." };
  });
  await check("match summary includes five saved leaders and legacy match subresources", { match: "m_18Uw0k" }, async () => {
    const value = await json("/api/matches/m_18Uw0k/summary"); assert.equal(value.data.match.leadingPlayers.length, 5); assert.ok(value.data.match.leadingPlayers.every((row) => row.matchId === "m_18Uw0k"));
    const subresources = [];
    for (const suffix of ["", "/stats", "/players", "/players/halves", "/lineups", "/shots", "/events", "/momentum", "/h2h", "/advanced", "/advanced/players", "/advanced/network", "/heatmaps?frame=acting_ltr"]) subresources.push(await parity("/api/pitchapi/matches/m_18Uw0k" + suffix));
    return { leaders: 5, subresources };
  });
  await check("legacy profiles, stored projections, assets and status retain source/cache/error semantics", {}, async () => {
    const paths = ["/api/status", "/api/pitchapi/leagues", "/api/pitchapi/leagues/l_3FJFUl", "/api/pitchapi/players/" + player, "/api/pitchapi/teams/" + team, "/api/archive/matches/m_18Uw0k", "/api/archive/profiles/players/" + player, "/api/archive/profiles/teams/" + team, "/api/standings?competition=l_3FJFUl&season=2025%2F2026", "/api/open-cups?competition=world-cup-history&season=2022", "/api/openligadb?competition=germany-cup&season=2025%2F2026", "/api/nations-results?season=2026%2F2027", "/api/stadium?id=Q1", "/api/club-wikidata?name=Paris&country=FRA", "/api/coach-portrait?name=Test", "/api/definitely-not-a-route"];
    if (current?.appearances.find((row) => row.imageUrl)?.imageUrl) paths.push("/api/assets?url=" + encodeURIComponent(current.appearances.find((row) => row.imageUrl).imageUrl));
    const output = []; for (const path of paths) output.push(await parity(path)); return output;
  });
  await check("rankings and matchday contracts", {}, async () => {
    const ranking = await json("/api/rankings/associations?year=2025"); assert.ok(ranking.rows.length);
    const links = await json("/api/club-links?club=" + team), club = await json("/api/rankings/club?club=" + team), days = await json("/api/matchdays?competition=l_0bfbkO&season=2026%2F2027");
    assert.ok(days.matches); return { associationRows: ranking.rows.length, clubLinks: Object.keys(links.links).length, clubEditions: club.rows?.length ?? null, matchdayEntries: Object.keys(days.matches).length };
  });
  await check("manifest validators and HEAD preserve legacy responses", {}, async () => {
    const response = await request("/api/dashboard/manifest"), etag = response.headers.get("etag"); assert.ok(etag);
    const conditional = await request("/api/dashboard/manifest", { headers: { "if-none-match": etag } }); assert.equal(conditional.status, 304); assert.equal(await conditional.text(), "");
    const head = await request("/api/dashboard/manifest", { method: "HEAD" }); assert.equal(head.status, 200); assert.equal(await head.text(), ""); return { conditionalStatus: 304, headStatus: 200, etag };
  });
  report.passed = checks.every((check) => check.passed);
} catch (error) { report.error = String(error.stack || error); }
finally {
  globalThis.fetch = originalFetch; server.stop(true);
  report.totals = { externalRequests: remoteCount, responseBytes: totalBytes, maximumConcurrentExternalReads: maximumRunning, localRequests: localRequests.length, checks: checks.length, passed: checks.filter((check) => check.passed).length };
  const artifact = directory + "bridge-acceptance-" + stamp + ".json";
  await writeFile(artifact, JSON.stringify(report, null, 2) + "\n");
  console.log(JSON.stringify({ passed: report.passed, error: report.error, totals: report.totals, failed: checks.filter((check) => !check.passed), artifact }));
}
process.exitCode = report.passed ? 0 : 1;
