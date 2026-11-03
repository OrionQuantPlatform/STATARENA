const report={setup:"Real 2026/2027 Neon data; independent Chromium profile; home cards → complete player rankings.",command:"python3 output/playwright/page-seasons-layout-20261103/run_cli.py ranking-links",expected:"Each shortcut preserves its mode, season and competition sample; totals and leading players match the card; reload/profile/back/reset remain usable.",checks:[],status:"failed"};
const check=(name,passed,actual)=>{report.checks.push({name,passed,actual});if(!passed)throw new Error(name+": "+JSON.stringify(actual));};
const base="http://127.0.0.1:3000";
async function home(extra=""){
  await page.goto(base+"/?season=2026%2F2027&focus=europe"+extra);
  await page.locator(".home-finishing").waitFor({timeout:30000});
  await page.locator(".home-season-scorers").waitFor();
}
async function openRanking(key,extra=""){
  await home(extra);
  const card=page.locator(key==="clinical"||key==="wasteful"?".home-finishing":".home-season-scorers");
  const labels={clinical:"Efficaces",wasteful:"Maladroits",goals:"Buteurs",assists:"Passeurs"};
  await card.getByRole("button",{name:labels[key],exact:true}).click();
  const expected=await card.locator("li[data-player-id]").evaluateAll((items)=>items.map((el)=>el.dataset.playerId));
  const link=card.getByRole("link",{name:"Tous les joueurs",exact:true});
  const href=await link.getAttribute("href");
  const target=new URL(href,page.url());
  check(key+" explicit season and ranking",target.searchParams.get("ranking")===key&&target.searchParams.get("season")==="2026/2027"&&target.searchParams.get("basis")==="total",href);
  await link.click();
  await page.waitForURL((url)=>url.pathname.startsWith("/joueurs")&&url.searchParams.get("ranking")===key);
  await page.locator("#player-ranking-filter").waitFor({timeout:30000});
  await page.waitForFunction(({ids,key})=>{
    const rows=[...document.querySelectorAll(".player-directory-table tbody tr")].slice(0,ids.length).map((el)=>el.dataset.playerId);
    return document.querySelector("#player-ranking-filter")?.value===key&&JSON.stringify(rows)===JSON.stringify(ids);
  },{ids:expected,key});
  const actual=await page.locator(".player-directory-table tbody tr").evaluateAll((items)=>items.map((el)=>el.dataset.playerId));
  check(key+" leading players match the home",expected.length>0&&JSON.stringify(actual.slice(0,expected.length))===JSON.stringify(expected),{expected,actual:actual.slice(0,expected.length)});
  check(key+" totals control is active",await page.locator(".player-directory-toolbar").getByRole("button",{name:"Total",exact:true}).getAttribute("aria-pressed")==="true",await page.locator("#player-ranking-filter").inputValue());
  return {target,expected,actual};
}
try{
  await page.goto(base+"/");
  await page.evaluate(()=>localStorage.clear());
  for(const key of ["clinical","wasteful","goals","assists"]){
    const result=await openRanking(key);
    check(key+" expands beyond the home shortlist",result.actual.length>result.expected.length,{home:result.expected.length,directory:result.actual.length});
    if(key==="goals"){
      await page.reload();
      await page.locator("#player-ranking-filter").waitFor({timeout:30000});
      check("scorer ranking survives reload",await page.locator("#player-ranking-filter").inputValue()==="goals",page.url());
    }
  }
  await openRanking("clinical","&league=l_3FJFUl");
  check("single competition stays selected",await page.locator("#league-filter").inputValue()==="l_3FJFUl",page.url());
  await page.locator("#player-ranking-filter").selectOption("");
  await page.waitForFunction(()=>!new URL(location.href).searchParams.has("ranking")&&document.querySelector("#player-ranking-filter")?.value==="");
  check("ranking can be removed",await page.locator("#player-ranking-filter").inputValue()==="",page.url());
  await home();
  await page.locator("#home-competition-filter").click();
  const modal=page.getByRole("dialog");
  await modal.getByRole("button",{name:"Toutes les compétitions",exact:true}).click();
  await modal.getByRole("button",{name:"Appliquer",exact:true}).click();
  await page.evaluate(()=>{
    const key=Object.keys(localStorage).find((name)=>{try{return Array.isArray(JSON.parse(localStorage.getItem(name)).favoriteLeagueIds);}catch{return false;}});
    if(!key)throw new Error("Saved competition preferences missing");
    const saved=JSON.parse(localStorage.getItem(key));
    localStorage.setItem(key,JSON.stringify({...saved,focus:"all",favoriteLeagueIds:["l_3FJFUl","l_4WFCIZ"],onboardingComplete:true}));
  });
  await page.goto(base+"/?season=2026%2F2027&focus=all");
  await page.locator(".home-season-scorers").waitFor({timeout:30000});
  const customCard=page.locator(".home-season-scorers");
  const expected=await customCard.locator("li[data-player-id]").evaluateAll((items)=>items.map((el)=>el.dataset.playerId));
  await customCard.getByRole("link",{name:"Tous les joueurs",exact:true}).click();
  await page.waitForURL((url)=>url.pathname.startsWith("/joueurs")&&url.searchParams.get("ranking")==="goals");
  await page.locator("#player-ranking-filter").waitFor({timeout:30000});
  await page.waitForFunction((ids)=>JSON.stringify([...document.querySelectorAll(".player-directory-table tbody tr")].slice(0,ids.length).map((el)=>el.dataset.playerId))===JSON.stringify(ids),expected);
  const cohorts=new URL(page.url()).searchParams.get("leagues").split(",").sort();
  check("custom competition cohort survives shortcut",JSON.stringify(cohorts)===JSON.stringify(["l_3FJFUl","l_4WFCIZ"].sort()),cohorts);
  check("custom cohort is visible and removable",await page.getByRole("button",{name:"Retirer les compétitions de l’accueil",exact:true}).count()===1,page.url());
  const first=page.locator(".player-directory-table tbody tr").first();
  await first.getByRole("checkbox").check();
  await page.waitForFunction((ids)=>JSON.parse(localStorage.getItem("statarena.research.v1"))?.comparison.some((p)=>JSON.stringify(p.scope.leagues)===JSON.stringify(ids)),cohorts);
  check("saved comparison retains custom cohort",true,cohorts);
  const name=await first.locator(".player-name").innerText();
  await first.locator(".table-player").click();
  await page.waitForURL((url)=>url.searchParams.has("id"));
  await page.getByRole("heading",{name,exact:true}).first().waitFor({state:"visible",timeout:30000});
  check("profile retains ranking and cohort",new URL(page.url()).searchParams.get("ranking")==="goals"&&new URL(page.url()).searchParams.has("leagues"),page.url());
  await page.goBack();
  await page.locator("#player-ranking-filter").waitFor({timeout:30000});
  await page.getByRole("button",{name:"Retirer les compétitions de l’accueil",exact:true}).click();
  await page.waitForFunction(()=>!new URL(location.href).searchParams.has("leagues"));
  check("cohort can be removed",true,page.url());
  await page.setViewportSize({width:390,height:844});
  check("ranking page has no mobile document overflow",await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth})));
  await page.screenshot({path:"/Users/lemonnierhugo/Desktop/Coding Project/Football_ranking/output/playwright/page-seasons-layout-20261103/ranking-mobile.png",fullPage:true});
  report.status="passed";
}catch(error){report.error=error.message;report.url=page.url();report.visibleRanking=await page.locator("#player-ranking-filter").inputValue().catch(()=>null);report.visiblePlayerIds=await page.locator(".player-directory-table tbody tr").evaluateAll((rows)=>rows.map((row)=>row.dataset.playerId)).catch(()=>[]);await page.screenshot({path:"/Users/lemonnierhugo/Desktop/Coding Project/Football_ranking/output/playwright/page-seasons-layout-20261103/ranking-links-failure.png",fullPage:true});}
return report;
