"""Read the twelve exact external bodies in RAM; no SQL or storage mutation."""
from pathlib import Path
import json
import sys
from urllib.parse import urlsplit

sys.dont_write_bytecode = True
import read_content as core

OUT, ROOT, SCOPE, LIMITS = core.OUT, core.ROOT, core.SCOPE, core.LIMITS


def client(source, context, budget, request_log):
    import boto3
    from botocore.config import Config
    config = Config(signature_version='s3v4', s3={'addressing_style':'path'}, retries={'total_max_attempts':1},
        connect_timeout=5, read_timeout=8, request_checksum_calculation='when_required', response_checksum_validation='when_required')
    if source=='neon':
        values={}
        for line in (ROOT/'dashboard/.env').read_text().splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                key,value=line.split('=',1);values[key.strip()]=value.strip().strip('"').strip("'")
        endpoint=values['NEON_STORAGE_ENDPOINT']
        if urlsplit(endpoint).scheme!='https' or urlsplit(endpoint).hostname!='br-mute-bonus-be23014e.storage.c-9.us-east-2.aws.neon.tech':
            raise ValueError('Configured storage endpoint does not match frozen source branch')
        api=boto3.client('s3',endpoint_url=endpoint,region_name=values.get('NEON_STORAGE_REGION','us-east-2'),
            aws_access_key_id=values['NEON_STORAGE_ACCESS_KEY_ID'],aws_secret_access_key=values['NEON_STORAGE_SECRET_ACCESS_KEY'],config=config,verify=True)
        bucket=values.get('NEON_STORAGE_BUCKET','statarena-data')
        owner={}
        identity={'host':urlsplit(endpoint).hostname,'bucket':bucket,'prefix':'data/','tlsVerification':True,'resolver':'dashboard/scripts/neon_store.py:47'}
    else:
        api=boto3.Session(profile_name='statarena',region_name='us-east-2').client('s3',config=config,verify=True)
        bucket='statarena-football-333rosky-70db6e5f';owner={'ExpectedBucketOwner':'361769570630'}
        identity={'bucket':bucket,'profile':'statarena','region':'us-east-2','prefix':'data/','tlsVerification':True,'expectedBucketOwner':'361769570630'}
    def before_send(request, **kwargs):
        if budget['objectHttpRequests']>=36:
            raise RuntimeError('Object HTTP request budget exhausted before send')
        budget['objectHttpRequests']+=1
        request_log.append({'number':budget['objectHttpRequests'],'source':source,'method':request.method,
            'objectPath':context.get('path'),'operation':context.get('operation'),'atUtc':core.NOW()})
    api.meta.events.register('before-send.s3',before_send)
    return api,bucket,owner,identity


def load_one(target, api, bucket, owner, context, budget, ram):
    path=target['path'];context['path']=path
    result={'source':target['source'],'path':path,'startedAt':core.NOW(),'expectedPhysicalSha256':target['expectedPhysicalSha256'],
        'expectedPhysicalBytes':target['expectedPhysicalBytes'],'storageKey':'data/'+path,'remoteWrites':[]}
    base={'Bucket':bucket,'Key':'data/'+path,**owner}
    try:
        context['operation']='HEAD';head=api.head_object(**base)
        length=head['ContentLength'];etag=head.get('ETag')
        result['head']={k:head.get(k) for k in ['ContentLength','ETag','VersionId','LastModified','ContentType','ContentEncoding']}
        if length!=target['expectedPhysicalBytes'] or length>LIMITS['physicalObjectBytesMaximum'] or length<18:
            raise ValueError('Physical HEAD size differs from frozen scope or exceeds limit')
        if not etag:
            raise ValueError('No ETag available for conditional exact-version fetch')
        context['operation']='GET_range_last4'
        tail=api.get_object(**base,Range='bytes=-4',IfMatch=etag)
        result['range']={k:tail.get(k) for k in ['ContentLength','ContentRange','ETag','VersionId']}
        try:
            if tail.get('ContentLength')!=4 or tail.get('ContentRange')!=f'bytes {length-4}-{length-1}/{length}':
                raise ValueError('Four-byte gzip size range was not honored')
            trailer=tail['Body'].read(4);budget['physicalBytesFetched']+=len(trailer)
        finally:tail['Body'].close()
        if len(trailer)!=4:
            raise ValueError('Incomplete four-byte gzip size range')
        declared=int.from_bytes(trailer,'little');result['announcedDecodedBytes']=declared
        if declared>LIMITS['decodedObjectBytesMaximum'] or declared+budget['decodedBytes']>LIMITS['decodedBytesMaximum']:
            raise ValueError('Announced decoded size exceeds remaining content budget before full GET')
        context['operation']='GET_bounded_body'
        response=api.get_object(**base,IfMatch=etag)
        result['get']={k:response.get(k) for k in ['ContentLength','ETag','VersionId']}
        try:
            if response.get('ContentLength')!=length:
                raise ValueError('Full GET length changed after HEAD')
            chunks=[];remaining=length
            while remaining:
                block=response['Body'].read(min(65536,remaining))
                if not block:break
                chunks.append(block);remaining-=len(block);budget['physicalBytesFetched']+=len(block)
            raw=b''.join(chunks)
        finally:response['Body'].close()
        result.update(actualPhysicalBytes=len(raw),actualPhysicalSha256=core.SHA(raw))
        if len(raw)!=length or core.SHA(raw)!=target['expectedPhysicalSha256']:
            raise ValueError('Fetched physical size/SHA does not match frozen expected version')
        if not raw.startswith(b'\x1f\x8b'):
            raise ValueError('Exact external object is not the expected gzip representation')
        parsed,decoded=core.decode(raw,budget)
        result['decodedBytes']=decoded
        if decoded!=declared:
            raise ValueError('Actual bounded decode size disagrees with gzip ISIZE')
        qualifications,selections=core.qualify(target,parsed)
        result.update(status='decoded',decodedTypedSha256=core.digest(parsed),rootState=core.state(parsed),qualifications=qualifications,
            shape=core.shape(parsed),selectionSummaries={k:{'state':core.state(v),'typedSha256':core.digest(v),'shape':core.shape(v)} for k,v in selections.items()})
        ram[(target['source'],path)]={'parsed':parsed,'selections':selections}
    except Exception as error:
        result.update(status='blocked',errorType=type(error).__name__,error=core.error_text(error))
    result['finishedAt']=core.NOW()
    return result


