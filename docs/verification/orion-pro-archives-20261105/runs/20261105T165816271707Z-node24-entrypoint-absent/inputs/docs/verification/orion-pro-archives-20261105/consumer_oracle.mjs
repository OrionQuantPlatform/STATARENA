// Original frontend functions; inputs are the captured synthetic HTTP DTOs.
import {readFileSync} from "node:fs";
import assert from "node:assert/strict";
import {archiveSeasons,buildArchiveSeason,archiveRows,archiveCsvRow} from "../../../dashboard/frontend/src/services/archive.js";
import {historicalScore,historicalCsvRow,historicalScoreNotes} from "../../../dashboard/frontend/src/services/openfootball-history.js";
import {normalizeSupplementalCup} from "../../../dashboard/frontend/src/services/cup-matches.js";
import {normalizeArchive} from "../../../dashboard/frontend/src/services/format.js";
import {loadRemoteMatch} from "../../../dashboard/frontend/src/services/remote-match.js";
import {FootballDataClient} from "../../../dashboard/frontend/src/services/football-client.js";

const v=JSON.parse(readFileSync(process.argv[2],"utf8"));
const entries=archiveSeasons(v.resultsIndex,v.goalsIndex);
assert.equal(entries.length,1);assert(entries[0].results&&entries[0].goals);
const combined=buildArchiveSeason(v.results,v.goals);
assert.equal(combined.matches.length,4);
assert(combined.matches.some((m)=>m.raw===null&&m.team1==="Observed team 3"));
const raw=v.results.competitions[0].matches.find((m)=>m.id==="m_000002");
assert.deepEqual(historicalScore(raw),[1,0]);
assert.deepEqual(historicalScoreNotes(raw),["après prolongation","tirs au but 3 – 4","Source : Original observation note"]);
assert.equal(historicalCsvRow({competition:"Fixture Cup",match:raw})[11],"8 Nov 2026 (source)");
assert.equal(historicalCsvRow({competition:"Fixture Cup",match:raw})[12],"Observed venue");
assert.equal(archiveRows(combined,"all","Observed striker").length,1);
assert(archiveCsvRow(combined.matches[0]).length>0);
if (process.argv[3]==="lists") {
  console.log(JSON.stringify({seasons:entries.length,matches:combined.matches.length,goalOnly:combined.matches.filter((m)=>m.raw===null).length}));
  process.exit(0);
}
const sup=v.supplemental.competitions[0];
assert.deepEqual(normalizeSupplementalCup(sup.results,sup.fixtures).map((m)=>m.status),["finished","finished"]);
const normalized=normalizeArchive(v.point);
assert.deepEqual(Object.keys(normalized),["match","shots"]);
assert.equal(normalized.match.data.id,"m_000001");
assert.equal(normalized.shots.data.periods[0].shots[0].expected_goals,0.82);
const client=Object.create(FootballDataClient.prototype);
client.request=()=>{throw Error("Unexpected provider fallback");};
const reads=[];
const remote=await loadRemoteMatch("m_000001",client,async(path)=>{
  reads.push(path);return path==="/api/archive/matches/m_000001"?v.point:null;
});
assert.equal(remote.id,"m_000001");assert.equal(remote.leagueId,"l_000001");
assert.equal(remote.home.name,"Observed team 1");assert.equal(remote.home.score,1);
assert.deepEqual(reads,["/api/matches/m_000001/summary","/api/archive/matches/m_000001"]);
console.log(JSON.stringify({seasons:entries.length,matches:combined.matches.length,goalOnly:combined.matches.filter((m)=>m.raw===null).length,supplemental:2,normalizedSections:Object.keys(normalized),remoteMatch:remote.id}));
