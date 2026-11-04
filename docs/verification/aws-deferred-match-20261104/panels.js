const events=[];page.on('response',r=>{const u=new URL(r.url());if(u.origin==='http://127.0.0.1:18947')events.push({path:u.pathname,league:u.searchParams.get('league'),status:r.status()});});
const root='http://127.0.0.1:18948/matchs/?focus=all&season=2026%2F2027&id=';
await page.goto(root+(mode==='shots'?'m_1HCdf3&view=shots':mode==='standings'?'m_1HCdf3&view=standings':'m_0SdhsF'),{waitUntil:'domcontentloaded'});await page.locator('.match-scoreboard').waitFor({timeout:20000});
try{
 const wanted=mode==='shots'?'/shots':mode==='standings'?'/fixtures':'/scouting/routes';
 await page.waitForFunction(()=>!document.querySelector('.match-view-panel .loading-state'),{},{timeout:10000});
 for(let n=0;n<30&&!events.find(e=>e.path.endsWith(wanted));n++)await page.waitForTimeout(150);
 await page.waitForTimeout(1000);
 return {mode,board:await page.locator('.match-scoreboard').innerText(),panel:(await page.locator('.match-view-panel').innerText()).slice(0,800),events};
}catch(e){return {error:String(e),events};}
