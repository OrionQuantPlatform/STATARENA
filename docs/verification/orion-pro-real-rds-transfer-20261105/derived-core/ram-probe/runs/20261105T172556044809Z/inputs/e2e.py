#!/usr/bin/env python3
"""Source-free before-code CLI and memory wire-to-inventory workflow."""
from datetime import datetime, timezone
from decimal import Decimal
import hashlib, importlib.util, io, json, os, pickle, shutil, sys, tempfile, time, traceback
from pathlib import Path

sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[4]
PROBE = BASE / 'probe.py'
CASES = ['implementation_available','offline_and_unreleased','local_wire_and_closed_inventory','time_and_coverage_disagreement',
         'packed_and_membership_refusals','bounded_pickle_refusals']


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p, v): p.write_text(json.dumps(v, indent=2)+'\n')


def fixture():
    def packed(rows):
        keys=list(dict.fromkeys(k for row in rows for k in row))
        missing={str(i):[j for j,k in enumerate(keys) if k not in row] for i,row in enumerate(rows) if set(row)!=set(keys)}
        return {'keys':keys,'rows':[[row.get(k) for k in keys] for row in rows],'dictionaries':{},'missing':missing}
    sides={'home_team':{'id':'t_TEST01','name':'metadata-only-canary'},'away_team':{'id':'t_TEST02'},'date':'2031-06-04','league':{'id':'l_TEST01'}}
    rows=[dict(sides,id='m_TEST01',time_utc='2031-06-04T00:00:00Z'),dict(sides,id='m_TEST02',time_utc='20:30'),
          dict(sides,id='m_TEST03'),dict(sides,id='m_TEST04',time_utc=None)]
    fixtures=packed(rows);col=fixtures['keys'].index('date');fixtures['dictionaries'][str(col)]=['2031-06-04']
    for row in fixtures['rows']:row[col]=Decimal(0)
    detail=packed([{'id':'m_TEST01','leagueId':'l_TEST01','date':'2031-06-04','timeUtc':'2031-06-04T00:00:00+00:00',
                    'detailCollected':True,'players':['performance-canary'],'coverage':{'players':True,'listedPlayers':Decimal(1)}},
                   {'id':'m_TEST02','leagueId':'l_TEST01','date':'2031-06-04','timeUtc':'20:30','detailCollected':True,'players':[],
                    'coverage':{'players':False,'listedPlayers':Decimal(0)}}])
    perf=packed([{'id':'performance-canary','matchId':'m_TEST01','playerId':'p_TEST01','teamId':'t_TEST01','playerRef':'profile-canary','minutes':Decimal('0')}])
    return {'format':'orion-packed-tables-v1','tables':{'fixtures':fixtures,'matches':detail,'performances':perf,
            'teams':packed([{'id':'t_TEST01'},{'id':'t_TEST02'},{'id':'t_TEST03'}]),'players':packed([{'id':'profile-canary','playerId':'p_TEST01'}])}}


def child(name):
    spec=importlib.util.spec_from_file_location('ram_probe_precode_workflow',PROBE);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    src=fixture();deadline=time.monotonic()+10
    args={'edition':'2031/2032','league':'l_TEST01','documentSha256':'1'*64}
    def inspect(doc):
        dec,meter=m.decode_wire(io.BytesIO(pickle.dumps(doc,protocol=5)),deadline=deadline,maximum_bytes=1024**2)
        return m.observe_edition(dec,args,deadline=deadline),meter
    def refuse(fn):
        try:fn()
        except m.Refusal as e:return e.code
        raise AssertionError('Unexpected admission')
    if name=='local_wire_and_closed_inventory':
        result,meter=inspect(src);out=json.dumps(result)
        assert set(result)=={'edition','documentSha256','counts','utcGrammarCounts','detailTimeAgreement','coverageStates','witnessDigests'}
        assert result['counts']=={'fixtures':4,'details':2,'performances':1,'listedTeams':3,'editionTeamWitnesses':2,'fixtureUtcComparable':2,'completeNonemptyPerformanceObservations':1}
        assert result['utcGrammarCounts']=={'utc_rfc3339_second':1,'utc_time_of_day_minute':1,'absent':1,'explicit_null':1}
        assert result['coverageStates']=={'matched_present':1,'explicit_empty_without_endpoint_witness':1,'no_detail_observation':2}
        assert all(token not in out for token in ['2031-06-04','20:30','metadata-only-canary','performance-canary','profile-canary','m_TEST01','t_TEST01'])
        return {'metadataOnly':True,'result':result,'meter':meter,'realSnapshotExecuted':False}
    if name=='time_and_coverage_disagreement':
        d=src['tables']['matches'];d['rows'][0][d['keys'].index('timeUtc')]='2031-06-04T01:00:00Z'
        d['rows'][0][d['keys'].index('players')]=['mismatched-performance']
        result,_=inspect(src)
        assert result['detailTimeAgreement']=={'different':1,'same':1}
        assert result['coverageStates']['list_mismatch']==1 and result['counts']['completeNonemptyPerformanceObservations']==0
        return result
    if name=='packed_and_membership_refusals':
        f=src['tables']['fixtures'];f['rows'][0][f['keys'].index('date')]=Decimal('0.1')
        first=refuse(lambda:inspect(src))
        src=fixture();f=src['tables']['fixtures'];f['rows'][0][f['keys'].index('away_team')]={'id':'t_OUTSID'}
        second=refuse(lambda:inspect(src))
        src=fixture();p=src['tables']['performances'];p['rows'].append(p['rows'][0])
        third=refuse(lambda:inspect(src))
        assert [first,second,third]==['PACKED_SHAPE','TEAM_SCOPE','PERFORMANCE_SCOPE']
        return {'refusals':[first,second,third]}
    body=pickle.dumps(src,protocol=5)
    probes=[(body[:-1],1024**2),(body+b'x',1024**2),(body,4),(pickle.dumps(Exception('not-allowed'),protocol=5),1024**2)]
    got=[refuse(lambda:m.decode_wire(io.BytesIO(b),deadline=deadline,maximum_bytes=cap)) for b,cap in probes]
    assert got==['WIRE_FORMAT','WIRE_TRAILING','WIRE_BOUND','WIRE_CLASS']
    return {'refusals':got}


