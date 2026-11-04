import { readFileSync, writeFileSync } from "node:fs";
import { gzipSync } from "node:zlib";
import assert from "node:assert/strict";
const c = JSON.parse(readFileSync("/tmp/statarena-aws-runtime-20261104.json"));
assert.equal(
  c.host,
  "statarena-postgres.clcy2iqyajbl.us-east-2.rds.amazonaws.com",
);
const url = new URL("postgresql://" + c.host + "/" + c.database);
url.username = c.username;
url.password = c.password;
Object.assign(process.env, {
  DATABASE_URL: url.href,
  STATARENA_DATA_PROVIDER: "aws",
  STATARENA_METRICS_SAMPLE_RATE: "0",
});
const { handleRequest } = await import("../../../dashboard/backend/aws-app.js");
const { closeDatabase } =
  await import("../../../dashboard/backend/services/postgres.js");
const { packPartition } =
  await import("../../../dashboard/backend/services/partition-wire.js");
const { decodePartition } =
  await import("../../../dashboard/frontend/src/season_data.js");
const report = {
  runtime: process.version,
  platform: process.platform,
  arch: process.arch,
  command:
    "/tmp/statarena-node24-20261104 --expose-gc docs/verification/aws-wire-pages/profile.mjs",
  iterations: [],
};
for (let i = 0; i < 4; i++) {
  globalThis.gc?.();
  const begin = performance.now(),
    rssBefore = process.memoryUsage().rss;
  const response = await handleRequest(
    new Request(
      "http://localhost/api/seasons/partition?season=2026%2F2027&league=l_0ALvwF&limit=100&format=columns",
    ),
  );
  assert.equal(response.status, 200);
  const bytes = await response.text(),
    end = performance.now(),
    page = JSON.parse(bytes);
  const startDecode = performance.now(),
    data = decodePartition(page.data),
    startPack = performance.now(),
    packed = packPartition(data),
    startSerialize = performance.now(),
    body = JSON.stringify(packed),
    endSerialize = performance.now();
  report.iterations.push({
    iteration: i + 1,
    fullReadMs: end - begin,
    bytes: Buffer.byteLength(bytes),
    compressedBytes: gzipSync(bytes).length,
    decodeMs: startPack - startDecode,
    packMs: startSerialize - startPack,
    stringifyMs: endSerialize - startSerialize,
    rawRecordDataBytes: Buffer.byteLength(JSON.stringify(data)),
    packedDataBytes: Buffer.byteLength(body),
    rssBefore,
    rssHighWaterBytes: process.resourceUsage().maxRSS * 1024,
  });
}
await closeDatabase();
writeFileSync(
  new URL(
    "profile-" + (process.versions.bun ? "bun" : "node24") + ".json",
    import.meta.url,
  ),
  JSON.stringify(report, null, 2) + "\n",
);
