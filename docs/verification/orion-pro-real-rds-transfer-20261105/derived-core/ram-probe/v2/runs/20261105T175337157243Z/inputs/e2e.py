#!/usr/bin/env python3
"""Precode wire parser and synthetic full-shape memory campaign; zero source reads."""
from datetime import datetime, timezone
from decimal import Decimal
import hashlib, importlib.util, json, os, pickle, shutil, sys, tempfile, time, traceback
from pathlib import Path

sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[5]
MODULE=BASE/'probe_v2.py'
CASES=['implementation_available','offline_and_unreleased','bounded_compact_wire','same_or_larger_synthetic_wire_shape']
ACTUAL_WIRE=12208712

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p,n):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def dense_edition(edition,nperf,nmatches,cols,offset):
 def table(keys,rows):return {'keys':keys,'rows':rows,'dictionaries':{}}
 teamids=[f't_{offset+i:06d}' for i in range(18)]
 prof=[(f'profile-fixture-{offset+i}',f'p_{offset+i:06d}') for i in range(800)]
 fixtures=[];details=[];performances=[]
 day='2032-08-14';kickoff='2032-08-14T20:30:00Z'
 keys=['id','matchId','playerId','teamId','playerRef']+[f'slot{i:02d}' for i in range(cols-5)]
 per,q=divmod(nperf,nmatches)
 for i in range(306):
  mid=f'm_{offset+i:06d}';home=teamids[i%18];away=teamids[(i+1)%18]
  fixtures.append([mid,day,kickoff,{'id':home},{'id':away},{'id':'l_TEST01'}])
  if i>=nmatches:continue
  ids=[]
  for j in range(per+(i<q)):
   pref,pid=prof[(i*31+j)%len(prof)];rid=f'perf-fixture-{mid}-{j}'
   ids.append(rid);row=[rid,mid,pid,home if j%2 else away,pref]
   idx=len(performances)
   for k in range(cols-5):
    t=(idx+k)%10
    if t<7:
     row.append(Decimal(f'{offset+idx*173+k}.{(idx*7+k*17)%100000000:08d}'))
    elif t==7:row.append(f'fixture-{idx:x}-{k:x}-Σ')
    elif t==8:row.append(None)
    else:row.append((idx+k)%3==0)
   performances.append(row)
  details.append([mid,'l_TEST01',day,kickoff,True,ids,{'players':True,'listedPlayers':Decimal(len(ids))}])
 assert len(performances)==nperf
 return {'format':'orion-packed-tables-v1','tables':{
    'fixtures':table(['id','date','time_utc','home_team','away_team','league'],fixtures),
    'matches':table(['id','leagueId','date','timeUtc','detailCollected','players','coverage'],details),
    'performances':table(keys,performances),'teams':table(['id'],[[x] for x in teamids]),'players':table(['id','playerId'],[list(p) for p in prof])}}

def child(case):
 m=load(MODULE,'bounded_ram_v2_candidate');deadline=time.monotonic()+50
 if case=='bounded_compact_wire':
  fixture=load(BASE.parent/'e2e.py','retained_precode_fixture').fixture()
  wire=bytearray(pickle.dumps(fixture,protocol=5));value,meter=m.decode_buffer(wire,deadline=deadline)
  result=m.v1.observe_edition(value,{'edition':'2031/2032','league':'l_TEST01','documentSha256':'1'*64},deadline=deadline)
  assert result['counts']['completeNonemptyPerformanceObservations']==1 and result['coverageStates']['no_detail_observation']==2
  text=json.dumps(result);assert all(x not in text for x in ('2031-06-04','m_TEST01','performance-canary'))
  broken=bytearray(wire);broken[3:11]=(len(wire)+10).to_bytes(8,'little')
  rejects=[]
  for body,cap in [(wire+b'x',m.WIRE),(broken,m.WIRE),(wire,4),(bytearray(pickle.dumps(Exception('forbidden'),protocol=5)),m.WIRE)]:
   try:m.decode_buffer(body,deadline=deadline,maximum_bytes=cap)
   except m.v1.Refusal as error:rejects.append(error.code)
   else:raise AssertionError('Unexpected wire admission')
  assert rejects==['WIRE_TRAILING','WIRE_FORMAT','WIRE_BOUND','WIRE_CLASS']
  return {'scope':'source_free_compact','result':result,'meter':meter,'refusals':rejects}
 r,w=os.pipe()
 pid=os.fork()
 if pid==0:
  os.close(r)
  try:
   with os.fdopen(w,'wb') as channel:
    fixture={'editions':[dense_edition('2025/2026',12200,306,46,0),dense_edition('2026/2027',3237,81,89,2000)]}
    pickle.dump(fixture,channel,protocol=5)
   os._exit(0)
  except BaseException:
   os._exit(1)
 os.close(w)
 try:
  with os.fdopen(r,'rb') as channel:wire=m.receive_buffer(channel.read,deadline)
  assert ACTUAL_WIRE<=len(wire)<m.WIRE
  value,meter=m.decode_buffer(wire,deadline=deadline)
  del wire
  results=[]
  for doc,edition,cols in zip(value['editions'],['2025/2026','2026/2027'],[46,89]):
   assert len(doc['tables']['performances']['keys'])==cols
   results.append(m.v1.observe_edition(doc,{'edition':edition,'league':'l_TEST01','documentSha256':'1'*64},deadline=deadline))
  assert [sum(e['counts'][n] for e in results) for n in ('fixtures','details','performances')]==[612,387,15437]
  peak=m.v1.tick(deadline);assert peak<=m.RSS
 finally:
  waited,status=os.waitpid(pid,0)
 assert waited==pid and os.waitstatus_to_exitcode(status)==0
 return {'scope':'synthetic_same_or_larger_wire_only','editions':results,'packedPerformanceColumns':[46,89],
         'rawBodiesPersisted':False,'consumerPeakRssBytes':peak,'meter':meter,'producerClosed':True}

