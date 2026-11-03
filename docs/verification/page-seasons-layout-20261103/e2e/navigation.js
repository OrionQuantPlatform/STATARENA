const report = {
  setup: "Local Next development server with real read-only Neon data; dedicated cached Chromium session.",
  command: "python3 output/playwright/page-seasons-layout-20261103/run_cli.py navigation",
  expected: "Home, calendar and players retain independent seasons across navigation, reload and history; historical record links preserve their season; no footer.",
  checks: [],
  status: "failed",
};
const record = (name, actual, expected) => {
  report.checks.push({name, actual, expected, passed: actual === expected});
  if (actual !== expected) throw new Error(`${name}: ${actual} instead of ${expected}`);
};
const year = () => page.locator("#season-filter").inputValue();
const ready = () => page.locator("#season-filter").waitFor({state: "visible", timeout: 30000});
const nav = async (name) => {
  const link = page.getByRole("navigation", {name: "Navigation principale"}).getByRole("link", {name, exact: true});
  const target = await link.getAttribute("href");
  await link.click();
  await page.waitForURL((url) => url.pathname.replace(/\/$/, "") === new URL(target, url).pathname.replace(/\/$/, ""));
  await page.waitForFunction((name) => document.querySelector(".main-nav [aria-current=page]")?.textContent === name, name);
};
const select = async (value) => {
  await page.locator("#season-filter").selectOption(value);
  await page.waitForFunction((value) => new URL(location.href).searchParams.get("season") === value, value);
  await ready();
};
try {
  await page.goto("http://127.0.0.1:3000/");
  await page.evaluate(() => { sessionStorage.clear(); localStorage.clear(); });
  await page.reload();
  await ready();
  const manifest = await page.evaluate(() => fetch("/data/dashboard-manifest.json").then((r) => r.json()));
  report.input = {defaultSeason: manifest.defaultSeason, home: "2025/2026", calendar: "2024/2025", players: "2023/2024"};
  record("fresh home year", await year(), manifest.defaultSeason);
  await select("2025/2026");
  await nav("Calendrier");
  await ready();
  record("unvisited calendar uses current year", await year(), manifest.defaultSeason);
  await select("2024/2025");
  await nav("Joueurs");
  await ready();
  record("unvisited players uses current year", await year(), manifest.defaultSeason);
  await select("2023/2024");
  await nav("Vue d’ensemble");
  await ready();
  record("home retains its year", await year(), "2025/2026");
  await page.locator(".home-race").waitFor();
  const recordHref = await page.locator(".home-race .inline-link").getAttribute("href");
  record("historical record link retains source season", new URL(recordHref, page.url()).searchParams.get("season"), "2025/2026");
  await nav("Calendrier");
  await ready();
  record("calendar retains its year", await year(), "2024/2025");
  await nav("Joueurs");
  await ready();
  record("players retains its year", await year(), "2023/2024");
  await page.reload();
  await ready();
  record("reload retains selected page year", await year(), "2023/2024");
  await nav("Vue d’ensemble");
  await ready();
  record("other page survives reload", await year(), "2025/2026");
  await page.goBack();
  await page.waitForURL((url) => url.pathname.startsWith("/joueurs"));
  await ready();
  record("back restores players", await year(), "2023/2024");
  await page.goForward();
  await page.waitForURL((url) => url.pathname === "/");
  await ready();
  record("forward restores home", await year(), "2025/2026");
  await page.goto("http://127.0.0.1:3000/matchs");
  await ready();
  record("URL without year restores that page", await year(), "2024/2025");
  record("no footer on data page", await page.locator("footer").count(), 0);
  await page.goto("http://127.0.0.1:3000/?season=1900%2F1901");
  await ready();
  record("invalid URL year falls back to saved home year", await year(), "2025/2026");
  record("invalid URL repaired", new URL(page.url()).searchParams.get("season"), "2025/2026");
  record("no footer on home", await page.locator("footer").count(), 0);
  report.status = "passed";
} catch (error) {
  report.error = error.message;
  await page.screenshot({path: "/Users/lemonnierhugo/Desktop/Coding Project/Football_ranking/output/playwright/page-seasons-layout-20261103/navigation-failure.png"});
}
return report;
