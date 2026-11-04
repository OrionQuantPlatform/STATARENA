"""Read-only observation of the already-submitted RDS storage operation."""
import datetime,json,pathlib,subprocess,urllib.request
p=pathlib.Path(__file__).resolve().parent;now=datetime.datetime.now(datetime.timezone.utc)
def aws(*args):return json.loads(subprocess.run(['aws','--profile','statarena','--region','us-east-2',*args,'--output','json'],capture_output=True,text=True,check=True).stdout)
state=aws('rds','describe-db-instances','--db-instance-identifier','statarena-postgres','--query','DBInstances[0].{Class:DBInstanceClass,AllocatedGiB:AllocatedStorage,Status:DBInstanceStatus,Pending:PendingModifiedValues,StorageType:StorageType,Iops:Iops,Throughput:StorageThroughput}')
metric=aws('cloudwatch','get-metric-statistics','--namespace','AWS/RDS','--metric-name','FreeStorageSpace','--dimensions','Name=DBInstanceIdentifier,Value=statarena-postgres','--start-time',(now-datetime.timedelta(minutes=12)).isoformat(),'--end-time',now.isoformat(),'--period','60','--statistics','Minimum','Average')
points=sorted(metric.get('Datapoints',[]),key=lambda r:r['Timestamp']);record={'atUtc':now.isoformat(),'rds':state,'recentFreeStorageSpace':points[-4:],'rerun':'python3 docs/verification/aws-capacity-expansion-20261104/observe.py'}
try:
 with urllib.request.urlopen('https://d317dq37z1tacb.cloudfront.net/api/health',timeout=15)as response:record['apiHealth']={'status':response.status,'body':json.loads(response.read())}
except Exception as error:record['apiHealth']={'errorType':type(error).__name__}
# A full-minute metric newer than the request avoids treating stale capacity as ready.
start=json.loads((p/'execution.json').read_text())['atUtc'];fresh=[r for r in points if r['Timestamp']>start and (now-datetime.datetime.fromisoformat(r['Timestamp'])).total_seconds()<240]
record['safeForNewGuard']=state['AllocatedGiB']==64 and state['Class']=='db.t4g.micro' and state['Iops']==3000 and state['Throughput']==125 and state['Status']in('available','storage-optimization')and bool(fresh and fresh[-1]['Minimum']>40_000_000_000)and record['apiHealth'].get('status')==200
with(p/'observations.jsonl').open('a')as f:f.write(json.dumps(record)+'\n')
(p/'latest.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
