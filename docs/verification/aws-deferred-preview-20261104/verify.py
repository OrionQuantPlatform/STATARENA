"""Run registered match and comparison interactions on this protected preview."""
import ast,datetime as dt,http.cookiejar,json,os,re,subprocess,sys,tempfile
from pathlib import Path
here=Path(__file__).resolve().parent
base=here.parent/'aws-preview-core-20261104'
defer=here.parent/'aws-deferred-match-20261104'
root=here.parents[2]
meta=json.loads((here/'deployment.json').read_text())
site='https://'+meta['url'];api='https://d317dq37z1tacb.cloudfront.net'
stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');mode=sys.argv[1]
assert mode in ('access','match','comparison')
os.umask(0o077)
out=here/(mode+'-'+stamp);out.mkdir()
report=dict(mode=mode,site=site,api=api,commit=meta['commit'],time=stamp,passed=False)
pw=[str(Path.home()/'.codex/skills/playwright/scripts/playwright_cli.sh'),'-s=hosted-'+mode+'-'+stamp[9:15]]
guard="""
const authChecks=[],bundles=[],footballOrigins=new Set(),offOrigin=[];
page.on('request',r=>{
 const u=new URL(r.url());
 if(u.origin===OPT.api){
   footballOrigins.add(u.origin);
   authChecks.push(r.allHeaders().then(h=>['cookie','authorization','x-vercel-protection-bypass'].some(k=>Boolean(h[k]))));
 }
 if(['fetch','xhr','eventsource','websocket'].includes(r.resourceType())&&(u.pathname.startsWith('/data/')||u.origin!==OPT.api&&u.pathname.startsWith('/api/')&&!(u.origin===OPT.site&&u.pathname==='/api/visitor-country')))offOrigin.push(u.origin+u.pathname);
});
page.on('response',r=>{
 const u=new URL(r.url());
 if(u.origin===OPT.site&&r.request().resourceType()==='script'&&u.pathname.startsWith('/_next/static/'))
 bundles.push(r.text().then(s=>s.includes(OPT.api)?u.pathname:null).catch(()=>null));
});
async function originProof(){
 const flags=await Promise.all(authChecks),b=(await Promise.all(bundles)).filter(Boolean);
 return {requestsToApi:flags.length,credentialBearingRequests:flags.filter(Boolean).length,observed:[...footballOrigins],scriptsWithEmbeddedApi:[...new Set(b)],offOrigin};
}
"""
def match_code():
    # Reuse the identical preregistered interactions and SQL fixture assertions.
    tree=ast.parse((defer/'production.py').read_text())
    env={'views':(base/'views.js').read_text()}
    for stmt in tree.body:
        if isinstance(stmt,ast.Assign) and isinstance(stmt.targets[0],ast.Name) and stmt.targets[0].id in ('intent','views'):
            if stmt.targets[0].id=='views' and not (isinstance(stmt.value,ast.Call) and isinstance(stmt.value.func,ast.Attribute) and isinstance(stmt.value.func.value,ast.Name) and stmt.value.func.value.id=='views'):continue
            exec(compile(ast.Module(body=[stmt],type_ignores=[]),'<registered interactions>','exec'),env)
    return env['views'].replace('return result;','result.originProof=await originProof();return result;')
def comparison_code():
    s=(defer/'comparison-race.js').read_text().replace('http://127.0.0.1:18948',site).replace('http://127.0.0.1:18947',api).replace('timeout:4500','timeout:60000').replace('timeout:30000','timeout:60000')
    return "const pageErrors=[];page.on('pageerror',e=>pageErrors.push(e.name));const mode='hosted';\n"+s.replace('return {mode,','await page.screenshot({path:OPT.out+"/comparison.png"});return {originProof:await originProof(),pageErrors,boardVisible:await page.locator(".match-scoreboard").isVisible(),mode,')
