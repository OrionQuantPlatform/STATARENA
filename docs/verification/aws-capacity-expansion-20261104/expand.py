"""Execute the exact owner-approved storage-only extension on the existing RDS."""
import datetime,json,pathlib,subprocess
p=pathlib.Path(__file__).resolve().parent
aws=['aws','--profile','statarena','--region','us-east-2']
def call(*args):return json.loads(subprocess.run(aws+list(args)+['--output','json'],check=True,capture_output=True,text=True).stdout)
fields='{Arn:DBInstanceArn,Class:DBInstanceClass,AllocatedGiB:AllocatedStorage,StorageType:StorageType,IOPS:Iops,Throughput:StorageThroughput,Status:DBInstanceStatus,Pending:PendingModifiedValues,Endpoint:Endpoint.Address,Vpc:DBSubnetGroup.VpcId}'
request={'DBInstanceIdentifier':'statarena-postgres','AllocatedStorage':64,'ApplyImmediately':True}
report={'atUtc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'ownerApproval':'Oui, passer à 64 Gio','approvedScope':'Only existing RDS20→64GiB allocated storage, quoted+$5.06USD/month before tax/credits; irreversible allocation restriction acknowledged.','request':request,'executed':False}
try:
 assert call('sts','get-caller-identity','--query','Account')=='361769570630'
 before=call('rds','describe-db-instances','--db-instance-identifier','statarena-postgres','--query','DBInstances[0].'+fields);report['before']=before
 assert before['Arn']=='arn:aws:rds:us-east-2:361769570630:db:statarena-postgres'
 assert before['Class']=='db.t4g.micro'and before['AllocatedGiB']==20 and before['StorageType']=='gp3'
 assert before['IOPS']==3000 and before['Throughput']==125 and before['Status']=='available'and before['Pending']=={}
 assert before['Endpoint']=='statarena-postgres.clcy2iqyajbl.us-east-2.rds.amazonaws.com'and before['Vpc']=='vpc-08e400afa07fc1812'
 requestfile=p/'request.json';requestfile.write_text(json.dumps(request,indent=2)+'\n')
 report['response']=call('rds','modify-db-instance','--cli-input-json','file://'+str(requestfile),'--query','DBInstance.'+fields)
 report['executed']=True
except BaseException as e:
 report['failureType']=type(e).__name__;raise
finally:
 (p/'execution.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report,indent=2))
