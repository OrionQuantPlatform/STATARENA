await page.setViewportSize({width:1920,height:1080});
await page.goto("http://127.0.0.1:3000/?season=2026%2F2027&focus=europe");
await page.locator(".home-motw").waitFor({timeout:30000});
await page.locator(".home-race").waitFor();
const metrics=await page.evaluate(()=>{
  const rect=(s)=>document.querySelector(s)?.getBoundingClientRect();
  return {
    weeklyHeight:rect(".home-motw")?.height,
    playerHeight:rect(".home-potw")?.height,
    playerBottomGap:rect(".home-potw-match")?.top-rect(".home-potw-season")?.bottom,
    chartHeight:rect(".home-xg-race")?.height,
    pitchHeight:rect(".home-shot-map")?.height,
    raceBottomGap:rect(".home-race")?.bottom-Math.max(rect(".home-race-chart")?.bottom||0,rect(".home-race-legend")?.bottom||0),
    raceTeams:document.querySelectorAll(".home-race-row").length,
  };
});
await page.locator(".home-motw").screenshot({path:"/Users/lemonnierhugo/Desktop/Coding Project/Football_ranking/output/playwright/page-seasons-layout-20261103/weekly-before.png"});
await page.locator(".home-race").screenshot({path:"/Users/lemonnierhugo/Desktop/Coding Project/Football_ranking/output/playwright/page-seasons-layout-20261103/race-gap-before.png"});
return {setup:"Real 2026/2027 season, Europe scope, 1920px Chromium before compacting the weekly row.",expected:"Record current weekly row, chart imbalance, player-card spacer and title-race bottom gap.",command:"python3 output/playwright/page-seasons-layout-20261103/run_cli.py weekly-before",status:"observed",metrics};
