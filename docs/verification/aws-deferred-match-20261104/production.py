"""Independent real Next production → AWS API → RDS browser workflow."""
import datetime, hashlib, json, pathlib, shutil, subprocess, sys, tempfile
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[2]
port=int(sys.argv[1]);site=f'http://127.0.0.1:{port}';api='https://d317dq37z1tacb.cloudfront.net'
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
out=ROOT/'output/playwright'/('aws-deferred-'+stamp);out.mkdir(parents=True)
base=HERE.parent/'aws-preview-core-20261104'
inputs=json.loads((base/'source.json').read_text())
opts={'site':site,'api':api,'s':inputs,'out':str(out)}
cli=[str(pathlib.Path.home()/'.codex/skills/playwright/scripts/playwright_cli.sh'),'-s=aws-deferred-'+stamp[9:15]]
config=HERE.parent/'rematerialization-completion-20261103/cli-headless.config.json'
views=(base/'views.js').read_text().replace('protected preview returned application','local production build returned application')
views=views.replace("await score('desktop');", "await score('desktop');check('desktop overview requests zero season partitions',!result.football.some(r=>r.path==='/api/seasons/partition'),result.football.filter(r=>r.path==='/api/seasons/partition')); ")
views=views.replace("await score('mobile');", "await score('mobile');check('mobile overview requests zero season partitions',!result.football.some(r=>r.path==='/api/seasons/partition'),result.football.filter(r=>r.path==='/api/seasons/partition')); ")
intent="""
try {
 phase='player intent from match';
 const board=page.locator('.match-scoreboard'),leader=page.locator('.match-leaders-card .match-player-row');
 const before=result.football.length;
 await leader.filter({hasText:p.name}).click();
 await page.getByRole('dialog').waitFor({timeout:10000});
 check('match stays visible while performance loads',await board.isVisible());
 await page.getByRole('dialog').getByRole('button',{name:'Comparer ce joueur',exact:true}).waitFor({timeout:60000});
 const text=await page.getByRole('dialog').innerText();
 check('intent opens exact RDS appearance',text.includes(p.name)&&text.includes(String(p.minutes)),{name:p.name,expectedMinutes:p.minutes,rendered:text.slice(0,400)});
 const loaded=getSince(before).filter(r=>r.path==='/api/seasons/partition');
 check('intent loads owning cohort successfully',loaded.length===3&&loaded.every(r=>r.status===200),loaded);
 await page.getByRole('dialog').getByRole('button',{name:'Comparer ce joueur',exact:true}).click();await page.keyboard.press('Escape');
 const other=leader.filter({hasNotText:p.name}).first();const otherText=await other.innerText();
 await other.click();await page.getByRole('dialog').getByRole('button',{name:'Comparer ce joueur',exact:true}).waitFor({timeout:10000});
 await page.getByRole('dialog').getByRole('button',{name:'Comparer ce joueur',exact:true}).click();await page.keyboard.press('Escape');
 await page.getByRole('button',{name:/^Comparer/}).last().click();
 const comparison=await page.getByRole('dialog').innerText();
 check('comparison retains both selected players',comparison.includes(p.name)&&comparison.includes(otherText.split('\\n').find(v=>v.includes(' '))||'Gaëtan Poussin'),comparison.slice(0,450));
 check('match scoreboard remains mounted after hydration',await board.isVisible());
 await page.screenshot({path:out+'/mobile-performance-comparison.png'});await page.keyboard.press('Escape');
} catch(e) {result.errors.push({phase,error:e.name,message:e.message.slice(0,180),stage:'on-intent performance'});}
"""
views=views.replace("try{\n await go('mobile player'",intent+"\ntry{\n await go('mobile player'")
files=['dashboard/frontend/src/hooks/FootballContext.jsx','dashboard/frontend/src/services/resources.js','dashboard/frontend/src/components/PlayerDetails.jsx','dashboard/frontend/src/components/MatchDetail.jsx']
report={'started':stamp,'target':'real localhost production Next → deployed CloudFront → RDS','rerun':f'python3 docs/verification/aws-deferred-match-20261104/production.py {port}', 'sourceFixture':'docs/verification/aws-preview-core-20261104/source.json','site':site,'api':api,'sourceHashes':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest()for f in files},'passed':False}
try:
 with tempfile.TemporaryDirectory() as work:
  opened=subprocess.run([*cli,'open','about:blank','--config',str(config)],cwd=work,capture_output=True,text=True,timeout=90)
  (out/'open.log').write_text(opened.stdout+opened.stderr)
  assert opened.returncode==0
  r=subprocess.run([*cli,'run-code','async page=>{const OPT='+json.dumps(opts)+';\n'+views+'\n}'],cwd=work,capture_output=True,text=True,timeout=240)
  (out/'browser.log').write_text(r.stdout+r.stderr)
  data,_=json.JSONDecoder().raw_decode(r.stdout.split('### Result\n',1)[1]);report.update(data)
  subprocess.run([*cli,'close'],cwd=work,capture_output=True,timeout=45)
except BaseException as e:
 report['harnessError']=type(e).__name__+': '+str(e)
finally:
 (out/'result.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
 durable=HERE/('production-'+stamp);shutil.copytree(out,durable)
 print(json.dumps({'receipt':str(durable/'result.json'),'passed':report['passed'],'checks':len(report.get('checks',[])),'failed':[x for x in report.get('checks',[])if not x['ok']],'errors':report.get('errors',[]),'harnessError':report.get('harnessError')},ensure_ascii=False))
raise SystemExit(not report['passed'])
