/** Small, read-only descriptive HTTP comparison; no production load claim. */
import { readFile, writeFile } from "node:fs/promises";
import { createHash } from "node:crypto";
const here = new URL("./", import.meta.url);
const sample = JSON.parse(await readFile(new URL("public-http.json", here))).sample;
const origins = {
  before: "https://statarena-analytics-naa4pt51w-hlemonniers-projects.vercel.app",
  after: "https://statarena-analytics-itzkb5hqy-hlemonniers-projects.vercel.app",
};
const report = {
  command: "bun docs/verification/backend-cache-20261103/deployment/benchmark.mjs",
  setup: "Same local client/network, one public player profile, alternating old/new production deployment URLs, one warm-up per URL then 20 samples each. Provider collection not invoked. Geographic latency and platform egress are not measured.",
  expected: "Both deployments return 200 and identical bytes. Describe p50/p95 and observed CDN states; do not attribute their difference causally to P0.",
  path: `/api/pitchapi/players/${sample.player}`, origins, samples: [], status: "failed",
};
try {
  for (let round = -1; round < 20; round++) for (const [version, base] of Object.entries(origins)) {
    const start = performance.now();
    const response = await fetch(base + report.path, { redirect: "error", signal: AbortSignal.timeout(20000) });
    const bytes = Buffer.from(await response.arrayBuffer());
    const row = { version, round, ms: performance.now() - start, status: response.status, bytes: bytes.length, sha256: createHash("sha256").update(bytes).digest("hex"), headers: Object.fromEntries(response.headers) };
    report.samples.push(row);
    if (row.status !== 200) throw new Error(`${version} returned ${row.status}`);
  }
  if (new Set(report.samples.map((s) => s.sha256)).size !== 1) throw new Error("Data changed; no comparable response-byte result");
  report.summary = Object.fromEntries(Object.keys(origins).map((version) => {
    const rows = report.samples.filter((r) => r.version === version && r.round >= 0), times = rows.map((r) => r.ms).sort((a,b) => a-b);
    const states = {};
    for (const r of rows) { const state = r.headers["x-vercel-cache"] || "not-exposed"; states[state] = (states[state] || 0) + 1; }
    return [version, { samples: rows.length, bytes: rows[0].bytes, p50Ms: times[Math.ceil(times.length * .5) - 1], p95Ms: times[Math.ceil(times.length * .95) - 1], cdnStates: states }];
  }));
  report.status = "passed";
} catch (error) { report.error = error.message; process.exitCode = 1; }
await writeFile(new URL("benchmark.json", here), JSON.stringify(report, null, 2) + "\n");
console.log(JSON.stringify({ status: report.status, error: report.error, summary: report.summary }));
