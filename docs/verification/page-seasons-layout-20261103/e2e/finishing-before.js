await page.goto("http://127.0.0.1:3000/?season=2026%2F2027&focus=europe");
await page.locator(".home-finishing").waitFor({timeout:30000});
const metrics = await page.locator(".home-finishing").evaluate((el) => ({
  rows:el.querySelectorAll(".home-dumbbells li").length,
  height:el.getBoundingClientRect().height,
  bottomGap:el.getBoundingClientRect().bottom - el.querySelector(".home-dumbbells li:last-child").getBoundingClientRect().bottom,
  width:el.getBoundingClientRect().width,
}));
await page.locator(".home-finishing").screenshot({path:"/Users/lemonnierhugo/Desktop/Coding Project/Football_ranking/output/playwright/page-seasons-layout-20261103/finishing-before.png"});
return {setup:"Current 2026/2027 real Neon season, Europe scope, desktop Chromium.",expected:"Observe the six-player finishing card and remaining bottom gap before increasing the list.",command:"python3 output/playwright/page-seasons-layout-20261103/run_cli.py finishing-before",status:"observed",metrics};
