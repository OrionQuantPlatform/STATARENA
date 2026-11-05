"""Real local CLI driver, phase barriers and bounded owned process management."""
from __future__ import annotations
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from urllib.parse import quote
from workflow_budget import OPTIONS,digest

BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[3]


def minimal_env():return {k:os.environ[k] for k in ['PATH','HOME','TMPDIR','USER','LANG','LC_ALL'] if k in os.environ}


class PublisherDriver:
    def __init__(self,run,port,budget,inputs):
        self.run=Path(run);self.port=port;self.budget=budget;self.inputs=inputs;self.children=[];self.invocations=[];self.serial=0

    def environment(self,worker):
        env=minimal_env();options=OPTIONS+' -c application_name=publisher_'+worker
        env.update(ORION_PUBLISHER_TEST_RUN=str(self.run),ORION_PUBLISHER_WORKER_ID=worker,ORION_PUBLISHER_OWNED_PORT=str(self.port),
          ORION_PUBLISHER_DATABASE_URL=f'postgresql://statarena_ingest@127.0.0.1:{self.port}/postgres?sslmode=disable&options={quote(options)}',
          STATARENA_TEST_DATABASE='1',PGPASSFILE=os.devnull,PGSERVICEFILE=os.devnull)
        return env

    def start(self,*,mode='publish',keys='ABC',admission=None,barrier=None,probe=False):
        self.budget.check();active=[v for v in self.children if v['process'].poll() is None]
        assert len(active)<2,'At most2 worker processes'
        used={v['worker'] for v in active};worker=next(v for v in ['worker1','worker2'] if v not in used)
        self.serial+=1;stem=f'publisher-{self.serial:02d}';receipt=self.run/(stem+'.json');events=self.run/(stem+'-events.jsonl')
        env=self.environment(worker)
        if probe:command=[sys.executable,'-I',str(BASE/'publisher_worker.py'),'--probe']
        else:
            invocation=self.inputs.admission()
            admission=invocation if admission is None else admission;admission_file=self.run/(stem+'-admission.json')
            admission_file.write_text(json.dumps(admission,sort_keys=True,indent=2)+'\n')
            import hashlib
            admission_sha=hashlib.sha256(admission_file.read_bytes()).hexdigest()
            command=[sys.executable,'-I',str(BASE/'publisher_worker.py'),'--','--local','--mode',mode,
              '--admission',str(admission_file),'--admission-sha256',admission_sha,'--dataset-generation',str(invocation['datasetGeneration']),
              '--catalog-generation',str(invocation['catalogGeneration']),'--editions',','.join(str(self.inputs.editions[k]['id']) for k in keys),
              '--receipt',str(receipt)]
            env['ORION_PUBLISHER_E2E_EVENTS']=str(events)
            if barrier:
                control=self.run/(stem+'-control.json');release=self.run/(stem+'.release')
                control.write_text(json.dumps({'phase':barrier,'releaseFile':str(release),'timeoutSeconds':3})+'\n')
                env['ORION_PUBLISHER_E2E_BARRIER']=str(control)
        out=self.run/(stem+'.stdout.log');err=self.run/(stem+'.stderr.log')
        a=out.open('w');b=err.open('w')
        process=subprocess.Popen(command,cwd=BASE,env=env,stdout=a,stderr=b,start_new_session=True,text=True)
        item={'process':process,'worker':worker,'receipt':receipt,'events':events,'release':self.run/(stem+'.release'),
              'stdout':out,'stderr':err,'streams':[a,b],'command':command,'mode':'probe' if probe else mode,'barrier':barrier}
        self.children.append(item);return item

    def wait_phase(self,item,phase):
        end=time.monotonic()+2
        while time.monotonic()<end:
            self.budget.check()
            if item['events'].exists():
                for line in item['events'].read_text().splitlines():
                    event=json.loads(line)
                    if event.get('phase')==phase:return event
            if item['process'].poll() is not None:break
            time.sleep(.01)
        raise AssertionError('Required real publisher phase was not observed: '+phase)

    def release(self,item):item['release'].write_text('release\n')

    def kill(self,item):
        if item['process'].poll() is None:os.killpg(item['process'].pid,signal.SIGKILL)
        return self.finish(item,killed=True)

    def finish(self,item,*,killed=False,rejected=False):
        end=time.monotonic()+15
        while item['process'].poll() is None:
            self.budget.check()
            if time.monotonic()>end:
                os.killpg(item['process'].pid,signal.SIGKILL);item['process'].wait(timeout=3)
                raise AssertionError('Worker process exceeded15s')
            time.sleep(.02)
        for stream in item['streams']:
            if not stream.closed:stream.close()
        for file in [item['stdout'],item['stderr'],*([item['receipt']] if item['receipt'].exists() else [])]:
            text=file.read_text()
            if 'postgresql://' in text or 'postgres://' in text:
                file.write_text('[REDACTED forbidden DSN output]\n');raise AssertionError('Worker emitted a forbidden DSN')
        result=json.loads(item['receipt'].read_text()) if item['receipt'].exists() else None
        record={k:str(item[k]) for k in ['worker','mode','barrier','receipt','events','stdout','stderr']}
        record.update(command=item['command'],exitCode=item['process'].returncode,killed=killed,result=result)
        self.invocations.append(record)
        if killed:assert item['process'].returncode<0
        elif item['mode']=='probe':assert item['process'].returncode==0,record
        elif rejected:
            assert item['process'].returncode!=0 and result and result.get('status') in ['rejected','retry'],record
            assert result.get('error',{}).get('code') in ['ADMISSION_MISMATCH','DRAFT_NOT_ADMITTED','MISSING_ENGAGEMENT','COVERAGE_INVALID','UNREADY_INPUT','STALE_PLAN'],record
        else:assert item['process'].returncode==0 and result and result.get('status') in ['planned','published','noop','retry'],record
        return result

    def execute(self,**kwargs):
        rejected=kwargs.pop('rejected',False);return self.finish(self.start(**kwargs),rejected=rejected)

    def close(self):
        for item in self.children:
            if item['process'].poll() is None:
                os.killpg(item['process'].pid,signal.SIGKILL);item['process'].wait(timeout=3)
            for stream in item['streams']:
                if not stream.closed:stream.close()
