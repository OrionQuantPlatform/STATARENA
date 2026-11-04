async (page) => ({
  capturedAt: Date.now(),
  url: page.url(),
  documentIdentity: await page.evaluate(() => window.__orionDocumentIdentity),
  body: await page.locator("body").innerText(),
  rows: await page.locator(".match-row").evaluateAll((rows) => rows.map((row) => ({ href: row.getAttribute("href"), text: row.textContent }))),
  scoreboard: await page.locator(".match-scoreboard").allTextContents(),
  score: await page.locator(".scoreboard-score").allTextContents(),
  points: await page.locator("circle.shot-point").evaluateAll((points) => points.map((point) => ({ cx: point.getAttribute("cx"), cy: point.getAttribute("cy"), r: point.getAttribute("r"), label: point.getAttribute("aria-label") }))),
  shotXg: await page.locator(".shot-xg").allTextContents(),
  activeTabs: await page.getByRole("tab", { selected: true }).allTextContents(),
  viewport: await page.evaluate(() => ({ width: innerWidth, height: innerHeight, scrollWidth: document.documentElement.scrollWidth })),
  proof: page.__orionUI,
})
