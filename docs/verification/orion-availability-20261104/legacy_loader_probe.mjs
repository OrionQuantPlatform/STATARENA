// Exercise the historical loader with the current decoder, without editing the app.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { cp, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const root=resolve(fileURLToPath(new URL("../../../",import.meta.url)));
const out=resolve(root,"docs/verification/orion-availability-20261104");
const stamp=new Date().toISOString().replace(/[-:.]/g,"");
const host="statarena-analytics-jumo9il0b-hlemonniers-projects.vercel.app";
const base="https://"+host;
const report={atUtc:new Date().toISOString(),command:"bun docs/verification/orion-availability-20261104/legacy_loader_probe.mjs",
  setup:"Exact 0aaf316 season loader and URL helper copied to a temporary directory with the current packed_data.js; fetches only the old Vercel host's saved Neon manifest and chunks. No application edits or provider calls.",
  expected:"The historic loadSeason(manifest, season, fetcher, leagueIds) contract remains usable with the current decoder for current and historical Ligue 1 data.",checks:[],passed:false};
const tmp=await mkdtemp(join(tmpdir(),"statarena-legacy-loader-"));
try {
  await writeFile(join(tmp,"package.json"),'{"type":"module"}\n');
  for(const name of ["season_data.js","data-url.js"]) {
    const data=execFileSync("git",["show",`0aaf316e0aa525c90b3787df623bb5bfcc2936c8:dashboard/frontend/src/${name}`],{cwd:root});
    await writeFile(join(tmp,name),data);
  }
  await cp(join(root,"dashboard/frontend/src/packed_data.js"),join(tmp,"packed_data.js"));
  const legacy=await import(pathToFileURL(join(tmp,"season_data.js")));
  const fetcher=(path,init)=>{ const url=new URL(path,base); assert.equal(url.hostname,host); return fetch(url,init); };
  const r=await fetcher("/data/dashboard-manifest.json"); assert.equal(r.status,200);
  const manifest=await r.json(); assert.equal(manifest.storage,"json-packed");
  for(const season of ["2026/2027","2025/2026"]) {
    const data=await legacy.loadSeason(manifest,season,fetcher,new Set(["l_3FJFUl"]));
    assert.equal(data.meta.currentSeason,season); assert.ok(data.matches.length>0); assert.ok(data.appearances.length>0);
    assert.ok(data.fixtures.length>0); assert.ok(data.competitions.some(c=>c.id==="l_3FJFUl"));
    report.checks.push({season,matchCount:data.matches.length,appearanceCount:data.appearances.length,fixtureCount:data.fixtures.length,
      competitionCount:data.competitions.length,passed:true});
  }
  report.passed=true;
} catch(e) { report.error=String(e?.stack||e); }
finally {
  await rm(tmp,{recursive:true,force:true});
  await writeFile(join(out,`legacy-loader-${stamp}.json`),JSON.stringify(report,null,2)+"\n");
  console.log(JSON.stringify({passed:report.passed,error:report.error,checks:report.checks,artifact:`legacy-loader-${stamp}.json`}));
}
process.exitCode=report.passed?0:1;
