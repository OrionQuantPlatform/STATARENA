"""Read-only live HTTP and Lambda REPORT evidence for an identical dense page."""
import datetime,gzip,hashlib,http.client,json,pathlib,re,subprocess,sys,time
p=pathlib.Path(__file__).resolve().parent;phase=sys.argv[1];assert phase in ('before','after')
aws=['aws','--profile','statarena','--region','us-east-2'];host='d317dq37z1tacb.cloudfront.net';route='/api/seasons/partition?season=2026%2F2027&league=l_0ALvwF&limit=100&format=columns';function='statarena-backend'
def call(*args):return json.loads(subprocess.run(aws+list(args)+['--output','json'],capture_output=True,text=True,check=True).stdout)
result={'phase':phase,'atUtc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'rerun':f'python3 docs/verification/aws-pg-transport-release-20261104/public.py {phase}','url':'https://'+host+route,'expected':{'status':200,'cache':'no-store','encodedBytes':431391,'decodedBytes':1973314,'sha256':'0d6bbe72588aa8df43b6d7933093a9d9cd8f028a1b53d61fc8c68bdc37f7d403'},'rows':[],'passed':False}
out=p/(phase+'.json')
def save():out.write_text(json.dumps(result,indent=2)+'\n')
try:
 assert call('sts','get-caller-identity','--query','Account')=='361769570630'
 result['lambda']=call('lambda','get-function-configuration','--function-name',function,'--query','{MemorySize:MemorySize,State:State,LastUpdateStatus:LastUpdateStatus,CodeSha256:CodeSha256}')
 result['rds']=call('rds','describe-db-instances','--db-instance-identifier','statarena-postgres','--query','DBInstances[0].{InstanceClass:DBInstanceClass,AllocatedGiB:AllocatedStorage,Status:DBInstanceStatus,Pending:PendingModifiedValues}')
 assert result['lambda']['MemorySize']==512 and result['lambda']['LastUpdateStatus']=='Successful'
 expected_code={'before':'F8nND1oBu4BU7+CuB6n5+SUiQ5J706zW+qZZG88np1c=','after':'vsqhv0VlCTZVXNAaafseQUBuTmDI2kPPMLaOt2+jXpE='}[phase]
 assert result['lambda']['CodeSha256']==expected_code,'Deploy the reviewed phase-specific immutable artifact before this comparison'
 save();connection=http.client.HTTPSConnection(host,timeout=45)
 for index in range(6):
  start_ms=int(time.time()*1000);start=time.perf_counter();connection.request('GET',route,headers={'Accept-Encoding':'gzip','User-Agent':'StatArena-PG-transport-E2E/1'});response=connection.getresponse();wire=response.read();elapsed=(time.perf_counter()-start)*1000
  body=gzip.decompress(wire) if response.getheader('Content-Encoding')=='gzip' else wire
  row={'index':index,'firstObservation':index==0,'startMs':start_ms,'endMs':int(time.time()*1000),'elapsedMs':round(elapsed,2),'status':response.status,'cache':response.getheader('Cache-Control'),'edgeCache':response.getheader('X-Cache'),'encodedBytes':len(wire),'decodedBytes':len(body),'sha256':hashlib.sha256(body).hexdigest(),'etag':response.getheader('ETag'),'requestId':response.getheader('X-Amzn-Requestid'),'pop':response.getheader('X-Amz-Cf-Pop')};result['rows'].append(row);save()
  assert all(row[k]==v for k,v in result['expected'].items()) and row['edgeCache']=='Miss from cloudfront'
  print(json.dumps({'phase':phase,'index':index,'elapsedMs':row['elapsedMs'],'status':row['status'],'sha256':row['sha256']}),flush=True)
 connection.close();time.sleep(3)
 start=min(r['startMs']for r in result['rows'])-2000;end=max(r['endMs']for r in result['rows'])+10000;ids={r['requestId']for r in result['rows']};reports=[]
 events=call('logs','filter-log-events','--log-group-name','/aws/lambda/'+function,'--start-time',str(start),'--end-time',str(end)).get('events',[])
 for event in events:
  message=event.get('message','');match=re.search(r'^REPORT RequestId:\s+(\S+)',message)
  if match and match[1]in ids:reports.append({'timestamp':event['timestamp'],'message':message.strip()})
 result['lambdaReports']=reports;result['matchingReports']=len(reports);result['passed']=True
except BaseException as error:
 result['error']=type(error).__name__+': '+str(error);raise
finally:
 result['finishedUtc']=datetime.datetime.now(datetime.timezone.utc).isoformat();save();print(json.dumps({'phase':phase,'receipt':str(out),'passed':result['passed'],'matchingReports':result.get('matchingReports')}),flush=True)
