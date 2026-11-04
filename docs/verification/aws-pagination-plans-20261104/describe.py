"""Derive the result table from recorded evidence and verify the ordered descriptor."""
import hashlib
import json
import re
from pathlib import Path
folder=Path(__file__).resolve().parent
p=json.loads((folder/'measurements.json').read_text())
r=json.loads((folder/'replay.json').read_text())
ddl=(folder.parents[2]/'dashboard/backend/migrations/003_relational_core.sql').read_text()
line=re.search(r'CREATE TABLE IF NOT EXISTS statarena_app.appearances\((.*?)\);',ddl)[1]
keys=[col.split(' ')[0] for col in line.split(',FOREIGN KEY')[0].split(',')]+['name','image_url','extras']
assert keys==r['appearanceKeys']
out={'descriptor':{'keys':len(keys),'matchesSealedMigration003PlusThreeExplicitJoinedFields':True,'sha256':hashlib.sha256(json.dumps(keys,separators=(',',':')).encode()).hexdigest()},'routes':[]}
for route in p['routes']:
    m=route['internal']['metrics']
    out['routes'].append({'label':route['label'],'serverMs':route['plan']['Execution Time'],'pgFields':sum(route['fieldBytes'].values()),'driverIncludingWanMs':m['sql_ms'],'driverFieldParseMs':route['parseMs'],'packMs':route['packMs'],'stringifyMs':m['serialize_ms'],'residualHandlerAfterSqlPackSerializeMs':round(route['internal']['duration_ms']-m['sql_ms']-route['packMs']-m['serialize_ms']-m['pool_wait_ms'],3),'bodyBytes':route['bytes'],'readBlocks':route['plan']['Plan']['Shared Read Blocks']})
(folder/'summary.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out))
