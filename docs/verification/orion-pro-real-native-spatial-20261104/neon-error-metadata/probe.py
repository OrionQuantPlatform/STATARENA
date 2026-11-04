"""One ROOT-authorized read-only metadata query, no body or implicit retry."""
import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
REPO=HERE.parents[3]
QUERY="""SELECT current_database(),current_user,current_setting('transaction_read_only'),current_setting('transaction_isolation'),current_setting('statement_timeout'),current_setting('lock_timeout'),pg_current_snapshot()::text,
r.status,coalesce(r.ref->>'path',r.ref->>'shard'),r.ref->>'ordinal',encode(o.sha256,'hex'),o.size,
pg_typeof(r.error)::text,r.error IS NULL,jsonb_typeof(r.error),r.error = 'null'::jsonb,octet_length(r.error::text)
FROM statarena.resources r JOIN statarena.objects o ON o.path=coalesce(r.ref->>'path',r.ref->>'shard')
WHERE r.endpoint=%s AND r.params=%s AND o.path=%s AND encode(o.sha256,'hex')=%s LIMIT 2"""
OUT=HERE/'result.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(value):OUT.write_text(json.dumps(value,indent=2,default=str)+'\n')
def main():
    if OUT.exists():raise SystemExit('Diagnostic already claimed; no implicit retry')
    m=json.loads((BASE/'MANIFEST.json').read_text());n=m['neon']
    old=REPO/m['oldLedger']['path'];failed=BASE/'budget.json';before={str(p):sha(p) for p in [old,failed]}
    report={'atUtc':dt.datetime.now(dt.timezone.utc).isoformat(),'status':'claimed','limitSelects':1,'limitDecodedBytes':8192,'selectAttempts':0,'httpRequests':0,'rawBodiesRead':0,'remoteWrites':0,'query':QUERY,'parameters':[n['endpoint'],n['params'],n['path'],n['physicalSha256']],'rerun':'PYTHONPATH=/tmp/statarena-publication-test-python python3 docs/verification/orion-pro-real-native-spatial-20261104/neon-error-metadata/probe.py','expected':'Classify SQL NULL versus JSON null for exact pinned resource without selecting error content.','inputSha256':{'capture.py':sha(BASE/'capture.py'),'MANIFEST.json':sha(BASE/'MANIFEST.json'),'probe.py':sha(Path(__file__))}}
    save(report);conn=None
    try:
        spec=importlib.util.spec_from_file_location('reviewed_readonly_capture',BASE/'capture.py');cap=importlib.util.module_from_spec(spec);spec.loader.exec_module(cap)
        values=cap.configuration();cap.validate_private_origins(values,m)
        conn=cap.connect('neon',m,values);report['clientTlsVerifyFull']=bool(conn.pgconn.ssl_in_use and conn.info.get_parameters().get('sslmode')=='verify-full');assert report['clientTlsVerifyFull']
        report['selectAttempts']=1;save(report)
        rows=conn.execute(QUERY,tuple(report['parameters'])).fetchall();assert len(rows)==1
        body=json.dumps(rows,default=str,separators=(',',':')).encode();assert len(body)<=8192
        row=rows[0];assert row[:6]==(n['database'],n['user'],'on','repeatable read','8s','1s')
        assert row[7:12]==(n['status'],n['path'],None,n['physicalSha256'],n['physicalBytes'])
        names=['database','role','readOnly','isolation','statementTimeout','lockTimeout','snapshot','status','path','ordinal','physicalSha256','metadataBytes','errorSqlType','errorIsSqlNull','errorJsonType','errorEqualsJsonNull','errorTextBytes']
        report.update(status='pass',decodedBytes=len(body),metadata=dict(zip(names,row)))
    except Exception as error:
        report.update(status='blocked',errorType=type(error).__name__,sqlstate=getattr(error,'sqlstate',None))
    finally:
        if conn is not None:conn.rollback();conn.close()
        report['sourceConnectionClosed']=True;report['priorLedgersByteIdentical']=all(sha(Path(p))==v for p,v in before.items());report['finishedAtUtc']=dt.datetime.now(dt.timezone.utc).isoformat();save(report)
    print(json.dumps({'status':report['status'],'selectAttempts':report['selectAttempts'],'decodedBytes':report.get('decodedBytes'),'metadata':report.get('metadata'),'priorLedgersByteIdentical':report['priorLedgersByteIdentical']}))
    return 0 if report['status']=='pass' else 1
if __name__=='__main__':raise SystemExit(main())
