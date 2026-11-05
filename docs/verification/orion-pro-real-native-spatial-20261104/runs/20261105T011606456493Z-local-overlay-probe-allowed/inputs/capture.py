#!/usr/bin/env python3
"""One explicitly approved bounded mixed-origin capture; source bodies stay in RAM."""
from __future__ import annotations
import argparse,fcntl,hashlib,importlib.util,json,os,pickle,socket,stat,subprocess,sys,time,zlib
from datetime import datetime,timezone
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlsplit

sys.dont_write_bytecode=True
DOC=Path(__file__).resolve().parent
REPO=DOC.parents[2]
MANIFEST_PATH=DOC/'MANIFEST.json'
NORMALIZER=REPO/'dashboard/scripts/orion_pro_normalize.py'
LIMITS={'selects':11,'decodedBytes':33554432,'objectHttpRequests':3,'physicalHttpBytes':1048576,'perDocumentDecodedBytes':8388608,'statementTimeoutMs':8000,'lockTimeoutMs':1000,'simultaneousSourceConnections':1}
OPTIONS='-c default_transaction_read_only=on -c default_transaction_isolation=repeatable\\ read -c statement_timeout=8000 -c lock_timeout=1000 -c idle_in_transaction_session_timeout=15000 -c max_parallel_workers_per_gather=0'
NOW=lambda:datetime.now(timezone.utc).isoformat()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

class CaptureError(ValueError):pass

def save(path,value):path.write_text(json.dumps(value,indent=2,default=str)+'\n')
def manifest():
    value=json.loads(MANIFEST_PATH.read_text())
    if value['limits']!=LIMITS:raise CaptureError('Frozen capture limits differ from hard-coded11SELECT/32MiB/3HTTP caps')
    return value

class Budget:
    def __init__(self,path,*,expected_selects=None,expected_decoded_bytes=None):
        self.path=Path(path);self.state=None
        if not self.path.resolve().is_relative_to(DOC):raise CaptureError('New budget must stay in its dedicated evidence namespace')
        if expected_selects is None or expected_decoded_bytes is None:raise CaptureError('Explicit initial SELECT and decoded-byte checkpoint required')
        if any(type(v) is not int or v!=0 for v in (expected_selects,expected_decoded_bytes)):raise CaptureError('This separate one-capture budget starts exactly0SELECT/0B; no imported or reset checkpoint')
        if not self.path.is_file():raise CaptureError('New budget ledger is missing; refusing creation/reset')
        self.state=json.loads(self.path.read_text());self._check_initial()
    def _check_initial(self):
        s=self.state
        if s.get('kind')!='orion_real_native_spatial_budget_v1' or s.get('limits')!=LIMITS:raise CaptureError('Wrong budget namespace/limits')
        if s.get('state')!='unstarted' or any(type(s.get(k)) is not int or s[k]!=0 for k in ['selects','decodedBytes','objectHttpRequests','physicalHttpBytes']):raise CaptureError('New capture is consumed or checkpoint differs; no replay/reset')
    def claim(self):
        with self.path.open('r+') as handle:
            fcntl.flock(handle,fcntl.LOCK_EX);self.state=json.load(handle);self._check_initial();self.state.update(state='capturing',capturePid=os.getpid(),startedAt=NOW(),journal=[]);handle.seek(0);json.dump(self.state,handle,indent=2);handle.write('\n');handle.truncate();handle.flush();os.fsync(handle.fileno())
    def _save(self):save(self.path,self.state)
    def _increment(self,key,amount):
        if type(amount) is not int or amount<0:raise CaptureError('Budget increment must be a nonnegative integer')
        if self.state['state']!='capturing' or self.state.get('capturePid')!=os.getpid():raise CaptureError('Budget is not claimed by this capture process')
        if self.state[key]+amount>LIMITS[key]:raise CaptureError('New bounded capture exhausted '+key+' before operation')
        self.state[key]+=amount;self._save()
    def before_select(self,origin,name,sql,params):
        if origin not in ('aws','neon') or not sql.lstrip().upper().startswith(('SELECT','WITH')):raise CaptureError('Only declared read-only source SELECT is allowed')
        self._increment('selects',1);self.state['journal'].append({'kind':'SELECT','number':self.state['selects'],'origin':origin,'name':name,'sql':sql,'parameters':params,'atUtc':NOW()});self._save();return self.state['journal'][-1]
    def before_http(self,method,key):
        if method not in ('HEAD','GET'):raise CaptureError('Only exact HEAD/GET source object operations are allowed')
        self._increment('objectHttpRequests',1);self.state['journal'].append({'kind':'object_http','number':self.state['objectHttpRequests'],'origin':'neon','method':method,'key':key,'atUtc':NOW()});self._save()
    def decoded(self,amount):self._increment('decodedBytes',amount)
    def physical(self,amount):self._increment('physicalHttpBytes',amount)
    def finish(self,state):self.state.update(state=state,finishedAt=NOW());self._save()

