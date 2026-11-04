async (page) => {
const SCREEN="/Users/lemonnierhugo/Desktop/Coding Project/Football_ranking/docs/verification/orion-pro-react-integration-20261104/output/playwright/20261104T222340062477Z-canonical/canonical";
const checks=[];
await page.setViewportSize({width:1600,height:1000});
await page.locator('.home-motw').waitFor({timeout:60000});
checks.push({name:'canonical current desktop',passed:await page.locator('.home-motw').count()>0,url:page.url()});
await page.screenshot({path:SCREEN+'-desktop.png'});
await page.setViewportSize({width:390,height:844});
await page.goto('https://statarena-analytics.vercel.app/?season=2025%2F2026&focus=europe&league=l_3FJFUl');
await page.locator('.home-motw').waitFor({timeout:60000});
const season=await page.getByRole('combobox',{name:'Saison',exact:true}).inputValue();
const dims=await page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth}));
checks.push({name:'canonical historical mobile',passed:season==='2025/2026'&&dims.scrollWidth===dims.width,season,...dims,url:page.url()});
await page.screenshot({path:SCREEN+'-mobile.png'});
return {checks,passed:checks.every(x=>x.passed)};
}
