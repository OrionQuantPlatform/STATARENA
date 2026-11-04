"""Resolve source fields in indexed staging, read only; return only a small counterexample."""
import json,os,gzip
from pathlib import Path
import psycopg
folder=Path(__file__).resolve().parent
def connect(seconds=10):
    cfg=json.loads(Path(os.environ.get("STATARENA_PROBE_CONFIG","/tmp/statarena-aws-runtime-20261104.json")).read_text())
    return psycopg.connect(host=cfg["host"],user=cfg["username"],password=cfg["password"],dbname="statarena_prod",sslmode="verify-full",sslrootcert=os.environ.get("STATARENA_PROBE_CA","/tmp/statarena-rds-us-east-2-20261104.pem"),options=f"-c default_transaction_read_only=on -c statement_timeout={seconds*1000} -c max_parallel_workers_per_gather=0",connect_timeout=4,autocommit=True)
if __name__=="__main__":
 with connect() as db:
    scope=db.execute("SELECT season,league_id FROM statarena_app.publication_jobs ORDER BY (season='@details'),season DESC,changed_at,league_id LIMIT 1").fetchone()
    print("scope",scope)
    fixtures=db.execute("select id from statarena.fixtures where season=any(%s) and league_id=%s order by day,id",([scope[0],scope[0].split('/')[0]],scope[1])).fetchall()
    for mid, in fixtures:
        ref=db.execute("""select s.ref->'tables'->'shots'->>'path', doc.document->o.ordinal->>'id'
          from statarena.observations o join statarena.shards s on s.id=o.shard join statarena.current_file_documents doc on doc.document_path=s.ref->'document'->>'path'
          where o.id=%s""",(mid,)).fetchone()
        sources=[]
        if ref and all(ref):sources.append((ref[0],{"path":ref[0],"documentId":ref[1]}))
        recent=db.execute("select ref from statarena.resources where endpoint=%s and params='{}' and status=200",("/matches/"+mid+"/shots",)).fetchone()
        if recent and recent[0]:sources.insert(0,(recent[0]["path"],recent[0]))
        for path,ref in sources:
            from psycopg.types.json import Jsonb
            data=db.execute("""with v as materialized(select case when %s::jsonb ? 'ordinal' then document->(%s::jsonb->>'ordinal')::int else document end as body from statarena.current_file_documents where document_path=%s),
             s as materialized(select case when %s::jsonb ? 'documentId' then jsonb_path_query_first(body,'$[*] ? (@.documentId == $id)',jsonb_build_object('id',%s::jsonb->>'documentId')) else body end as item from v),
             p as materialized(select coalesce(item->'response',item->'observation',item)->'data' as data from s)
             select data from p where jsonb_path_exists(data,'$.periods[*].shots[*].is_own_goal')""",(Jsonb(ref),Jsonb(ref),path,Jsonb(ref),Jsonb(ref))).fetchone()
            if data:
                sha=db.execute("select encode(sha256,'hex') from statarena.objects where path=%s",(path,)).fetchone()[0]
                capture={"scope":scope,"match":mid,"sourcePath":path,"sourceDigest":sha,"ref":ref,"family":"shots","response":{"status":200,"data":data[0],"error":None}}
                (folder/"own-goal-source.json.gz").write_bytes(gzip.compress(json.dumps(capture,separators=(",",":")).encode(),mtime=0))
                print("captured",mid,path);raise SystemExit()
    raise SystemExit("No counterexample in eligible archive/saved shots")
