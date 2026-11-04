const events=[];let phase='cold';page.on('response',r=>{const u=new URL(r.url());if(u.origin==='http://127.0.0.1:18947')events.push({phase,path:u.pathname,status:r.status()});});const root='http://127.0.0.1:18948/matchs/?focus=all&season=2026%2F2027';
if(mode==='warm'){
 await page.goto(root+'&tab=results&league=l_0275VP',{waitUntil:'domcontentloaded',timeout:60000});const link=page.locator('a.match-row').first();try{await link.waitFor({timeout:15000});}catch(e){return {error:String(e),body:(await page.locator('body').innerText()).slice(-1500),events};}await page.waitForTimeout(650);phase='match';
 await link.click();await page.locator('.match-scoreboard').waitFor({timeout:20000});await page.waitForTimeout(420);
 return {mode,match:await page.locator('.match-scoreboard').innerText(),events};
}
await page.goto(root+'&id=m_1HCdf3',{waitUntil:'domcontentloaded',timeout:60000});await page.locator('.match-scoreboard').waitFor({timeout:35000});
phase='bookmark';const mark=page.locator('.research-bookmark').first();await mark.click();const saved=await mark.getAttribute('aria-pressed');await page.waitForTimeout(200);
phase='search';const search=page.getByRole('combobox').first();await search.fill('Yaya Fofana');const hit=page.getByRole('option').filter({hasText:'Yaya Fofana'}).first();await hit.waitFor({timeout:30000});return {mode,saved,hit:await hit.innerText(),events};
