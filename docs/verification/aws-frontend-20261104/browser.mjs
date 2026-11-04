import {
  archiveIndex,
  archiveSeason,
  clubRanking,
  associationRanking,
  cupIndex,
  cupTable,
} from "../../../dashboard/frontend/src/services/catalog-client.js";
import { loadPlayerHonours } from "../../../dashboard/frontend/src/services/player-honours.js";
import { loadSeason } from "../../../dashboard/frontend/src/season_data.js";
import {
  historicalFixtures,
  playerRoutes,
} from "../../../dashboard/frontend/src/services/scouting-history.js";
import { FootballDataClient } from "../../../dashboard/frontend/src/services/football-client.js";
import { cupWorkerSnapshot } from "../../../dashboard/frontend/src/services/cup-worker-client.js";
import { loadClubFacts } from "../../../dashboard/frontend/src/services/club-facts.js";

const assert = (ok, msg) => {
  if (!ok) throw Error(msg);
};
async function run() {
  const chunks = [
    { leagueId: "l_AAAAAA", sourceDigest: "v1" },
    { leagueId: "l_BBBBBB", sourceDigest: "v1" },
  ];
  const manifest = {
    storage: "aws-relational",
    schemaVersion: 4,
    defaultSeason: "2026/2027",
    seasons: [{ id: "2026/2027", chunks }],
    scouting: { version: 2 },
  };
  const season = await loadSeason(manifest, manifest.defaultSeason);
  assert(
    season.matches.length === 102 &&
      season.appearances.length === 102 &&
      season.fixtures.length === 102,
    "full page traversal",
  );
  assert(
    season.meta.shotCount === 102 &&
      season.competitions[0].sampleMatches === 101 &&
      season.teams.length === 2,
    "whole partition metadata duplicated",
  );
  assert(
    !season.matches.some((m) => m.id.includes("retired")),
    "mixed generations",
  );
  await loadSeason(manifest, manifest.defaultSeason);
  chunks[0].sourceDigest = "v2";
  await loadSeason(manifest, manifest.defaultSeason);
  const history = await historicalFixtures(manifest, "l_AAAAAA");
  assert(history.length === 103, "historical fixtures truncated");
  const routes = await playerRoutes(manifest, {
    players: ["p_AAAAAA"],
    teams: ["t_BBBBBB"],
  });
  assert(
    routes.routes.p_AAAAAA && routes.clubRoutes.t_BBBBBB,
    "scoped routes absent",
  );
  const facts = await loadClubFacts("t_BBBBBB", [], fetch, {
    name: "One",
    country: "FRA",
  });
  assert(facts.wiki?.founded === "1900", "club facts missing");
  const client = new FootballDataClient({ data: season });
  await client.loadSupplemental();
  assert(client.supplementalData.meta.v === 1, "supplemental absent");
  const cup = await cupWorkerSnapshot("open-cups", "demo", "2026/2027");
  assert(cup.matches[0].id === "cup1", "cup rows absent");
  const [
    resultIndex,
    goalIndex,
    archive,
    ranking,
    associations,
    worker,
    supplement,
    table,
    honour,
    absent,
  ] = await Promise.all([
    archiveIndex("results"),
    archiveIndex("goals"),
    archiveSeason("goals", "2020/2021"),
    clubRanking("t_BBBBBB"),
    associationRanking(2020),
    cupIndex("worker"),
    cupIndex("supplemental"),
    cupTable("FRA_CUP_demo", "2020/2021", "results"),
    loadPlayerHonours("p_AAAAAA", "First"),
    loadPlayerHonours("p_000000", "Missing"),
  ]);
  assert(
    resultIndex.seasons[0].id === goalIndex.seasons[0].id &&
      archive.season === "2020/2021",
    "archives",
  );
  assert(
    ranking[0].row === null &&
      ranking[1].row.points === 12 &&
      associations.rows[0].rank === 2,
    "rankings",
  );
  assert(
    worker.competitions.length === 1 &&
      supplement.competitions.length === 2 &&
      table[0].score === 0,
    "cup catalog",
  );
  assert(
    honour.groups.length === 1 && absent.groups.length === 0,
    "SQL-only honours",
  );
  const denseManifest={...manifest,seasons:[{id:manifest.defaultSeason,chunks:[{leagueId:"l_CCCCCC",sourceDigest:"dense"}]}]};
  const dense=await loadSeason(denseManifest,manifest.defaultSeason);
  assert(dense.matches.length===26 && dense.appearances.length===26 && dense.meta.shotCount===26 && dense.matches.every(m=>m.id.startsWith("dense")),"adaptive 413 left partial rows");
  return {
    adaptive413Matches:dense.matches.length,
    seasonMatches: season.matches.length,
    appearances: season.appearances.length,
    history: history.length,
    shotCount: season.meta.shotCount,
  };
}
try {
  window.result = { ok: true, ...(await run()) };
} catch (e) {
  window.result = { ok: false, error: String(e.stack || e) };
}
document.body.innerText = JSON.stringify(window.result);
