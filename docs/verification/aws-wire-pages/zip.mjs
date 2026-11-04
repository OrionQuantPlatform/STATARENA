import { readFileSync, writeFileSync } from "node:fs";
import { gunzipSync } from "node:zlib";
import assert from "node:assert/strict";
import { pathToFileURL } from "node:url";
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
  DATABASE_POOL_MAX: "1",
  LAMBDA_TASK_ROOT: "/tmp/statarena-wire-zip",
  STATARENA_METRICS_SAMPLE_RATE: "0",
});
const { handler } = await import(
  pathToFileURL(process.env.LAMBDA_TASK_ROOT + "/index.mjs")
);
const report = {
  command:
    "/tmp/statarena-node24-20261104 --max-old-space-size=256 docs/verification/aws-wire-pages/zip.mjs",
  runtime: process.version,
  heapCapMiB: 256,
  platform: process.platform,
  iterations: [],
};
let etag;
const invoke = (method, headers) =>
  handler({
    version: "2.0",
    rawPath: "/api/seasons/partition",
    rawQueryString:
      "season=2026%2F2027&league=l_0ALvwF&limit=100&format=columns",
    headers,
    requestContext: { http: { method } },
  });
for (let i = 0; i < 5; i++) {
  const start = performance.now(),
    cpu = process.cpuUsage(),
    r = await invoke("GET", { "accept-encoding": "gzip" }),
    dt = performance.now() - start,
    used = process.cpuUsage(cpu);
  assert.equal(r.statusCode, 200);
  assert.equal(r.headers["content-encoding"], "gzip");
  etag = r.headers.etag;
  const zipped = Buffer.from(r.body, "base64"),
    bytes = gunzipSync(zipped).length;
  report.iterations.push({
    ms: dt,
    processCpuMs: (used.user + used.system) / 1000,
    gzipBytes: zipped.length,
    bodyBytes: bytes,
    peakRssMiB: process.resourceUsage().maxRSS / 1024,
  });
}
for (const [method, headers, status] of [
  ["HEAD", {}, 200],
  ["GET", { "if-none-match": etag }, 304],
  ["HEAD", { "if-none-match": etag }, 304],
]) {
  const r = await invoke(method, headers);
  assert.equal(r.statusCode, status);
  assert.ok(!r.body);
  assert.equal(r.headers.etag, etag);
  report.iterations.push({
    method,
    expectedStatus: status,
    observed: r.statusCode,
    empty: true,
  });
}
report.passed = true;
writeFileSync(
  new URL("zip-node24.json", import.meta.url),
  JSON.stringify(report, null, 2) + "\n",
);
console.log(JSON.stringify(report));
process.exit();
