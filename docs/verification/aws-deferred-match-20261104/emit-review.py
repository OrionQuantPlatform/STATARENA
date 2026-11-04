import subprocess,difflib,json,collections,hashlib
from pathlib import Path
p=Path(__file__).resolve().parent;root=p.parents[2];rev=(p/'base.txt').read_text().strip()
files=['dashboard/frontend/src/'+f for f in ['hooks/FootballContext.jsx','components/PlayerDetails.jsx','components/MatchDetail.jsx','services/resources.js']]
patch=[]
for f in files:
 a=subprocess.check_output(['git','-C',str(root),'show',rev+':'+f],text=True);b=(root/f).read_text()
 patch+=list(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile='a/'+f,tofile='b/'+f))
(p/'candidate.patch').write_text(''.join(patch))
r={'base':rev,'patchSha256':hashlib.sha256((p/'candidate.patch').read_bytes()).hexdigest(),'files':files,'sources':[],'browser':{}}
for f in sorted((p/'api-cache').glob('*.json')):
 m=json.loads(f.read_text());b=f.with_suffix('.bin').read_bytes();r['sources'].append({**m,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
for mode in ['before','after','fault','intent','warm','shots','upcoming','standings','foreign-before','foreign-after','native-before','native-after','cancel']:
 f=p/(mode+'-browser.log');f=f if f.exists() else p/'replay-logs'/(mode+'-browser.log');lines=f.read_text().splitlines();assert lines[0]=='### Result',(mode,lines[:2]);record=json.loads(lines[1]);assert 'error' not in record or mode.startswith(('native','foreign')),(mode,record)
 r['browser'][mode]=record
rs=r['browser']
for mode in ['before','after','fault']:
 v=rs[mode]
 assert len(v['names'])>=2 and 'Yaya Fofana' in v['player'] and 'Comparaison de performances' in v['comparison'] and 'Théo Leoni' in v['comparison']
rs_before=rs['before'];rs_after=rs['after']
def select(v,stage):
 return [e for e in v['events'] if isinstance(e,dict) and e['phase']==stage and e['path']!='/api/assets']
def partitions(v,stage):
 return len([e for e in select(v,stage) if e['path']=='/api/seasons/partition'])
assert partitions(rs_before,'initial')==7 and partitions(rs_after,'initial')==0 and partitions(rs_after,'player')==7
assert rs_after['keep'] and rs['fault']['keep'] and rs['fault']['retry'] and rs['cancel']['remainingDialogs']==0
assert rs['intent']['saved']=='true' and 'Yaya Fofana' in rs['intent']['hit'] and partitions(rs['intent'],'search')==7
assert not any(e['path'].endswith('/summary') or e['path']=='/api/seasons/partition' for e in select(rs['warm'],'match'))
for k in ['native','foreign']:assert rs[k+'-before']['actualPlayer']==0 and rs[k+'-after']['actualPlayer']==1
assert {e[3] for e in rs['foreign-after']['events'] if e[0]=='player' and e[1]=='/api/seasons/partition'}=={'l_0275VP'}
assert not any(e['path']=='/api/seasons/partition' for e in rs['shots']['events']) and 'Analyse des tirs' in rs['shots']['panel']
assert 'Classement' in rs['standings']['panel'] and 'Avant le' in rs['upcoming']['panel']
r['initialBytes']={k:sum(e['bytes'] for e in select(rs[k],'initial')) for k in ('before','after')}
r['result']='passed';(p/'results.json').write_text(json.dumps(r,indent=2,ensure_ascii=False)+'\n')
print(r['patchSha256'],r['initialBytes'],len(r['browser']))
