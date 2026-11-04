"""Refresh delayed REPORT attribution without repeating any football request."""
import datetime,json,pathlib,re,subprocess,sys
p=pathlib.Path(__file__).resolve().parent;phase=sys.argv[1];assert phase in ('before','after');f=p/(phase+'.json');d=json.loads(f.read_text());rows=d['rows'];ids={r['requestId']for r in rows}
a=['aws','--profile','statarena','--region','us-east-2','logs','filter-log-events','--log-group-name','/aws/lambda/statarena-backend','--start-time',str(min(r['startMs']for r in rows)-2000),'--end-time',str(max(r['endMs']for r in rows)+10000),'--output','json']
raw=subprocess.run(a,capture_output=True,text=True,check=True);events=json.loads(raw.stdout).get('events',[]);reports=[]
for event in events:
 message=event.get('message','');m=re.search(r'^REPORT RequestId:\s+(\S+)',message)
 if m and m[1]in ids:reports.append({'timestamp':event['timestamp'],'message':message.strip()})
d.setdefault('initialMatchingReports',d.get('matchingReports'));d['lambdaReports']=reports;d['matchingReports']=len(reports);d['logsRefreshedUtc']=datetime.datetime.now(datetime.timezone.utc).isoformat();f.write_text(json.dumps(d,indent=2)+'\n');print(json.dumps({'phase':phase,'eventsInExactTimeWindow':len(events),'matchingReports':len(reports)}))
