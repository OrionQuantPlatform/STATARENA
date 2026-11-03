const metrics = await page.evaluate(() => {
  const svg = document.querySelector(".home-race-chart");
  const box = svg.getBoundingClientRect();
  const nav = [...document.querySelectorAll(".main-nav a")].find((link) => link.textContent === "Joueurs");
  return {
    url: location.href,
    navPlayers: nav?.getAttribute("href"),
    width: box.width,
    height: box.height,
    viewBox: svg.getAttribute("viewBox"),
    plotFraction: (svg.viewBox.baseVal.width - 56) * svg.getScreenCTM().a / box.width,
    hasHomeSeasonControl: Boolean(document.querySelector("#season-filter")),
    emptyWrappers: [...document.querySelectorAll(".home-bento > div")].filter((el) => !el.children.length).length,
  };
});
await page.locator(".home-race").screenshot({path: "/Users/lemonnierhugo/Desktop/Coding Project/Football_ranking/output/playwright/page-seasons-layout-20261103/before-race.png"});
return metrics;
