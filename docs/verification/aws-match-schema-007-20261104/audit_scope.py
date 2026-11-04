"""Audit every archived and saved match response in the first blocked scope."""
import gzip,json,sys
from collections import Counter
from pathlib import Path
from capture import connect
folder=Path(__file__).resolve().parent
sys.path.insert(0,str(folder.parents[2]/"dashboard/scripts"))
from relational_match import _resource_address,prepare,unpack_record
from relational_match_model import context
from relational_materialize import envelope
phase=sys.argv[1]
season,league="2026/2027","l_0275VP"
with connect(15) as db:
    fs=db.execute("""select f.id,o.ordinal,s.id,s.ref from statarena.fixtures f left join statarena.observations o on o.id=f.id left join statarena.shards s on s.id=o.shard
    where f.season=any(%s) and league_id=%s order by f.day,f.id""",([season,season.split('/')[0]],league)).fetchall()
    refs=db.execute("""select mid,r.endpoint,r.params,r.status,r.ref,r.error from unnest(%s::text[]) mid cross join lateral
      (select endpoint,params,status,ref,error from statarena.resources where endpoint>='/matches/'||mid and endpoint<'/matches/'||mid||'~') r""",([x[0] for x in fs],)).fetchall()
    paths={t["path"] for _,_,_,ref in fs if ref for t in [ref["document"],*ref["tables"].values()]}
    paths|={r[4]["path"] for r in refs if r[4] and r[4].get("path")}
    budget=db.execute("select count(*),sum(octet_length(document::text)) from statarena.current_file_documents where document_path=any(%s)",(list(paths),)).fetchone()
    assert budget[0]==len(paths) and budget[1]<48*1024*1024,budget
    docs={}
    for i in range(0,len(paths),20):
        docs.update(db.execute("select document_path,document from statarena.current_file_documents where document_path=any(%s)",(sorted(paths)[i:i+20],)).fetchall())
issues=Counter();categories=Counter(); samples={}
def check(cat,mid,record):
    categories[cat]+=1
    try:
        if cat=="context":unpack_record(context,record,None,"context")
        else:prepare(cat,record)
    except (TypeError,ValueError) as e:
        issues[str(e)]+=1
        if str(e) not in samples:samples[str(e)]={"family":cat,"match":mid,"value":record}
for mid,ordinal,shard,ref in fs:
    if not ref:continue
    doc=docs[ref["document"]["path"]][ordinal];check("context",mid,doc["metadata"])
    for family in doc["endpoints"]:
        table=docs[ref["tables"][family]["path"]]
        row=next(x for x in table if x["documentId"]==doc["id"]);check(family,mid,row["response"])
for mid,endpoint,params,status,ref,error in refs:
    address=_resource_address(endpoint)
    if not address:issues["Unmapped saved endpoint "+endpoint]+=1;continue
    check(address[1],mid,envelope(docs[ref["path"]] if ref else None,ref,status,error))
out={"season":season,"league":league,"fixtures":len(fs),"savedResources":len(refs),"inputDocuments":len(paths),"inputJsonTextBytes":budget[1],"cases":categories,"issues":issues}
(folder/("scope-"+phase+".json")).write_text(json.dumps(out,indent=2)+"\n")
if phase=="before":(folder/"scope-counterexamples.json.gz").write_bytes(gzip.compress(json.dumps(samples,separators=(",",":")).encode(),mtime=0))
print(out)
