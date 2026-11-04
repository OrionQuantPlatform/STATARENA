"""Replay the protected-preview fixture against a private production build + live AWS."""
import datetime as dt,json,subprocess,sys,tempfile
from pathlib import Path
here=Path(__file__).resolve().parent; baseline=here.parent/'aws-preview-core-20261104'
port=int(sys.argv[1]);site=f'http://127.0.0.1:{port}';api='https://d317dq37z1tacb.cloudfront.net'
source=baseline/'source.py';exec(compile(source.read_text(),str(source),'exec'),{'__file__':str(here/'source.py')})
stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out=here/stamp;out.mkdir()
pw=[str(Path.home()/'.codex/skills/playwright/scripts/playwright_cli.sh'),'-s=statarena-local-compact-'+stamp[9:15]]
opts={'site':site,'api':api,'s':json.loads((here/'source.json').read_text()),'out':str(out)}
report={'started':stamp,'target':'localhost Next production build against deployed AWS','commit':'d5df4c5a9a31ee7954dc9403f2fdccb8736371e9','site':site,'api':api,'passed':False}
config=here.parent/'rematerialization-completion-20261103/cli-headless.config.json'
extra="""
const compactRequests=[];
page.on('response', r=>{
 const u=new URL(r.url()); if(u.origin!==OPT.api||u.pathname!=='/api/seasons/partition')return;
 const label=phase;
 compactRequests.push((async()=>{
  const timing=r.request().timing(), size=await r.request().sizes(), pageBody=await r.json();
  return {phase:label,league:u.searchParams.get('league'),format:u.searchParams.get('format'),limit:u.searchParams.get('limit'),cursor:u.searchParams.has('cursor'),status:r.status(),generation:pageBody.pagination?.generation,fixtureCount:pageBody.data?.tables?.fixtures.rows.length,matchCount:pageBody.data?.tables?.matches.rows.length,appearanceCount:pageBody.data?.tables?.appearances.rows.length,wireBytes:size.responseBodySize,decodedBytes:(await r.body()).length,requestMs:timing.responseEnd};
 })().catch(e=>({phase:label,error:e.name})));
});
"""
summary="""
result.partitions=await Promise.all(compactRequests);
const expected={'desktop match overview':4,'mobile match overview':4,'mobile player':3};
for(const [view,count] of Object.entries(expected)){
 const rows=result.partitions.filter(r=>r.phase===view);
 const valid=rows.length===count&&rows.every(r=>r.format==='columns'&&r.limit==='100'&&r.status===200)&&new Set(rows.map(r=>r.generation)).size===1;
 check(view+': complete compact traversal without retries',valid,{requests:rows.length,expected:count,fixtures:rows.reduce((acc,r)=>acc+r.fixtureCount,0),appearances:rows.reduce((acc,r)=>acc+r.appearanceCount,0)});
}
"""
views=(baseline/'views.js').read_text().replace("function check(name,ok,actual)",extra+"\nfunction check(name,ok,actual)").replace('protected preview returned application','local production build returned application').replace('result.passed=result.checks',summary+'\nresult.passed=result.checks')
with tempfile.TemporaryDirectory() as work:
 try:
  subprocess.run([*pw,'open','about:blank','--config',str(config)],cwd=work,capture_output=True,check=True,timeout=90)
  proc=subprocess.run([*pw,'run-code','async page=>{const OPT='+json.dumps(opts)+';\n'+views+'\n}'],cwd=work,capture_output=True,text=True,timeout=240)
  data,_=json.JSONDecoder().raw_decode(proc.stdout.split('### Result\n',1)[1]);report.update(data)
 finally: subprocess.run([*pw,'close'],cwd=work,capture_output=True,timeout=45)
(out/'result.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
print(stamp,report['passed'],len(report.get('checks',[])),[r for r in report.get('checks',[]) if not r['ok']])
sys.exit(not report['passed'])
