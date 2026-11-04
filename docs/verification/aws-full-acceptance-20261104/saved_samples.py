"""Check a genuine saved selector per scoped family/status/variant against public AWS."""
from pathlib import Path
import argparse
import datetime
import gzip
import hashlib
import http.client
import json
import sys
from urllib.parse import urlencode
from source_gate import canonical, connection
from relational_materialize import envelope

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument("--source",required=True,type=Path)
parser.add_argument("--out",required=True,type=Path)
args=parser.parse_args()
gate=json.loads(args.source.read_text())
if gate.get("status")!="source_metadata_passed":parser.error("source gate must be complete before public traffic")
if args.out.exists():parser.error("supply new report path")
host="d317dq37z1tacb.cloudfront.net"
report={"began":datetime.datetime.now(datetime.timezone.utc).isoformat(),"origin":"https://"+host,"generation":gate["generation"],"command":sys.argv,"checks":[],"passed":False}
digest=lambda b:hashlib.sha256(canonical(b).encode()).hexdigest()

def same_json(left,right):
    if isinstance(left,bool) or isinstance(right,bool):
        return type(left) is type(right) and left==right
    if isinstance(left,dict) and isinstance(right,dict):
        return left.keys()==right.keys() and all(same_json(left[k],right[k]) for k in left)
    if isinstance(left,list) and isinstance(right,list):
        return len(left)==len(right) and all(same_json(a,b) for a,b in zip(left,right))
    return left==right


def save():
    args.out.write_text(json.dumps(report,indent=2,ensure_ascii=False,default=str)+"\n")

try:
    with connection() as db:
        db.autocommit=True
        session=http.client.HTTPSConnection(host,timeout=35)
        try:
            for item in gate["samples"]:
                ep,p=item["endpoint"],item["params"]
                check={"selector":item,"passed":False}
                report["checks"].append(check)
                try:
                    sql="""SELECT r.status,r.error,r.ref,encode(o.sha256,'hex'),CASE
                      WHEN r.ref IS NULL THEN NULL WHEN r.ref?'ordinal' THEN d.document->(r.ref->>'ordinal')::integer
                      WHEN r.ref?'documentId' THEN (SELECT j FROM jsonb_array_elements(d.document) j WHERE j->>'documentId'=r.ref->>'documentId' LIMIT 1)
                      ELSE d.document END FROM statarena.resources r LEFT JOIN statarena.objects o ON o.path=r.ref->>'path'
                      LEFT JOIN statarena.current_file_documents d ON d.source_path=o.path AND d.document_path=o.path
                      WHERE r.endpoint=%s AND r.params=%s"""
                    row=db.execute(sql,(ep,p)).fetchone()
                    assert row is not None and row[0]==item["status"],"Source moved or disappeared"
                    code,error,ref,physical,doc=row
                    assert not ref or (doc is not None and physical),"Pinned source document unavailable"
                    value=envelope(doc,{"path":ref["path"]} if ref else None,code,error)
                    expected={"data":value["data"]} if code==200 else {"ok":False,"error":value["error"] or {"code":"RESOURCE_NOT_FOUND","message":"Donnée indisponible."}}
                    path="/api/pitchapi"+ep;params=json.loads(p)
                    if params:path+="?"+urlencode(params)
                    check.update(path=path,physicalObjectSha=physical,normalizedSourceSha=digest(value),expectedPublicSha=digest(expected),sourceRef=ref)
                    session.request("GET",path,headers={"Accept-Encoding":"gzip"})
                    response=session.getresponse()
                    raw=response.read(6*1024*1024+1)
                    assert len(raw)<=6*1024*1024,"Exceeded public transport bound"
                    body=gzip.decompress(raw) if response.getheader("content-encoding")=="gzip" else raw
                    actual=json.loads(body)
                    check.update(httpStatus=response.status,actualPublicSha=digest(actual),publicBodySha=hashlib.sha256(body).hexdigest(),
                                 bytes=len(body),cache=response.getheader("cache-control"),requestId=response.getheader("x-amzn-requestid"))
                    assert response.status==code and same_json(actual,expected),"Public response differs from saved source"
                    if code!=200:assert "no-store" in (check["cache"] or ""),"Saved failure unexpectedly cached"
                    check["passed"]=True
                except Exception as e:
                    check.update(error=type(e).__name__,sqlstate=getattr(e,"sqlstate",None),reason=str(e) if isinstance(e,AssertionError) else None)
                    session.close()
                save()
            generation=db.execute("SELECT generation FROM statarena_app.publications WHERE singleton").fetchone()[0]
            report["generationAfter"]=generation
            report["passed"]=bool(report["checks"]) and generation==gate["generation"] and all(c["passed"] for c in report["checks"])
        finally:
            session.close()
finally:
    save()
print(json.dumps({"checks":len(report["checks"]),"passed":report["passed"]}))
raise SystemExit(0 if report["passed"] else 1)
