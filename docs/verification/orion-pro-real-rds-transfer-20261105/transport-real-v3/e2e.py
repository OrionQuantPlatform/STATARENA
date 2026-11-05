#!/usr/bin/env python3
"""Precode V3 CLI E2E. All fixtures are structural metadata; never real acceptance."""
from datetime import datetime,timezone
import hashlib,json,os,shutil,sys,tempfile,time,traceback
from pathlib import Path

sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[3];MODULE=ROOT/'dashboard/scripts/orion_pro_native_transport_real_v3.py';OLD=BASE.parent/'real-core-operation-v3'
CASES=['implementation_available','offline_tripwire','structural_pair','closed_policy_mutations','live_mode_refusals','qualified_code_audit']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):Path(p).write_text(json.dumps(v,indent=2)+'\n')

def main():
 sys.path.insert(0,str(ROOT/'tests'));from orion_e2e_process import run_bounded
 run=BASE/'runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');(run/'inputs').mkdir(parents=True)
 report={'kind':'real_v3_015_transport_boundary_cli_e2e_v1','command':[sys.executable,str(Path(__file__))],'expected':str(BASE/'PROTOCOL.md'),'cases':[],'cliCommands':[],'connections':0,'sourceReads':0,'ramGets':0,'cloudCalls':0,'realSourceAccepted':False,'realTargetAccepted':False,'fullAcceptance':False}
 for p in [Path(__file__),BASE/'PROTOCOL.md',MODULE,BASE/'BINDINGS.json',BASE/'TARGET_POLICY.json']:
  if p.is_file():shutil.copy2(p,run/'inputs'/p.name)
 private=None;block=None;started=time.monotonic()
 def cli(args,label,expected=0,extraenv=None):
  e=dict(env);e.update(extraenv or {});cmd=[sys.executable,str(MODULE),*args];r=run_bounded(cmd,cwd=ROOT,env=e,deadline=started+60,output_limit=1024**2);(run/(label+'.stdout.log')).write_text(r.stdout);(run/(label+'.stderr.log')).write_text(r.stderr);report['cliCommands'].append({'command':cmd,'exitCode':r.returncode,'stdout':label+'.stdout.log','stderr':label+'.stderr.log'});assert not(private/'forbidden').exists(),'Offline V3 attempted driver/DNS/process';assert r.returncode==expected,(label,r.returncode,r.stdout,r.stderr);return json.loads(r.stdout) if r.stdout.strip() else {}
 try:
  for case in CASES:
   if block:report['cases'].append({'case':case,'status':'unverified','reason':block});continue
   try:
    if case=='implementation_available':
     assert MODULE.is_file(),'RealV3 target015 adapter absent (expected precode RED)';private=Path(tempfile.mkdtemp(prefix='orion-real-v3-tripwire-',dir='/tmp'));(private/'sitecustomize.py').write_text("import builtins,os,socket,subprocess\nfrom pathlib import Path\nold=builtins.__import__\ndef deny(*a,**k):\n Path(os.environ['V3_TRIPWIRE']).touch()\n raise RuntimeError('Forbidden V3 offline external action')\ndef imports(n,*a,**k):\n if n.split('.')[0] in {'psycopg','psycopg2','boto3','botocore','requests'}:return deny()\n return old(n,*a,**k)\nbuiltins.__import__=imports\nsocket.getaddrinfo=deny\nsocket.socket.connect=deny\nsocket.socket.connect_ex=deny\nsubprocess.Popen=deny\n");env={k:v for k,v in os.environ.items() if not k.startswith('PG')};env.update(PYTHONPATH=str(private)+':'+str(ROOT/'dashboard/scripts'),PYTHONDONTWRITEBYTECODE='1',V3_TRIPWIRE=str(private/'forbidden'));actual={'moduleSha256':sha(MODULE)}
    elif case=='offline_tripwire':
     out=cli([],case,extraenv={'PGHOSTADDR':'192.0.2.8','PGOPTIONS':'-c statement_timeout=0'});assert out['status']=='offline_plan' and out['connections']==0;actual=out
    elif case=='structural_pair':
     fixture=json.loads((BASE/'STRUCTURE_FIXTURE.json').read_text());assert fixture['kind']=='local_real_v3_structure_fixture' and fixture['origin']=='local_metadata_only' and fixture['realSourceExecuted'] is False;path=run/'structure.json';save(path,fixture);out=cli(['--check-local-structure','--structure',str(path),'--structure-sha256',sha(path)],case);assert out['status']=='structure_only' and out['realSourceAccepted'] is False and out['realTargetAccepted'] is False and out['connections']==0;actual=out
    elif case=='closed_policy_mutations':
     mutations=[]
     def add(name,mutate):mutations.append((name,mutate))
     add('old_pair_kind',lambda x:x['pair'].__setitem__('kind','explicit_native_sql_transport_real_v2_pair'))
     add('old_acceptance_kind',lambda x:x['acceptance'].__setitem__('kind','native_sql_real_receipt_acceptance_v2'))
     add('fixture_origin',lambda x:x['acceptance'].__setitem__('dataOrigin','owned_source_free_fixture'))
     add('wrong_model',lambda x:x['acceptance'].__setitem__('modelSha256','0'*64))
     add('wrong_source_producer',lambda x:x['acceptance'].__setitem__('producerSha256','0'*64))
     add('wrong_source_checkpoint',lambda x:x['acceptance'].__setitem__('sourceCheckpointSha256','0'*64))
     add('wrong_source_native',lambda x:x['acceptance'].__setitem__('sourceNativeSha256','0'*64))
     add('wrong_source_rows',lambda x:x['acceptance'].__setitem__('sourceRows',553561))
     add('wrong_source_phase',lambda x:x['acceptance']['sourcePhases'][0].__setitem__('generation',3))
     add('source_fake014',lambda x:x['pair']['source']['journal'].append(x['pair']['target']['journal'][2]))
     add('target_p1_kind',lambda x:x['pair']['target'].__setitem__('kind','typed_native_p1_journal_v1'))
     add('target_p1_origin',lambda x:x['pair']['target'].__setitem__('origin','existing_rds_p1'))
     add('target_omit015',lambda x:x['pair']['target']['journal'].pop())
     add('target_hide014',lambda x:x['pair']['target']['journal'].pop(2))
     add('target_add016',lambda x:x['pair']['target']['journal'].append(['016','0'*64,'2026-11-05T15:00:00+00:00','0'*40]))
     add('target_bad015_sha',lambda x:x['pair']['target']['journal'][-1].__setitem__(1,'0'*64))
     add('target_extra_table',lambda x:x['pair']['target']['nativeCatalogueCounts'].__setitem__('table',98))
     add('target_privileged_actor',lambda x:x['pair']['target']['endpoint'].__setitem__('actor','statarena_admin'))
     add('target_tls_false',lambda x:x['pair']['target']['endpoint'].__setitem__('tls',False))
     add('target_wrong_policy',lambda x:x['targetPolicy'].__setitem__('policyId','membership-original-restored-m18da43-local099-v1'))
     add('target_wrong_definition',lambda x:x['targetPolicy'].__setitem__('canonicalDefinitionSha256','0'*64))
     add('target_old_e24_baseline',lambda x:x['targetPolicy'].__setitem__('beforeStateSha256','e24d2f4864f2a24c639d5556b4012d276b8958f5df3d02e2a80e52a601ae9a32'))
     add('target_wrong_sequence_gaps',lambda x:x['targetPolicy'].__setitem__('accountedSequenceGaps',0))
     add('target_source_alias',lambda x:x['pair']['target'].__setitem__('origin','real_native_sql_checkpoint'))
     add('missing_target_policy',lambda x:x.pop('targetPolicy'))
     for label,mutate in mutations:
      item=json.loads(json.dumps(fixture));mutate(item);p=run/(label+'.json');save(p,item);out=cli(['--check-local-structure','--structure',str(p),'--structure-sha256',sha(p)],label,1);assert out['status']=='refused' and out['connections']==0
     actual={'refused':len(mutations),'connections':0}
    elif case=='live_mode_refusals':
     actual=[]
     for label,args in [('missing_actual_authority',['--preflight-rds']),('apply_unreleased',['--apply-rds']),('host_override',['--host','external.invalid']),('actor_override',['--actor','statarena_admin'])]:
      out=cli(args,label,2 if label in ['host_override','actor_override'] else 1);actual.append({'case':label,'status':out.get('status','argparse_refused')})
     out=cli(['--preflight-rds'],'pg_poison',1,{'PGHOSTADDR':'192.0.2.9'});assert out['connections']==0
    else:
     out=cli(['--audit-qualified-core'],case);assert out['status']=='qualified_code_identical' and out['copyMethodsIdentical'] is True and out['oldModuleGlobalsUnchanged'] is True;actual=out
    report['cases'].append({'case':case,'status':'pass','actual':actual})
   except BaseException as e:block=case;report['cases'].append({'case':case,'status':'fail','error':str(e),'traceback':traceback.format_exc()})
 finally:
  if private:shutil.rmtree(private)
  report['privateTripwireRemoved']=private is None or not private.exists();report['elapsedSeconds']=round(time.monotonic()-started,3);report['counts']={s:sum(c['status']==s for c in report['cases']) for s in ['pass','fail','unverified']};report['status']='pass_structure_and_boundaries_only' if report['counts']=={'pass':len(CASES),'fail':0,'unverified':0} else 'fail';save(run/'result.json',report);print(json.dumps({'status':report['status'],'counts':report['counts'],'cliCommands':len(report['cliCommands']),'evidence':str(run/'result.json')}))
 return 0 if report['status']=='pass_structure_and_boundaries_only' else 1

if __name__=='__main__':raise SystemExit(main())
