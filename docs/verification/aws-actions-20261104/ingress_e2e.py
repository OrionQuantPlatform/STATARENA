"""Run the action pre/post with real aws-cli EC2 Query serialization to a local fixture."""
import http.server, json, os, pathlib, subprocess, sys, tempfile, threading, urllib.parse, xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
folder=pathlib.Path(__file__).resolve().parent; root=folder.parents[2]
entry=root/'.github/actions/aws-database/runner-ingress/index.cjs'
phase=sys.argv[1]; out=folder/phase; out.mkdir(exist_ok=True)
if phase.endswith('-before'):
    # The original revision had no ingress action. Reproduce that absent entry point.
    if subprocess.run(['git','cat-file','-e','923bb0ff4a9ab4da8a528fdc7f138b31a5f6f68f:.github/actions/aws-database/runner-ingress/index.cjs'],capture_output=True).returncode == 0:
        raise RuntimeError('unexpected ingress implementation in baseline')
    baseline=tempfile.TemporaryDirectory(); entry=pathlib.Path(baseline.name)/'index.cjs'
sg='sg-0667c20e8ff5d2431'; account='361769570630'; ip='44.217.15.9'; rid='sgr-0123456789abcdef0'
checks=[]
def require(ok, msg):
    if not ok: raise ValueError(msg)