def main():
 if len(sys.argv)==3 and sys.argv[1]=='--child':print(json.dumps(child(sys.argv[2])));return 0
 sys.path.insert(0,str(ROOT/'tests'));from orion_e2e_process import run_bounded
 run=BASE/'runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');(run/'inputs').mkdir(parents=True)
 report={'kind':'ram_probe_v2_scale_precode_e2e_v1','command':[sys.executable,str(Path(__file__))],'expected':str(BASE/'PROTOCOL.md'),
         'cases':[],'invocations':[],'ramGets':0,'connections':0,'providerCalls':0,'businessWrites':0,'rawBodiesPersisted':False,'fullAcceptance':False}
 for p in [Path(__file__),MODULE,BASE/'PROTOCOL.md',BASE/'PINS.json',BASE/'ARCHIVES.json']:
  if p.is_file():shutil.copy2(p,run/'inputs'/p.name)
 private=None;block=None;start=time.monotonic()
 try:
  for case in CASES:
   if block:report['cases'].append({'case':case,'status':'unverified','reason':block});continue
   try:
    if case=='implementation_available':
     assert MODULE.is_file(),'RAM V2 probe absent (expected precode RED)'
     private=Path(tempfile.mkdtemp(prefix='orion-probe-v2-tripwire-',dir='/tmp'))
     (private/'sitecustomize.py').write_text("""import builtins,os,socket
from pathlib import Path
old=builtins.__import__
def deny(*a,**k):
 Path(os.environ['PROBE_V2_TRIPWIRE']).touch()
 raise RuntimeError('Forbidden synthetic source action')
def guarded(name,*a,**k):
 if name.split('.')[0] in {'psycopg','psycopg2','boto3','botocore','requests'}:return deny()
 return old(name,*a,**k)
builtins.__import__=guarded
socket.getaddrinfo=socket.socket.connect=socket.socket.connect_ex=deny
""")
     env={k:v for k,v in os.environ.items() if k in {'PATH','HOME','USER','TMPDIR','LANG'}}
     env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(private),PROBE_V2_TRIPWIRE=str(private/'attempted'))
     actual={'sha256':sha(MODULE)}
    else:
     cmds=[([sys.executable,str(MODULE),'--check-plan'],0),([sys.executable,str(MODULE),'--inventory'],1)] if case=='offline_and_unreleased' else [([sys.executable,str(Path(__file__)),'--child',case],0)]
     actual=[]
     for idx,(cmd,code) in enumerate(cmds):
      r=run_bounded(cmd,cwd=ROOT,env=env,deadline=start+60,output_limit=1024**2);n=f'{case}-{idx}'
      (run/(n+'.stdout.log')).write_text(r.stdout);(run/(n+'.stderr.log')).write_text(r.stderr)
      report['invocations'].append({'command':cmd,'exitCode':r.returncode,'stdout':n+'.stdout.log','stderr':n+'.stderr.log'})
      assert not(private/'attempted').exists() and r.returncode==code,(r.stdout,r.stderr)
      data=json.loads(r.stdout)
      if case=='offline_and_unreleased':assert data['status']==['verified_retained_metadata_inputs_only','refused'][idx] and data['ramGets']==0
      actual.append(data)
    report['cases'].append({'case':case,'status':'pass','actual':actual})
   except BaseException as e:
    block=case;report['cases'].append({'case':case,'status':'fail','error':str(e),'traceback':traceback.format_exc()})
 finally:
  if private:shutil.rmtree(private)
  report['privateTripwireRemoved']=private is None or not private.exists();report['status']='fail' if block else 'pass_source_free_only'
  report['counts']={s:sum(x['status']==s for x in report['cases']) for s in ['pass','fail','unverified']}
  report['elapsedSeconds']=round(time.monotonic()-start,3);(run/'result.json').write_text(json.dumps(report,indent=2)+'\n')
  print(json.dumps({'status':report['status'],'counts':report['counts'],'evidence':str(run/'result.json')}))
 return 1 if block else 0
if __name__=='__main__':raise SystemExit(main())
