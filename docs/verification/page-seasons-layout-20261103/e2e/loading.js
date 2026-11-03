const report = {
  setup: "A fresh Chromium tab; real Neon chunk requests paused briefly at the browser boundary, then continued unchanged.",
  command: "python3 output/playwright/page-seasons-layout-20261103/run_cli.py loading",
  expected: "Loading shell has no footer and links to another page's own year; archived data loads after requests resume; archived home has no empty wrappers.",
  checks: [],
  status: "failed",
};
const check = (name, actual, expected) => {
  report.checks.push({name,actual,expected,passed:actual === expected});
  if (actual !== expected) throw new Error(`${name}: ${actual} instead of ${expected}`);
};
const tab = await page.context().newPage();
let resume;
const paused = new Promise((resolve) => {resume = resolve;});
await tab.route("**/data/computed/dashboard/**", async (route) => {await paused;await route.continue();});
try {
  await tab.goto("http://127.0.0.1:3000/?season=2021%2F2022&focus=europe",{waitUntil:"domcontentloaded"});
  await tab.locator(".season-loading").waitFor({state:"visible",timeout:15000});
  check("loading footer removed",await tab.locator("footer").count(),0);
  await tab.waitForFunction(() => [...document.querySelectorAll(".main-nav a")].find((el)=>el.textContent === "Joueurs")?.getAttribute("href")?.includes("season="));
  const href = await tab.getByRole("navigation",{name:"Navigation principale"}).getByRole("link",{name:"Joueurs",exact:true}).getAttribute("href");
  check("loading navigation has independent year",new URL(href,tab.url()).searchParams.get("season"),"2026/2027");
  await tab.screenshot({path:"/Users/lemonnierhugo/Desktop/Coding Project/Football_ranking/output/playwright/page-seasons-layout-20261103/loading-no-footer.png",fullPage:true});
  resume();
  await tab.locator("#season-filter").waitFor({state:"visible",timeout:30000});
  check("oldest season loads",await tab.locator("#season-filter").inputValue(),"2021/2022");
  check("archived home footer removed",await tab.locator("footer").count(),0);
  const layout = await tab.evaluate(() => ({
    empty:[...document.querySelectorAll(".home-bento > div")].filter((el)=>!el.children.length).length,
    race:document.querySelectorAll(".home-race").length,
    weekly:document.querySelectorAll(".home-potw").length,
  }));
  check("oldest season has no empty widget wrappers",layout.empty,0);
  report.layout = layout;
  await tab.screenshot({path:"/Users/lemonnierhugo/Desktop/Coding Project/Football_ranking/output/playwright/page-seasons-layout-20261103/oldest-season-page.png",fullPage:true});
  report.status = "passed";
} catch (error) {
  report.error = error.message;
  await tab.screenshot({path:"/Users/lemonnierhugo/Desktop/Coding Project/Football_ranking/output/playwright/page-seasons-layout-20261103/loading-failure.png",fullPage:true});
} finally {resume();await tab.close();}
return report;