def main():
    if (OUT/'external-execution.json').exists():raise SystemExit('External receipt already exists; no implicit replay')
    initial=json.loads((OUT/'execution.json').read_text())
    budget={'sqlInstructions':initial['budget']['sqlInstructions'],'decodedBytes':initial['budget']['decodedBytes'],
        'objectHttpRequests':0,'physicalBytesFetched':0,'initialManifestDecodedBytes':initial['budget']['decodedBytes']}
    ram={};requests=[];all_results=[];started=core.NOW()
    for source in ['neon','aws']:
        targets=[t for t in SCOPE['targets'] if t['source']==source and t['kind']=='observation']
        initial_source=json.loads((OUT/(source+'-content.json')).read_text())
        current={r['path']:r for r in initial_source['preflight']['objects']}
        selectors={(r['endpoint'],r['params']):r for r in initial_source['preflight']['selectors'] or []}
        context={};record={'source':source,'startedAt':core.NOW(),'sqlInstructionsAdded':0,'objects':[],'remoteWrites':[]}
        try:
            api,bucket,owner,identity=client(source,context,budget,requests);record['storage']=identity
            for target in targets:
                meta=current[target['path']]
                if meta.get('stored_sha256')!=target['expectedPhysicalSha256'] or meta.get('size')!=target['expectedPhysicalBytes']:
                    record['objects'].append({'path':target['path'],'status':'blocked','error':'frozen SQL fingerprint differs'})
                    continue
                if any(any(selectors[(s['endpoint'],s['params'])].get(k)!=s.get(k) for k in ['status','ref_path','ref_ordinal']) for s in target['selectors']):
                    record['objects'].append({'path':target['path'],'status':'blocked','error':'frozen resource selector differs'})
                    continue
                result=load_one(target,api,bucket,owner,context,budget,ram);record['objects'].append(result)
                print(json.dumps({'source':source,'path':target['path'],'status':result['status'],'decodedBytes':result.get('decodedBytes'),'qualifications':[{k:q.get(k) for k in ['endpoint','qualified','responseIdState','bodyHttpStatus','dataState','error']} for q in result.get('qualifications',[])],'error':result.get('error'),'httpCumulative':budget['objectHttpRequests']}),flush=True)
            api.close()
        except Exception as error:
            record.update(errorType=type(error).__name__,error=core.error_text(error))
        record['finishedAt']=core.NOW();core.save('external-'+source+'.json',record);all_results+=record['objects']
    pairs=[r for r in core.pair_results(ram) if r['kind']=='resource']
    core.save('external-content-comparison.json',pairs)
    result={'startedAt':started,'finishedAt':core.NOW(),'budget':budget,'decodedExternalVersions':len(ram),'expectedExternalVersions':12,
        'httpRequestLog':requests,'sourceCodeSha256':core.SHA(Path(__file__).read_bytes()),'coreCodeSha256':core.SHA((OUT/'read_content.py').read_bytes()),
        'bodyPersistence':False,'providerRequests':0,'remoteWrites':[],
        'limitsRespected':budget['sqlInstructions']<=18 and budget['decodedBytes']<=33554432 and budget['objectHttpRequests']<=36}
    core.save('external-execution.json',result)
    print(json.dumps({'externalDecoded':len(ram),'budget':budget,'limitsRespected':result['limitsRespected']}),flush=True)
    ram.clear();core.save('external-ram-cleanup.json',{'atUtc':core.NOW(),'bodyFilesWritten':[],'state':'references released; external reader exiting'})


if __name__=='__main__':main()
