"""Read-only guard, concurrency and narrow publication metadata snapshot."""
import base64,datetime as dt,json,subprocess
from pathlib import Path
import psycopg,yaml
from psycopg.rows import dict_row
out=Path(__file__).resolve().parent
repo='OrionQuantPlatform/STATARENA';branch='codex/aws-backend-20261104'
def gh(*args):return subprocess.check_output(['gh',*args],text=True)
sha=gh('api',f'repos/{repo}/git/ref/heads/{branch}','--jq','.object.sha').strip()
now=dt.datetime.now(dt.timezone.utc).isoformat()
report={'time':now,'branch':branch,'sha':sha,'workflows':{},'openRuns':{}}
for name in ('daily-sync','historical-backfill','uefa-standings','rematerialize'):
    obj=json.loads(gh('api',f'repos/{repo}/contents/.github/workflows/{name}.yml?ref={sha}'))
    wf=yaml.safe_load(base64.b64decode(obj['content']))
    for key,job in wf['jobs'].items():
        if not any(step.get('with',{}).get('mode')=='ingest' for step in job.get('steps',[])):continue
        report['workflows'][name]={'job':key,'guard':job['env']['STATARENA_SQL_LIMIT_BYTES'],'concurrency':job.get('concurrency',wf.get('concurrency')),'publication':next(step['run']for step in job['steps'] if 'relational_materialize.py' in step.get('run',''))}
for state in ('in_progress','queued','pending','waiting','requested'):
    data=json.loads(gh('api',f'repos/{repo}/actions/runs?status={state}&per_page=100'))
    report['openRuns'][state]=[{'id':r['id'],'name':r['name'],'status':r['status'],'branch':r['head_branch'],'sha':r['head_sha'],'event':r['event'],'created':r['created_at']}for r in data['workflow_runs']]
    assert data['total_count']<=100
report['configuredCap']=int(gh('variable','get','STATARENA_SQL_LIMIT_BYTES','-R',repo).strip())
c=json.loads(Path('/tmp/statarena-aws-runtime-20261104.json').read_text());assert c['database']=='statarena_prod' and c['host']=='statarena-postgres.clcy2iqyajbl.us-east-2.rds.amazonaws.com'
with psycopg.connect(host=c['host'],dbname=c['database'],user=c['username'],password=c['password'],sslmode='verify-full',sslrootcert='/tmp/statarena-rds-us-east-2-20261104.pem',application_name='statarena-readiness-audit',options='-c default_transaction_read_only=on -c statement_timeout=3000',row_factory=dict_row) as db:
    report['rds']=db.execute("""SELECT current_database() AS database,current_setting('transaction_read_only') AS read_only,pg_database_size(current_database()) AS database_bytes,
      (SELECT count(*) FROM statarena_app.publication_jobs) queued,
      (SELECT count(*) FROM statarena_app.partitions) published,
      (SELECT count(*) FROM statarena_app.matches) published_matches,
      (SELECT count(*) FROM pg_locks WHERE locktype='advisory' AND database=(SELECT oid FROM pg_database WHERE datname=current_database()) AND classid=0 AND objid=97813003 AND objsubid=1 AND granted) publication_leases""").fetchone()
    report['state']=db.execute("SELECT workflow,status,remaining,updated_at FROM statarena_app.workflow_state WHERE workflow='relational-materialize'").fetchone()
    report['next']=db.execute("""SELECT season,league_id FROM statarena_app.publication_jobs ORDER BY (season='@details'),season DESC,changed_at,league_id LIMIT 10""").fetchall()
print(json.dumps(report,indent=2,default=str))
