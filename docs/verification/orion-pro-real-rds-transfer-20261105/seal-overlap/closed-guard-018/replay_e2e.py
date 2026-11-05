#!/usr/bin/env python3
"""Precode controlled COPY transport/replay workflow with no DB."""
from datetime import datetime,timezone
import hashlib,importlib.util,json,shutil,sys,traceback
from pathlib import Path
sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parent;TARGET=BASE/'metric_replay.py'
class Stream:
    def __init__(self,body,observed):self.body=body;self.observed=observed
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def __iter__(self):return iter([self.body[:3],self.body[3:]])
    def write(self,raw):self.observed.append(bytes(raw))
class Pipe:
    def __init__(self):self.out=0;self.into=[];self.pending=[]
    def cursor(self):return self
    def copy(self,sql,params=None):
        if sql.endswith('TO STDOUT'):
            self.out+=1
            return Stream(self.pending.pop(0),self.into)
        assert sql.endswith('FROM STDIN')
        return Stream(b'',self.into)
def main():
    run=BASE/'replay-runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');(run/'inputs').mkdir(parents=True)
    report={'kind':'owned018_metric_replay_precode_e2e_v1','command':[sys.executable,str(Path(__file__))],
            'expected':str(BASE/'MATCHED_B_PROTOCOL.md'),'cases':[],'connections':0,'rdsCalls':0,'sourceCalls':0,
            'rawBodiesPersisted':False,'fullAcceptance':False}
    for p in [Path(__file__),TARGET,BASE/'MATCHED_B_PROTOCOL.md']:
        if p.is_file():shutil.copy2(p,run/'inputs'/p.name)
    block=None
    for case in ('implementation_available','one_capture_three_exact_replays','bounded_buffer_refused'):
        if block:report['cases'].append({'case':case,'status':'unverified','reason':block});continue
        try:
            if case=='implementation_available':
                assert TARGET.is_file(),'Bounded replay operator absent (expected precode RED)'
                spec=importlib.util.spec_from_file_location('bounded_copy_replay',TARGET);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
                actual={'codeSha256':hashlib.sha256(TARGET.read_bytes()).hexdigest()}
            elif case=='one_capture_three_exact_replays':
                c=Pipe();c.pending=[b'a\nb\n',b'c\n'];batches=[('"value"','SELECT %s',(1,)),('"value"','SELECT %s',(2,))]
                cache=m.capture(c,batches,tick=lambda:None,maximum_bytes=128)
                assert c.out==2 and c.into==[]
                rec=[m.replay(c,cache,tick=lambda:None) for _ in range(3)]
                assert c.out==2 and c.into==[b'a\nb\n',b'c\n']*3
                assert all(r==rec[0] for r in rec) and rec[0]['rows']==3 and rec[0]['commands']==2
                actual={'copyToCount':c.out,'replays':rec,'wireCache':cache.evidence}
            else:
                c=Pipe();c.pending=[b'0123456789abcdef\n'];batches=[('"value"','SELECT %s',(1,))]
                try:m.capture(c,batches,tick=lambda:None,maximum_bytes=8)
                except m.ReplayError as e:assert e.code=='COPY_BUFFER' and c.into==[];actual={'reasonCode':e.code,'copyFrom':0}
                else:raise AssertionError('Over-limit fixture COPY was accepted')
            report['cases'].append({'case':case,'status':'pass','actual':actual})
        except BaseException as e:
            block=case;report['cases'].append({'case':case,'status':'fail','error':str(e),'traceback':traceback.format_exc()})
    report['status']='fail' if block else 'pass_source_free_only';report['counts']={s:sum(c['status']==s for c in report['cases']) for s in ('pass','fail','unverified')}
    (run/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':report['status'],'counts':report['counts'],'evidence':str(run/'result.json')}))
    return 1 if block else 0
if __name__=='__main__':raise SystemExit(main())