IDENTITY_SQL="SELECT current_database(),current_user,current_setting('transaction_read_only'),current_setting('transaction_isolation'),current_setting('statement_timeout'),current_setting('lock_timeout'),pg_current_snapshot()::text,clock_timestamp(),coalesce((SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()),false)"
DOCUMENT_SQL="""WITH wanted AS (SELECT * FROM jsonb_to_recordset(%s::jsonb) w(path text,sha256 text))
SELECT w.path,encode(o.sha256,'hex'),s.status,s.error_count,o.size,o.updated_at,d.document::text
FROM wanted w JOIN statarena.objects o ON o.path=w.path AND encode(o.sha256,'hex')=w.sha256
JOIN statarena.file_document_sources s ON s.source_path=w.path AND s.source_sha256=o.sha256 AND s.status='ready' AND s.error_count=0
JOIN statarena.file_documents d ON d.document_path=w.path AND d.source_path=w.path AND d.source_sha256=o.sha256 AND d.error IS NULL
WHERE octet_length(d.document::text)<=8388608 ORDER BY w.path LIMIT 3"""
PROFILE_ROWS_SQL="""SELECT r.endpoint,r.status,r.ref->>'path' path,r.ref->>'ordinal' ordinal,encode(o.sha256,'hex') sha256,s.status readiness,s.error_count errors
FROM statarena.resources r LEFT JOIN statarena.objects o ON o.path=r.ref->>'path'
LEFT JOIN statarena.file_document_sources s ON s.source_path=o.path AND s.source_sha256=o.sha256
WHERE r.endpoint=ANY(%s) AND r.params='{}' ORDER BY r.endpoint LIMIT 2049"""

def profile_envelope_query(inner):
    return """WITH rows AS MATERIALIZED ("""+inner+"""), bounded AS (
 SELECT CASE WHEN coalesce(octet_length(endpoint),0)<=128 AND coalesce(octet_length(path),0)<=2048
 AND coalesce(octet_length(ordinal),0)<=32 AND coalesce(octet_length(sha256),0)<=64 AND coalesce(octet_length(readiness),0)<=32
 THEN jsonb_build_array(endpoint,status,path,ordinal,sha256,readiness,errors) END item FROM rows), encoded AS (
 SELECT CASE WHEN count(*)=0 THEN '[]' WHEN count(*)<=2048 AND bool_and(item IS NOT NULL)
 THEN jsonb_agg(item ORDER BY item->>0)::text END payload,count(*) row_count FROM bounded)
 SELECT CASE WHEN octet_length(payload)<=%s THEN payload END,row_count,octet_length(payload) FROM encoded"""
NEON_SQL="""SELECT current_database(),current_user,current_setting('transaction_read_only'),current_setting('transaction_isolation'),current_setting('statement_timeout'),current_setting('lock_timeout'),pg_current_snapshot()::text,clock_timestamp(),
r.status,CASE WHEN octet_length(coalesce(r.ref->>'path',r.ref->>'shard'))<=2048 THEN coalesce(r.ref->>'path',r.ref->>'shard') END,
CASE WHEN octet_length(r.ref->>'ordinal')<=32 THEN r.ref->>'ordinal' END,encode(o.sha256,'hex'),o.size,o.updated_at,(r.error IS NOT NULL AND r.error <> 'null'::jsonb)
FROM (SELECT 1) one LEFT JOIN statarena.resources r ON r.endpoint=%s AND r.params=%s
LEFT JOIN statarena.objects o ON o.path=coalesce(r.ref->>'path',r.ref->>'shard')"""

