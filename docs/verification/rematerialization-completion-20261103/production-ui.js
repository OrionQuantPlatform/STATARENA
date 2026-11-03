const origin='https://statarena-analytics.vercel.app';
const out='/Users/lemonnierhugo/Desktop/Coding Project/Football_ranking/output/playwright/rematerialization-completion-20261103/';
const report={setup:'Public deployed STATARENA, real regenerated Neon data, desktop and 390px Chromium; no mocks or provider writes.',command:'python3 output/playwright/rematerialization-completion-20261103/run_cli.py production-ui',expected:'Actual shot coordinates and height from the public packed data are rendered in the homepage; player and match actions remain usable; mobile fits.',checks:[],pageErrors:[],status:'failed'};
const check=(name,passed,actual)=>{report.checks.push({name,passed,actual});if(!passed)throw new Error(name+': '+JSON.stringify(actual));};
page.on('pageerror',e=>report.pageErrors.push(e.message));
try{
 await page.setViewportSize({width:1600,height:1000});await page.goto(origin+'/?season=2026%2F2027&focus=europe'+(TEST_OPTIONS.league?'&league='+encodeURIComponent(TEST_OPTIONS.league):''));await page.locator('.home-motw').waitFor({timeout:60000});
 const href=await page.locator('.home-motw-actions a').getAttribute('href');const url=new URL(href,origin);const mid=url.searchParams.get('id'),league=url.searchParams.get('competition');
 const data=await page.evaluate(async({mid,league})=>{
  const unpack=t=>t.rows.map((r,i)=>Object.fromEntries(t.keys.flatMap((key,j)=>(t.missing?.[i]||[]).includes(j)?[]:[[key,r[j]!==null&&t.dictionaries?.[j]?t.dictionaries[j][r[j]]:r[j]]])));
  const manifest=await(await fetch('/data/dashboard-manifest.json',{cache:'no-store'})).json();const season=manifest.seasons.find(s=>s.id==='2026/2027');const chunk=season.chunks.find(c=>c.leagueId===league);const response=await fetch('/data/'+chunk.path);if(!response.ok)throw new Error('Packed data HTTP '+response.status);
  const packed=await new Response(response.body.pipeThrough(new DecompressionStream('gzip'))).json();const matches=unpack(packed.tables.matches),match=matches.find(m=>m.id===mid);const shots=unpack(packed.tables.shots).filter(s=>s.matchId===mid);const players=unpack(packed.tables.performances).filter(p=>p.matchId===mid);
  return {chunk:chunk.path,match,shots,players:players.map(p=>({id:p.id,playerId:p.playerId,isCaptain:p.isCaptain,passesAccurate:p.passesAccurate,passesAttempted:p.passesAttempted,groundDuelsWon:p.groundDuelsWon})),columns:{shots:packed.tables.shots.keys,players:packed.tables.performances.keys,matches:packed.tables.matches.keys}};
 },{mid,league});
 report.fixture={id:mid,competition:league,chunk:data.chunk,teams:[data.match.home.name,data.match.away.name],date:data.match.date};
 check('featured match uses enriched shot/player/match columns',data.columns.shots.includes('goalCrossedY')&&data.columns.shots.includes('goalCrossedZ')&&data.columns.players.includes('isCaptain')&&data.columns.matches.includes('stadium'),data.columns);
 const points=data.shots.filter(s=>!s.isOwnGoal&&[data.match.home.id,data.match.away.id].includes(s.teamId)&&Number.isFinite(s.x)&&Number.isFinite(s.y)).map(s=>({...s,home:s.teamId===data.match.home.id,px:s.teamId===data.match.home.id?105-s.x:s.x,py:s.teamId===data.match.home.id?68-s.y:s.y}));
 check('all source shots remain rendered',await page.locator('.home-shot-hit').count()===points.length,{source:points.length,rendered:await page.locator('.home-shot-hit').count()});
 const choose=predicate=>points.map((p,i)=>({...p,index:i,separation:Math.min(...points.filter((q,j)=>i!==j).map(q=>Math.hypot(p.px-q.px,p.py-q.py)))})).filter(predicate).sort((a,b)=>b.separation-a.separation)[0];
 async function hoverShot(s){await page.locator('.home-shot-hit').nth(s.index).hover();await page.locator('.home-shot-path').waitFor();return await page.locator('.home-shot-path').evaluate(el=>({x1:Number(el.getAttribute('x1')),y1:Number(el.getAttribute('y1')),x2:Number(el.getAttribute('x2')),y2:Number(el.getAttribute('y2')),className:el.getAttribute('class')}));}
 const crossed=choose(s=>!s.isBlocked&&Number.isFinite(s.goalCrossedY)&&Number.isFinite(s.goalCrossedZ)&&s.playerId&&Math.abs(s.goalCrossedY-34)>.1);
 check('a real measured noncentral goal crossing is available',Boolean(crossed),crossed&&{id:crossed.id,player:crossed.playerName,y:crossed.goalCrossedY,z:crossed.goalCrossedZ,separation:crossed.separation});
 let line=await hoverShot(crossed);let expected={x:crossed.home?0:105,y:crossed.home?68-crossed.goalCrossedY:crossed.goalCrossedY};
 check('trajectory reaches the actual goal-line crossing',Math.abs(line.x2-expected.x)<.001&&Math.abs(line.y2-expected.y)<.001&&!line.className.includes('is-estimated'),{source:crossed,expected,rendered:line});
 const tip=page.locator('.home-viz').filter({has:page.locator('.home-shot-map')}).locator('.home-tip');const text=await tip.innerText();
 const shownHeight=Number((text.match(/à ([0-9.,]+) m de haut/)||[])[1]?.replace(',','.'));
 check('shot height is visible in the tooltip',text.includes(crossed.playerName)&&Number.isFinite(shownHeight)&&Math.abs(shownHeight-crossed.goalCrossedZ)<.051,{height:crossed.goalCrossedZ,text,shownHeight});await page.locator('.home-motw').screenshot({path:out+'production-measured-goal-crossing.png'});
 const blocked=choose(s=>s.isBlocked&&Number.isFinite(s.blockedX)&&Number.isFinite(s.blockedY)&&s.playerId);
 check('a real measured blocked shot is available',Boolean(blocked),blocked&&{id:blocked.id,player:blocked.playerName,x:blocked.blockedX,y:blocked.blockedY});line=await hoverShot(blocked);expected={x:blocked.home?105-blocked.blockedX:blocked.blockedX,y:blocked.home?68-blocked.blockedY:blocked.blockedY};
 check('blocked trajectory stops at the actual block',Math.abs(line.x2-expected.x)<.001&&Math.abs(line.y2-expected.y)<.001&&!line.className.includes('is-estimated'),{source:blocked,expected,rendered:line});await page.locator('.home-motw').screenshot({path:out+'production-measured-block.png'});
 const captain=data.players.find(p=>p.isCaptain);check('real captain and attempted passes reach the site payload',Boolean(captain)&&data.players.some(p=>Number.isFinite(p.passesAttempted)),captain||data.players[0]);
 await page.locator('.home-shot-hit').nth(blocked.index).click();await page.getByRole('dialog').waitFor({timeout:30000});check('clicking the measured shot opens its real player',await page.getByRole('dialog').innerText().then(t=>t.includes(blocked.playerName)),await page.getByRole('dialog').innerText().then(t=>t.slice(0,300)));await page.keyboard.press('Escape');
 await page.setViewportSize({width:390,height:844});check('regenerated home fits mobile',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth})));await page.locator('.home-motw').screenshot({path:out+'production-enriched-mobile.png'});
 await page.locator('.home-motw-actions a').click();await page.waitForURL(u=>u.pathname.startsWith('/matchs')&&u.searchParams.get('id')===mid);await page.getByRole('heading',{level:1}).waitFor();check('complete match link keeps the real fixture',new URL(page.url()).searchParams.get('id')===mid,page.url());
 check('no application page exception',report.pageErrors.length===0,report.pageErrors);report.status='passed';
}catch(error){report.error=error.message;report.url=page.url();await page.screenshot({path:out+'production-ui-failure.png',fullPage:true});}
return report;
