const EVENTS=[],origin='http://127.0.0.1:18947',dest='http://127.0.0.1:18948/matchs/?focus=all&season=2026%2F2027&id=m_1HCdf3';
let phase='initial',responseStart=Date.now();
page.on('response',r=>{const u=new URL(r.url());if(u.origin===origin)EVENTS.push({phase,path:u.pathname,league:u.searchParams.get('league'),status:r.status(),ms:Date.now()-responseStart,bytes:Number(r.headers()['content-length']||0)});});
await page.goto(dest,{waitUntil:'domcontentloaded',timeout:70000});
const board=page.locator('.match-scoreboard'),leader=page.locator('.match-leaders-card .match-player-row');
await board.waitFor({timeout:60000});const scoreboardMs=Date.now()-responseStart;
await leader.first().waitFor({timeout:15000});await page.waitForTimeout(350);
const initial=EVENTS.filter(r=>r.phase==='initial'),summary=await board.innerText(),names=await leader.allInnerTexts();
phase='player';
let keep, busy, retry, failed=false;
if(mode==='fault'){
  await page.route('**/api/seasons/partition?**',async route=>{if(!failed){failed=true;await route.fulfill({status:503,contentType:'application/json',body:'{}'});}else await route.continue();});
}
await leader.first().click();
if(mode!=='before'){
 busy=await page.getByRole('status').filter({hasText:'Chargement de la performance'}).count();
 keep=await board.isVisible();
 if(mode==='fault'){await page.getByRole('alert').filter({hasText:'HTTP 503'}).waitFor();retry=await page.getByRole('button',{name:'Réessayer'}).isVisible();await page.getByRole('button',{name:'Réessayer'}).click();}
}
await page.getByRole('dialog').getByRole('button',{name:'Comparer ce joueur'}).waitFor({timeout:40000});const dialog=page.getByRole('dialog');
const buttons=await dialog.getByRole('button').allTextContents();const player=await dialog.innerText();
await dialog.getByRole('button',{name:/Comparer ce joueur/i}).click();await page.keyboard.press('Escape');await leader.nth(1).click();await page.getByRole('dialog').getByRole('button',{name:/Comparer ce joueur/i}).click();await page.keyboard.press('Escape');
await page.getByRole('button',{name:/^Comparer/}).last().click();const comp=await page.getByRole('dialog').innerText();await page.keyboard.press('Escape');
const record={mode,keep,busy,retry,scoreboardMs,initial,events:EVENTS,summary:summary.slice(0,230),names,buttons,player:player.slice(0,250),comparison:comp.slice(0,350)};
return record;