def scenario(name, wrong='', duplicate=False, tamper=False, supplied_ip=ip, replay=False, lost=False):
    calls=[]; store={}; xml_ns='http://ec2.amazonaws.com/doc/2016-11-15/'
    def item(r):
        return '<item>'+''.join(f'<{k}>{escape(str(v))}</{k}>' for k,v in r.items() if k!='tagSet')+'<tagSet><item><key>ManagedBy</key><value>statarena-actions</value></item></tagSet></item>'
    if duplicate:
        store[rid]=dict(securityGroupRuleId=rid,groupId=sg,groupOwnerId=account,isEgress='false',ipProtocol='tcp',fromPort=5432,toPort=5432,cidrIpv4=ip+'/32',description='friend-existing')
    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def send(self,body,code=200):
            b=body.encode();self.send_response(code);self.send_header('Content-Type','text/xml');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
        def do_GET(self):
            self.send(supplied_ip+'\n')
        def do_POST(self):
            arg={k:v[0] for k,v in urllib.parse.parse_qs(self.rfile.read(int(self.headers['Content-Length'])).decode()).items()}
            a=arg['Action'];calls.append(a)
            if a=='DescribeSecurityGroups':
                body=f'<securityGroupInfo><item><groupId>{sg if wrong!="sg" else "sg-001"}</groupId><ownerId>{account if wrong!="account" else "000000000000"}</ownerId></item></securityGroupInfo>'
            elif a=='AuthorizeSecurityGroupIngress':
                prefix='IpPermissions.1.'
                require(arg['GroupId']==sg and arg[prefix+'IpProtocol']=='tcp' and arg[prefix+'FromPort']==arg[prefix+'ToPort']=='5432','unexpected group/protocol/port')
                require(arg[prefix+'IpRanges.1.CidrIp']==ip+'/32','wrong CIDR')
                if store:
                    return self.send('<Response><Errors><Error><Code>InvalidPermission.Duplicate</Code><Message>duplicate</Message></Error></Errors><RequestID>fixture</RequestID></Response>',400)
                store[rid]=dict(securityGroupRuleId=rid,groupId=sg,groupOwnerId=account,isEgress='false',ipProtocol='tcp',fromPort=5432,toPort=5432,cidrIpv4=ip+'/32',description=arg[prefix+'IpRanges.1.Description'])
                body='<return>true</return><securityGroupRuleSet>'+item(store[rid])+'</securityGroupRuleSet>'
            elif a=='DescribeSecurityGroupRules':
                body='<securityGroupRuleSet>'+''.join(item(r) for r in store.values())+'</securityGroupRuleSet>'
            elif a=='RevokeSecurityGroupIngress':
                require(arg['GroupId']==sg and arg['SecurityGroupRuleId.1']==rid,'wrong revoke target')
                require(store[rid]['description']!='friend-existing','foreign rule was revoked')
                del store[rid];body='<return>true</return>'
            else: raise ValueError('unexpected AWS action '+a)
            self.send(f'<{a}Response xmlns="{xml_ns}"><requestId>local-only</requestId>{body}</{a}Response>')
    with tempfile.TemporaryDirectory() as d, http.server.ThreadingHTTPServer(('127.0.0.1',0),H) as server:
        t=threading.Thread(target=server.serve_forever,daemon=True);t.start()
        state=pathlib.Path(d)/'state';state.touch()
        ep=f'http://127.0.0.1:{server.server_port}'
        env={'PATH':os.environ['PATH'],'HOME':d,'AWS_EC2_METADATA_DISABLED':'true','AWS_ACCESS_KEY_ID':'fixture','AWS_SECRET_ACCESS_KEY':'fixture','AWS_REGION':'us-east-2','AWS_ENDPOINT_URL_EC2':ep,'AWS_MAX_ATTEMPTS':'1','GITHUB_STATE':str(state),'GITHUB_RUN_ID':'12345','GITHUB_RUN_ATTEMPT':'2','GITHUB_JOB':'publish','GITHUB_REPOSITORY_ID':'1441213700','TEST_CHECKIP':ep,'NODE_OPTIONS':'--require='+str(folder/'ingress-checkip.cjs')}
        def run(phase):
            return subprocess.run(['node',str(entry),phase],env=env,text=True,capture_output=True,timeout=45)
        try:
            opened=run('open')
            require(entry.is_file(),'network action missing')
            if wrong or supplied_ip!=ip or duplicate:
                require(opened.returncode!=0 and 'RevokeSecurityGroupIngress' not in calls,'unsafe success/cleanup')
                if wrong or supplied_ip!=ip: require('AuthorizeSecurityGroupIngress' not in calls,'unexpected authorization attempt')
                if duplicate: require(store[rid]['description']=='friend-existing','duplicate foreign entry altered')
            else:
                require(opened.returncode==0,'open failed: '+opened.stderr[-220:]);require(len(store)==1,'rule missing')
            env.update({'STATE_'+s.partition('=')[0]:s.partition('=')[2] for s in state.read_text().splitlines()})
            if tamper: store[rid]['description']='friend-existing'
            if lost: env.pop('STATE_rule_id',None)
            closed=run('close')
            if tamper:
                require('RevokeSecurityGroupIngress' not in calls and len(store)==1,'tampered rule deleted')
            elif not wrong and supplied_ip==ip and not duplicate:
                require(closed.returncode==0 and not store,'cleanup failed: '+closed.stderr[-200:])
                if replay: require(run('close').returncode==0,'second post should succeed')
            elif duplicate:
                require('RevokeSecurityGroupIngress' not in calls and len(store)==1,'foreign duplicate revoked in post')
            return {'open':opened.returncode,'post':closed.returncode,'calls':calls,'remaining_rules':len(store)}
        finally: server.shutdown()
for name,kwargs in [('create remove and replay',{'replay':True}),('reject private IPv4',{'supplied_ip':'10.1.2.3'}),('reject IPv6',{'supplied_ip':'2001:db8::e'}),('reject multi-address',{'supplied_ip':'44.217.15.9\n1.1.1.1'}),('wrong SG',{'wrong':'sg'}),('wrong account',{'wrong':'account'}),('foreign duplicate',{'duplicate':True}),('changed ownership',{'tamper':True}),('recover lost returned ID',{'lost':True})]:
    try: checks.append({'name':name,'pass':True,'actual':scenario(name,**kwargs)})
    except Exception as e: checks.append({'name':name,'pass':False,'error':str(e)})
report={'setup':'Node subprocess and real AWS CLI, local EC2 XML and checkip fixtures, zero remote writes.','rerun':f'python3 docs/verification/aws-actions-20261104/ingress_e2e.py {phase}','pass':sum(c['pass'] for c in checks),'total':len(checks),'checks':checks}
(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print(report['pass'],'/',report['total'])
for c in checks:
    if not c['pass']: print(c['name'],c['error'])
sys.exit(report['pass']!=report['total'])
