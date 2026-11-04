import gzip,json,os,subprocess,sys
from pathlib import Path
import psycopg

here=Path(__file__).resolve().parent
root=here.parents[2]
sys.path.insert(0,str(root/"dashboard/scripts"))
from relational_support import publish_supporting
fixture=json.load(gzip.open(here.parent/"aws-support-20261104/projections.json.gz","rt"))
source=next(b for n,p,b in fixture if n=="player-honours" and json.loads(p).get("id")=="p_1mZO3B")
expected=json.loads((here/"curated-before.json").read_text())
def project(value):
    return json.loads(subprocess.check_output(["node",str(root/"dashboard/scripts/materialize_curated.mjs")],
                                               input=json.dumps(value),text=True))
actual=project(source)
assert actual[0]["body"]["displayGroups"]==expected["expected"]
assert project(None)[0]["body"]["displayGroups"]==expected["withoutSource"]
with psycopg.connect(os.environ["LOCAL_FIXTURE_DB"]) as db:
    print(json.dumps(publish_supporting(db,actual)))
