// Focused real saved-data HTTP workflow specified before implementation in ACCEPTANCE_PROTOCOL.md.
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { gunzipSync } from "node:zlib";
import { readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { legacyCompatibility } from "../../../dashboard/frontend/src/server/legacy-compat.js";
import { archiveSeason } from "../../../dashboard/frontend/src/services/catalog-client.js";

const old = "https://statarena-analytics-jumo9il0b-hlemonniers-projects.vercel.app", originalFetch = globalThis.fetch;
const directory = fileURLToPath(new URL("./", import.meta.url)), stamp = new Date().toISOString().replace(/[-:.]/g, "");
const sha = (body) => createHash("sha256").update(body).digest("hex"), checks = [], network = [], cache = new Map();
const report = { atUtc: new Date().toISOString(), command: "bun docs/verification/orion-availability-20261104/archive_goals_e2e.mjs", setup: "Actual compatibility endpoint and current archiveSeason catalog client on localhost. Only the old immutable Vercel saved archive index/gzip are read (maximum 12 reads/8 MiB; no payload persisted). Synthetic metadata/error cases labelled separately. No Neon SDK credentials or provider calls.", expected: "2020/21 goals load with exact saved JSON and original validators/HEAD/cache metadata despite decoded size over 2 MiB; invalid/missing/error and encoded-size limits stay explicit.", sourceSha256: sha(await readFile(new URL("../../../dashboard/frontend/src/server/legacy-compat.js", import.meta.url))), checks, network, passed: false };
let reads = 0, totalBytes = 0, mode = "real";
async function saved(path, method = "GET", headers = {}) {
  const key = method + path + JSON.stringify(headers);
  if (!cache.has(key)) cache.set(key, (async () => {
    assert.ok(++reads <= 12); const started = performance.now();
    const response = await originalFetch(old + path, { method, headers: { "accept-encoding": "identity", ...headers }, signal: AbortSignal.timeout(30000) });
    const bytes = Buffer.from(await response.arrayBuffer()); totalBytes += bytes.length; assert.ok(totalBytes <= 8 * 1024 * 1024);
    const copied = new Headers(response.headers); copied.delete("content-encoding");
    network.push({ path, method, status: response.status, bytes: bytes.length, sha256: sha(bytes), elapsedMs: Math.round(performance.now() - started) });
    return { status: response.status, bytes, headers: copied };
  })());
  return cache.get(key);
}
const index = await saved("/data/raw/historical-goals/index.json"), compressed = await saved("/data/raw/historical-goals/2020-2021.json.gz");
assert.equal(compressed.status, 200); const decoded = gunzipSync(compressed.bytes), source = JSON.parse(decoded);
report.source = { path: "/data/raw/historical-goals/2020-2021.json.gz", compressedBytes: compressed.bytes.length, decodedBytes: decoded.length, compressedSha256: sha(compressed.bytes), decodedSha256: sha(decoded) };
const server = Bun.serve({ hostname: "127.0.0.1", port: 0, fetch: (request) => legacyCompatibility(request, {
  readJson: async (path) => { if (path === "raw/historical-goals/index.json") return JSON.parse(index.bytes); assert.equal(path, "raw/historical-goals/2020-2021.json.gz"); return source; },
  handleLegacy: async (request) => {
    if (mode === "oversize") return new Response("must not be returned", { headers: { "content-length": String(2 * 1024 * 1024 + 1), "content-type": "application/gzip" } });
    if (mode === "error") return new Response("saved data unavailable", { status: 503 });
    const url = new URL(request.url), headers = {}; if (request.headers.has("if-none-match")) headers["if-none-match"] = request.headers.get("if-none-match");
    const value = await saved(url.pathname + url.search, request.method, headers);
    return new Response(request.method === "HEAD" || value.status === 304 ? null : value.bytes, { status: value.status, headers: value.headers });
  },
}) });
const path = "/api/archives/season?kind=goals&season=2020%2F2021", request = (value = path, init) => originalFetch(new URL(value, server.url), init);
globalThis.fetch = (value, init) => typeof value === "string" && value.startsWith("/") ? request(value, init) : originalFetch(value, init);
async function check(name, workflow) { try { checks.push({ name, passed: true, actual: await workflow() }); } catch (error) { checks.push({ name, passed: false, error: String(error.stack || error) }); } }
try {
  await check("real catalog client loads exact oversized decoded archive", async () => { const value = await archiveSeason("goals", "2020/2021"); assert.deepEqual(value, source); return { decodedBytes: decoded.length, semanticSha256: sha(JSON.stringify(value)) }; });
  await check("encoded response metadata, HEAD and conditional GET", async () => {
    const response = await request(); assert.equal(response.status, 200); assert.equal(response.headers.get("content-encoding"), "gzip");
    assert.equal(response.headers.get("content-length"), String(compressed.bytes.length));
    for (const name of ["etag", "cache-control", "x-data-source"]) assert.equal(response.headers.get(name), compressed.headers.get(name));
    assert.deepEqual(await response.json(), source);
    const head = await request(path, { method: "HEAD" }); assert.equal(head.status, 200); assert.equal(await head.text(), ""); assert.equal(head.headers.get("content-length"), String(compressed.bytes.length));
    const conditional = await request(path, { headers: { "if-none-match": compressed.headers.get("etag") } }); assert.equal(conditional.status, 304); assert.equal(await conditional.text(), "");
    return { status: 200, headStatus: 200, conditionalStatus: 304, etag: response.headers.get("etag"), encodedBytes: compressed.bytes.length, cacheControl: response.headers.get("cache-control") };
  });
  await check("archive query and missing season errors remain explicit", async () => {
    const samples = [[path + "&kind=results", 400], ["/api/archives/season?kind=other&season=2020%2F2021", 400], ["/api/archives/season?kind=goals&season=wrong", 400], ["/api/archives/season?kind=goals&season=2098%2F2099", 404]];
    for (const [url, status] of samples) assert.equal((await request(url)).status, status); return samples;
  });
  await check("Accept-Encoding negotiation respects explicit coding exclusions", async () => {
    const samples = [["identity", 413], ["gzip;q=0, *;q=1", 413], ["br", 413], ["gzip, identity;q=0", 200], ["*;q=0.5", 200]];
    for (const [encoding, status] of samples) {
      const response = await request(path, { headers: { "accept-encoding": encoding } }); assert.equal(response.status, status, encoding);
      assert.equal(response.headers.get("content-encoding"), status === 200 ? "gzip" : null, encoding);
      if (status === 200) assert.deepEqual(await response.json(), source); else await response.arrayBuffer();
    }
    return samples;
  });
  await check("synthetic oversized encoded object fails closed", async () => { mode = "oversize"; const response = await request(); assert.equal(response.status, 413); assert.equal((await response.json()).error.code, "PAGE_TOO_LARGE"); return { status: 413, encodedBytes: 2 * 1024 * 1024 + 1 }; });
  await check("synthetic source error remains visible", async () => { mode = "error"; const response = await request(); assert.equal(response.status, 503); return { status: response.status }; });
  report.passed = checks.every((check) => check.passed);
} finally {
  server.stop(true); globalThis.fetch = originalFetch;
  report.totals = { externalReads: reads, responseBytes: totalBytes };
  const artifact = directory + "archive-goals-" + stamp + ".json"; await writeFile(artifact, JSON.stringify(report, null, 2) + "\n");
  console.log(JSON.stringify({ passed: report.passed, failed: checks.filter((check) => !check.passed), artifact }));
}
process.exitCode = report.passed ? 0 : 1;
