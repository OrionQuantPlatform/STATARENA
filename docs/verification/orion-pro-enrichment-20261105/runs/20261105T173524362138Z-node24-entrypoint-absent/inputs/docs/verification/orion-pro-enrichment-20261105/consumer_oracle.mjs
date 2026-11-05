// Real front-end consumer functions read the untouched HTTP wire.
import { readFileSync } from "node:fs";
import assert from "node:assert/strict";
import { loadClubFacts } from "../../../dashboard/frontend/src/services/club-facts.js";
import { loadPlayerHonours } from "../../../dashboard/frontend/src/services/player-honours.js";
import { safeImageUrl } from "../../../dashboard/frontend/src/services/format.js";

const responses = JSON.parse(readFileSync(process.argv[2], "utf8"));
const reads = [], unexpected = [];
globalThis.fetch = async (url) => {
  unexpected.push(url);
  throw Error("External fetch is forbidden");
};
async function fetcher(path) {
  reads.push(path);
  const r = responses[path];
  if (!r) {
    unexpected.push(path);
    throw Error("Unrecorded HTTP path");
  }
  return new Response(r.body, { status: r.status });
}
const club = await loadClubFacts("t_000001", [], fetcher);
assert.equal(club.wiki.founded, "1899");
assert.equal(club.wiki.coach.name, "Alex Fixture");
assert.equal(club.wiki.coach.photo.author, "Fixture Photographer");
assert.equal(club.observedStadium, null);
assert.equal(club.observedCoach, null);
const asset = safeImageUrl(club.wiki.coach.photo.url);
assert.equal(asset, "/api/assets?url=" + encodeURIComponent("https://upload.wikimedia.org/wikipedia/commons/a/ab/Fixture_portrait.jpg"));

const fallback = await loadClubFacts("t_000003", [], fetcher, {
  name: "Factual Fixture Club",
  country: "France",
});
assert.equal(fallback.wiki.founded, "1921");
assert.equal(fallback.wiki.coach, null);

const honours = await loadPlayerHonours("p_000001", "", fetcher);
assert.equal(honours.partial, true);
assert.equal(honours.sourceUrl, "https://en.wikipedia.org/wiki/Fixture_player");
assert.equal(honours.fetchedAt, "2026-11-04T17:00:00.000000Z");
assert.deepEqual(honours.groups, [
  { group: "Étoile Fixture", items: [
    { title: "Ligue des champions", count: 2, years: "2024/2025, 2023/2024" },
  ] },
  { group: "Distinctions individuelles", items: [
    { title: "Ballon d’Or", count: 1, years: "2025" },
  ] },
]);
assert.deepEqual(await loadPlayerHonours("p_000002", "", fetcher), {
  groups: [], partial: true,
});
assert.deepEqual(reads, [
  "/api/club-links?club=t_000001",
  "/api/club-wikidata?uefa=0000012345",
  "/api/club-links?club=t_000003",
  "/api/club-wikidata?name=Factual+Fixture+Club&country=France",
  "/api/player-honours?id=p_000001",
  "/api/player-honours?id=p_000002",
]);
assert.deepEqual(unexpected, []);
console.log(JSON.stringify({
  founded: [club.wiki.founded, fallback.wiki.founded], honourGroups: honours.groups.length,
  observedLabelledHonours: honours.groups.reduce((n, g) => n + g.items[0].count, 0),
  mediaAliasRoute: asset, reads, unexpected,
}));
