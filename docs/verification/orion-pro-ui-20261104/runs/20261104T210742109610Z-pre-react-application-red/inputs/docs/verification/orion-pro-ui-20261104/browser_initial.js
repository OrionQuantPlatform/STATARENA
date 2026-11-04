async (page) => {
  const proof = page.__orionUI;
  try {
    await page.waitForFunction(() => document.querySelectorAll(".match-row").length === 30, null, { timeout: 20000 });
  } catch (error) { proof.initialWait = String(error); }
  return {
    url: page.url(),
    rows: await page.locator(".match-row").count(),
    links: await page.locator(".match-row").evaluateAll((rows) => rows.map((row) => ({ href: row.getAttribute("href"), text: row.textContent }))),
    body: await page.locator("body").innerText(),
    proof,
  };
}