def execute(conn,budget,origin,name,sql,params=(),body_column=None):
    entry=budget.before_select(origin,name,sql,params);started=time.monotonic()
    try:
        rows=conn.execute(sql,params).fetchall();safe=[]
        for row in rows:
            if body_column is not None:
                raw=(row[body_column] or '').encode();budget.decoded(len(raw));safe.append(list(row[:body_column])+[{'decodedBytes':len(raw),'decodedSha256':hashlib.sha256(raw).hexdigest()}]+list(row[body_column+1:]))
            else:safe.append(row)
        # Source SELECT metadata is charged conservatively as well as body content.
        budget.decoded(len(json.dumps(safe,default=str,separators=(',',':')).encode()));entry.update(rowCount=len(rows),metadata=safe,status='pass');return rows
    except Exception as error:
        entry.update(status='fail',errorType=type(error).__name__,sqlstate=getattr(error,'sqlstate',None));raise CaptureError('Bounded source SELECT failed: '+name+' ['+type(error).__name__+']') from None
    finally:entry['elapsedMs']=round((time.monotonic()-started)*1000,3);budget._save()

def configuration():
    values={}
    for line in (REPO/'dashboard/.env').read_text().splitlines():
        if '=' in line and not line.lstrip().startswith('#'):
            key,value=line.split('=',1);values[key.strip()]=value.strip().strip('"').strip("'")
    return values

def validate_private_origins(values,m):
    # Resolve required client modules before claiming the source capture.
    import boto3
    from botocore.config import Config
    from psycopg.conninfo import conninfo_to_dict
    n=m['neon'];dsn=values.get('NEON_DATABASE_URL','').replace('ep-steep-boat-bekuqo4w-pooler.','ep-steep-boat-bekuqo4w.')
    try:info=conninfo_to_dict(dsn)
    except Exception:raise CaptureError('Existing Neon DB configuration cannot be parsed; no new authentication') from None
    if info.get('host')!=n['host'] or info.get('dbname')!=n['database'] or info.get('user')!=n['user']:
        raise CaptureError('Existing Neon DB host/database/role does not match the frozen public identity')
    endpoint=values.get('NEON_STORAGE_ENDPOINT','')
    if endpoint not in ('https://'+n['storageHost'],'https://'+n['storageHost']+'/'):
        raise CaptureError('Existing Neon storage endpoint must be the exact unsigned HTTPS origin')
    if values.get('NEON_STORAGE_BUCKET','statarena-data')!=n['bucket'] or values.get('NEON_STORAGE_REGION','us-east-2')!='us-east-2':
        raise CaptureError('Existing Neon storage bucket/region differs from the frozen source')
    if not values.get('NEON_STORAGE_ACCESS_KEY_ID') or not values.get('NEON_STORAGE_SECRET_ACCESS_KEY'):
        raise CaptureError('Existing Neon object credentials unavailable; no new authentication')

def connect(origin,m,values):
    if os.environ.get('STATARENA_SOURCE_FORBIDDEN')=='1':raise CaptureError('Source access forbidden during preparation E2E')
    import psycopg
    common=dict(sslmode='verify-full',options=OPTIONS,connect_timeout=7,autocommit=False,application_name='statarena-real-native-spatial-ro')
    if origin=='aws':return psycopg.connect(host=m['aws']['host'],dbname=m['aws']['database'],user=m['aws']['user'],sslrootcert=str(REPO/'dashboard/backend/certs/rds-us-east-2.pem'),**common)
    dsn=values.get('NEON_DATABASE_URL')
    if not dsn:raise CaptureError('Existing Neon DB credentials unavailable; no new authentication')
    dsn=dsn.replace('ep-steep-boat-bekuqo4w-pooler.','ep-steep-boat-bekuqo4w.')
    from psycopg.conninfo import conninfo_to_dict
    info=conninfo_to_dict(dsn)
    if info.get('host')!=m['neon']['host'] or info.get('dbname')!=m['neon']['database'] or info.get('user')!=m['neon']['user']:raise CaptureError('Existing Neon configuration does not match frozen source identity')
    return psycopg.connect(dsn,sslrootcert='/etc/ssl/cert.pem',**common)

