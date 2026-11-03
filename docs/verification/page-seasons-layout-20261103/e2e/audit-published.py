"""Read-only inspection of published enrichment columns, one Ligue 1 chunk per season."""
from pathlib import Path
import json,gzip,urllib.request,concurrent.futures
folder=Path(__file__).resolve().parent
base='http://127.0.0.1:3000/data/'
manifest=json.load(urllib.request.urlopen(base+'dashboard-manifest.json'))
def sample(season):
 chunk=next((c for c in season['chunks'] if c.get('leagueId')=='l_3FJFUl'),None)
 if not chunk:return {'season':season['id'],'unavailable':True}
 doc=json.loads(gzip.decompress(urllib.request.urlopen(base+chunk['path']).read()))
 shots=doc['tables']['shots'];players=doc['tables']['performances'];matches=doc['tables']['matches']
 return {'season':season['id'],'path':chunk['path'],'retrievedAt':doc.get('meta',{}).get('retrievedAt'),'shots':{'rows':len(shots['rows']),'enrichedColumns':[k for k in ['goalCrossedY','goalCrossedZ','isBlocked','blockedX','blockedY','insideBox','keeperName','minuteAdded','period'] if k in shots['keys']]},'players':{'rows':len(players['rows']),'columns':len(players['keys']),'captainColumn':'isCaptain' in players['keys']},'matches':{'rows':len(matches['rows']),'metadataColumns':[k for k in ['referee','stadium','roundName'] if k in matches['keys']]}}
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:samples=list(pool.map(sample,manifest['seasons']))
report={'setup':'Read-only same-origin Neon backend; one Ligue 1 published partition sampled per available season. No DB or object mutations.','command':'python3 output/playwright/page-seasons-layout-20261103/audit-published.py','scope':'Column presence is not field completeness; this sample does not prove every season/competition has been fully regenerated.','manualWorkflowDispatched':False,'samples':samples}
(folder/'rematerialize-published-samples.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'sampled':len(samples),'shotColumnsPresent':sum(bool(s.get('shots',{}).get('enrichedColumns')) for s in samples)}))