def run():
    with tempfile.TemporaryDirectory(prefix='statarena-hosted-auth-') as work:
        work=Path(work);jar=work/'cookies';jar.touch(0o600)
        auth=subprocess.run(['npx','--yes','vercel@latest','--scope','team_IYt7KqupdSTtMuQuMvNa9wiJ','curl',site+'/','--','--silent','--show-error','--output',os.devnull,'--cookie-jar',str(jar),'--header','x-vercel-set-bypass-cookie: true','--write-out','%{http_code}'],cwd=root,capture_output=True,text=True,timeout=90)
        m=re.search(r'\b(\d{3})\s*$',auth.stdout);report['authStatus']=int(m[1]) if m else None
        assert auth.returncode==0
        j=http.cookiejar.MozillaCookieJar(str(jar));j.load(ignore_discard=True,ignore_expires=True)
        cookies=[dict(name=c.name,value=c.value,domain=meta['url'],path='/',secure=True,httpOnly=True,sameSite='Lax',expires=c.expires or -1)for c in j if c.domain.lstrip('.')==meta['url']]
        report['hostOnlyCookies']=len(cookies);assert cookies
        if mode=='access':report['passed']=True;return
        state=work/'state';state.write_text(json.dumps({'cookies':cookies,'origins':[]}))
        config=json.loads((defer/'playwright.json' if mode=='comparison' else here.parent/'rematerialization-completion-20261103/cli-headless.config.json').read_text())
        config['browser']['contextOptions']['storageState']=str(state)
        cfg=work/'config.json';cfg.write_text(json.dumps(config))
        opened=False
        try:
            op=subprocess.run([*pw,'open','about:blank','--config',str(cfg)],cwd=work,capture_output=True,text=True,timeout=80);opened=op.returncode==0;assert opened
            opts=dict(site=site,api=api,s=json.loads((here/'source.json').read_text()),out=str(out))
            script='async page=>{const OPT='+json.dumps(opts)+';\n'+guard+(match_code() if mode=='match' else comparison_code())+'\n}'
            proc=subprocess.run([*pw,'run-code',script],cwd=work,capture_output=True,text=True,timeout=260)
            if '### Result\n' not in proc.stdout:
                report['browserFailure']={'timeout':'Timeout' in proc.stdout,'selectorTimeouts':re.findall(r'locator\.(\w+): Timeout (\d+)ms exceeded',proc.stdout)}
                raise RuntimeError('no sanitized browser result')
            actual,_=json.JSONDecoder().raw_decode(proc.stdout.split('### Result\n',1)[1]);report['actual']=actual
            if mode=='match':checks={c['name']:c['ok'] for c in actual['checks']}
            else:
                events=actual['events'];owner=[e for e in events if e[0]=='foreign-player' and e[1]=='/api/seasons/partition']
                checks={'no preemptive foreign cohort':not any(e[0]=='foreign'and e[1]=='/api/seasons/partition'for e in events),
                'actual foreign player opens':bool(actual.get('player')and'Yaya Fofana'in actual['player']and not actual['error']),
                'exactly three owning league pages':len(owner)==3 and all(e[2]=='l_0275VP'and e[3]==200 for e in owner),
                'original two selected players retained':len(actual['names'])==2 and all(n in actual['oldPairBefore']and n in actual['originalComparison']for n in actual['names']),
                'comparison opens without cohort fetch':not any(e[0]=='comparison'and e[1]=='/api/seasons/partition'for e in events),
                'match visible and no JS exceptions':actual['boardVisible']and not actual['pageErrors']}
            o=actual['originProof']
            report['checks']=checks;report['originPassed']=o['requestsToApi']>0 and o['credentialBearingRequests']==0 and bool(o['scriptsWithEmbeddedApi']) and not o['offOrigin']
            report['passed']=actual['passed'] and all(checks.values()) and report['originPassed']
        finally:
            if opened:subprocess.run([*pw,'close'],cwd=work,capture_output=True,timeout=45)
try:run()
except Exception as e:report['error']=type(e).__name__
(out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'receipt':str(out/'result.json'),'passed':report['passed'],'checks':len(report.get('checks',{})),'failure':report.get('error'),'origin':report.get('originPassed')}))
sys.exit(not report['passed'])
