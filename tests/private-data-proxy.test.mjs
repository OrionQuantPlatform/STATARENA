import test from "node:test";
import assert from "node:assert/strict";

const revision = "a".repeat(40);
const token = "test-token-not-a-real-credential";
process.env.ORION_REMOTE_DATA = "1";
process.env.ORION_DATA_REVISION = revision;
process.env.GITHUB_DATA_TOKEN = token;
process.env.NEXT_PUBLIC_DATA_REVISION = revision;
const { handleRequest } = await import("../dashboard/backend/app.js");
const { dataJson, remoteDataUrl } = await import("../dashboard/backend/services/data-store.js");
const { dataUrl } = await import("../dashboard/frontend/src/data-url.js");
const originalFetch = globalThis.fetch;
let calls = [];
let upstreamStatus = 200;
globalThis.fetch = async (url, options) => {
  calls.push({ url: String(url), options });
  return new Response(upstreamStatus === 200 ? '{"works":true}' : "denied", { status: upstreamStatus });
};
const request = (route, method = "GET") => handleRequest(new Request(`https://site.example${route}`, { method }));

test("revisioned public data are served using a server-side Contents token", async () => {
  const url = dataUrl("dashboard-manifest.json");
  assert.equal(url, `/data/${revision}/computed/dashboard/index.json`);
  const result = await request(url);
  assert.equal(result.status, 200);
  assert.deepEqual(await result.json(), { works: true });
  assert.match(result.headers.get("cache-control"), /s-maxage=31536000/);
  assert.equal(result.headers.get("location"), null);
  assert.equal(calls.at(-1).url, `https://api.github.com/repos/OrionQuantPlatform/STATARENA/contents/data/computed/dashboard/index.json?ref=${revision}`);
  assert.equal(calls.at(-1).options.headers.Authorization, `Bearer ${token}`);
  assert.equal(calls.at(-1).options.headers.Accept, "application/vnd.github.raw+json");
  assert.doesNotMatch(JSON.stringify([...result.headers]), /test-token/);
});

test("internal JSON reads use the same authenticated revision", async () => {
  assert.deepEqual(await dataJson("raw/example.json"), { works: true });
  assert.match(calls.at(-1).url, /\/data\/raw\/example\.json\?ref=a{40}$/);
});

test("other revisions and invalid paths cannot select private repository files", async () => {
  const count = calls.length;
  assert.equal((await request(`/data/${"b".repeat(40)}/raw/index.json`)).status, 404);
  assert.equal((await request(`/data/${revision}/raw/%2e%2e%2fsecret.json`)).status, 403);
  assert.throws(() => remoteDataUrl("raw/../secret.json"), /Invalid data path/);
  assert.equal(calls.length, count);
});

test("HEAD and upstream failures do not expose credentials", async () => {
  const head = await request(`/data/${revision}/raw/index.json`, "HEAD");
  assert.equal(head.status, 200);
  assert.equal(await head.text(), "");
  upstreamStatus = 403;
  const failure = await request(`/data/${revision}/raw/denied.json`);
  assert.equal(failure.status, 503);
  assert.equal(failure.headers.get("cache-control"), "no-store");
  assert.doesNotMatch(await failure.text(), /test-token|denied/);
  upstreamStatus = 200;
});

test("public repositories still work without a token", async () => {
  delete process.env.GITHUB_DATA_TOKEN;
  const result = await request(`/data/${revision}/raw/index.json`);
  assert.equal(result.status, 307);
  assert.equal(result.headers.get("location"), `https://raw.githubusercontent.com/OrionQuantPlatform/STATARENA/${revision}/data/raw/index.json`);
});

test.after(() => { globalThis.fetch = originalFetch; });