def verify_connection(conn,origin,m,row):
    expected=m[origin]
    if row[:6]!=(expected['database'],expected['user'],'on','repeatable read','8s','1s'):raise CaptureError('Source database/role/RO/isolation/timeouts differ from frozen identity')
    if not conn.pgconn.ssl_in_use or conn.info.get_parameters().get('sslmode')!='verify-full':raise CaptureError('Source client TLS verify-full is not active')
    if origin=='aws' and row[8] is not True:raise CaptureError('AWS server TLS is not active')

def normalizer():
    spec=importlib.util.spec_from_file_location('frozen_real_capture_normalizer',NORMALIZER);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    class NoRemote:
        def __init__(self,*a,**kw):raise CaptureError('Old SourceReader and its ledger are forbidden in new capture')
    module.SourceReader=NoRemote;return module

def neon_object(m,budget,values):
    if os.environ.get('STATARENA_SOURCE_FORBIDDEN')=='1':raise CaptureError('Source HTTP forbidden during preparation E2E')
    import boto3
    from botocore.config import Config
    n=m['neon'];endpoint=values.get('NEON_STORAGE_ENDPOINT','')
    if urlsplit(endpoint).scheme!='https' or urlsplit(endpoint).hostname!=n['storageHost'] or values.get('NEON_STORAGE_BUCKET','statarena-data')!=n['bucket']:raise CaptureError('Existing Neon storage endpoint/bucket differs from frozen origin')
    if not values.get('NEON_STORAGE_ACCESS_KEY_ID') or not values.get('NEON_STORAGE_SECRET_ACCESS_KEY'):raise CaptureError('Existing Neon object credentials unavailable; no new authentication')
    client=boto3.client('s3',endpoint_url=endpoint,region_name=values.get('NEON_STORAGE_REGION','us-east-2'),aws_access_key_id=values['NEON_STORAGE_ACCESS_KEY_ID'],aws_secret_access_key=values['NEON_STORAGE_SECRET_ACCESS_KEY'],verify=True,
        config=Config(signature_version='s3v4',s3={'addressing_style':'path'},retries={'total_max_attempts':1},connect_timeout=5,read_timeout=8,request_checksum_calculation='when_required',response_checksum_validation='when_required'))
    client.meta.events.register('before-send.s3',lambda request,**kw:budget.before_http(request.method,n['key']))
    base={'Bucket':n['bucket'],'Key':n['key']};receipt={'origin':'neon','path':n['path'],'bucket':n['bucket'],'key':n['key'],'host':n['storageHost']}
    try:
        head=client.head_object(**base);length=head.get('ContentLength');etag=head.get('ETag');receipt['head']={k:head.get(k) for k in ['ContentLength','ETag','VersionId','LastModified']}
        if length!=n['physicalBytes'] or length>LIMITS['physicalHttpBytes']-4 or not etag:raise CaptureError('Neon exact object HEAD version/size is not admitted')
        tail=client.get_object(**base,Range='bytes=-4',IfMatch=etag)
        try:
            if tail.get('ContentLength')!=4 or tail.get('ContentRange')!=f'bytes {length-4}-{length-1}/{length}':raise CaptureError('Neon gzip range not honored')
            trailer=tail['Body'].read(4);budget.physical(len(trailer))
        finally:tail['Body'].close()
        if len(trailer)!=4:raise CaptureError('Truncated Neon gzip size trailer')
        declared=int.from_bytes(trailer,'little')
        if declared!=n['decodedBytes'] or declared>min(LIMITS['perDocumentDecodedBytes'],LIMITS['decodedBytes']-budget.state['decodedBytes']):raise CaptureError('Neon announced decoded size exceeds exact expected version/budget')
        response=client.get_object(**base,IfMatch=etag)
        try:
            if response.get('ContentLength')!=length:raise CaptureError('Neon object length changed after HEAD')
            raw=response['Body'].read(length);budget.physical(len(raw))
        finally:response['Body'].close()
        if len(raw)!=length or hashlib.sha256(raw).hexdigest()!=n['physicalSha256'] or not raw.startswith(b'\x1f\x8b'):raise CaptureError('Neon exact physical SHA/gzip bytes mismatch')
        decoder=zlib.decompressobj(16+zlib.MAX_WBITS);decoded=decoder.decompress(raw,declared)
        if len(decoded)!=declared or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:raise CaptureError('Bounded Neon gzip decode does not match exact single-object size')
        budget.decoded(len(decoded));parsed=json.loads(decoded,parse_float=Decimal,parse_int=Decimal)
        if not isinstance(parsed,dict) or not isinstance(parsed.get('data'),dict) or parsed['data'].get('match_id')!=n['matchId'] or parsed['data'].get('grid',{}).get('frame')!=n['frame']:raise CaptureError('Neon response identity/data root/frame mismatch')
        receipt.update(physicalSha256=hashlib.sha256(raw).hexdigest(),decodedBytes=len(decoded),decodedSha256=hashlib.sha256(decoded).hexdigest(),sourceUrl=endpoint.rstrip('/')+'/'+n['bucket']+'/'+n['key'])
        return parsed,receipt
    finally:client.close()

