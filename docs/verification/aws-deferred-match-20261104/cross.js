const root='http://127.0.0.1:18948/matchs/?focus=all&season=2026%2F2027',id='m_1HCdf3',events=[];let stage='start';
page.on('response',r=>{const u=new URL(r.url());if(u.origin==='http://127.0.0.1:18947'&&u.pathname!='/api/assets')events.push([stage,u.pathname,u.searchParams.get('season'),u.searchParams.get('league'),r.status()]);});
if(mode.startsWith('native'))await page.route('**/api/matches/'+id+'/summary',async route=>{const r=await route.fetch();const b=await r.json();b.data.match.season='2026';await route.fulfill({response:r,json:b});});
if(mode.startsWith('foreign')){
 await page.goto(root+'&tab=results&league=l_0ALvwF',{waitUntil:'domcontentloaded'});await page.locator('a.match-row').first().waitFor({timeout:30000});await page.waitForTimeout(350);
 stage='match';await page.evaluate(u=>history.pushState(null,'',u),root+'&id='+id+'&league=l_0ALvwF');
}else{
 stage='match';await page.goto(root+'&id='+id,{waitUntil:'domcontentloaded'});
}
await page.locator('.match-leaders-card .match-player-row').first().waitFor({timeout:35000});
await page.waitForTimeout(200);stage='player';await page.locator('.match-leaders-card .match-player-row').first().click();
if(mode.startsWith('cancel')){
 const busy=page.getByRole('dialog').filter({hasText:/Chargement/});await busy.waitFor({timeout:4000});await page.keyboard.press('Escape');await page.waitForTimeout(1300);return {mode,remainingDialogs:await page.getByRole('dialog').count(),board:await page.locator('.match-scoreboard').isVisible(),events};
}
try{await page.getByRole('dialog').getByRole('button',{name:'Comparer ce joueur'}).waitFor({timeout:4500});}catch{}
return {mode,actualPlayer:await page.getByRole('dialog').getByRole('button',{name:'Comparer ce joueur'}).count(),error:await page.getByRole('alert').allInnerTexts(),body:(await page.getByRole('dialog').allInnerTexts()).join('\n').slice(0,180),events};
