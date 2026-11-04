"""Live AWS production E2E for selected comparisons across match navigation."""
import datetime,hashlib,json,pathlib,shutil,subprocess,sys,tempfile
here=pathlib.Path(__file__).resolve().parent;root=here.parents[2];port=int(sys.argv[1])
site=f'http://127.0.0.1:{port}';api='https://d317dq37z1tacb.cloudfront.net'
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out=root/'output/playwright'/('aws-comparison-'+stamp);out.mkdir(parents=True)
cli=[str(pathlib.Path.home()/'.codex/skills/playwright/scripts/playwright_cli.sh'),'-s=aws-comparison-'+stamp[9:15]]
source=(here/'comparison-race.js').read_text().replace('http://127.0.0.1:18948',site).replace('http://127.0.0.1:18947',api).replace('timeout:4500','timeout:60000').replace('timeout:30000','timeout:60000')
source="const pageErrors=[];page.on('pageerror',e=>pageErrors.push(e.name));const mode='production-pair-after';\n"+source
source=source.replace('return {mode,','return {pageErrors,boardVisible:await page.locator(".match-scoreboard").isVisible(),mode,')
files=['dashboard/frontend/src/hooks/FootballContext.jsx','dashboard/frontend/src/services/resources.js','dashboard/frontend/src/components/PlayerDetails.jsx','dashboard/frontend/src/components/MatchDetail.jsx']
report={'started':stamp,'setup':'Production Next→liveAWS; actual selected leaders; only genuine target-summary request delayed500ms to expose ordering. No mocked football values.', 'rerun':f'python3 docs/verification/aws-deferred-match-20261104/production-race.py {port}','site':site,'api':api,'sourceHashes':{f:hashlib.sha256((root/f).read_bytes()).hexdigest()for f in files},'passed':False}
with tempfile.TemporaryDirectory() as work:
 try:
  opened=subprocess.run([*cli,'open','about:blank','--config',str(here/'playwright.json')],cwd=work,capture_output=True,text=True,timeout=90);(out/'open.log').write_text(opened.stdout+opened.stderr);assert opened.returncode==0
  r=subprocess.run([*cli,'run-code','async page=>{'+source+'}'],cwd=work,capture_output=True,text=True,timeout=240);(out/'browser.log').write_text(r.stdout+r.stderr)
  data,_=json.JSONDecoder().raw_decode(r.stdout.split('### Result\n',1)[1]);report['actual']=data
  events=data['events'];owner=[e for e in events if e[0]=='foreign-player'and e[1]=='/api/seasons/partition']
  checks={'no preemptive foreign cohort':not any(e[0]=='foreign'and e[1]=='/api/seasons/partition'for e in events),
          'actual foreign player opens':bool(data.get('player')and'Yaya Fofana'in data['player']and not data['error']),
          'exactly three owning league pages':len(owner)==3 and all(e[2]=='l_0275VP'and e[3]==200 for e in owner),
          'original two selected players retained':len(data['names'])==2 and all(n in data['oldPairBefore']and n in data['originalComparison']for n in data['names']),
          'comparison opens without cohort fetch':not any(e[0]=='comparison'and e[1]=='/api/seasons/partition'for e in events),
          'match visible and no JS exceptions':data['boardVisible']and not data['pageErrors']}
  report['checks']=checks;report['passed']=data['passed']and all(checks.values())
 except BaseException as e:report['error']=type(e).__name__+': '+str(e)
 finally:
  subprocess.run([*cli,'close'],cwd=work,capture_output=True,timeout=45)
  (out/'result.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
  durable=here/('production-race-'+stamp);shutil.copytree(out,durable)
  print(json.dumps({'receipt':str(durable/'result.json'),'passed':report['passed'],'checks':report.get('checks'),'error':report.get('error')},ensure_ascii=False))
raise SystemExit(not report['passed'])
