#!/usr/bin/env python3
"""Test-first actual CLI receipt structures; no PG/source/real acceptance fixture."""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import hashlib,json,os
from pathlib import Path
import shutil,sys,time,traceback

sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[3]
WRITER=ROOT/'dashboard/scripts/orion_pro_native_transport_real_v2.py'
CASES=['implementation_available','offline_default','local_structural_receipts','production_route_refusals']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):Path(p).write_text(json.dumps(v,indent=2)+'\n')
def plain(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def normalized(v):
    if type(v) is int:return {'number':str(v)}
    if isinstance(v,list):return [normalized(x) for x in v]
    if isinstance(v,dict):return {k:normalized(x) for k,x in sorted(v.items())}
    return v
def producer_hash(v):return plain(normalized(v))

def fixture():
    documents=[['fixture:part-a','a'*64],['fixture:part-b','b'*64]]
    binding={'kind':'orion_pro_phase_receipt_v2','phase':'core','transform_sha256':'4b98a829bc7e32e11a7e66381ffecae6248ce536d17771aa080502374fe844bc',
        'transform_version':'real_source_core_v2_native31','model_sha256':'18da43f940870b7a3a3cb49323c847dd5e5174e5eea1f8ff0c8a159cf373cb08',
        'source_document_count':2,'source_document_manifest_sha256':producer_hash(documents),'selector_manifest_sha256':'c'*64}
    binding['input_manifest_sha256']=producer_hash(binding)
    report={'generation':2,'reused':False,'facts':{'fixtures':4,'performances':40},'manifestSha256':binding['input_manifest_sha256']}
    cp={'kind':binding['kind'],'phase':'core','receipt_key':'real-source-v2:core:'+binding['input_manifest_sha256'],'binding':binding,'generation':2,'snapshot_id':2,'report':report,'report_sha256':producer_hash(report)}
    counters={'full_acceptance':False,'local_only':True,'source_document_count':2};clock='2026-11-05T00:00:00+00:00'
    contract={'phase':{'phase':'core','generation':2,'snapshotId':2,'runId':1},'binding':binding,'report':report,'documents':documents,'parameters':{},'counters':counters}
    run={'id':1,'mode':'rebuild','status':'partial','transform_version':binding['transform_version'],'code_commit':binding['transform_sha256'],
        'started_at':clock,'finished_at':clock,'parameters':{},'counters':counters,'checkpoint':cp,'error':None}
    snapshot={'id':2,'generation':2,'status':'sealed','manifest_sha256':producer_hash({'input_manifest_sha256':binding['input_manifest_sha256'],'report_sha256':cp['report_sha256']}),
        'snapshot_key':cp['receipt_key'],'transform_version':binding['transform_version'],'source_priority_version':binding['transform_version'],'knowledge_cutoff_at':None,'created_at':clock,'sealed_at':clock}
    return {'kind':'local_receipt_structure_fixture_v2','origin':'owned_local_receipt_metadata','realProducerExecuted':False,'contract':contract,'run':run,'snapshot':snapshot,'documents':documents}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--precode-only',action='store_true');ap.add_argument('--label',default='receipt-structure');args=ap.parse_args();assert args.label.replace('-','').isalnum()
    sys.path.insert(0,str(ROOT/'tests'));from orion_e2e_process import run_bounded
    run=BASE/'runs'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-'+args.label);(run/'inputs').mkdir(parents=True)
    report={'kind':'source_free_real_receipt_adapter_cli_e2e_v2','command':[sys.executable,str(Path(__file__)),*sys.argv[1:]],'expected':str(BASE/'PROTOCOL.md'),
        'cases':[],'invocations':[],'inputSha256':{},'pgStarts':0,'sourceRamReads':0,'remoteCalls':0,'fullAcceptance':False}
    for p in [Path(__file__),BASE/'PROTOCOL.md',BASE/'BINDINGS.json',BASE/'REAL_SOURCE_CONTRACT.json',WRITER,ROOT/'tests/orion_e2e_process.py']:
        if p.is_file():
            dest=run/'inputs'/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest);report['inputSha256'][str(p.relative_to(ROOT))]=sha(p)
    guard=run/'tripwire';guard.mkdir();(guard/'sitecustomize.py').write_text("import socket,subprocess\ndef deny(*a,**k):raise RuntimeError('UNEXPECTED_EXTERNAL_OPERATION')\nsocket.socket.connect=deny\nsocket.getaddrinfo=deny\nsubprocess.Popen=deny\n");(guard/'psycopg.py').write_text("raise RuntimeError('UNEXPECTED_DRIVER_IMPORT')\n")
    env={k:v for k,v in os.environ.items() if k in ['PATH','HOME','USER','TMPDIR','LANG']};env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(guard));deadline=time.monotonic()+60;block=None
    def cli(flags,label):
        argv=[sys.executable,str(WRITER),*map(str,flags)];r=run_bounded(argv,cwd=ROOT,env=env,deadline=deadline)
        (run/(label+'.stdout.log')).write_text(r.stdout);(run/(label+'.stderr.log')).write_text(r.stderr);report['invocations'].append({'command':argv,'exitCode':r.returncode,'stdout':label+'.stdout.log','stderr':label+'.stderr.log'})
        assert 'UNEXPECTED_' not in r.stdout+r.stderr,r.stderr
        return r,json.loads(r.stdout) if r.stdout.startswith('{') else None
    def mutation(name,fn):
        value=fixture();fn(value);path=run/(name+'.json');save(path,value);r,j=cli(['--check-local-structure','--receipt',path,'--receipt-sha256',sha(path)],name)
        assert r.returncode!=0 and j['reasonCode']=='SOURCE_RECEIPT' and j['connections']==0,j
        return {'case':name,'reasonCode':j['reasonCode'],'connections':0}
    for case in CASES:
        if block or(args.precode_only and case!='implementation_available'):report['cases'].append({'case':case,'status':'unverified','reason':block or 'Precode only'});continue
        try:
            if case=='implementation_available':assert WRITER.is_file(),'Real normalizer receipt adapter v2 is absent';actual={'writerSha256':sha(WRITER)}
            elif case=='offline_default':
                env['PGHOSTADDR']='203.0.113.9';r,j=cli([],case);env.pop('PGHOSTADDR');assert r.returncode==0 and j['status']=='offline_plan' and j['connections']==0;actual=j
            elif case=='local_structural_receipts':
                path=run/'valid-local-metadata.json';save(path,fixture());r,j=cli(['--check-local-structure','--receipt',path,'--receipt-sha256',sha(path)],'valid-local-metadata');assert r.returncode==0 and j['status']=='local_structure_only' and j['realSourceAccepted'] is False and j['connections']==0,j
                actual=[{'case':'valid-local-metadata','status':'pass'}]
                tests=[('plain_input_hash',lambda x:x['run']['checkpoint']['binding'].update(input_manifest_sha256=plain({k:v for k,v in x['run']['checkpoint']['binding'].items() if k!='input_manifest_sha256'}))),
                    ('plain_report_hash',lambda x:x['run']['checkpoint'].update(report_sha256=plain(x['run']['checkpoint']['report']))),
                    ('wrong_sealed_hash',lambda x:x['snapshot'].update(manifest_sha256='0'*64)),('wrong_run_id',lambda x:x['run'].update(id=2)),
                    ('wrong_mode',lambda x:x['run'].update(mode='backfill')),('wrong_status',lambda x:x['run'].update(status='running')),
                    ('wrong_transform',lambda x:x['run'].update(transform_version='fixture')),('wrong_producer',lambda x:x['run'].update(code_commit='0'*64)),
                    ('run_error',lambda x:x['run'].update(error='failed')),('run_parameters',lambda x:x['run'].update(parameters={'extra':1})),
                    ('counter_extra',lambda x:x['run']['counters'].update(extra=1)),('counter_local_false',lambda x:x['run']['counters'].update(local_only=False)),
                    ('counter_full_true',lambda x:x['run']['counters'].update(full_acceptance=True)),('counter_bool_count',lambda x:x['run']['counters'].update(source_document_count=True)),
                    ('checkpoint_extra',lambda x:x['run']['checkpoint'].update(extra=1)),('binding_extra',lambda x:x['run']['checkpoint']['binding'].update(extra=1)),
                    ('report_extra',lambda x:x['run']['checkpoint']['report'].update(extra=1)),('wrong_selector',lambda x:x['run']['checkpoint']['binding'].update(selector_manifest_sha256='0'*64)),
                    ('wrong_phase',lambda x:x['run']['checkpoint'].update(phase='families')),('wrong_generation',lambda x:x['run']['checkpoint'].update(generation=3)),
                    ('wrong_snapshot_ref',lambda x:x['run']['checkpoint'].update(snapshot_id=3)),('wrong_receipt_key',lambda x:x['run']['checkpoint'].update(receipt_key='foreign')),
                    ('missing_clock',lambda x:x['run'].update(started_at=None)),('naive_clock',lambda x:x['run'].update(started_at='2026-11-05T00:00:00')),
                    ('unequal_clock',lambda x:x['snapshot'].update(sealed_at='2026-11-05T00:00:01+00:00')),('unsealed',lambda x:x['snapshot'].update(status='draft')),
                    ('wrong_snapshot_id',lambda x:x['snapshot'].update(id=3)),('wrong_priority',lambda x:x['snapshot'].update(source_priority_version='other')),
                    ('wrong_cutoff',lambda x:x['snapshot'].update(knowledge_cutoff_at='2026-01-01T00:00:00+00:00')),
                    ('missing_document',lambda x:x['documents'].pop()),('duplicate_document',lambda x:x['documents'].append(x['documents'][0])),
                    ('wrong_document',lambda x:x['documents'][0].__setitem__(1,'0'*64))]
                for name,fn in tests:actual.append(mutation(name,fn))
            else:
                actual=[]
                for flags in [['--preflight-rds'],['--apply-rds'],['--preflight-local'],['--host','external.invalid'],['--dsn','postgresql://external.invalid/x']]:
                    r,j=cli(flags,'route-'+str(len(actual)));assert r.returncode!=0 and (j is None or j['connections']==0);actual.append(flags)
            report['cases'].append({'case':case,'status':'pass','actual':actual})
        except BaseException as error:block=str(error);report['cases'].append({'case':case,'status':'fail','error':str(error),'traceback':traceback.format_exc()})
    report['status']='fail' if block else 'pass_source_free_structure_only';report['counts']={s:sum(c['status']==s for c in report['cases']) for s in ['pass','fail','unverified']}
    report['inputHashesExact']=all(sha(ROOT/p)==h for p,h in report['inputSha256'].items());report['cleanup']={'pgStarted':False,'connections':0};save(run/'result.json',report);print(json.dumps({'status':report['status'],'counts':report['counts'],'invocations':len(report['invocations']),'evidence':str(run/'result.json')}))
    return 1 if block else 0

if __name__=='__main__':raise SystemExit(main())
