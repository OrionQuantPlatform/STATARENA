const {site,api,s,out}=OPT, m=s.match, p=s.player;
const result={checks:[],football:[],violations:[],exceptions:[],errors:[],views:[],passed:false};let phase='bootstrap';
function check(name,ok,actual){result.checks.push({name,ok:Boolean(ok),actual});return Boolean(ok);}
const safe=(u)=>u.origin+u.pathname;
const external=/(^|\.)(pitchapi\.dev|thesportsdb\.com|wikidata\.org|wikipedia\.org|openligadb\.de|uefa\.com|amazonaws\.com|githubusercontent\.com)$/i;
page.on('pageerror',e=>result.exceptions.push({phase,type:e.name}));
page.on('request',r=>{
 const u=new URL(r.url()),type=r.resourceType(),structured=['fetch','xhr','eventsource','websocket'].includes(type);
 if((u.pathname.startsWith('/api/')&&u.origin!==api&&!(u.origin===site&&u.pathname==='/api/visitor-country'))||structured&&(u.pathname.startsWith('/data/')||external.test(u.hostname)))result.violations.push({phase,type,url:safe(u)});
});
page.on('response',r=>{
 const u=new URL(r.url());
 if(u.origin===api)result.football.push({phase,path:u.pathname,status:r.status(),method:r.request().method(),ttfbMs:r.request().timing().responseStart,edge:r.headers()['x-cache']||null});
});
const url=(path,params)=>site+path+'?'+new URLSearchParams(params);
const remote=url('/matchs/',{season:s.alternate.season,league:s.alternate.league_id,focus:'all',id:m.id,sourceSeason:m.season,competition:m.league_id,tab:'results'});
const playerUrl=url('/joueurs/',{season:m.season,league:m.league_id,focus:'all',id:p.player_id});
const base='/api/pitchapi/matches/'+m.id,summary='/api/matches/'+m.id+'/summary',archive='/api/archive/matches/'+m.id;
const getSince=(idx)=>result.football.slice(idx);
const did=(list,path)=>list.some(x=>x.path===path&&x.status===200);
async function go(name,target){phase=name;const res=await page.goto(target,{waitUntil:'domcontentloaded',timeout:35000});const u=new URL(page.url());result.views.push({name,origin:u.origin,path:u.pathname,http:res.status()});if(!check(name+': protected preview returned application',u.origin===site&&res.status()===200,[u.origin,u.pathname,res.status()]))throw Error('auth/navigation');}
async function score(name){
 const box=page.locator('.match-scoreboard');await box.waitFor({state:'visible',timeout:60000});
 const heading=await page.locator('h1').allTextContents();
 const teams=await box.locator('.scoreboard-team').allTextContents();
 const scores=(await box.locator('.scoreboard-score strong').allTextContents()).map(Number);
 check(name+': RDS score and teams',teams.length===2&&teams[0].includes(m.home_name)&&teams[1].includes(m.away_name)&&scores[0]===m.home_score&&scores[1]===m.away_score,{heading,teams:teams.map(t=>t.trim()),scores});
}
async function tab(name,path,select){
 const wait=page.waitForResponse(r=>new URL(r.url()).origin===api&&new URL(r.url()).pathname===path,{timeout:35000});
 const [resp]=await Promise.all([wait,page.getByRole('tab',{name,exact:true}).click({timeout:18000})]);
 check(name+': on-demand CloudFront HTTP',resp.status()===200,resp.status());
 await page.locator(select).first().waitFor({state:'visible',timeout:25000});
}
try{
 await page.setViewportSize({width:1440,height:1000});
 const start=result.football.length;await go('desktop match overview',remote);await score('desktop');
 let overview=getSince(start);
 check('bounded match summary fetched by preview',did(overview,summary),overview.filter(x=>x.path===summary));
 check('overview requested no heavy family or whole-match archive',!overview.some(x=>x.path.startsWith(base+'/')||x.path===archive),overview.map(x=>x.path));
 await page.screenshot({path:out+'/desktop-score.png',timeout:9000});
 phase='open stats';await tab('Statistiques',base+'/stats','.stats-board .stat-rows');
 const stat=await page.locator('.stats-board dt').filter({hasText:/^Interceptions$/}).locator('..').first().innerText({timeout:13000});
 const sample=s.stats.find(row=>row.metric_key==='interceptions');
 const numbers=(stat.match(/\d+(?:[,.]\d+)?/g)||[]).map(x=>Number(x.replace(',','.')));
 check('rendered interception values match RDS',sample&&numbers.includes(sample.home_value)&&numbers.includes(sample.away_value),{rendered:stat,expected:[sample?.home_value,sample?.away_value]});
 phase='open shots';await tab('Tirs & xG',base+'/shots','.match-shot-list li');
 const shotRows=await page.locator('.match-shot-list li').allInnerTexts();
 check('all source shot rows rendered',shotRows.length===s.shots.length,{count:shotRows.length,expected:s.shots.length,sample:shotRows.slice(0,3)});
 const observed=s.shots.find(x=>x.player_name&&x.minute!=null&&x.xg!=null);
 if(observed)check('source shot player and minute rendered',shotRows.some(row=>row.includes(observed.player_name)&&row.includes(String(observed.minute)+'′')),{player:observed.player_name,minute:observed.minute,xg:observed.xg});
 check('no whole-match download after successful lazy detail',!getSince(start).some(x=>x.path===archive));
 await page.screenshot({path:out+'/desktop-shots.png',timeout:9000});
}catch(e){result.errors.push({phase,error:e.name,stage:'overview and lazy detail'});}
try{
 await page.setViewportSize({width:390,height:844});await go('mobile match overview',remote);await score('mobile');
 check('mobile match fits viewport',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2));
 await page.screenshot({path:out+'/mobile-match.png',timeout:9000});
}catch(e){result.errors.push({phase,error:e.name,stage:'mobile match'});}
try{
 await go('mobile player',playerUrl);
 await page.locator('.research-stat-strip').waitFor({state:'visible',timeout:55000});
 const names=await page.locator('.season-player-identity,h1').allInnerTexts();
 const metrics=await page.locator('.research-stat-strip > div').evaluateAll(rows=>Object.fromEntries(rows.map(r=>[r.querySelector('span')?.textContent,r.querySelector('strong')?.textContent])));
 check('player name matches RDS identity',names.some(x=>x.includes(p.name)),names.map(x=>x.slice(0,100)));
 check('season appearance/minutes match RDS',Number(metrics.Matchs)===s.playerTotals.played&&Number(metrics.Minutes?.replace(/\s/g,''))===s.playerTotals.minutes,{rendered:metrics,expected:s.playerTotals});
 check('mobile player fits viewport',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2));
 await page.screenshot({path:out+'/mobile-player.png',timeout:9000});
}catch(e){result.errors.push({phase,error:e.name,stage:'mobile player'});}
check('all structured football traffic went to the dedicated CloudFront API',result.football.length>0&&!result.violations.length,{requests:result.football.length,violations:result.violations.length});
check('zero application JS exceptions',!result.exceptions.length,result.exceptions);
result.unavailable=result.football.filter(x=>x.status>=400).map(x=>({path:x.path,status:x.status,phase:x.phase}));
result.passed=result.checks.length>0&&result.checks.every(x=>x.ok)&&!result.errors.length;
return result;
