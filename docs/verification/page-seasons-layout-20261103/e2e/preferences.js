const report = {
  setup: "Dedicated browser profile; local server and real read-only Neon data.",
  command: "python3 output/playwright/page-seasons-layout-20261103/run_cli.py preferences",
  expected: "Europe competition filter is active for new profiles; explicit All selection persists; missing/invalid page-season storage falls back safely; unavailable storage still permits navigation.",
  checks: [],
  status: "failed",
};
const check = (name, actual, expected) => {
  report.checks.push({name,actual,expected,passed:actual === expected});
  if (actual !== expected) throw new Error(`${name}: ${actual} instead of ${expected}`);
};
try {
  await page.goto("http://127.0.0.1:3000/");
  await page.evaluate(() => {sessionStorage.clear();localStorage.clear();});
  await page.goto("http://127.0.0.1:3000/");
  await page.locator("#home-competition-filter").waitFor({timeout:30000});
  check("new profile default competition scope", await page.locator("#home-competition-filter").getAttribute("aria-label"), "Filtrer les compétitions : Top 7 Europe + UEFA");
  check("new profile filter is active", await page.locator("#home-competition-filter").evaluate((el) => el.classList.contains("is-active")), true);
  await page.locator("#home-competition-filter").click();
  const modal = page.getByRole("dialog");
  await modal.getByRole("button", {name:"Toutes les compétitions",exact:true}).click();
  await modal.getByRole("button", {name:"Appliquer",exact:true}).click();
  await page.waitForFunction(() => new URL(location.href).searchParams.get("focus") === "all");
  await page.reload();
  await page.locator("#home-competition-filter").waitFor({timeout:30000});
  check("explicit All survives reload", await page.locator("#home-competition-filter").getAttribute("aria-label"), "Filtrer les compétitions : Toutes les compétitions");
  await page.evaluate(() => sessionStorage.setItem("statarena:page-seasons:v1", JSON.stringify({"/joueurs":"1900/1901","/clubs":42})));
  await page.goto("http://127.0.0.1:3000/joueurs?focus=europe");
  await page.locator("#season-filter").waitFor({timeout:30000});
  const current = await page.evaluate(() => fetch("/data/dashboard-manifest.json").then((r)=>r.json()).then((m)=>m.defaultSeason));
  check("invalid saved page year falls back", await page.locator("#season-filter").inputValue(), current);
  await page.evaluate(() => sessionStorage.setItem("statarena:page-seasons:v1", "{invalid"));
  await page.goto("http://127.0.0.1:3000/matchs?focus=europe");
  await page.locator("#season-filter").waitFor({timeout:30000});
  check("corrupt saved state falls back", await page.locator("#season-filter").inputValue(), current);
  const blocked = await page.context().newPage();
  await blocked.addInitScript(() => {
    Object.defineProperty(window,"sessionStorage",{get(){throw new DOMException("Blocked","SecurityError");}});
    Object.defineProperty(window,"localStorage",{get(){throw new DOMException("Blocked","SecurityError");}});
  });
  try {
    await blocked.goto("http://127.0.0.1:3000/?focus=europe");
    await blocked.locator("#season-filter").waitFor({timeout:30000});
    await blocked.locator("#season-filter").selectOption("2025/2026");
    await blocked.waitForFunction(() => new URL(location.href).searchParams.get("season") === "2025/2026");
    await blocked.getByRole("navigation",{name:"Navigation principale"}).getByRole("link",{name:"Joueurs",exact:true}).click();
    await blocked.waitForURL((url) => url.pathname.startsWith("/joueurs"));
    await blocked.waitForFunction(() => document.querySelector(".main-nav [aria-current=page]")?.textContent === "Joueurs");
    await blocked.locator("#season-filter").waitFor({timeout:30000});
    check("blocked storage leaves other page on current year", await blocked.locator("#season-filter").inputValue(), current);
    await blocked.getByRole("navigation",{name:"Navigation principale"}).getByRole("link",{name:"Vue d’ensemble",exact:true}).click();
    await blocked.waitForURL((url) => url.pathname === "/");
    await blocked.waitForFunction(() => document.querySelector(".main-nav [aria-current=page]")?.textContent === "Vue d’ensemble");
    await blocked.locator("#season-filter").waitFor({timeout:30000});
    check("blocked storage keeps independent in-memory selection", await blocked.locator("#season-filter").inputValue(), "2025/2026");
  } finally { await blocked.close(); }
  report.status = "passed";
} catch (error) {
  report.error = error.message;
  await page.screenshot({path:"/Users/lemonnierhugo/Desktop/Coding Project/Football_ranking/output/playwright/page-seasons-layout-20261103/preferences-failure.png",fullPage:true});
}
return report;
