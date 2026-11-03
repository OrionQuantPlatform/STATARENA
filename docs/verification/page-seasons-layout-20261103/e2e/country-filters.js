const report={setup:"Real 2026/2027 Neon records in Chromium; country groups in native selectors and the home picker.",command:"python3 output/playwright/page-seasons-layout-20261103/run_cli.py country-filters",expected:"Competition entries remain available under one country heading; selecting/resetting a league still filters the page; home country search and mobile remain usable.",checks:[],status:"failed"};
const check=(name,passed,actual)=>{report.checks.push({name,passed,actual});if(!passed)throw new Error(name+": "+JSON.stringify(actual));};
const base="http://127.0.0.1:3000", folder="/Users/lemonnierhugo/Desktop/Coding Project/Football_ranking/output/playwright/page-seasons-layout-20261103/";
async function inspect(selector,name){
 const el=page.locator(selector); await el.waitFor({timeout:30000});
 await page.waitForFunction((selector)=>document.querySelector(selector)?.querySelectorAll("optgroup").length>0,selector);
 const state=await el.evaluate((el)=>({groups:[...el.querySelectorAll("optgroup")].map((g)=>({label:g.label,options:[...g.children].map((o)=>({value:o.value,label:o.textContent}))})),ungrouped:[...el.children].filter((x)=>x.tagName==="OPTION").map((o)=>o.value),france:el.querySelector('option[value="l_3FJFUl"]')?.parentElement.label,uefa:el.querySelector('option[value="l_0bfbkO"]')?.parentElement.label}));
 check(name+" has country groups",state.groups.length>=3,state);
 check(name+" preserves Ligue 1 under France and Champions League under Europe",state.france==="France"&&state.uefa==="Europe",state);
 check(name+" leaves only the All option ungrouped",state.ungrouped.length===1&&state.ungrouped[0]==="all",state.ungrouped);
 check(name+" has no duplicate option IDs",new Set(state.groups.flatMap((g)=>g.options.map((o)=>o.value))).size===state.groups.reduce((n,g)=>n+g.options.length,0),state.groups.map((g)=>g.label));
}
try{
 await page.setViewportSize({width:1440,height:1000}); await page.goto(base+"/");await page.evaluate(()=>{localStorage.clear();sessionStorage.clear();});
 for(const [path,selector,name] of [["/joueurs?playersView=table","#league-filter","players"],["/calendrier?tab=upcoming","#league-filter","calendar"],["/clubs?clubsView=explore","select[aria-label='Compétition des clubs']","clubs"]]){
  await page.goto(base+path+"&season=2026%2F2027&focus=europe"); await inspect(selector,name);
  await page.locator(selector).selectOption("l_3FJFUl");
  await page.waitForFunction((selector)=>document.querySelector(selector)?.value==="l_3FJFUl",selector);
  check(name+" keeps selection actionable",await page.locator(selector).inputValue()==="l_3FJFUl",page.url());
  await page.locator(selector).selectOption("all");
  await page.waitForFunction((selector)=>document.querySelector(selector)?.value==="all",selector);
  check(name+" can return to all",await page.locator(selector).inputValue()==="all",page.url());
 }
 await page.goto(base+"/?season=2026%2F2027&focus=europe");await page.locator("#home-competition-filter").click();const modal=page.getByRole("dialog");
 const groups=await modal.locator(".home-competition-section h3").allTextContents();
 check("home picker groups its countries",groups.includes("France")&&groups.includes("Europe")&&new Set(groups).size===groups.length,groups);
 await modal.getByRole("searchbox",{name:"Rechercher une compétition"}).fill("France");
 await page.waitForFunction(()=>[...document.querySelectorAll(".home-competition-section h3")].every((el)=>el.textContent==="France"));
 check("country search keeps the country heading",JSON.stringify(await modal.locator("h3").allTextContents())===JSON.stringify(["France"]),await modal.locator("h3").allTextContents());
 const choices=await modal.getByRole("checkbox").count();check("country search keeps actual competitions",choices>0,choices);
 await modal.screenshot({path:folder+"competition-groups.png"});await page.setViewportSize({width:390,height:844});
 check("mobile picker has no document overflow",await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth})));
 await modal.screenshot({path:folder+"competition-groups-mobile.png"});await modal.getByRole("button",{name:"Annuler",exact:true}).click();
 report.status="passed";
}catch(error){report.error=error.message;report.url=page.url();await page.screenshot({path:folder+"country-filters-failure.png",fullPage:true});}
return report;