def capture(m,budget,private):
    module=normalizer();cache={};meta={};profile_metadata=[];profile_gaps=[];identity={}
    conn=None
    try:
        conn=connect('aws',m,private);rows=execute(conn,budget,'aws','identity',IDENTITY_SQL);verify_connection(conn,'aws',m,rows[0]);identity['aws']={'database':rows[0][0],'role':rows[0][1],'snapshot':rows[0][6],'clientTlsVerifyFull':True,'serverTls':rows[0][8]}
        wanted=[{'path':m['aws']['manifest']['path'],'sha256':m['aws']['manifest']['physicalSha256']}]+[{'path':x['path'],'sha256':x['sha256']} for x in m['aws']['partitions']]
        if LIMITS['decodedBytes']-budget.state['decodedBytes']<3*8388608+65536:raise CaptureError('Insufficient global decoded budget before three bounded AWS document SELECT')
        docs=execute(conn,budget,'aws','three_exact_current_indexed_documents',DOCUMENT_SQL,(json.dumps(wanted),),body_column=6)
        if len(docs)!=3 or {r[0] for r in docs}!={p['path'] for p in wanted}:raise CaptureError('Exact AWS source/index version absent, duplicated or exceeds bounded size')
        for path,h,status,errors,size,updated,text in docs:
            cache[path]=json.loads(text,parse_float=Decimal,parse_int=Decimal);meta[path]={'path':path,'physicalSha256':h,'bytes':size,'updatedAt':updated,'origin':'aws','retrievedAt':NOW()}
        # Verify each frozen pointer is still in this exact source catalogue.
        def pointers(node):
            if isinstance(node,dict):
                if 'path' in node and 'sha256' in node:yield node
                for value in node.values():yield from pointers(value)
            elif isinstance(node,list):
                for value in node:yield from pointers(value)
        current=list(pointers(cache[m['aws']['manifest']['path']]))
        for p in m['aws']['partitions']:
            if sum(x.get('path')==p['path'] and x.get('sha256')==p['sha256'] for x in current)!=1:raise CaptureError('Pinned AWS manifest source pointer is missing or ambiguous')
        unpacked=module.load_parts(type('Cached',(),{'documents':lambda self,expected:{p:cache[p] for p in expected}})(),json.loads((REPO/'docs/verification/orion-pro-pilot-20261104/source_scope.json').read_text()))
        players={r['playerId'] for p in unpacked for r in p['tables']['players']};teams={r['id'] for p in unpacked for r in p['tables']['teams']}
        endpoints=['/players/'+p for p in sorted(players)]+['/teams/'+t for t in sorted(teams)]
        if len(endpoints)>2048:raise CaptureError('Scoped profile metadata exceeds declared2048-key bound')
        admitted=min(2*1024*1024,LIMITS['decodedBytes']-budget.state['decodedBytes']-65536)
        if admitted<=0:raise CaptureError('No decoded budget remains before bounded profile metadata SELECT')
        envelope=execute(conn,budget,'aws','exact_scoped_profile_resource_metadata',profile_envelope_query(PROFILE_ROWS_SQL),(endpoints,admitted),body_column=0)[0]
        if envelope[0] is None:raise CaptureError('Profile resource metadata exceeded server row/text/remaining-byte admission')
        profiles=json.loads(envelope[0])
        profile_metadata=[{'endpoint':r[0],'status':r[1],'path':r[2],'ordinal':int(r[3]) if r[3] is not None else None,'sha256':r[4],'ready':r[5]=='ready' and r[6]==0} for r in profiles]
        available={r['endpoint'].split('/')[-1] for r in profile_metadata if r['endpoint'].startswith('/players/') and r['status']==200 and r['sha256'] and r['ready']};profile_gaps=sorted(players-available)
    finally:
        if conn is not None:conn.rollback();conn.close()
    conn=None
    try:
        conn=connect('neon',m,private);n=m['neon'];rows=execute(conn,budget,'neon','identity_exact_heatmap_selector_object',NEON_SQL,(n['endpoint'],n['params']));row=rows[0]
        if len(rows)!=1:raise CaptureError('Neon exact selector is not unique')
        verify_connection(conn,'neon',m,row);expected=(n['status'],n['path'],None,n['physicalSha256'],n['physicalBytes'])
        if tuple(row[8:13])!=expected or row[14] is not False:raise CaptureError('Neon exact resource/object fingerprint changed or is erroneous')
        identity['neon']={'database':row[0],'role':row[1],'snapshot':row[6],'clientTlsVerifyFull':True,'branchId':n['branchId']};parsed,http=neon_object(m,budget,private);cache[n['path']]=parsed
        meta[n['path']]={'path':n['path'],'physicalSha256':n['physicalSha256'],'bytes':n['physicalBytes'],'updatedAt':row[13],'origin':'neon','retrievedAt':NOW(),'storageVersion':http['head'].get('VersionId'),'sourceUrl':http['sourceUrl']}
    finally:
        if conn is not None:conn.rollback();conn.close()
    for path,value in cache.items():meta[path]['decodedCanonicalSha256']=module.hashed(value)
    return {'format':'orion_source_memory_v1','captureKind':'orion_real_native_spatial_ram_v1','cache':cache,'meta':meta,'profile_metadata':profile_metadata,'profile_gaps':profile_gaps,'sourceBudget':{'queries':budget.state['selects'],'decodedBytes':budget.state['decodedBytes'],'limits':LIMITS},'captureBudget':{k:budget.state[k] for k in ['selects','decodedBytes','objectHttpRequests','physicalHttpBytes']},'manifestSha256':sha(MANIFEST_PATH),'normalizerSha256':sha(NORMALIZER),'captureCodeSha256':sha(Path(__file__)),'sourceIdentity':identity,'httpReceipt':http}

