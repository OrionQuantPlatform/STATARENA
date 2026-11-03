import assert from "node:assert/strict";
import { gunzipSync } from "node:zlib";
import { handleRequest } from "../dashboard/backend/app.js";
import { database } from "../dashboard/backend/services/neon.js";

const get = (path) => handleRequest(new Request("http://localhost" + path));
try {
  const health = await get("/api/health");
  assert.equal(health.status, 200);
  const profile = await get("/api/pitchapi/players/p_TEST02");
  assert.equal(profile.status, 200);
  assert.equal((await profile.json()).data.id, "p_TEST02");
  const manifestResponse = await get("/data/dashboard-manifest.json");
  assert.equal(manifestResponse.status, 200);
  const manifest = await manifestResponse.json();
  const chunk = manifest.seasons.find((s) => s.id === "2010/2011").chunks[0];
  const chunkResponse = await get("/data/" + chunk.path);
  assert.equal(chunkResponse.status, 200);
  const packed = JSON.parse(gunzipSync(Buffer.from(await chunkResponse.arrayBuffer())));
  assert.equal(packed.meta.matchCount, 1);
  console.log(JSON.stringify({ status: "passed", checks: ["health", "profile", "manifest", "stored_chunk"] }));
} finally {
  await database().end();
}
