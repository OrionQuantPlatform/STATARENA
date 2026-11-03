"""HTTP E2E: inspect actual enriched partitions served by the production origin."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,gzip,urllib.request,concurrent.futures,hashlib
p=argparse.ArgumentParser();p.add_argument('--origin',default='https://statarena-analytics.vercel.app');a=p.parse_args()
out=Path(__file__).resolve().parent
base=a.origin.rstrip('/')
def get(path):
 with urllib.request.urlopen(urllib.request.Request(base+path,headers={'Cache-Control':'no-cache'}),timeout=60) as r:return r.read(),dict(r.headers)
def decode(table):
 keys=table['keys'];d=table.get('dictionaries',{});missing=table.get('missing',{})
 return [{key:(d[str(j)][values[j]] if str(j) in d and values[j] is not None else values[j]) for j,key in enumerate(keys) if j not in missing.get(str(i),[])} for i,values in enumerate(table['rows'])]
body,headers=get('/data/dashboard-manifest.json');manifest=json.loads(body)
def sample(season):
 chunk=next((c for c in season['chunks'] if c['leagueId']=='l_3FJFUl'),None)
 if not chunk:return {'season':season['id'],'status':'unavailable'}
 body,h=get('/data/'+chunk['path']);doc=json.loads(gzip.decompress(body));tables=doc['tables'];shots=decode(tables['shots']);players=decode(tables['performances']);matches=decode(tables['matches'])
 columns={kind:tables[kind]['keys'] for kind in ['shots','performances','matches']}
 checks={'shot_columns':all(k in columns['shots'] for k in ['goalCrossedY','goalCrossedZ','isBlocked','blockedX','blockedY','insideBox','keeperName','minuteAdded','period']),'player_columns':all(k in columns['performances'] for k in ['isCaptain','passesAttempted','groundDuelsWon','aerialsWon','topSpeed']),'match_columns':all(k in columns['matches'] for k in ['referee','stadium','roundName'])}
 example=next((s for s in shots if s.get('goalCrossedY') is not None and s.get('goalCrossedZ') is not None),None)
 performance=next((r for r in players if r.get('isCaptain') is True and r.get('passesAttempted') is not None),None)
 metadata=next((m for m in matches if m.get('referee') and m.get('stadium')),None)
 checks.update(actual_shot_value=example is not None,actual_captain_and_attempts=performance is not None,actual_match_metadata=metadata is not None)
 return {'season':season['id'],'path':chunk['path'],'sha256':hashlib.sha256(body).hexdigest(),'manifestHashMatches':hashlib.sha256(body).hexdigest()==chunk['sha256'],'rows':{k:len(tables[k]['rows']) for k in ['shots','performances','matches']},'columns':columns,'checks':checks,'nonNullCounts':{k:sum(s.get(k) is not None for s in shots) for k in ['goalCrossedY','goalCrossedZ','blockedX','blockedY']},'examples':{'shot':{k:example.get(k) for k in ['id','matchId','playerName','goalCrossedY','goalCrossedZ','isBlocked','blockedX','blockedY']} if example else None,'player':{k:performance.get(k) for k in ['playerId','matchId','isCaptain','passesAccurate','passesAttempted','aerialsWon','groundDuelsWon']} if performance else None,'match':{k:metadata.get(k) for k in ['id','referee','stadium','roundName']} if metadata else None},'status':'passed' if all(checks.values()) else 'failed'}
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:samples=list(pool.map(sample,manifest['seasons']))
report={'setup':'Public production origin, actual content-addressed packed partitions and manifest; no synthetic data or mutation.','command':'python3 output/playwright/rematerialization-completion-20261103/verify_public_data.py','expected':'All six Ligue 1 seasons expose the enriched shot/player/match columns and actual non-null examples; partition hashes match the public manifest.','checkedAt':datetime.now(timezone.utc).isoformat(),'origin':base,'manifestEtag':headers.get('ETag') or headers.get('Etag'),'samples':samples,'status':'passed' if len(samples)==6 and all(s['status']=='passed' and s['manifestHashMatches'] for s in samples) else 'failed'}
file=out/('public-data-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.json');file.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n');print(json.dumps({'report':str(file),'status':report['status'],'samples':[{'season':s['season'],'status':s['status'],'nonNullCounts':s.get('nonNullCounts')} for s in samples]}));raise SystemExit(report['status']!='passed')
