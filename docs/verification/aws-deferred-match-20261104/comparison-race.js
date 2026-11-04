const site='http://127.0.0.1:18948/matchs/?focus=all&season=2026%2F2027&league=l_0ALvwF', events=[];
let stage='serie-list';page.on('response',res=>{const u=new URL(res.url());if(u.origin==='http://127.0.0.1:18947'&&u.pathname!='/api/assets')events.push([stage,u.pathname,u.searchParams.get('league'),res.status()]);});
await page.goto(site+'&tab=results',{waitUntil:'domcontentloaded'});const link=page.locator('a.match-row').first();
await link.waitFor({timeout:30000});stage='serie-match';await link.click();
const leaders=page.locator('.match-leaders-card .match-player-row');await leaders.nth(1).waitFor({timeout:18000});const names=[];
for(let i=0;i<2;i++){names.push(await leaders.nth(i).locator('.player-name').innerText());await leaders.nth(i).click();await page.getByRole('dialog').getByRole('button',{name:'Comparer ce joueur'}).click();await page.keyboard.press('Escape');}
const tray=page.locator('.compare-tray');await tray.getByRole('button',{name:'Comparer',exact:true}).waitFor();
await page.route('**/api/matches/m_1HCdf3/summary',async route=>{await new Promise(r=>setTimeout(r,500));await route.continue();});
stage='foreign';await page.evaluate(u=>history.pushState(null,'',u),site+'&id=m_1HCdf3');
await page.getByText('Yaya Fofana',{exact:true}).first().waitFor({timeout:20000});
const oldPairBefore=await tray.count()?await tray.innerText():'';
stage='foreign-player';await leaders.first().click();let player=null;
try{await page.getByRole('dialog').getByRole('button',{name:'Comparer ce joueur'}).waitFor({timeout:4500});player=(await page.getByRole('dialog').innerText()).slice(0,210);}catch{}
const error=(await page.getByRole('alert').allInnerTexts()).join(' ');
if(await page.getByRole('dialog').count())await page.keyboard.press('Escape');
stage='comparison';let originalComparison='';
if(await tray.count()){
 await tray.getByRole('button',{name:'Comparer',exact:true}).click();originalComparison=(await page.getByRole('dialog').innerText()).slice(0,500);
}
return {mode,names,oldPairBefore,player,error,originalComparison,events,passed:Boolean(player?.includes('Yaya Fofana')&&names.every(n=>oldPairBefore.includes(n)&&originalComparison.includes(n))&&events.some(([s,p,l])=>s==='foreign-player'&&p==='/api/seasons/partition'&&l==='l_0275VP')&&!events.some(([s,p])=>s==='foreign'&&p==='/api/seasons/partition'))};
