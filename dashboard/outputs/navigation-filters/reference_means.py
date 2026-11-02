"""Independent raw-table reference inputs for the browser E2E run.
Run from repo root: python3 dashboard/outputs/navigation-filters/reference_means.py
"""
from pathlib import Path
from collections import defaultdict
import gzip,json,math
ROOT=Path(__file__).resolve().parents[3]
DATA=ROOT/'data'
read=lambda p:json.loads(gzip.decompress(p.read_bytes()))
index=json.loads((DATA/'raw/index.json').read_text())
season=next(s for s in index['seasons'] if s['id']=='2026/2027')
out={}
for league in ['l_0ErfuF','l_3FJFUl']:
    chunk=next(c for c in season['chunks'] if c['leagueId']==league)
    identities={r['id']:r for r in read(DATA/chunk['tables']['players']['path'])}
    players={}
    for row in read(DATA/chunk['tables']['performances']['path']):
        pid=row['playerId']
        if not isinstance(row.get('minutes'),(int,float)) or row['minutes']<=0:continue
        p=players.setdefault(pid,{'playerId':pid,'name':identities[row['playerRef']]['name'],'matches':set(),'minutes':[],'stats':defaultdict(list),'observedMinutes':defaultdict(list)})
        if row['matchId'] in p['matches']:continue
        p['matches'].add(row['matchId']);p['minutes'].append(row['minutes'])
        for key in ['rating','goals','assists','xg','xa','saves','goalsPrevented']:
            value=row.get(key)
            if isinstance(value,(int,float)) and math.isfinite(value):
                p['stats'][key].append(value);p['observedMinutes'][key].append(row['minutes'])
    values=[]
    for p in players.values():
        averages={key:sum(v)/len(v) for key,v in p['stats'].items() if v}
        per90={key:averages[key] if key=='rating' else 90*sum(v)/sum(p['observedMinutes'][key]) for key,v in p['stats'].items() if v}
        values.append({'playerId':p['playerId'],'name':p['name'],'matches':len(p['matches']),'meanMinutes':sum(p['minutes'])/len(p['minutes']),'averages':averages,'per90':per90,'counts':{key:len(v) for key,v in p['stats'].items()}})
    out[league]={'players':len(values),'ratingAtLeast8':[p['playerId'] for p in values if p['averages'].get('rating',0)>=8],'goalsAtLeastHalf':[p['playerId'] for p in values if p['averages'].get('goals',0)>=.5],'examples':[p for p in values if 'raphinha' in p['name'].lower() or 'hakimi' in p['name'].lower()]}
manifest=json.loads((DATA/'computed/dashboard/index.json').read_text())
out['clubCountryCount']=len(manifest['clubCountries'])
output=Path(__file__).parent/'reference-means.json'
output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(out,ensure_ascii=False,indent=2))

# Reference for cross-competition identity and aggregate pass-percentage filters.
europe={'l_4WFCIZ','l_0ErfuF','l_1Isor4','l_0ALvwF','l_3FJFUl','l_4QexZg','l_4H43wr','l_0bfbkO','l_38d9HA','l_2WZ2tt'}
seen=set();europe_rows=[];numerator=denominator=0
for chunk in season['chunks']:
    if chunk['leagueId'] not in europe:continue
    for row in read(DATA/chunk['tables']['performances']['path']):
        if row['playerId']!='p_2DQMAL' or not isinstance(row.get('minutes'),(int,float)) or row['minutes']<=0 or row['matchId'] in seen:continue
        seen.add(row['matchId']);europe_rows.append(row)
        if chunk['leagueId']=='l_0ErfuF' and isinstance(row.get('passesAccurate'),(int,float)) and isinstance(row.get('passesAttempted'),(int,float)) and row['passesAttempted']>0:
            numerator+=row['passesAccurate'];denominator+=row['passesAttempted']
ratings=[row['rating'] for row in europe_rows if isinstance(row.get('rating'),(int,float))]
extra={'raphinhaEuropeMatches':len(seen),'raphinhaEuropeRating':sum(ratings)/len(ratings),'raphinhaLaLigaPassAccuracy':100*numerator/denominator,'source':'raw performances joined by playerId, played matches deduplicated; pass accuracy uses only rows with both counts'}
(Path(__file__).parent/'reference-extra.json').write_text(json.dumps(extra,indent=2)+'\n')
