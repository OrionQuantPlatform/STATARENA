import { readFileSync } from "node:fs";
import assert from "node:assert/strict";
import { associationRanking, clubRanking } from "../../../dashboard/frontend/src/services/catalog-client.js";
import { associationRanks, europeanPlaces, performanceSpots } from "../../../dashboard/frontend/src/services/standings-zones.js";

const wire = JSON.parse(readFileSync(process.argv[2], "utf8"));
const calls = [], unexpected = [];
globalThis.fetch = async (path) => {
  calls.push(path);
  if (!Object.hasOwn(wire, path)) {
    unexpected.push(path);
    throw Error("Unrecorded HTTP path");
  }
  return new Response(wire[path].body, { status: wire[path].status });
};
const earlier = await associationRanking(2026);
const running = await associationRanking(2027);
assert.deepEqual([...associationRanks(earlier)], [["FRA", 1], ["ESP", 2], ["ITA", 2]]);
assert.deepEqual([...performanceSpots(running, 2027)], ["ESP", "ITA"]);
assert.deepEqual(europeanPlaces(associationRanks(earlier).get("FRA"), { eps: false }),
  ["cl", "cl", "cl", "cl", "el", "ecl"]);
assert.equal(running.rows[0].sourceRow.seasonRankings[0].nationalAssociationPoints, 0);
assert.equal(running.rows[1].sourceRow.seasonRankings[0].nationalAssociationPoints, null);
assert.equal(running.rows.some((r) => r.sourceRow?.overallRanking?.numberOfTeamsStillInPlaying > 0), false);
const club = await clubRanking("t_000001");
assert.deepEqual(club.map(({ edition, row }) => [edition.edition, edition.period, row?.position ?? null]),
  [["2027.uefa", "2026/2027", null], ["2026.uefa", "2025/2026", 2]]);
assert.equal(club[1].row.entityId, "uefa:0000012345");
assert.equal(club[1].row.points, 123.450001);
assert.equal(await clubRanking("t_000003"), null);
assert.deepEqual(calls, [
  "/api/rankings/associations?year=2026", "/api/rankings/associations?year=2027",
  "/api/rankings/club?club=t_000001", "/api/rankings/club?club=t_000003",
]);
assert.deepEqual(unexpected, []);
console.log(JSON.stringify({ calls, unexpected, rankFRA: 1, observedPerformanceSpots: ["ESP", "ITA"], clubEditions: 2 }));
