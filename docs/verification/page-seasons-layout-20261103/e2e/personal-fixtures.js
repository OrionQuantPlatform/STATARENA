const report={setup:"Complete homepage in an isolated Chromium tab with browser-only controlled packed Neon responses. Source and production records are untouched.",command:"python3 output/playwright/page-seasons-layout-20261103/run_cli.py personal-fixtures",expected:"Saved clubs and current clubs of saved players lead. On the same Paris day: Champions, Europa, Conference, domestic. Old/national clubs, duplicates, outside-scope and out-of-horizon fixtures must not leak into priorities; no preferences retains editorial fallback.",checks:[],status:"failed"};
const check=(name,passed,actual)=>{report.checks.push({name,passed,actual});if(!passed)throw new Error(name+": "+JSON.stringify(actual));};
const folder="/Users/lemonnierhugo/Desktop/Coding Project/Football_ranking/output/playwright/page-seasons-layout-20261103/";
const tab=await page.context().newPage();
try{
 const season="2026/2027", now=Date.now(), future=new Date(now+86400000).toISOString().slice(0,10);
 const leagues=[{id:"l_4WFCIZ",name:"Premier League",country:"ENG"},{id:"l_0bfbkO",name:"Champions League",country:"UEFA"},{id:"l_38d9HA",name:"Europa League",country:"UEFA"},{id:"l_2WZ2tt",name:"Conference League",country:"UEFA"}];
 const team=(id,name)=>({id,name});const fixture=(id,league,home,away,hour,day=future)=>({id,league:leagues.find((c)=>c.id===league)||{id:league,name:"Outside scope"},season,status:"not_started",date:day,time_utc:day+"T"+hour+":00:00Z",home_team:home,away_team:away});
 const opponent=team("t_Opponent","Adversaire E2E");
 const fixtures=[
  fixture("m_Domestic","l_4WFCIZ",team("t_Domestic","Club national suivi E2E"),opponent,"12"),
  fixture("m_Conference","l_2WZ2tt",team("t_Conference","Club Conference suivi E2E"),opponent,"18"),
  fixture("m_EuropaPlayer","l_38d9HA",team("t_Current","Club actuel du joueur E2E"),opponent,"19"),
  fixture("m_Champions","l_0bfbkO",team("t_Champions","Club LDC suivi E2E"),opponent,"21"),
  fixture("m_Editorial","l_0bfbkO",team("t_41iFW3","Paris Saint-Germain"),team("t_0dVrhE","Real Madrid"),"20"),
  fixture("m_OldClub","l_0bfbkO",team("t_Old","Ancien club E2E"),opponent,"10"),
  fixture("m_NationalTeam","l_0bfbkO",team("t_National","Sélection nationale E2E"),opponent,"11"),
  fixture("m_Outside","l_Outside",team("t_Champions","Club LDC suivi E2E"),opponent,"21"),
  fixture("m_TooFar","l_0bfbkO",team("t_Champions","Club LDC suivi E2E"),opponent,"21",new Date(now+9*86400000).toISOString().slice(0,10)),
 ];fixtures.push(fixtures[3]);
 const performance=(id,teamId,country,leagueId,date)=>({id,playerRef:"p_Saved",playerId:"p_Saved",name:"Joueur suivi E2E",matchId:id,teamId,team:teamId,season,country,leagueId,date,minutes:90,rating:7,goals:0,assists:0,xg:0,xa:0});
 const performances=[performance("a_old","t_Old","ENG","l_4WFCIZ","2026-10-01"),performance("a_current","t_Current","ENG","l_4WFCIZ","2026-10-30"),performance("a_national","t_National","INT","l_WorldCup","2026-11-01")];
 const tables={players:[{id:"p_Saved",name:"Joueur suivi E2E",imageUrl:""}],performances,matches:[],shots:[],team_statistics:[],teams:[],competitions:leagues,fixtures};
 const packed={format:"orion-packed-tables-v1",meta:{},metrics:[],tables:Object.fromEntries(Object.entries(tables).map(([name,rows])=>{const keys=[...new Set(rows.flatMap((row)=>Object.keys(row)))];return [name,{keys,rows:rows.map((row)=>keys.map((key)=>row[key]??null))}];}))};
 const routePath="computed/dashboard/personal-e2e.json.gz";
 const manifest={schemaVersion:2,storage:"json-packed",defaultSeason:season,clubCountries:{},seasons:[{id:season,chunks:[{leagueId:"l_4WFCIZ",competitions:leagues,path:routePath}]}]};
 await tab.route("**/data/dashboard-manifest.json",(route)=>route.fulfill({json:manifest}));
 const gzipBytes=await tab.evaluate(async(text)=>Array.from(new Uint8Array(await new Response(new Blob([text]).stream().pipeThrough(new CompressionStream("gzip"))).arrayBuffer())),JSON.stringify(packed));
 await tab.route("**/data/"+routePath,(route)=>route.fulfill({contentType:"application/gzip",body:Buffer.from(gzipBytes)}));
 const saved=[{id:"t_Domestic",name:"Club national suivi E2E",kind:"clubs",season},{id:"t_Champions",name:"Club LDC suivi E2E",kind:"clubs",season},{id:"t_Conference",name:"Club Conference suivi E2E",kind:"clubs",season},{id:"p_Saved",name:"Joueur suivi E2E",kind:"players",season}];
 await tab.addInitScript(({saved})=>{localStorage.clear();sessionStorage.clear();localStorage.setItem("statarena.research.v1",JSON.stringify({version:1,activeList:"main",lists:[{id:"main",name:"Ma sélection",entries:saved.slice(0,2)},{id:"other",name:"Autre sélection",entries:saved.slice(2)}],comparison:[],settings:{}}));},{saved});
 await tab.goto("http://127.0.0.1:3000/?season=2026%2F2027&focus=europe");await tab.locator(".home-next-main").waitFor({timeout:30000});
 const ids=await tab.locator(".home-next-main, .home-next-list a").evaluateAll((els)=>els.map((el)=>new URL(el.href).searchParams.get("id")));
 const expected=["m_Champions","m_EuropaPlayer","m_Conference","m_Domestic","m_Editorial"];
 check("personal European match leads the card",ids[0]===expected[0],ids);
 check("same-day European order and current player's club",JSON.stringify(ids)===JSON.stringify(expected),ids);
 check("all lists participate",ids.includes("m_Conference")&&ids.includes("m_EuropaPlayer"),ids);
 check("former/national/outside/far fixtures stay out",["m_OldClub","m_NationalTeam","m_Outside","m_TooFar"].every((id)=>!ids.includes(id)),ids);
 check("fixtures are distinct",new Set(ids).size===ids.length,ids);
 const href=await tab.locator(".home-next-main").getAttribute("href");check("main action retains fixture and season",new URL(href,tab.url()).searchParams.get("id")==="m_Champions"&&new URL(href,tab.url()).searchParams.get("sourceSeason")===season,href);
 await tab.locator(".home-next").screenshot({path:folder+"personal-europe-fixtures.png"});
 await tab.setViewportSize({width:390,height:844});check("personal fixtures fit mobile",await tab.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),await tab.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth})));

 await tab.evaluate(()=>{
  localStorage.setItem("statarena.research.v1",JSON.stringify({version:1,activeList:"main",lists:[{id:"main",name:"Ma sélection",entries:[]}],comparison:[],settings:{}}));
  window.dispatchEvent(new StorageEvent("storage",{key:"statarena.research.v1"}));
 });
 await tab.waitForFunction(()=>new URL(document.querySelector(".home-next-main").href).searchParams.get("id")==="m_Editorial");
 check("empty preferences restore editorial fallback",new URL(await tab.locator(".home-next-main").getAttribute("href"),tab.url()).searchParams.get("id")==="m_Editorial",await tab.locator(".home-next-main").innerText());
 await tab.goto("http://127.0.0.1:3000/?season=2026%2F2027&focus=europe&league=l_4WFCIZ");
 await tab.locator(".home-next-main").waitFor({timeout:30000});
 const scoped=await tab.locator(".home-next-main, .home-next-list a").evaluateAll((els)=>els.map((el)=>new URL(el.href).searchParams.get("id")));
 check("explicit domestic filter remains respected",JSON.stringify(scoped)===JSON.stringify(["m_Domestic"]),scoped);
 report.inputs={now,future,saved,fixtures,performances};report.status="passed";
}catch(error){report.error=error.message;report.text=await tab.locator("body").innerText().catch(()=>"");await tab.screenshot({path:folder+"personal-fixtures-failure.png",fullPage:true});}
finally{await tab.close();}
return report;
