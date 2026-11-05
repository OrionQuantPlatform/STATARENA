#!/usr/bin/env python3
"""Compare actual accepted text-PK ordering across source C and RDS C.UTF-8."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[2]

def main():
    p=argparse.ArgumentParser();p.add_argument('--checkpoint',type=Path);p.add_argument('--output',type=Path);args=p.parse_args()
    if not args.checkpoint:
        print(json.dumps({'status':'offline_plan','connections':0,'writes':[]}));return 0
    assert args.output and not args.output.exists()
    import psycopg
    import ingest_actor
    model_path=ROOT/'docs/architecture/orion-plan-20261104/target-schema.proposed.json'
    assert hashlib.sha256(model_path.read_bytes()).hexdigest()=='18da43f940870b7a3a3cb49323c847dd5e5174e5eea1f8ff0c8a159cf373cb08'
    model=json.loads(model_path.read_text());cp=json.loads(args.checkpoint.read_text());m=cp['marker']
    assert cp['native94Sha256']=='220b5da11d56ae16c010fbaa35c535b389af6fe8bc55988a84804f27057d1eb8'
    q=lambda s:'"'+s+'"' if re.fullmatch('[a-z_][a-z0-9_]*',s) else (_ for _ in ()).throw(ValueError('Identifier'))
    tables=[t for s in model['schemas'] for t in s['tables'] if t['phase']!='models' and any(t['columns'][c]['type']=='text' for c in t['primary_key']['columns'])]
    chunks=[];target=[]
    for t in tables:
        name=t['qualified_name'];keys=t['primary_key']['columns'];cols=','.join(q(c) for c in keys)
        chunks.append("SELECT '"+name+"'::text relation,row_number() OVER(ORDER BY "+cols+") ordinal,jsonb_build_array("+','.join(q(c)+'::text' for c in keys)+') keys FROM '+'.'.join(q(v) for v in name.split('.')))
        order=["(keys->>"+str(i)+')::'+t['columns'][c]['type'] for i,c in enumerate(keys)]
        target.append("SELECT '"+name+"' relation,ordinal,row_number() OVER(ORDER BY "+','.join(order)+") sorted FROM x WHERE relation='"+name+"'")
    source_sql='SELECT relation,ordinal,keys FROM ('+' UNION ALL '.join(chunks)+') keys LIMIT 20001'
    options='-c default_transaction_read_only=on -c statement_timeout=8000 -c lock_timeout=1000'
    with psycopg.connect(host='127.0.0.1',hostaddr='127.0.0.1',port=m['port'],dbname='postgres',user='orion_pro_runtime',passfile='/dev/null',sslmode='verify-full',sslrootcert=m['certificatePath'],options=options,autocommit=True,connect_timeout=7) as c:
        rows=c.execute(source_sql).fetchall()
    assert len(rows)<20001
    payload=json.dumps([dict(zip(['relation','ordinal','keys'],r)) for r in rows],separators=(',',':'))
    assert len(payload.encode())<=2*1024**2
    target_sql="WITH x AS (SELECT * FROM jsonb_to_recordset(%s::jsonb) AS x(relation text,ordinal bigint,keys jsonb)),ordered AS ("+' UNION ALL '.join(target)+') SELECT relation,count(*),bool_and(ordinal=sorted) FROM ordered GROUP BY relation ORDER BY relation'
    with ingest_actor.private_authentication() as auth:
        with psycopg.connect(host=ingest_actor.HOST,port=5432,dbname=ingest_actor.DATABASE,user=ingest_actor.ACTOR,passfile=str(auth),sslmode='verify-full',sslrootcert=str(ROOT/'dashboard/backend/certs/rds-us-east-2.pem'),options=options,autocommit=True,connect_timeout=7) as c:
            result=c.execute(target_sql,(payload,)).fetchall()
    passed=sum(r[1] for r in result)==len(rows) and all(r[2] is True for r in result)
    report={'kind':'actual_native_pk_order_comparison','atUtc':datetime.now(timezone.utc).isoformat(),'command':[sys.executable,*sys.argv],'expected':'Every actual collatable PK tuple retains its ordinal under the RDS default ordering. No business value is modified.','status':'pass' if passed else 'fail','relationsInspected':len(tables),'populatedRelationResults':result,'keysCompared':len(rows),'metadataParameterBytes':len(payload.encode()),'metadataParameterSha256':hashlib.sha256(payload.encode()).hexdigest(),'sourceSql':source_sql,'targetSql':target_sql,'selects':2,'writes':[],'rawBodiesPersisted':False,'privateAuthenticationRemoved':not auth.exists()}
    args.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':report['status'],'keysCompared':len(rows),'parameterBytes':report['metadataParameterBytes'],'evidence':str(args.output)}));return 0 if passed else 1

if __name__=='__main__':raise SystemExit(main())
