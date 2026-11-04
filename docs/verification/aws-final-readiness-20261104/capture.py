"""Bounded read-only metadata audit. Captures readiness; never claims full coverage."""
import datetime,json,pathlib,subprocess,sys
import psycopg
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def aws(*args):
 r=subprocess.run(['aws','--profile','statarena','--region','us-east-2',*args,'--output','json'],capture_output=True,text=True,check=True)
 return json.loads(r.stdout)
report={'atUtc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'rerun':'PYTHONPATH=/tmp/statarena-archive-remat-pg/python python3 docs/verification/aws-final-readiness-20261104/capture.py','setup':'Existing RDS; SSM runtime secret held only in memory; verified regional TLS CA; read-only session; bounded metadata/count queries. No data or infrastructure writes.','captureSucceeded':False,'objectiveAchieved':False}
try:
 assert aws('sts','get-caller-identity','--query','Account')=='361769570630'
 c=json.loads(aws('ssm','get-parameter','--name','/statarena/app/rds-runtime','--with-decryption')['Parameter']['Value'])
 assert c['host']=='statarena-postgres.clcy2iqyajbl.us-east-2.rds.amazonaws.com' and c['database']=='statarena_prod'
 with psycopg.connect(host=c['host'],dbname=c['database'],user=c['username'],password=c['password'],sslmode='verify-full',sslrootcert=str(ROOT/'dashboard/backend/certs/rds-us-east-2.pem'),connect_timeout=5,options='-c default_transaction_read_only=on -c statement_timeout=5000 -c lock_timeout=1000',autocommit=True,application_name='statarena-final-readiness')as db:
  identity=db.execute("SELECT current_database(),current_setting('transaction_read_only'),ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()").fetchone()
  assert identity==('statarena_prod','on',True)
  report['session']={'database':identity[0],'readOnly':identity[1],'tls':identity[2]}
  report['documentTypedServingColumns']=[dict(zip(('table','column','type'),r))for r in db.execute("SELECT table_name,column_name,data_type FROM information_schema.columns WHERE table_schema='statarena_app' AND data_type IN('json','jsonb','bytea') ORDER BY table_name,column_name")]
  report['servingRelations']=[dict(zip(('type','count'),r))for r in db.execute("SELECT table_type,count(*) FROM information_schema.tables WHERE table_schema='statarena_app' GROUP BY table_type ORDER BY table_type")]
  counts=db.execute('SELECT (SELECT count(*) FROM statarena_app.partitions),(SELECT count(*) FROM statarena_app.matches),(SELECT count(*) FROM statarena_app.appearances),(SELECT count(*) FROM statarena_app.publication_jobs)').fetchone()
  report['exactCounts']=dict(zip(('publishedPartitions','matches','appearances','queuedPartitions'),counts))
  report['committedInputKinds']=[{'kind':r[0],'count':r[1]}for r in db.execute('SELECT kind,count(*) FROM statarena_app.worker_inputs GROUP BY kind ORDER BY kind')]
  report['workflowReceipt']=db.execute("SELECT status,remaining,updated_at FROM statarena_app.workflow_state WHERE workflow='relational-materialize'").fetchone()
 report['rds']=aws('rds','describe-db-instances','--db-instance-identifier','statarena-postgres','--query','DBInstances[0].{Class:DBInstanceClass,AllocatedGiB:AllocatedStorage,Status:DBInstanceStatus,Pending:PendingModifiedValues}')
 report['backend']=aws('lambda','get-function-configuration','--function-name','statarena-backend','--query','{Runtime:Runtime,MemorySize:MemorySize,State:State,LastUpdateStatus:LastUpdateStatus,CodeSha256:CodeSha256}')
 report['captureSucceeded']=True
 report['remaining']='Full source publication, full-scale endpoint and website acceptance, active writer runs and production cutover/legacy retirement remain unproven. This metadata capture is not a full endpoint or source-parity test.'
except BaseException as error:
 report['failureType']=type(error).__name__
finally:
 (HERE/'metadata.json').write_text(json.dumps(report,indent=2,default=str)+'\n')
 print(json.dumps({'captureSucceeded':report['captureSucceeded'],'objectiveAchieved':False,'exactCounts':report.get('exactCounts'),'documentTypedServingColumns':report.get('documentTypedServingColumns'),'failureType':report.get('failureType')}))
raise SystemExit(not report['captureSucceeded'])
