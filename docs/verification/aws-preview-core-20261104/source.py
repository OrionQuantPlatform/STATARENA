import datetime as dt,json
from pathlib import Path
import psycopg
from psycopg.rows import dict_row
here=Path(__file__).resolve().parent
c=json.loads(Path('/tmp/statarena-aws-runtime-20261104.json').read_text())
assert c['database']=='statarena_prod' and c['host']=='statarena-postgres.clcy2iqyajbl.us-east-2.rds.amazonaws.com'
with psycopg.connect(host=c['host'],dbname=c['database'],user=c['username'],password=c['password'],sslmode='verify-full',sslrootcert='/tmp/statarena-rds-us-east-2-20261104.pem',application_name='statarena-preview-validation',options='-c default_transaction_read_only=on -c statement_timeout=5000',row_factory=dict_row) as db:
 def one(q,a=()):return db.execute(q,a).fetchone()
 def many(q,a=()):return db.execute(q,a).fetchall()
 id='m_02vUAH';report={'time':dt.datetime.now(dt.timezone.utc).isoformat(),'session':one("select current_setting('transaction_read_only') readonly,(select ssl from pg_stat_ssl where pid=pg_backend_pid()) tls"),'match':one('select id,season,league_id,league,date,home_name,away_name,home_score,away_score,home_id,away_id from statarena_app.matches where id=%s',(id,))}
 m=report['match'];assert m
 report['alternate']=one('select league_id,season from statarena_app.partitions where league_id!=%s order by season desc limit 1',(m['league_id'],))
 report['player']=one('select a.id,a.player_id,p.name,a.minutes,a.rating,a.team_id,a.team from statarena_app.appearances a join statarena_app.players p on p.id=a.player_ref where a.match_id=%s and a.rating is not null order by a.rating desc,a.id limit 1',(id,))
 report['playerTotals']=one('select count(*) appearances,count(*) filter(where minutes>0) played,sum(minutes) minutes,sum(goals) goals from statarena_app.appearances where player_id=%s and season=%s and league_id=%s',(report['player']['player_id'],m['season'],m['league_id']))
 report['stats']=many('select metric_key,label,home_value,away_value,home_raw,away_raw from statarena_app.team_statistics where match_id=%s order by ordinal',(id,))
 report['shots']=many('select id,player_name,minute,xg,team_id from statarena_app.shots where match_id=%s order by ordinal',(id,))
 report['families']=many("select family,status,source_digest from statarena_app.match_families where match_id=%s and subject_id='' and params='{}' order by family",(id,))
 report['coverage']=one('select count(*) parts,(select count(*) from statarena_app.matches) matches from statarena_app.partitions')
(here/'source.json').write_text(json.dumps(report,ensure_ascii=False,default=str,indent=2)+'\n')
print(m['home_name'],m['home_score'],m['away_score'],m['away_name'],report['player']['name'],len(report['shots']),len(report['stats']),report['alternate'])