def fetch_snapshot(path):
    path=Path(path);info=path.stat(follow_symlinks=False);parent=path.parent.stat()
    if not stat.S_ISSOCK(info.st_mode) or info.st_uid!=os.getuid() or parent.st_uid!=os.getuid() or parent.st_mode&0o077:raise CaptureError('RAM source endpoint must be an owned private Unix socket')
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as client:
        client.connect(str(path));client.sendall(b'GET\n')
        with client.makefile('rb') as stream:snapshot=pickle.load(stream)
    if snapshot.get('captureKind')!='orion_real_native_spatial_ram_v1' or snapshot.get('manifestSha256')!=sha(MANIFEST_PATH) or snapshot.get('normalizerSha256')!=sha(NORMALIZER):raise CaptureError('RAM source manifest/normalizer binding differs')
    return snapshot

def main():
    p=argparse.ArgumentParser();p.add_argument('--ledger',type=Path,default=DOC/'budget.json');p.add_argument('--expected-selects',type=int);p.add_argument('--expected-decoded-bytes',type=int);p.add_argument('--check-only',action='store_true');p.add_argument('--source-authorized',action='store_true');p.add_argument('--approved-commit');p.add_argument('--socket',type=Path);p.add_argument('--evidence',type=Path,default=DOC/'capture');args=p.parse_args();budget=None;endpoint=None;server=None;receipt={}
    try:
        m=manifest();budget=Budget(args.ledger,expected_selects=args.expected_selects,expected_decoded_bytes=args.expected_decoded_bytes)
        if sha(NORMALIZER)!=m['normalizerSha256']:raise CaptureError('Frozen normalizer bytes changed before capture')
        old=REPO/m['oldLedger']['path']
        if sha(old)!=m['oldLedger']['sha256']:raise CaptureError('Old source ledger differs; no new capture may mask that change')
        checkpoint={'status':'valid_initial_checkpoint','selects':0,'decodedBytes':0,'limits':LIMITS,'sourceConnections':0,'sourceCalls':0,'oldLedgerUnchanged':True,'releaseGate':'Parent commit and separate capture approval required'}
        if args.check_only:print(json.dumps(checkpoint));return 0
        if not args.source_authorized or not args.approved_commit or args.socket is None:raise CaptureError('Explicit parent-approved commit, source authorization and private socket are required')
        blob=subprocess.run(['git','show',args.approved_commit+':dashboard/scripts/orion_pro_normalize.py'],cwd=REPO,capture_output=True,check=False)
        if blob.returncode or hashlib.sha256(blob.stdout).hexdigest()!=m['normalizerSha256'] or args.approved_commit!=m['approvedCommit']:raise CaptureError('Approved commit does not bind the frozen normalizer')
        endpoint=args.socket;parent=endpoint.parent.stat()
        if endpoint.exists() or parent.st_uid!=os.getuid() or parent.st_mode&0o077:raise CaptureError('Fresh private0700RAM socket directory required')
        if not args.evidence.resolve().is_relative_to(DOC) or args.evidence.exists():raise CaptureError('Fresh capture evidence directory required inside new namespace')
        private=configuration();validate_private_origins(private,m)
        args.evidence.mkdir();server=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);server.bind(str(endpoint));os.chmod(endpoint,0o600);server.listen(4);budget.claim();snapshot=capture(m,budget,private);private.clear();budget.finish('captured')
        receipt={'kind':snapshot['captureKind'],'ready':True,'pid':os.getpid(),'socket':str(endpoint),'manifestSha256':snapshot['manifestSha256'],'normalizerSha256':snapshot['normalizerSha256'],'captureCodeSha256':snapshot['captureCodeSha256'],'budget':snapshot['captureBudget'],'sourceIdentity':snapshot['sourceIdentity'],'httpReceipt':snapshot['httpReceipt'],'documentCount':len(snapshot['cache']),'rawBodiesPersisted':False,'command':[sys.executable,*sys.argv]};save(args.evidence/'capture.json',receipt);print(json.dumps(receipt,default=str),flush=True)
        while True:
            client,_=server.accept()
            with client:
                with client.makefile('rb') as request:command=request.readline(32)
                if command==b'STOP\n':break
                if command!=b'GET\n':continue
                with client.makefile('wb') as output:pickle.dump(snapshot,output,protocol=5)
        snapshot.clear();receipt.update(ready=False,stoppedAt=NOW(),ramReleased=True);save(args.evidence/'capture.json',receipt);return 0
    except Exception as error:
        if budget is not None and budget.state.get('state')=='capturing':budget.finish('failed')
        # Never emit connector exceptions, DSNs, credentials or source payloads.
        print(json.dumps({'status':'blocked','error':str(error) if isinstance(error,CaptureError) else type(error).__name__,'sourceConnections':0 if budget is None or budget.state.get('state')=='unstarted' else 'see_budget_journal'}),flush=True);return 2
    finally:
        if server is not None:server.close()
        if endpoint is not None and endpoint.exists():endpoint.unlink()
if __name__=='__main__':raise SystemExit(main())
