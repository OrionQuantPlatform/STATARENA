#!/usr/bin/env python3
"""Bounded existing Vercel/CloudFront health checks; no deployment or data import."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.request

HERE=Path(__file__).resolve().parent
TARGETS={
    'canonical_health':'https://statarena-analytics.vercel.app/api/health',
    'canonical_manifest':'https://statarena-analytics.vercel.app/api/dashboard/manifest',
    'aws_health':'https://d317dq37z1tacb.cloudfront.net/api/health',
}


def probe(item):
    name,url=item; start=time.monotonic()
    result={'case':name,'url':url,'expected':'HTTP200 with a JSON object; response body is hashed, not saved'}
    try:
        request=urllib.request.Request(url,headers={'Accept':'application/json','Accept-Encoding':'identity','User-Agent':'StatArena-schema-pilot-verification'})
        with urllib.request.urlopen(request,timeout=20) as response:
            body=response.read(1048577)
            result.update(httpStatus=response.status,bodyBytes=len(body),bodySha256=hashlib.sha256(body).hexdigest(),contentType=response.headers.get('Content-Type'),vercelId=response.headers.get('x-vercel-id'),cache=response.headers.get('x-cache'))
            decoded=json.loads(body) if len(body)<=1048576 else None
            result['status']='pass' if response.status==200 and isinstance(decoded,dict) else 'fail'
    except Exception as error:
        result.update(status='fail',errorType=type(error).__name__,httpStatus=error.code if isinstance(error,urllib.error.HTTPError) else None)
    result['elapsedMs']=round((time.monotonic()-start)*1000,3)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--label',required=True); args=parser.parse_args()
    if not re.fullmatch('[a-zA-Z0-9][a-zA-Z0-9-]{0,79}',args.label):parser.error('Use a simple bounded label')
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    run=HERE/'public-probes'/f'{stamp}-{args.label}'; run.mkdir(parents=True)
    source=Path(__file__).read_bytes(); (run/'public_probe.py').write_bytes(source)
    report={'kind':'bounded_public_health_probe','startedAt':datetime.now(timezone.utc).isoformat(),
        'setup':'Three public GETs on the existing canonical Vercel and AWS CloudFront origins; no authentication or external mutation',
        'command':['python3','docs/verification/orion-pro-pilot-20261104/public_probe.py',*sys.argv[1:]],
        'scriptSha256':hashlib.sha256(source).hexdigest(),'remoteWrites':[],
        'limits':['Health/manifest smoke only; full user flows are outside this probe','One unordered parallel sample per endpoint is not a comparable latency benchmark','The current Vercel saved-data bridge remains in use; this is not typed RDS cutover acceptance']}
    with ThreadPoolExecutor(max_workers=3) as pool:report['cases']=list(pool.map(probe,TARGETS.items()))
    report['status']='pass' if all(c['status']=='pass' for c in report['cases']) else 'fail'
    report['finishedAt']=datetime.now(timezone.utc).isoformat(); (run/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'status':report['status'],'receipt':str(run.relative_to(HERE))+'/result.json','statuses':{c['case']:c.get('httpStatus') for c in report['cases']}}))
    return 0 if report['status']=='pass' else 1


if __name__=='__main__':raise SystemExit(main())
