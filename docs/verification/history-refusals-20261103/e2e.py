"""Complete CLI/Git workflows against a local provider fixture (no real API)."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
import gzip
import json
import os
import subprocess
import sys
import threading

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
CALLS = []
MODE = 'refusals'
CATALOG = {'leagues': [
    {'id':'l_ARG000','country_code':'ARG','seasons':['2023']},
    {'id':'l_BRA000','country_code':'BRA','seasons':['2023']},
]}

class Provider(BaseHTTPRequestHandler):
    def do_GET(self):
        endpoint = self.path.split('?')[0].removeprefix('/v1')
        CALLS.append(endpoint)
        status, body = 200, {'data':{}}
        if endpoint == '/leagues': body['data'] = CATALOG
        elif endpoint == '/leagues/l_ARG000':
            body['data'] = {'players':['p_ARG000','p_DENIED']}
        elif endpoint == '/leagues/l_BRA000': body['data'] = {'players':['p_BRA000']}
        elif endpoint.endswith('/matches'): body['data'] = {'matches':[]}
        elif endpoint in ('/players/p_ARG000','/players/p_DENIED'):
            if MODE == 'recovery' and endpoint.endswith('p_ARG000'):
                body['data'] = {'id':'p_ARG000','name':'Recovered fixture player'}
            else:
                status = 401 if MODE == 'unauthorized' else 403
                body = {'error':{'code':'UNAUTHORIZED' if status == 401 else 'PLAN_UPGRADE_REQUIRED','message':'Fixture refusal'}}
        elif endpoint == '/players/p_BRA000': body['data'] = {'id':'p_BRA000','name':'Brazil fixture player'}
        encoded = json.dumps(body).encode()
        self.send_response(status)
        self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)
    def log_message(self,*args): pass

BOOTSTRAP = '''
import importlib,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
root=Path.cwd(); base=sys.argv[2]; target=sys.argv[3]
import collect_pitchapi_all as shared
shared.ROOT=root; shared.BASE_URL=base
import collect_pitchapi_world as world
world.DATA=root/'data'; world.STATE=world.DATA/'computed/pitchapi-world'; world.BLOBS=world.DATA/'raw/pitchapi-world/blobs'
import collect_pitchapi_countries as countries
countries.DATA=world.DATA; countries.STATE=world.STATE; countries.BLOBS=world.BLOBS
countries.CHECKPOINTS=world.DATA/'raw/pitchapi-world/checkpoints'; countries.PROGRESS=world.DATA/'raw/pitchapi-world/countries.json'
module=importlib.import_module(target)
if target == 'retry_pitchapi_refusals':
    module.DATA=world.DATA; module.CHECKPOINTS=countries.CHECKPOINTS
sys.argv=[target]+sys.argv[4:]
module.main()
'''

def git(root,*args):
    return subprocess.check_output(['git','-C',str(root),*args],stderr=subprocess.STDOUT,text=True)

def seed(root):
    (root/'.gitignore').write_text('/data/computed/\n/github-output\n')
    for name,value in [('match-observations',{}),('observation-shards',{}),('profile-index',{'entities':{}})]:
        path=root/'data/raw'/f'{name}.json'; path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(value))
    git(root,'init','-b','main'); git(root,'config','user.email','fixture@example.invalid'); git(root,'config','user.name','Fixture')
    git(root,'add','.'); git(root,'commit','-m','fixture baseline')
    remote=root.parent/(root.name+'-remote.git')
    subprocess.check_output(['git','init','--bare',str(remote)],stderr=subprocess.STDOUT)
    git(root,'remote','add','origin',str(remote)); git(root,'push','-u','origin','main')
    return remote

def run(root,label,args=(),module='collect_pitchapi_countries',expected=0):
    output=root/'github-output'; output.write_text('')
    env={**os.environ,'PITCHAPI_API_KEY':'pk_test_fixture','GITHUB_OUTPUT':str(output),'GITHUB_RUN_ID':'fixture-retry'}
    cmd=[sys.executable,'-c',BOOTSTRAP,str(ROOT/'dashboard/scripts'),BASE,module,*args]
    result=subprocess.run(cmd,cwd=root,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    (OUT/(label+'.log')).write_text(result.stdout)
    assert 'pk_test_fixture' not in result.stdout
    assert result.returncode == expected, result.stdout
    return output.read_text()

def receipt(root): return json.loads((root/'data/raw/pitchapi-world/countries.json').read_text())

server=ThreadingHTTPServer(('127.0.0.1',0),Provider)
BASE=f'http://127.0.0.1:{server.server_port}/v1'
threading.Thread(target=server.serve_forever,daemon=True).start()
checks=[]
try:
    with TemporaryDirectory(prefix='history-refusal-e2e-') as temporary:
        top=Path(temporary)
        root=top/'normal';root.mkdir();remote=seed(root)
        assert run(root,'traverse',('--minutes','2','--publish')) == 'continue=false\n'
        states=receipt(root)
        assert states['ARG']['state']=='complete_with_errors',states
        assert states['ARG']['failures']==2 and len(states['ARG']['failedRequests'])==2,states
        assert states['BRA']['state']=='complete',states
        published=json.loads(git(remote,'show','main:data/raw/pitchapi-world/countries.json'))
        assert published==states
        before=list(CALLS)
        assert run(root,'restart',('--minutes','2','--publish'))=='continue=false\n'
        assert CALLS==before,'terminal countries caused duplicate provider requests'
        checks.append({'case':'refusal traversal, Git publication and terminal restart','passed':True,'receipt':states})

        MODE='recovery'
        checkpoint_dir=root/'data/raw/pitchapi-world/checkpoints'
        before_buckets={p.name:p.read_bytes() for p in checkpoint_dir.glob('*.gz')}
        retry_root=top/'retry-sparse'
        subprocess.check_output(['git','clone','--sparse','--branch','main',str(remote),str(retry_root)],stderr=subprocess.STDOUT)
        git(retry_root,'config','user.email','fixture@example.invalid');git(retry_root,'config','user.name','Fixture')
        git(retry_root,'sparse-checkout','set','data/raw/pitchapi-world/checkpoints','data/raw/pitchapi-world/refusal-retries')
        run(retry_root,'retry',('--publish',),module='retry_pitchapi_refusals')
        assert before_buckets=={p.name:p.read_bytes() for p in checkpoint_dir.glob('*.gz')},'retry mutated active checkpoints'
        git(root,'fetch','origin','main');git(root,'rebase','origin/main')
        archives=list((root/'data/raw/pitchapi-world/refusal-retries').glob('*.json.gz'))
        assert len(archives)==1
        retry_rows=json.loads(gzip.decompress(archives[0].read_bytes()))
        assert sorted(row['status'] for row in retry_rows)==[200,403],retry_rows
        git(remote,'cat-file','-e','main:'+archives[0].relative_to(root).as_posix())
        states['ARG']['state']='partial'
        (root/'data/raw/pitchapi-world/countries.json').write_text(json.dumps(states))
        git(root,'add','.');git(root,'commit','-m','fixture interrupted country')
        calls_before=CALLS.count('/players/p_ARG000')
        assert run(root,'resume-recovery',('--minutes','2','--publish'))=='continue=false\n'
        assert CALLS.count('/players/p_ARG000')==calls_before,'recovered profile hit provider again'
        assert receipt(root)['ARG']['failures']==1
        checks.append({'case':'bounded mixed retry, separate archive and cached recovery on partial resume','passed':True})

        MODE='refusals'
        root=top/'deadline';root.mkdir();seed(root)
        assert run(root,'deadline',('--minutes','0'))=='continue=true\n'
        assert receipt(root)['ARG']['state']=='partial'
        assert run(root,'deadline-resume',('--minutes','2'))=='continue=false\n'
        assert receipt(root)['BRA']['state']=='complete'
        checks.append({'case':'deadline continuation and resumption','passed':True})

        MODE='unauthorized'
        root=top/'authentication';root.mkdir();seed(root)
        start=len(CALLS)
        assert run(root,'authentication',('--minutes','2'),expected=1)==''
        assert receipt(root)['ARG']['state']=='partial'
        assert '/leagues/l_BRA000' not in CALLS[start:]
        checks.append({'case':'fatal authentication stops before next country','passed':True})
    (OUT/'e2e-result.json').write_text(json.dumps({'fixtureCatalog':CATALOG,'checks':checks,'requests':CALLS},indent=2)+'\n')
    print(json.dumps({'checks':checks,'requestCount':len(CALLS)},indent=2))
finally:
    server.shutdown()
