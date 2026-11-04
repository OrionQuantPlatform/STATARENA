import json,os,sys
from pathlib import Path
from urllib.parse import urlparse
import psycopg
root=Path(os.environ['CANDIDATE_ROOT'])
sys.path.insert(0,str(root/'dashboard/scripts'))
from relational_core import publish_snapshot
target=urlparse(os.environ['TEST_DATABASE_URL'])
assert target.hostname=='127.0.0.1' and target.path=='/relational_core_e2e'
s=json.loads(Path(sys.argv[1]).read_text())
with psycopg.connect(os.environ['TEST_DATABASE_URL']) as db:
    publish_snapshot(db,'2026/2027','l_0ALvwF',s['data'])
    db.execute("UPDATE statarena_app.partitions SET source_digest=%s WHERE season='2026/2027' AND league_id='l_0ALvwF'",(s['generation'],))
    db.execute("insert into statarena_app.partitions(season,league_id,source_digest) VALUES ('2026/2027','l_000000',repeat('0',64))")
    db.execute("insert into statarena_app.appearance_metrics(appearance_id,metric_key,value) select id,key,0 from statarena_app.appearances cross join (values ('constructor'),('__proto__')) k(key) where match_id='m_000001'")
    db.execute('analyze')
