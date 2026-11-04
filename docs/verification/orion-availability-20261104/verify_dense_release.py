"""Bounded post-release read-only acceptance; no source rows or secrets persisted."""
import base64
import datetime as dt
import gzip
import hashlib
import http.client
import json
from pathlib import Path
import subprocess
import time

HERE=Path(__file__).resolve().parent
SHA="6827c8a889c2622b84ef05f5eb088cdae8255a3d00321f553d0cb77b3cb00ddb"
HOST="d317dq37z1tacb.cloudfront.net"
PATH="/api/seasons/partition?season=2026%2F2027&league=l_0ALvwF&limit=100&format=columns"
GEN="69ef399dc44cf3fbfccff34c42f90dcbaed3c8221b884a4aa96dd01a31034216"
report={"atUtc":dt.datetime.now(dt.timezone.utc).isoformat(),"command":"python3 docs/verification/orion-availability-20261104/verify_dense_release.py","setup":"ExistingAWSprofile; sanitized control-plane readback, at most3 sequential ordinary compact100-matchGETs plusHEAD/conditional. No cache-busting, concurrent load, provider call or writes.","expected":"Exact deployedZIP and resource identities; existing deadline/configuration; all sampledHTTP responses complete and preserve one generation/counts/validators. Samples are notp95 or load acceptance.","releaseZipSha256":SHA,"requests":[],"checks":[],"passed":False}
def aws(*args):
    p=subprocess.run(["aws","--profile","statarena","--region","us-east-2","--no-cli-pager","--output","json",*args],capture_output=True,text=True,timeout=30)
    if p.returncode:raise RuntimeError("AWS readback failed")
    return json.loads(p.stdout)
def check(name,value):
    report["checks"].append({"name":name,"passed":bool(value)})
    if not value:raise AssertionError(name)
def request(method="GET",extra=None):
    c=http.client.HTTPSConnection(HOST,timeout=30);start=time.perf_counter()
    try:
        c.request(method,PATH,headers={"Accept-Encoding":"gzip","Origin":"https://statarena-analytics.vercel.app",**(extra or {})})
        r=c.getresponse();raw=r.read(8*1024*1024+1)
        if len(raw)>8*1024*1024:raise RuntimeError("Response exceeds acceptance budget")
        h={k.lower():v for k,v in r.getheaders() if k.lower() in {"etag","age","cache-control","content-type","content-encoding","content-length","x-cache","x-amz-cf-pop","x-amz-cf-id","access-control-allow-origin"}}
        body=gzip.decompress(raw) if raw and h.get("content-encoding")=="gzip" else raw
        row={"method":method,"path":PATH,"status":r.status,"elapsedMs":round((time.perf_counter()-start)*1000,2),"encodedBytes":len(raw),"decodedBytes":len(body),"decodedSha256":hashlib.sha256(body).hexdigest(),"headers":h}
        report["requests"].append(row)
        return row,json.loads(body) if body else None
    finally:c.close()
try:
    s=aws("cloudformation","describe-stacks","--stack-name","statarena-backend")["Stacks"][0]
    f=aws("lambda","get-function-configuration","--function-name","statarena-backend")
    u=aws("lambda","get-function-url-config","--function-name","statarena-backend")
    d=aws("cloudfront","get-distribution","--id","E26GD325YNN0LL")["Distribution"]
    before=json.loads((HERE/"aws-before-resource-identities.json").read_text())
    report["deployment"]={"stackStatus":s["StackStatus"],**{k:f[k] for k in ["FunctionName","FunctionArn","Runtime","MemorySize","Timeout","CodeSha256","State","LastUpdateStatus"]},"functionUrl":u["FunctionUrl"],"urlAuth":u["AuthType"],"distributionStatus":d["Status"]}
    check("stackUPDATE_COMPLETE",s["StackStatus"]=="UPDATE_COMPLETE")
    check("exactZIP deployed",f["CodeSha256"]==base64.b64encode(bytes.fromhex(SHA)).decode())
    check("runtime configuration unchanged",f["Runtime"]=="nodejs24.x" and f["MemorySize"]==512 and f["Timeout"]==25 and f["State"]=="Active" and f["LastUpdateStatus"]=="Successful")
    check("signed origin identity unchanged",f["FunctionArn"]==before["functionArn"] and u["FunctionUrl"]==before["functionUrl"] and u["AuthType"]=="AWS_IAM")
    check("CloudFront deployed with unchanged origin",d["Status"]=="Deployed" and [o["DomainName"] for o in d["DistributionConfig"]["Origins"]["Items"]]==before["distributionOrigins"])
    first=None
    for number in range(3):
        row,value=request()
        check("denseGET200 sample"+str(number+1),row["status"]==200)
        data=value.get("data",{});pagination=value.get("pagination",{})
        row["generation"]=pagination.get("generation")
        row["matches"]=len(data.get("tables",{}).get("matches",{}).get("rows",[]));row["appearances"]=len(data.get("tables",{}).get("appearances",{}).get("rows",[]))
        check("complete same-generation sample"+str(number+1),data.get("format")=="orion-packed-tables-v1" and row["generation"]==GEN and row["matches"]==100 and row["appearances"]==4788)
        if first is None:first=row
        else:check("stable bytes and validator sample"+str(number+1),row["decodedSha256"]==first["decodedSha256"] and row["headers"].get("etag")==first["headers"].get("etag"))
    check("validator present",bool(first["headers"].get("etag")))
    head,_=request("HEAD");check("HEAD200 same validator empty",head["status"]==200 and head["decodedBytes"]==0 and head["headers"].get("etag")==first["headers"].get("etag"))
    conditional,_=request("GET",{"If-None-Match":first["headers"]["etag"]});check("conditional304empty",conditional["status"]==304 and conditional["decodedBytes"]==0)
    report["passed"]=True
except Exception as error:report["error"]={"type":type(error).__name__,"message":str(error) if isinstance(error,AssertionError) else "Bounded verification failed; see recorded statuses"}
finally:
    report["limits"]=["At most3 sequential denseGETs; cachehits are not originSQL timing.","Read-only same-generation sample; no p95, capacity or timeout-elimination claim.","SQL deadline8s is unchanged in committed reader; Lambda timeout25s remains distinct."]
    out=HERE/("aws-dense-release-"+dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")+".json");out.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"artifact":str(out),"passed":report["passed"],"error":report.get("error"),"requests":report["requests"]}))
raise SystemExit(not report["passed"])
