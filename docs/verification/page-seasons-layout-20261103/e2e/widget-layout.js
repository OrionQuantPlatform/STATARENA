const report={setup:"Real 2026/2027 Neon data, Top 7 Europe + UEFA, 1920px/390px Chromium.",command:"python3 output/playwright/page-seasons-layout-20261103/run_cli.py widget-layout",expected:"Compact weekly row and spacers; six title-race teams; wider readable tooltips; ten scorers/assist providers; three distinct defensive teams; no document overflow.",checks:[],status:"failed"};
const check=(name,passed,actual)=>{report.checks.push({name,passed,actual});if(!passed)throw new Error(name+": "+JSON.stringify(actual));};
const folder="/Users/lemonnierhugo/Desktop/Coding Project/Football_ranking/output/playwright/page-seasons-layout-20261103/";
try{
  await page.setViewportSize({width:1920,height:1080});
  await page.goto("http://127.0.0.1:3000/");
  await page.evaluate(()=>localStorage.clear());
  await page.goto("http://127.0.0.1:3000/?season=2026%2F2027&focus=europe");
  await page.locator(".home-motw").waitFor({timeout:30000});
  await page.locator(".home-race").waitFor();
  const layout=await page.evaluate(()=>{
    const rect=(s)=>document.querySelector(s)?.getBoundingClientRect();
    return {
      weeklyHeight:rect(".home-motw").height,
      playerBottomGap:rect(".home-potw-match").top-rect(".home-potw-season").bottom,
      raceBottomGap:rect(".home-race").bottom-Math.max(rect(".home-race-chart").bottom,rect(".home-race-legend").bottom),
      raceTeams:document.querySelectorAll(".home-race-row").length,
      defenceTeams:1+document.querySelectorAll(".home-defence-rivals li").length,
      defenceBottomGap:rect(".home-defence").bottom-rect(".home-defence-rivals").bottom,
      scorers:document.querySelectorAll(".home-season-scorers .home-scorers-list li").length,
      scorerBottomGap:rect(".home-season-scorers").bottom-rect(".home-season-scorers .home-trend-more").bottom,
      scorerListGap:rect(".home-season-scorers .home-trend-more").top-rect(".home-season-scorers li:last-child").bottom,
      stats:document.querySelectorAll(".home-motw .home-stat-bar").length,
    };
  });
  check("weekly row is shorter than 700px (baseline 796px)",layout.weeklyHeight<700,layout);
  check("player card spacer is compact (baseline 120px)",layout.playerBottomGap>=0&&layout.playerBottomGap<=40,layout.playerBottomGap);
  check("title race has six teams and compact bottom",layout.raceTeams===6&&layout.raceBottomGap>=0&&layout.raceBottomGap<=28,layout);
  check("defence card has three teams and compact bottom",layout.defenceTeams===3&&layout.defenceBottomGap>=0&&layout.defenceBottomGap<=28,layout);
  check("ten scorers without bottom void",layout.scorers===10&&layout.scorerBottomGap>=0&&layout.scorerBottomGap<=28&&layout.scorerListGap>=0&&layout.scorerListGap<=18,layout);
  check("all eight match statistics preserved",layout.stats===8,layout.stats);
  const defenceIds=await page.locator(".home-defence a").evaluateAll((links)=>links.map((link)=>new URL(link.href).searchParams.get("id")));
  check("defensive teams are distinct and linked",new Set(defenceIds).size===3&&defenceIds.every(Boolean),defenceIds);
  await page.locator(".home-season-scorers").getByRole("button",{name:"Passeurs",exact:true}).click();
  check("ten assist providers",await page.locator(".home-season-scorers li").count()===10,await page.locator(".home-season-scorers li").count());
  const svg=page.locator(".home-xg-race");const box=await svg.boundingBox();
  await svg.hover({position:{x:box.width*.82,y:box.height*.5}});
  await page.locator(".home-motw .home-tip").waitFor({state:"visible"});
  const tooltip=await page.locator(".home-motw .home-tip").evaluate((el)=>({width:el.getBoundingClientRect().width,left:el.getBoundingClientRect().left,right:el.getBoundingClientRect().right,rows:[...el.querySelectorAll(".home-tip-row")].map((row)=>row.getBoundingClientRect().height),text:el.textContent}));
  check("tooltip is wider with single-line team names",tooltip.width>=240&&tooltip.rows.length>=2&&tooltip.rows.every((height)=>height<=22),tooltip);
  check("tooltip stays in viewport",tooltip.left>=0&&tooltip.right<=1920,tooltip);
  await page.locator(".home-motw").screenshot({path:folder+"weekly-compact.png"});
  await page.locator(".home-potw").screenshot({path:folder+"player-week-compact.png"});
  await page.locator(".home-race").screenshot({path:folder+"race-six-teams.png"});
  await page.locator(".home-defence").screenshot({path:folder+"defence-three-teams.png"});
  await page.locator(".home-season-scorers").screenshot({path:folder+"ten-assist-providers.png"});
  await page.locator(".home-shot-hit").first().hover();
  check("shot map interaction preserved",await page.locator(".home-motw .home-tip").count()>0,await page.locator(".home-motw .home-tip").allTextContents());
  const detail=await page.locator(".home-motw-actions").getByRole("link",{name:"Analyse complète du match"}).getAttribute("href");
  check("complete match action retains match ID",Boolean(new URL(detail,page.url()).searchParams.get("id")),detail);
  await page.setViewportSize({width:390,height:844});
  await page.locator(".home-motw").screenshot({path:folder+"weekly-compact-mobile.png"});
  check("mobile does not overflow horizontally",await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth})));
  check("footer stays removed",await page.locator("footer").count()===0,await page.locator("footer").count());
  report.status="passed";
}catch(error){report.error=error.message;await page.screenshot({path:folder+"widget-layout-failure.png",fullPage:true});}
return report;
