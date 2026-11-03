const folder = "/Users/lemonnierhugo/Desktop/Coding Project/Football_ranking/output/playwright/page-seasons-layout-20261103/";
const report = {
  setup: "Real 2026/2027 Neon data, Top 7 Europe + UEFA, desktop and 390px Chromium.",
  command: "python3 output/playwright/page-seasons-layout-20261103/run_cli.py finishing",
  expected: "Eight actual players in each finishing mode, a small bottom padding, working player dialog and no mobile overflow.",
  checks: [],
  status: "failed",
};
const check = (name, passed, actual) => {
  report.checks.push({name,actual,passed});
  if (!passed) throw new Error(name+": "+JSON.stringify(actual));
};
const metrics = () => page.locator(".home-finishing").evaluate((el) => ({
  rows:el.querySelectorAll(".home-dumbbells li").length,
  height:el.getBoundingClientRect().height,
  bottomGap:el.getBoundingClientRect().bottom-Math.max(el.querySelector(".home-dumbbells li:last-child").getBoundingClientRect().bottom,el.querySelector(".home-trend-more")?.getBoundingClientRect().bottom||0),
  names:[...el.querySelectorAll(".home-dumbbell-name strong")].map((p)=>p.textContent),
}));
try {
  await page.setViewportSize({width:1920,height:1080});
  await page.goto("http://127.0.0.1:3000/?season=2026%2F2027&focus=europe");
  await page.locator(".home-finishing").waitFor({timeout:30000});
  const clinical=await metrics();
  check("eight clinical players",clinical.rows===8,clinical);
  check("clinical gap is only normal card padding",clinical.bottomGap>=0&&clinical.bottomGap<=28,clinical.bottomGap);
  check("clinical rows contain distinct actual names",new Set(clinical.names).size===8 && clinical.names.every(Boolean),clinical.names);
  await page.locator(".home-finishing").screenshot({path:folder+"finishing-eight-clinical.png"});
  await page.locator(".home-finishing").getByRole("button",{name:"Maladroits",exact:true}).click();
  const wasteful=await metrics();
  check("eight wasteful players",wasteful.rows===8,wasteful);
  check("wasteful gap is only normal card padding",wasteful.bottomGap>=0&&wasteful.bottomGap<=28,wasteful.bottomGap);
  await page.locator(".home-finishing").screenshot({path:folder+"finishing-eight-wasteful.png"});
  const first=await page.locator(".home-finishing .home-dumbbell-name strong").first().innerText();
  await page.locator(".home-finishing .home-dumbbells button").first().click();
  await page.getByRole("dialog").waitFor({state:"visible"});
  check("player card opens for selected player",(await page.getByRole("dialog").innerText()).includes(first),first);
  await page.goto("http://127.0.0.1:3000/?season=2026%2F2027&focus=europe");
  await page.locator(".home-finishing").waitFor({timeout:30000});
  await page.setViewportSize({width:390,height:844});
  const mobile=await metrics();
  check("mobile keeps eight players",mobile.rows===8,mobile);
  check("mobile has no horizontal overflow",await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),await page.evaluate(()=>({scroll:document.documentElement.scrollWidth,viewport:innerWidth})));
  check("mobile bottom gap stays compact",mobile.bottomGap>=0&&mobile.bottomGap<=28,mobile.bottomGap);
  await page.locator(".home-finishing").screenshot({path:folder+"finishing-eight-mobile.png"});
  report.status="passed";
} catch (error) {
  report.error=error.message;
  await page.screenshot({path:folder+"finishing-failure.png",fullPage:true});
}
return report;