def main():
    if len(sys.argv)==3 and sys.argv[1]=='--child':
        print(json.dumps(child(sys.argv[2])));return 0
    sys.path.insert(0,str(ROOT/'tests'));from orion_e2e_process import run_bounded
    out=BASE/'runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');(out/'inputs').mkdir(parents=True)
    report={'kind':'retained_ram_metadata_source_free_e2e_v1','command':[sys.executable,str(Path(__file__))],'expected':str(BASE/'PROTOCOL.md'),
            'cases':[],'invocations':[],'connections':0,'ramGets':0,'providerCalls':0,'businessWrites':0,'fullAcceptance':False}
    for p in [Path(__file__),BASE/'PROTOCOL.md',BASE/'PINS.json',PROBE]:
        if p.is_file():shutil.copy2(p,out/'inputs'/p.name)
    private=None;block=None;started=time.monotonic()
    try:
        for case in CASES:
            if block:report['cases'].append({'case':case,'status':'unverified','reason':block});continue
            try:
                if case=='implementation_available':
                    assert PROBE.is_file(),'RAM metadata probe absent (expected precode RED)'
                    private=Path(tempfile.mkdtemp(prefix='orion-ram-meta-tripwire-',dir='/tmp'))
                    (private/'sitecustomize.py').write_text("""import builtins,os,socket,subprocess
from pathlib import Path
old=builtins.__import__
def deny(*a,**k):
 Path(os.environ['RAM_PROBE_TRIPWIRE']).touch()
 raise RuntimeError('Forbidden source-free external action')
def guarded(name,*a,**k):
 if name.split('.')[0] in {'psycopg','psycopg2','boto3','botocore','requests'}:return deny()
 return old(name,*a,**k)
builtins.__import__=guarded
socket.getaddrinfo=socket.socket.connect=socket.socket.connect_ex=subprocess.Popen=deny
""")
                    env={k:v for k,v in os.environ.items() if k in {'PATH','HOME','USER','TMPDIR','LANG'}}
                    env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(private),RAM_PROBE_TRIPWIRE=str(private/'attempted'))
                    actual={'sha256':sha(PROBE)}
                else:
                    cmds=[([sys.executable,str(PROBE)],0),([sys.executable,str(PROBE),'--inventory'],1)] if case=='offline_and_unreleased' else [([sys.executable,str(Path(__file__)),'--child',case],0)]
                    actual=[]
                    for idx,(cmd,code) in enumerate(cmds):
                        r=run_bounded(cmd,cwd=ROOT,env=env,deadline=started+45,output_limit=1024**2);key=f'{case}-{idx}'
                        (out/(key+'.stdout.log')).write_text(r.stdout);(out/(key+'.stderr.log')).write_text(r.stderr)
                        report['invocations'].append({'command':cmd,'exitCode':r.returncode,'stdout':key+'.stdout.log','stderr':key+'.stderr.log'})
                        assert r.returncode==code and not(private/'attempted').exists(),(r.stdout,r.stderr)
                        val=json.loads(r.stdout)
                        if case=='offline_and_unreleased':assert val['status']==['offline_plan','refused'][idx] and val['ramGets']==val['providerCalls']==0
                        actual.append(val)
                report['cases'].append({'case':case,'status':'pass','actual':actual})
            except BaseException as error:
                block=case;report['cases'].append({'case':case,'status':'fail','error':str(error),'traceback':traceback.format_exc()})
    finally:
        if private:shutil.rmtree(private)
        report['privateTripwireRemoved']=private is None or not private.exists()
        report['status']='fail' if block else 'pass_source_free_only'
        report['counts']={s:sum(c['status']==s for c in report['cases']) for s in ('pass','fail','unverified')}
        report['elapsedSeconds']=round(time.monotonic()-started,3);save(out/'result.json',report)
        print(json.dumps({'status':report['status'],'counts':report['counts'],'evidence':str(out/'result.json')}))
    return 1 if block else 0

if __name__=='__main__':raise SystemExit(main())
