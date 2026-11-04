"""Read existing sampled origin events. Sends no requests to the website or database."""
from datetime import datetime,timezone
import json
import re
import subprocess
from pathlib import Path

folder=Path(__file__).resolve().parent
baseline=json.loads((folder.parent/'aws-lambda-memory-20261104/result.json').read_text())
pages=json.loads((folder/'measurements.json').read_text())
sizes={r['bytes']:r['label'] for r in pages['routes']}
start=int(datetime.fromisoformat(baseline['started']).timestamp()*1000)-30*60*1000
end=int(datetime.fromisoformat(pages['when']).timestamp()*1000)
config=subprocess.run(['aws','--profile','statarena','--region','us-east-2','logs','filter-log-events','--log-group-name','/aws/lambda/statarena-backend','--start-time',str(start),'--end-time',str(end),'--filter-pattern','"statarena.request"','--max-items','200','--output','json'],capture_output=True,text=True,check=True)
found=json.loads(config.stdout)
known={r['originRequestId']:g['memoryMiB'] for g in baseline['configurations'] for r in g['rows']}
records=[]
for row in found['events']:
    msg=row['message']
    pos=msg.find('{"event":"statarena.request"')
    if pos<0:continue
    event=json.loads(msg[pos:])
    if event['route'] not in ['/api/seasons/partition','/api/fixtures']: continue
    ids=re.findall(r'\b[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}\b',msg[:pos])
    reqid=ids[-1] if ids else None
    records.append(dict(timestamp=row['timestamp'],requestId=reqid,exactBaselineMemory=known.get(reqid),
                        matchingLogicalSize=sizes.get(event['metrics'].get('response_bytes')),sample=event))
out={'startMs':start,'endMs':end,'eventsInspected':len(found['events']),'truncated':bool(found.get('NextToken')),'matchingRouteEvents':records}
(folder/'origin.json').write_text(json.dumps(out,indent=2)+'\n')
print('sampled',out['eventsInspected'],'pagination',len(records),'exact dense sessions',sum(r['exactBaselineMemory'] is not None for r in records))
