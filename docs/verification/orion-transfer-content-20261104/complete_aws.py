"""Finish three exact AWS reads with existing CLI auth held only in RAM."""
import json
from pathlib import Path
import subprocess

import boto3
from botocore.config import Config

import read_content as core
import read_external as external

OUT,ROOT,SCOPE=core.OUT,core.ROOT,core.SCOPE
if (OUT/'aws-completion-execution.json').exists():raise SystemExit('AWS completion already recorded; no replay')
previous=json.loads((OUT/'external-execution.json').read_text())
budget=previous['budget'].copy()
if budget['objectHttpRequests']!=27:raise SystemExit('Unexpected remaining HTTP budget; require explicit review')
record={'startedAt':core.NOW(),'sqlInstructionsAdded':0,'remoteWrites':[],'objects':[],
    'authMethod':'existing aws configure export-credentials --profile statarena --format process, captured only in RAM; values never emitted or persisted'}
requests=[];context={};ram={};secret_values=[]
try:
    process=subprocess.run(['aws','configure','export-credentials','--profile','statarena','--format','process'],capture_output=True,text=True,timeout=20)
    if process.returncode:
        raise RuntimeError('Existing AWS CLI credential export failed: '+core.error_text(process.stderr)[:1000])
    credentials=json.loads(process.stdout)
    secret_values=[credentials[k] for k in ['AccessKeyId','SecretAccessKey','SessionToken'] if credentials.get(k)]
    record['credentialExportExitCode']=0
    configuration=Config(signature_version='s3v4',s3={'addressing_style':'path'},retries={'total_max_attempts':1},connect_timeout=5,read_timeout=8,
        request_checksum_calculation='when_required',response_checksum_validation='when_required')
    api=boto3.client('s3',region_name='us-east-2',aws_access_key_id=credentials['AccessKeyId'],aws_secret_access_key=credentials['SecretAccessKey'],
        aws_session_token=credentials.get('SessionToken'),config=configuration,verify=True)
    def before_send(request,**kwargs):
        if budget['objectHttpRequests']>=36:raise RuntimeError('HTTP object cap reached before send')
        budget['objectHttpRequests']+=1
        requests.append({'number':budget['objectHttpRequests'],'source':'aws','method':request.method,'objectPath':context.get('path'),
            'operation':context.get('operation'),'atUtc':core.NOW()})
    api.meta.events.register('before-send.s3',before_send)
    for target in [t for t in SCOPE['targets'] if t['source']=='aws' and t['kind']=='observation']:
        result=external.load_one(target,api,'statarena-football-333rosky-70db6e5f',{'ExpectedBucketOwner':'361769570630'},context,budget,ram)
        record['objects'].append(result)
        print(json.dumps({'path':target['path'],'status':result['status'],'decodedBytes':result.get('decodedBytes'),'error':result.get('error'),'httpCumulative':budget['objectHttpRequests']}),flush=True)
    api.close()
except Exception as error:
    record.update(errorType=type(error).__name__,error=core.error_text(error))
record['finishedAt']=core.NOW();core.save('aws-completion-content.json',record)
neon=json.loads((OUT/'external-neon.json').read_text())
neon_by={o['path']:o for o in neon['objects'] if o['status']=='decoded'}
aws_by={o['path']:o for o in record['objects'] if o['status']=='decoded'}
pairs=[]
for pair in SCOPE['pairs']:
    if pair['kind']!='resource':continue
    key=pair['key']['endpoint']+' '+pair['key']['params']
    left=neon_by.get(pair['neonPath'],{}).get('selectionSummaries',{}).get(key)
    right=aws_by.get(pair['awsPath'],{}).get('selectionSummaries',{}).get(key)
    result={**pair,'status':'unverified'}
    if left and right:
        equal=left['typedSha256']==right['typedSha256']
        ls,rs=left['shape'],right['shape']
        field_diff=[{'path':path,'neonStates':ls['fieldStates'].get(path,{}),'awsStates':rs['fieldStates'].get(path,{})}
            for path in sorted(set(ls['fieldStates'])|set(rs['fieldStates'])) if ls['fieldStates'].get(path)!=rs['fieldStates'].get(path)]
        ids=[]
        for path in sorted(set(ls['qualifyingIds'])|set(rs['qualifyingIds'])):
            ni,ai=set(ls['qualifyingIds'].get(path,[])),set(rs['qualifyingIds'].get(path,[]))
            if ni!=ai:ids.append({'path':path,'neonOnly':sorted(ni-ai),'awsOnly':sorted(ai-ni)})
        result.update(status='compared_exact_selected_digest_and_metadata',neonTypedSha256=left['typedSha256'],awsTypedSha256=right['typedSha256'],
            equalSelectedTypedContent=equal,fieldStateDifferences=field_diff,qualifyingIdDifferences=ids,
            scalarValueDifferenceLimit='Whole exact typed digest proves equality when equal. If unequal, field/state/ID differences are qualified here; exhaustive scalar leaf pairing remains unverified.',
            supplierFreshnessOrdering='unverified')
    pairs.append(result)
core.save('qualified-resource-pairs.json',pairs)
all_physical=budget['physicalBytesFetched']+previous['budget']['initialManifestDecodedBytes']
execution={'startedAt':record['startedAt'],'finishedAt':core.NOW(),'budget':budget,'totalPhysicalBytesFetchedIncludingManifestsAndRange':all_physical,
    'decodedAwsVersions':len(ram),'httpRequestLog':requests,'sourceCodeSha256':core.SHA(Path(__file__).read_bytes()),
    'limitsRespected':budget['sqlInstructions']<=18 and budget['objectHttpRequests']<=36 and budget['decodedBytes']<=33554432,
    'remoteWrites':[],'bodyPersistence':False,'additionalSqlInstructions':0}
core.save('aws-completion-execution.json',execution)
credential_hits=[]
for path in OUT.rglob('*'):
    if path.is_file() and path.suffix in {'.json','.md','.py','.log'}:
        text=path.read_text()
        if any(secret in text for secret in secret_values):credential_hits.append(str(path.relative_to(OUT)))
core.save('aws-credential-output-scan.json',{'atUtc':core.NOW(),'knownCredentialValuesChecked':len(secret_values),'matchingPaths':credential_hits,'valuesPersisted':False,'passed':not credential_hits})
ram.clear();secret_values.clear();core.save('aws-completion-ram-cleanup.json',{'atUtc':core.NOW(),'bodyFilesWritten':[],'state':'references released; AWS completion exiting'})
print(json.dumps({'awsDecoded':execution['decodedAwsVersions'],'budget':budget,'pairs':[{ 'key':p['key'],'equal':p.get('equalSelectedTypedContent'),'status':p['status']} for p in pairs],
    'limitsRespected':execution['limitsRespected'],'credentialOutputScanPassed':not credential_hits}),flush=True)
