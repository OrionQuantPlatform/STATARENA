const report={setup:"Real Neon records; player comparison, Arsenal club scope and archive selector in Chromium.",command:"python3 output/playwright/page-seasons-layout-20261103/run_cli.py extra-country-filters",expected:"Secondary competition selectors use country groups without losing their all/reset or selection behavior.",checks:[],status:"failed"};
const check=(name,passed,actual)=>{report.checks.push({name,passed,actual});if(!passed)throw new Error(name+": "+JSON.stringify(actual));};
const base="http://127.0.0.1:3000", folder="/Users/lemonnierhugo/Desktop/Coding Project/Football_ranking/output/playwright/page-seasons-layout-20261103/";
async function grouped(selector,name){
 const el=page.locator(selector);await el.waitFor({timeout:30000});await page.waitForFunction((selector)=>document.querySelector(selector)?.querySelectorAll("optgroup option").length>0,selector);
 const state=await el.evaluate((el)=>({groups:[...el.querySelectorAll("optgroup")].map((g)=>g.label),ids:[...el.querySelectorAll("optgroup option")].map((o)=>o.value),direct:[...el.children].filter((el)=>el.tagName==="OPTION").map((o)=>o.value)}));
 check(name+" has grouped unique entries",state.groups.length>0&&state.ids.length>0&&new Set(state.ids).size===state.ids.length,state);
 check(name+" retains a single All option",JSON.stringify(state.direct)===JSON.stringify(["all"]),state.direct);
 return state;
}
try{
 await page.setViewportSize({width:1440,height:1000});await page.goto(base+"/");await page.evaluate(()=>{localStorage.removeItem("statarena.research.v1");});
 await page.goto(base+"/joueurs?season=2026%2F2027&focus=europe&playersView=table&ranking=goals&basis=total");await page.locator(".player-directory-table tbody tr").nth(1).waitFor({timeout:30000});
 await page.locator(".player-directory-table tbody tr").nth(0).getByRole("checkbox").check();await page.locator(".player-directory-table tbody tr").nth(1).getByRole("checkbox").check();
 await page.locator(".research-compare-tray").getByRole("button",{name:"Comparer",exact:true}).click();await page.getByRole("dialog").waitFor();
 const selects=page.getByRole("dialog").locator("select[aria-label^='Compétition de']");await selects.first().waitFor({timeout:30000});
 for(let i=0;i<2;i++){
  const selector="dialog select[aria-label^='Compétition de']:nth-of-type(1)";
  await page.waitForFunction((i)=>document.querySelectorAll("dialog select[aria-label^='Compétition de']")[i]?.querySelectorAll("optgroup option").length>0,i);
  const groups=await selects.nth(i).evaluate((el)=>[...el.querySelectorAll("optgroup")].map((g)=>g.label));check("comparison player "+(i+1)+" has countries",groups.length>=1,groups);
 }
 const option=await selects.first().locator("optgroup option").first().getAttribute("value");await selects.first().selectOption(option);await page.waitForFunction((id)=>document.querySelector("dialog select[aria-label^='Compétition de']")?.value===id,option);check("comparison competition remains selectable",await selects.first().inputValue()===option,option);
 await page.getByRole("dialog").screenshot({path:folder+"comparison-country-groups.png"});await page.keyboard.press("Escape");
 await page.goto(base+"/clubs?season=2026%2F2027&focus=europe&id=t_1gkhxH&clubsView=explore");const club=await grouped("select[aria-label='Compétition analysée']","club analysis");
 check("club analysis resolves domestic and Europe countries",club.groups.includes("Angleterre")&&club.groups.includes("Europe"),club.groups);
 await page.locator("select[aria-label='Compétition analysée']").selectOption(club.ids[0]);await page.waitForURL((url)=>url.searchParams.get("clubScope")===club.ids[0]);check("club analysis scope remains in URL",true,page.url());
 await page.goto(base+"/archives?season=2026%2F2027&focus=europe");const archive=await grouped("select[aria-label='Compétition des archives']","archives");
 await page.locator("select[aria-label='Compétition des archives']").selectOption(archive.ids[0]);await page.waitForURL((url)=>url.searchParams.get("ac")===archive.ids[0]);check("archive competition remains in URL",true,page.url());
 report.status="passed";
}catch(error){report.error=error.message;report.url=page.url();await page.screenshot({path:folder+"extra-country-filters-failure.png",fullPage:true});}
return report;
