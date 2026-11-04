// Synthetic HTTP workflows; see ACCEPTANCE_PROTOCOL.md for failures specified first.
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { legacyCompatibility } from "../../../dashboard/frontend/src/server/legacy-compat.js";
import { readPages } from "../../../dashboard/frontend/src/season_data.js";

const directory = fileURLToPath(new URL("./", import.meta.url));
const source = fileURLToPath(new URL("../../../dashboard/frontend/src/server/legacy-compat.js", import.meta.url));
const stamp = new Date().toISOString().replace(/[-:.]/g, "");
const checks = [], requests = [];
const report = {
  atUtc: new Date().toISOString(),
  command: "bun docs/verification/orion-availability-20261104/fixture_integrity_e2e.mjs",
  setup: "Actual compatibility handler on ephemeral localhost Bun HTTP server; synthetic saved legacy fixtures only. No remote requests, credentials or writes.",
  expected: "Malformed or truncated saved fixture lists fail closed; complete valid HTTP pagination, filters, cursor generation and historical enumeration preserve values.",
  sourceSha256: createHash("sha256").update(await readFile(source)).digest("hex"),
  checks, requests, passed: false,
};
const fixture = (id, status, date, extra = {}) => ({ id, status, date, season: "2025/2026", league: { id: "l_3FJFUl" }, ...extra });
const valid = [fixture("m_first1", "finished", "2025-08-01"), fixture("m_next22", "not_started", "2026-05-01"), fixture("m_last33", "finished", null)];
let rows = valid, manifest = { seasons: [{ id: "2025/2026", chunks: [{ leagueId: "l_3FJFUl" }] }, { id: "2026/2027", chunks: [{ leagueId: "l_3FJFUl" }] }] };
let legacyStatus = 200;
const server = Bun.serve({ hostname: "127.0.0.1", port: 0, fetch: (request) => legacyCompatibility(request, {
  readJson: async (path) => { assert.equal(path, "raw/index.json"); return manifest; },
  handleLegacy: async (request) => {
    requests.push(new URL(request.url).pathname + new URL(request.url).search);
    return Response.json({ data: { matches: rows } }, { status: legacyStatus });
  },
}) });
const base = "/api/fixtures?league=l_3FJFUl&season=2025%2F2026&limit=1";
const request = (path = base, init) => fetch(new URL(path, server.url), init);
async function check(name, input, workflow) {
  try { const actual = await workflow(); checks.push({ name, input, passed: true, actual }); }
  catch (error) { checks.push({ name, input, passed: false, error: String(error.message || error) }); }
}
try {
  for (const malformed of [null, { date: "2025-08-01" }, { id: 123 }, { id: "" }]) {
    rows = [valid[0], malformed];
    await check("malformed fixture fails closed", rows, async () => {
      const response = await request(); const body = await response.json();
      assert.equal(response.status, 503, JSON.stringify(body));
      assert.equal(body.error?.code, "DATA_UNAVAILABLE");
      assert.ok(!body.data); return { status: response.status, code: body.error.code };
    });
  }
  rows = [valid[0], valid[0], valid[1], valid[2]];
  await check("complete cursor traversal preserves full rows and deduplicates identities", rows, async () => {
    const pages = await readPages("/api/fixtures", { league: "l_3FJFUl", season: "2025/2026", status: "all" }, (path) => request(path));
    const matches = pages.flatMap((page) => page.matches); assert.deepEqual(matches, valid);
    return { pages: pages.length, ids: matches.map((row) => row.id) };
  });
  for (const [status, expected] of [["played", [valid[0], valid[2]]], ["upcoming", [valid[1]]]]) {
    await check("fixture status " + status, { status }, async () => {
      const pages = await readPages("/api/fixtures", { league: "l_3FJFUl", season: "2025/2026", status }, (path) => request(path));
      assert.deepEqual(pages.flatMap((page) => page.matches), expected); return { count: expected.length };
    });
  }
  await check("calendar scope and historical enumeration use stored queries", {}, async () => {
    requests.length = 0;
    assert.equal((await request("/api/fixtures?from=2025-08-01&to=2025-08-01")).status, 200);
    assert.ok(requests.includes("/api/pitchapi/date/2025-08-01?status=all"));
    requests.length = 0;
    assert.equal((await request("/api/fixtures?league=l_3FJFUl")).status, 200);
    assert.equal(requests.length, 2); assert.ok(requests.every((path) => path.includes("status=all")));
    return { savedQueries: [...requests] };
  });
  await check("changed saved publication rejects the cursor", {}, async () => {
    rows = valid; const first = await (await request()).json();
    rows = [...valid, fixture("m_new444", "finished", "2025-09-01")];
    const response = await request(base + "&cursor=" + first.pagination.nextCursor);
    assert.equal(response.status, 409); return { status: response.status };
  });
  await check("legacy row limit cannot silently truncate", { rows: 20000 }, async () => {
    rows = Array.from({ length: 20000 }, (_, i) => ({ ...valid[0], id: "synthetic-" + i }));
    const response = await request(); assert.equal(response.status, 503); return { status: response.status };
  });
  rows = valid;
  for (const status of [404, 500]) {
    await check("saved source error remains visible", { status }, async () => {
      legacyStatus = status; const response = await request();
      assert.equal(response.status, status === 404 ? 404 : 503); return { status: response.status };
    });
  }
  legacyStatus = 200;
  for (const suffix of ["&season=2026%2F2027", "&status=unknown", "&limit=101", "&other=value"]) {
    await check("invalid or duplicate query rejected", suffix, async () => { const response = await request(base + suffix); assert.equal(response.status, 400); return { status: response.status }; });
  }
  await check("HEAD retains status and omits body", {}, async () => { const response = await request(base, { method: "HEAD" }); assert.equal(response.status, 200); assert.equal(await response.text(), ""); return { status: response.status }; });
  report.passed = checks.every((check) => check.passed);
} finally {
  server.stop(true);
  const artifact = directory + "fixture-integrity-" + stamp + ".json";
  await writeFile(artifact, JSON.stringify(report, null, 2) + "\n");
  console.log(JSON.stringify({ passed: report.passed, checks: checks.length, failed: checks.filter((check) => !check.passed), artifact }));
}
process.exitCode = report.passed ? 0 : 1;
