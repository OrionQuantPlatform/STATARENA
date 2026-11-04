from pathlib import Path
import os,sys,gzip,json
import psycopg
root=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(root/"dashboard/scripts"))
from relational_catalog import publish_catalog
f=root/"docs/verification/aws-catalog-20261104/captures/raw__cup-worker__native__l_0bfbkO__2025-2026.json.gz"
value=json.load(gzip.open(f,'rt'))
x,y=value["matches"][:2]
value["matches"]=[{**x,"id":"m_000000","score_home":77},{**y,"id":"m_KEEP01"}]
value["rounds"]={"m_KEEP01":{"name":"Saved final","playoff":True}}
value["roundsChecked"]={}
with psycopg.connect(os.environ["FIXTURE_DB"]) as db:
    publish_catalog(db,[("raw/cup-worker/native/l_0bfbkO/2025-2026.json",value)])
