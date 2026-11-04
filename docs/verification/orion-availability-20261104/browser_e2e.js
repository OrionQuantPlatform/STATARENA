const host = "statarena-analytics-jumo9il0b-hlemonniers-projects.vercel.app";
const base = "https://" + host;
const report = {setup:"Real headless Chromium on the old immutable Vercel deployment and its Neon-backed saved data. Every other browser network host is blocked; no provider calls or mocks.",
  command:"python3 docs/verification/orion-availability-20261104/run_browser.py",
  expected:"Current Ligue 1 home loads, a match and its team statistics open, and the prior season loads at mobile width without horizontal overflow.",
  checks:[], responses:[], pageErrors:[], status:"failed"};
const check = (name, condition, details) => { report.checks.push({name,passed:!!condition,details}); if (!condition) throw Error(name); };
page.on("pageerror", e => report.pageErrors.push(e.message));
page.on("response", r => { const u=new URL(r.url()); if(u.hostname===host && (u.pathname.startsWith("/data/") || u.pathname.startsWith("/api/"))) report.responses.push({path:u.pathname,status:r.status()}); });
try {
  await page.route("**/*", route => { const u = new URL(route.request().url()); return u.hostname===host ? route.continue() : route.abort(); });
  await page.setViewportSize({width:1600,height:1000});
  await page.goto(base+"/?season=2026%2F2027&focus=europe&league=l_3FJFUl");
  await page.locator(".home-motw").waitFor({timeout:60000});
  const selected = await page.getByRole("combobox",{name:"Saison"}).inputValue();
  const matchLink = page.locator('.home-motw a[href*="/matchs?"]').first();
  const matchHref = await matchLink.getAttribute("href");
  const matchId = new URL(matchHref,base).searchParams.get("id");
  check("current season and featured match",selected==="2026/2027" && !!matchId,{selected,matchId});
  await matchLink.click();
  await page.getByRole("tab",{name:"Statistiques"}).waitFor({timeout:30000});
  check("match route retains selected match",new URL(page.url()).searchParams.get("id")===matchId,{url:page.url()});
  await page.getByRole("tab",{name:"Statistiques"}).click();
  const stats=page.getByRole("region",{name:"Statistiques des équipes"});
  await stats.waitFor({timeout:30000});
  check("team statistics rendered",(await stats.innerText()).includes("Possession"),{});
  await page.screenshot({path:ARTIFACT_PREFIX+"-match.png"});
  await page.goto(base+"/?season=2025%2F2026&focus=europe&league=l_3FJFUl");
  await page.locator(".home-motw").waitFor({timeout:60000});
  const history = await page.getByRole("combobox",{name:"Saison"}).inputValue();
  check("historical season rendered",history==="2025/2026",{selected:history});
  await page.setViewportSize({width:390,height:844});
  const dimensions=await page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth}));
  check("mobile page fits viewport",dimensions.scrollWidth<=dimensions.width,dimensions);
  await page.screenshot({path:ARTIFACT_PREFIX+"-mobile.png"});
  check("no application page exceptions",report.pageErrors.length===0,report.pageErrors);
  report.status="passed";
} catch(error) { report.error=error.message; report.url=page.url(); await page.screenshot({path:ARTIFACT_PREFIX+"-failure.png"}); }
return report;
