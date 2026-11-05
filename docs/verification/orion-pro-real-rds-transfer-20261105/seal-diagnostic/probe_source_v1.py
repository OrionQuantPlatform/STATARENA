#!/usr/bin/env python3
"""One ROOT-allocated six-query source diagnostic; default is offline."""
from __future__ import annotations
from datetime import datetime,timezone
import hashlib,json,os,re,sys,time,traceback
from pathlib import Path

sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[3]
SOURCE=BASE.parent/'core-checkpoint/runs-v2/20261105T125423772600Z'
MIGRATION=ROOT/'dashboard/backend/migrations/014_orion_pro_membership_nonnull.sql'
LINES=[155,156,157,241,243]
MIGRATION_SHA='e0810f8670b2cb627ade2c76e3c8eb527ab31fd595d5cf939fd63bfc5cf649d6'
CHECKPOINT_SHA='8f4d77a9358a36419ac6424560c98f8ebf166e882702aac968f2e69a36164db6'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):Path(p).write_text(json.dumps(v,indent=2,default=str)+'\n')
def main():
    assert len(sys.argv) in [1,2] and (len(sys.argv)==1 or sys.argv[1]=='--run')
    assert sha(MIGRATION)==MIGRATION_SHA and sha(SOURCE/'checkpoint.json')==CHECKPOINT_SHA
    lines=MIGRATION.read_text().splitlines();queries=[]
    for number in LINES:
        line=lines[number-1];m=re.fullmatch(r"IF EXISTS \((.*)\) THEN RAISE EXCEPTION USING ERRCODE='23514', MESSAGE='([^']*)'; END IF;",line)
        assert m,'Unexpected sealed predicate structure'
        predicate=re.sub(r'\bg\b','2',m[1]);queries.append({'line':number,'invariant':m[2],'sql':'EXPLAIN (ANALYZE, BUFFERS, SETTINGS, FORMAT JSON) SELECT EXISTS ('+predicate+')'})
    if len(sys.argv)==1:
        print(json.dumps({'status':'offline_plan','selects':0,'connections':0,'plannedSelects':6,'queryLines':LINES,'businessWrites':[]}));return 0
    assert not any(k.startswith('PG') for k in os.environ),'Inherited libpq settings refused'
    assert datetime.now(timezone.utc)<datetime(2026,11,5,13,53,tzinfo=timezone.utc),'Source diagnostic allocation expired'
    run=BASE/'runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');run.mkdir(parents=True)
    consumed=BASE/'source-plans-v1.consumed.json';fd=os.open(consumed,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o644)
    with os.fdopen(fd,'w') as f:json.dump({'run':str(run),'executions':1,'maximumSelects':6,'maximumRetainedPlanBytes':65536,'maximumStatementSeconds':8,'maximumLockSeconds':1,'approvedByMessage':'ROOT scoped source-only diagnostic allocation'},f,indent=2);f.write('\n')
    report={'kind':'readonly_source_seal_planner_diagnostic_v1','command':[sys.executable,str(Path(__file__)),*sys.argv[1:]],'expected':str(BASE/'PROTOCOL.md'),
            'sourceCheckpointSha256':CHECKPOINT_SHA,'migrationSha256':MIGRATION_SHA,'scriptSha256':sha(Path(__file__)),'selects':0,'retainedServerMetadataBytes':0,
            'sourceRamReads':0,'cloudCalls':0,'businessWrites':[],'analyzeCommands':0,'generationFunctionCalls':0,'queries':[],'fullAcceptance':False}
    c=None;started=time.monotonic();status=1
    def execute(name,sql):
        assert report['selects']<6 and time.monotonic()-started<90
        entry={'name':name,'sql':sql,'sqlSha256':hashlib.sha256(sql.encode()).hexdigest(),'attempted':True};report['queries'].append(entry);report['selects']+=1;save(run/'progress.json',report)
        tick=time.monotonic();row=c.execute(sql).fetchone()[0];raw=json.dumps(row,separators=(',',':'),default=str).encode();entry['elapsedMs']=round((time.monotonic()-tick)*1000,3);entry['decodedBytes']=len(raw)
        assert report['retainedServerMetadataBytes']+len(raw)<=65536,'Retained server plan metadata bound exceeded'
        report['retainedServerMetadataBytes']+=len(raw);entry['actual']=row;save(run/'progress.json',report);return row
    try:
        checkpoint=json.loads((SOURCE/'checkpoint.json').read_text());marker=checkpoint['marker'];sys.path.insert(0,'/tmp/statarena-publication-test-python');import psycopg
        c=psycopg.connect(host='127.0.0.1',hostaddr='127.0.0.1',port=55467,dbname='postgres',user='orion_pro_runtime',password='',passfile='/dev/null',
            sslmode='verify-full',sslrootcert=marker['certificatePath'],autocommit=True,connect_timeout=7,
            options='-c default_transaction_read_only=on -c statement_timeout=8000 -c lock_timeout=1000 -c timezone=UTC -c search_path=pg_catalog -c idle_in_transaction_session_timeout=15000')
        c.execute('BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY')
        metadata=execute('source_identity_and_planner_stats',"""SELECT jsonb_build_object(
 'identity',jsonb_build_object('db',current_database(),'actor',current_user,'sessionActor',session_user,'version',current_setting('server_version_num'),'ro',current_setting('transaction_read_only'),'isolation',current_setting('transaction_isolation'),'statement',current_setting('statement_timeout'),'lock',current_setting('lock_timeout'),'tls',(SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()),'epoch',pg_postmaster_start_time()),
 'settings',(SELECT jsonb_object_agg(name,setting) FROM pg_settings WHERE name IN ('work_mem','jit','random_page_cost','seq_page_cost','cpu_tuple_cost','cpu_operator_cost','effective_cache_size','enable_nestloop','enable_hashjoin','enable_mergejoin','plan_cache_mode')),
 'statistics',(SELECT jsonb_agg(jsonb_build_object('relation',n.nspname||'.'||c.relname,'reltuples',c.reltuples,'relpages',c.relpages,'liveEstimate',s.n_live_tup,'modSinceAnalyze',s.n_mod_since_analyze,'lastAnalyze',s.last_analyze,'lastAutoAnalyze',s.last_autoanalyze,'analyzeCount',s.analyze_count,'autoanalyzeCount',s.autoanalyze_count,'ingestMaintain',has_table_privilege('orion_pro_ingest',c.oid,'MAINTAIN'),'ownerMaintain',has_table_privilege('orion_pro_owner',c.oid,'MAINTAIN')) ORDER BY c.relname) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace LEFT JOIN pg_stat_all_tables s ON s.relid=c.oid WHERE n.nspname='football' AND c.relname IN ('player_match_metric_values','match_players','player_match_stats')))""")
        identity=metadata['identity'];assert [identity[k] for k in ['db','actor','sessionActor','version','ro','isolation','statement','lock','tls']]==['postgres','orion_pro_runtime','orion_pro_runtime','180006','on','repeatable read','8s','1s',True]
        assert datetime.fromisoformat(identity['epoch'])==datetime.fromisoformat(marker['postmasterStartedAt'])
        for entry in queries:
            actual=execute(str(entry['line'])+' '+entry['invariant'],entry['sql']);plan=actual[0]
            report['queries'][-1]['planningTimeMs']=plan.get('Planning Time');report['queries'][-1]['executionTimeMs']=plan.get('Execution Time')
        c.rollback();report['readTransactionRolledBack']=True;report['status']='pass_readonly_diagnostic_only';status=0
    except BaseException as error:
        report.update(status='fail_diagnostic',errorType=type(error).__name__,sqlstate=getattr(error,'sqlstate',None),error=str(error),traceback=traceback.format_exc())
        if c is not None:
            try:c.rollback();report['readTransactionRolledBack']=True
            except BaseException:report['readTransactionRolledBack']=False
    finally:
        if c is not None:c.close()
        report['connectionClosed']=c is None or c.closed;report['elapsedSeconds']=round(time.monotonic()-started,3);save(run/'result.json',report)
        print(json.dumps({'status':report['status'],'selects':report['selects'],'retainedServerMetadataBytes':report['retainedServerMetadataBytes'],'evidence':str(run/'result.json')}))
    return status

if __name__=='__main__':raise SystemExit(main())
