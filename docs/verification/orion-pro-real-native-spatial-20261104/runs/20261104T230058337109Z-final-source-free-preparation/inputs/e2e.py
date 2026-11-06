#!/usr/bin/env python3
"""Independent pre-capture E2E; real candidate contains no synthetic sports rows."""
from __future__ import annotations
import argparse,hashlib,importlib.util,json,os,shlex,shutil,subprocess,sys
from collections import Counter,defaultdict
from datetime import datetime,timezone
from decimal import Decimal
from pathlib import Path

sys.dont_write_bytecode=True
DOC=Path(__file__).resolve().parent
REPO=DOC.parents[2]
PILOT=REPO/'docs/verification/orion-pro-pilot-20261104'
NORMALIZER=REPO/'dashboard/scripts/orion_pro_normalize.py'
MANIFEST=json.loads((DOC/'MANIFEST.json').read_text())
FIELDS=json.loads((DOC/'FIELDS.json').read_text())['fields']
ABSENT=object()

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def initial_budget():return {'kind':'orion_real_native_spatial_budget_v1','state':'unstarted',**MANIFEST['checkpoint'],'limits':MANIFEST['limits'],'runs':[]}
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);out=importlib.util.module_from_spec(spec);spec.loader.exec_module(out);return out

def unpack_independent(snapshot):
    parts=[]
    for pointer in MANIFEST['aws']['partitions']:
        doc=snapshot['cache'][pointer['path']];tables={}
        for name,table in doc['tables'].items():
            keys=table['keys'];dictionaries=table.get('dictionaries',{});rows=[]
            for ordinal,values in enumerate(table['rows']):
                missing={int(i) for i in table.get('missing',{}).get(str(ordinal),[])}
                if len(values)!=len(keys) or any(i<0 or i>=len(keys) for i in missing):raise AssertionError('Invalid packed table layout:'+name)
                row={}
                for index,key in enumerate(keys):
                    if index in missing:continue
                    value=values[index]
                    if str(index) in dictionaries and value is not None:value=dictionaries[str(index)][int(value)]
                    row[key]=value
                rows.append(row)
            tables[name]=rows
        parts.append({'season':pointer['season'],'path':pointer['path'],'tables':tables})
    return parts

def native(v):
    if v is ABSENT:return 'absent',(None,None,None)
    if v is None:return 'null',(None,None,None)
    if isinstance(v,bool):return 'boolean',(None,None,v)
    if isinstance(v,str):return 'string',(None,v,None)
    if isinstance(v,(int,Decimal)) and not isinstance(v,bool):
        value=Decimal(v)
        if not value.is_finite():raise AssertionError('Nonfinite native source number')
        return 'number',(value,None,None)
    raise AssertionError('Unrepresentable native source kind')

def native_oracle(conn,parts):
    """Direct SQL; independent field registry, unpack and native token logic."""
    wanted={}
    for part in parts:
        for ordinal,row in enumerate(part['tables']['performances']):
            key=(part['path'],str(row['id']))
            if key in wanted:raise AssertionError('Duplicate source performance identity')
            wanted[key]=(ordinal,row)
    columns=','.join('s.'+f['commonColumn'] for f in FIELDS)
    wide_sql="SELECT d.legacy_object_path,r.external_key,r.locator,s.source_record_id,s.revision_id,s.match_id,s.player_id,s.team_id,s.match_player_revision_id,s.source_id,s.period_code,s.period_definition_version,s.variant_key,s.recorded_from_gen,"+columns+" FROM football.player_match_stats s JOIN ingest.source_records r ON r.id=s.source_record_id JOIN ingest.source_documents d ON d.id=r.document_id WHERE s.is_canonical AND s.recorded_to_gen IS NULL ORDER BY s.source_record_id"
    wide=list(conn.execute(wide_sql));by_record={};errors=Counter();source_states=Counter();typed_states=Counter();source_hash=hashlib.sha256();typed_hash=hashlib.sha256()
    for row in wide:
        key=(row[0],row[1])
        if key not in wanted:errors['unexpected_wide_identity']+=1;continue
        ordinal,source=wanted[key]
        if row[2]!='/tables/performances/rows/'+str(ordinal):errors['performance_locator']+=1
        by_record[row[3]]=(row,source)
    metric_sql="SELECT source_record_id,metric_code,value_kind,numeric_value,text_value,boolean_value,numerator,denominator,source_display,match_id,player_id,team_id,match_player_revision_id,source_id,period_code,period_definition_version,variant_key,recorded_from_gen,metric_definition_version FROM football.player_match_metric_values WHERE is_canonical AND recorded_to_gen IS NULL ORDER BY source_record_id,metric_code"
    field_by_code={'legacy_normalized_'+f['sourceField']:(i,f) for i,f in enumerate(FIELDS)};seen=set();slot_count=0
    with conn.transaction():
        with conn.cursor(name='independent_native31') as cursor:
            cursor.itersize=2048;cursor.execute(metric_sql)
            for v in cursor:
                code=v[1];record=v[0]
                if record not in by_record or code not in field_by_code:errors['unexpected_metric']+=1;continue
                if (record,code) in seen:errors['duplicate_metric']+=1;continue
                seen.add((record,code));wide_row,source=by_record[record];index,field=field_by_code[code];raw=source.get(field['sourceField'],ABSENT);kind,exact=native(raw);common=wide_row[14+index]
                same_value=v[2]==kind and tuple(v[3:6])==exact and all(x is None for x in v[6:9])
                same_binding=tuple(v[9:17])==tuple(wide_row[5:13]) and v[17]==wide_row[13] and v[18]==MANIFEST['transformVersion']
                common_ok=common is None if kind!='number' else common is not None and Decimal(str(common))==exact[0]
                if not same_value:errors['native_value:'+field['sourceField']]+=1
                if not same_binding:errors['native_binding:'+field['sourceField']]+=1
                if not common_ok:errors['common_projection:'+field['sourceField']]+=1
                detail='zero' if kind=='number' and exact[0]==0 else 'empty_string' if kind=='string' and exact[1]=='' else kind
                source_states[field['sourceField']+':'+detail]+=1
                td='zero' if v[2]=='number' and v[3]==0 else 'empty_string' if v[2]=='string' and v[4]=='' else v[2];typed_states[field['sourceField']+':'+td]+=1
                # Hash identical tagged value stream; source values never emitted.
                source_hash.update(json.dumps([wide_row[0],wide_row[1],code,kind,exact],default=str,separators=(',',':')).encode()+b'\n')
                typed_hash.update(json.dumps([wide_row[0],wide_row[1],code,v[2],tuple(v[3:6])],default=str,separators=(',',':')).encode()+b'\n');slot_count+=1
    expected=len(wanted)*31
    if len(wide)!=len(wanted) or len(by_record)!=len(wanted):errors['wide_membership']+=1
    if slot_count!=expected:errors['missing_native_slot_is_unknown']+=expected-slot_count
    definitions=list(conn.execute('SELECT code,unit,scope,aggregation,allows_negative FROM football.metric_definitions ORDER BY code'))
    expected_def=sorted(('legacy_normalized_'+f['sourceField'],'source_native','player','none',f['sourceField'] in {'rating','goalsPrevented'}) for f in FIELDS)
    if definitions!=expected_def:errors['metric_definition_units']+=1
    rules={'integer':'exact nonnegative int32','numeric':'exact finite unconstrained numeric','double precision':'finite Decimal(str(float(native))) == native'}
    mappings=list(conn.execute("SELECT raw_key,metric_code,metric_definition_version,mapping_version,parse_rule->>'common_column',parse_rule->>'common_sql_type',parse_rule->>'number_projection' FROM football.source_metric_mappings WHERE family_code='normalized_performance' ORDER BY raw_key"))
    expected_map=sorted((f['sourceField'],'legacy_normalized_'+f['sourceField'],MANIFEST['transformVersion'],MANIFEST['transformVersion'],f['commonColumn'],f['commonSqlType'],rules[f['commonSqlType']]) for f in FIELDS)
    if mappings!=expected_map:errors['mapping_registry']+=1
    result={'sourcePerformances':len(wanted),'expectedSlots':expected,'typedSlots':slot_count,'historicalExpectedSlots':478547,'historicalScopeConfirmed':len(wanted)==15437,'sourceStates':dict(sorted(source_states.items())),'typedStates':dict(sorted(typed_states.items())),'sourceSha256':source_hash.hexdigest(),'typedSha256':typed_hash.hexdigest(),'errors':dict(errors),'sql':{'wide':wide_sql,'metric':metric_sql,'definitions':'SELECT code,unit,scope,aggregation,allows_negative FROM football.metric_definitions ORDER BY code','mappings':"SELECT raw_key,metric_code,metric_definition_version,mapping_version,parse_rule->>'common_column',parse_rule->>'common_sql_type',parse_rule->>'number_projection' FROM football.source_metric_mappings WHERE family_code='normalized_performance' ORDER BY raw_key"}}
    return result,not errors and source_hash.digest()==typed_hash.digest() and source_states==typed_states

def spatial_oracle(conn,snapshot):
    n=MANIFEST['neon'];data=snapshot['cache'][n['path']]['data'];expected={};errors=Counter();count=0
    for kind in ('teams','players'):
        rows=data.get(kind,ABSENT)
        if rows is ABSENT or rows is None:rows=[]
        if not isinstance(rows,list):raise AssertionError('Invalid real spatial collection')
        for ordinal,row in enumerate(rows):
            key='/data/'+kind+'/'+str(ordinal);expected[key]=(kind,row);count+=len(row.get('cells') or [])
    sql="SELECT h.id,r.locator,d.legacy_object_path,d.storage_provider,d.storage_bucket,d.storage_key,d.content_sha256,t.public_key,p.public_key,s.side,h.grid_columns,h.grid_rows,h.cell_length_m,h.cell_width_m,h.coordinate_frame,h.actions,h.cells_state,h.source_id,h.source_record_id,h.match_team_revision_id FROM football.match_heatmaps h JOIN ingest.source_records r ON r.id=h.source_record_id JOIN ingest.source_documents d ON d.id=r.document_id JOIN ingest.public_aliases_current t ON t.route_kind='team' AND t.team_id=h.team_id LEFT JOIN ingest.public_aliases_current p ON p.route_kind='player' AND p.player_id=h.player_id JOIN football.match_teams s ON s.revision_id=h.match_team_revision_id WHERE h.is_canonical AND h.recorded_to_gen IS NULL ORDER BY r.locator"
    rows=list(conn.execute(sql));source_rows=[];typed_rows=[];grid=data['grid'];observed_cells=0
    for v in rows:
        if v[1] not in expected:errors['unknown_collection_locator']+=1;continue
        kind,raw=expected[v[1]];cells=raw.get('cells',ABSENT);state='absent' if cells is ABSENT else 'null' if cells is None else 'empty' if not cells else 'available'
        wanted=(raw['team']['id'],raw['player']['id'] if kind=='players' else None,raw['side'],int(grid['length']),int(grid['width']),Decimal(str(grid['cell_length_m'])),Decimal(str(grid['cell_width_m'])),grid['frame'],raw.get('actions'),state)
        actual=(*v[7:12],Decimal(str(v[12])),Decimal(str(v[13])),*v[14:17])
        if actual!=wanted:errors['parent_native_grid_actor']+=1
        if v[2:7]!=(n['path'],'neon_s3',n['bucket'],n['key'],n['physicalSha256']):errors['source_origin']+=1
        source_cells=[(i,int(c[0]),int(c[1]),int(c[2])) for i,c in enumerate([] if cells is ABSENT or cells is None else cells)]
        typed_cells=list(conn.execute('SELECT cell_ordinal,column_index,row_index,action_count FROM football.match_heatmap_cells WHERE heatmap_id=%s ORDER BY cell_ordinal',(v[0],)))
        if typed_cells!=source_cells:errors['cell_order_coordinate_action']+=1
        source_rows.append((v[1],wanted,source_cells));typed_rows.append((v[1],actual,typed_cells));observed_cells+=len(typed_cells)
    if len(rows)!=len(expected) or observed_cells!=count:errors['parent_child_membership']+=1
    slot_sql="SELECT c.feature_code,c.collection_state,c.observed_row_count,r.locator,d.legacy_object_path FROM ingest.match_coverage c JOIN ingest.source_records r ON r.id=c.source_record_id JOIN ingest.source_documents d ON d.id=r.document_id WHERE c.is_canonical AND c.recorded_to_gen IS NULL AND c.feature_code LIKE 'heatmaps.%%' ORDER BY c.feature_code"
    slots=list(conn.execute(slot_sql));wanted_slots=[]
    for k in ('players','teams'):
        value=data.get(k,ABSENT);state='absent' if value is ABSENT else 'null' if value is None else 'empty' if not value else 'present'
        wanted_slots.append(('heatmaps.'+k,state,len(value) if isinstance(value,list) else None,'/data/'+k,n['path']))
    if slots!=wanted_slots:errors['coverage_slot_provenance']+=1
    result={'expectedParents':len(expected),'typedParents':len(rows),'expectedTriplets':count,'typedCells':observed_cells,'historical1344Confirmed':count==1344,'sourceSha256':digest(source_rows),'typedSha256':digest(typed_rows),'errors':dict(errors),'sql':{'parents':sql,'cells':'SELECT cell_ordinal,column_index,row_index,action_count FROM football.match_heatmap_cells WHERE heatmap_id=%s ORDER BY cell_ordinal','slots':slot_sql},'slots':slots,'nameShirtFullFidelityAccepted':False}
    return result,not errors and result['sourceSha256']==result['typedSha256']

def fingerprint(conn):
    tables=[x[0] for x in conn.execute("SELECT n.nspname||'.'||c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE c.relkind='r' AND n.nspname IN ('ingest','football','analytics') ORDER BY 1")];rows=[]
    for table in tables:
        count,h=conn.execute("SELECT count(*),encode(sha256(convert_to(coalesce(string_agg(h,'' ORDER BY h),''),'UTF8')),'hex') FROM (SELECT encode(sha256(convert_to(t::text,'UTF8')),'hex') h FROM "+table+' t) s').fetchone();rows.append((table,count,h))
    seq=list(conn.execute("SELECT schemaname,sequencename,last_value FROM pg_sequences WHERE schemaname IN ('ingest','football','analytics') ORDER BY 1,2"))
    return {'tables':rows,'sequences':seq,'sha256':digest([rows,seq])}

def guard_cli(run):
    capture=DOC/'capture.py'
    if not capture.exists():raise AssertionError('Missing bounded real-source capture guard before implementation')
    outcomes=[];base=run/'guard-cli';base.mkdir()
    template=initial_budget()
    for label,flags,mutate in [('zero',['--expected-selects','0','--expected-decoded-bytes','0'],None),('missing',[],None),('missing-bytes',['--expected-selects','0'],None),('old-89',['--expected-selects','89','--expected-decoded-bytes','254796352'],None),('nonzero',['--expected-selects','1','--expected-decoded-bytes','0'],None),('negative',['--expected-selects','-1','--expected-decoded-bytes','0'],None),('missing-ledger',['--expected-selects','0','--expected-decoded-bytes','0'],'missing'),('replayed',['--expected-selects','0','--expected-decoded-bytes','0'],'replayed')]:
        folder=base/label;folder.mkdir();ledger=folder/'budget.json';state=dict(template)
        if mutate=='replayed':state['state']='captured'
        if mutate!='missing':ledger.write_text(json.dumps(state)+'\n')
        command=[sys.executable,str(capture),'--check-only','--ledger',str(ledger),*flags];env=os.environ.copy();env['STATARENA_SOURCE_FORBIDDEN']='1';result=subprocess.run(command,text=True,capture_output=True,env=env,timeout=20)
        (folder/'stdout.log').write_text(result.stdout);(folder/'stderr.log').write_text(result.stderr)
        ok=result.returncode==0 if label=='zero' else result.returncode!=0
        if not ok:raise AssertionError('Checkpoint CLI did not enforce '+label)
        if label=='zero':assert json.loads(result.stdout)['sourceConnections']==0
        outcomes.append({'case':label,'command':command,'exitCode':result.returncode,'expectedAccepted':label=='zero','sourceConnections':0})
    return {'outcomes':outcomes}

def budget_boundary(run):
    cap=load('new_bounded_capture',DOC/'capture.py');outcomes=[];template=initial_budget()
    for label in ['selects','http','decoded','physical','claim']:
        p=run/('guard-budget-'+label+'.json');p.write_text(json.dumps(template)+'\n');budget=cap.Budget(p,expected_selects=0,expected_decoded_bytes=0);budget.claim();refused=False
        try:
            if label=='selects':
                for i in range(12):budget.before_select('aws','boundary-'+str(i),'SELECT 1',())
            elif label=='http':
                for i in range(4):budget.before_http('HEAD','synthetic-metadata-key')
            elif label=='decoded':budget.decoded(33554433)
            elif label=='physical':budget.physical(1048577)
            else:cap.Budget(p,expected_selects=0,expected_decoded_bytes=0)
        except cap.CaptureError:refused=True
        assert refused,label
        final=json.loads(p.read_text());assert final['selects']<=11 and final['objectHttpRequests']<=3 and final['decodedBytes']<=33554432 and final['physicalHttpBytes']<=1048576
        outcomes.append({'case':label,'refused':True,'counters':{k:final[k] for k in ['selects','objectHttpRequests','decodedBytes','physicalHttpBytes']}})
    return {'outcomes':outcomes,'sourceCalls':0,'metadataOnlySimulation':True}

def private_config_boundary():
    cap=load('new_private_config_guard',DOC/'capture.py');n=MANIFEST['neon']
    good={'NEON_DATABASE_URL':'postgresql://'+n['user']+':explicit_synthetic_credential@'+n['host']+'/'+n['database'],'NEON_STORAGE_ENDPOINT':'https://'+n['storageHost'],'NEON_STORAGE_BUCKET':n['bucket'],'NEON_STORAGE_ACCESS_KEY_ID':'explicit_synthetic_key','NEON_STORAGE_SECRET_ACCESS_KEY':'explicit_synthetic_secret'}
    cap.validate_private_origins(good,MANIFEST);outcomes=[]
    for key,value in [('NEON_DATABASE_URL',good['NEON_DATABASE_URL'].replace(n['user'],'wrong_role')),('NEON_DATABASE_URL',good['NEON_DATABASE_URL'].replace(n['host'],'wrong.invalid')),('NEON_STORAGE_ENDPOINT','https://wrong.invalid'),('NEON_STORAGE_ENDPOINT','https://user:secret@'+n['storageHost']),('NEON_STORAGE_ENDPOINT','https://'+n['storageHost']+'?signature=synthetic'),('NEON_STORAGE_ENDPOINT','https://'+n['storageHost']+'#fragment'),('NEON_STORAGE_ENDPOINT','https://'+n['storageHost']+':444'),('NEON_STORAGE_ENDPOINT','https://'+n['storageHost']+'/other'),('NEON_STORAGE_BUCKET','wrong_bucket'),('NEON_STORAGE_SECRET_ACCESS_KEY','')]:
        invalid=dict(good);invalid[key]=value;refused=False
        try:cap.validate_private_origins(invalid,MANIFEST)
        except cap.CaptureError:refused=True
        assert refused,key;outcomes.append({'configurationKey':key,'refused':True,'sourceCalls':0})
    return {'positivePublicIdentity':{'database':n['database'],'user':n['user'],'host':n['host'],'storageHost':n['storageHost'],'bucket':n['bucket']},'invalidConfigurations':outcomes,'realCredentialsLoaded':False}

def main():
    p=argparse.ArgumentParser();p.add_argument('--label',default='prepare');p.add_argument('--prepare-only',action='store_true');p.add_argument('--source-socket',type=Path);p.add_argument('--worker',action='store_true');p.add_argument('--evidence',type=Path);p.add_argument('--pg-bin',type=Path,default=Path('/tmp/statarena-cache-test-tools/node_modules/@embedded-postgres/darwin-arm64/native/bin'));args=p.parse_args()
    if args.worker:
        cap=load('real_capture_worker',DOC/'capture.py');candidate=load('real_candidate_worker',DOC/'candidate.py');snapshot=cap.fetch_snapshot(args.source_socket)
        import psycopg
        with psycopg.connect(os.environ['ORION_PILOT_DATABASE_URL'],autocommit=True) as conn:
            conn.execute('SET ROLE orion_pro_ingest');result=candidate.import_candidate(conn,args.evidence,snapshot)
        print(json.dumps({'status':'pass','coreReused':result['core']['reused'],'spatialReused':result['spatial'].get('reused',False),'sourceCalls':0}));return 0
    if not args.prepare_only and args.source_socket is None:p.error('Explicit --prepare-only or --source-socket required; no source fallback')
    run=DOC/'runs'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-'+args.label);run.mkdir(parents=True);(run/'inputs').mkdir()
    for q in [Path(__file__),DOC/'PLAN.md',DOC/'PROTOCOL.md',DOC/'MANIFEST.json',DOC/'FIELDS.json',DOC/'capture.py',DOC/'candidate.py',NORMALIZER,PILOT/'harness.py']:
        if q.exists():shutil.copy2(q,run/'inputs'/q.name)
    old_ledger=REPO/MANIFEST['oldLedger']['path'];before_old=sha(old_ledger);assert before_old==MANIFEST['oldLedger']['sha256']
    sys.path.insert(0,str(PILOT));from harness import LocalPostgres
    import psycopg
    pg=LocalPostgres(args.pg_bin,run);conn=None;blocked=None;snapshot=None;parts=None
    report={'command':'PYTHONPATH=/tmp/statarena-publication-test-python '+shlex.join([sys.executable,*sys.argv]),'environment':'owned LOCAL PG18.6; real candidate has source-derived facts only','normalizerSha256':sha(NORMALIZER),'testSha256':sha(Path(__file__)),'manifestSha256':sha(DOC/'MANIFEST.json'),'fullAcceptance':False,'sourceCallsByTest':0,'realNativeStatesCompared':0,'realTripletsCompared':0,'cases':[]}
    cases=['empty_local_bootstrap','source_startup_contract','future_captured_ledger_guard','capture_checkpoint_cli','global_budget_guards','profile_metadata_admission','private_origin_configuration','real_core_import','independent_native31','real_spatial_import_and_oracle','fresh_process_noop']
    try:
        pg.start();pg.migration(REPO);conn=psycopg.connect(pg.dsn,autocommit=True);conn.execute('SET ROLE orion_pro_ingest')
        for case in cases:
            if blocked or (args.prepare_only and case.startswith(('real_','independent_','fresh_'))):report['cases'].append({'case':case,'status':'unverified','reason':blocked or 'Awaiting separately approved single real capture'});continue
            try:
                if case=='empty_local_bootstrap':
                    assert conn.execute('SELECT current_user').fetchone()[0]=='orion_pro_ingest';counts={t:conn.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in ['football.players','football.teams','football.matches','football.player_match_stats','football.match_heatmaps']};assert not any(counts.values());actual={'role':'orion_pro_ingest','businessRows':counts,'syntheticSportsRowsInserted':0}
                elif case=='source_startup_contract':
                    cap=load('exact_startup_options',DOC/'capture.py')
                    with psycopg.connect(pg.dsn,options=cap.OPTIONS,autocommit=False) as local:
                        local.execute('SET ROLE orion_pro_ingest');settings=local.execute(cap.IDENTITY_SQL).fetchone();assert settings[:6]==('postgres','orion_pro_ingest','on','repeatable read','8s','1s')
                    pointers=[MANIFEST['aws']['manifest']]+MANIFEST['aws']['partitions'];assert len({p['path'] for p in pointers})==3
                    hashes=[p.get('sha256',p.get('physicalSha256')) for p in pointers];assert all(len(h)==64 and h!='0'*64 and all(c in '0123456789abcdef' for c in h) for h in hashes)
                    blob=subprocess.check_output(['git','show',MANIFEST['approvedCommit']+':dashboard/scripts/orion_pro_normalize.py'],cwd=REPO);assert hashlib.sha256(blob).hexdigest()==MANIFEST['normalizerSha256']
                    actual={'localSettings':settings[:7],'sourceCalls':0,'normalizerCommittedShaVerified':True,'frozenPaths':[p['path'] for p in pointers],'frozenHashes':hashes,'actualBackslashesInOptions':cap.OPTIONS.count(chr(92))}
                elif case=='capture_checkpoint_cli':actual=guard_cli(run)
                elif case=='future_captured_ledger_guard':
                    mutable=DOC/'budget.json';old_read=Path.read_text;real_before=sha(mutable);folder=run/'future-main-ledger';folder.mkdir()
                    def future_read(path,*a,**kw):
                        if path==mutable:
                            simulated=json.loads(old_read(path));simulated.update(state='captured',selects=4,decodedBytes=10000000,objectHttpRequests=3,physicalHttpBytes=3961);return json.dumps(simulated)
                        return old_read(path,*a,**kw)
                    Path.read_text=future_read
                    try:cli=guard_cli(folder);boundaries=budget_boundary(folder)
                    finally:Path.read_text=old_read
                    assert sha(mutable)==real_before;actual={'cli':cli,'budgets':boundaries,'realLedgerByteUnchanged':True,'simulatedState':'captured/nonzero in read view only'}
                elif case=='global_budget_guards':actual=budget_boundary(run)
                elif case=='profile_metadata_admission':
                    cap=load('server_metadata_admission',DOC/'capture.py');prefix="SELECT 'endpoint'::text endpoint,200 status,";suffix=" path,NULL::text ordinal,repeat('a',64) sha256,'ready'::text readiness,0 errors"
                    outcomes=[]
                    for label,inner,limit,accepted in [('valid',prefix+"'raw/synthetic-metadata-key'"+suffix,10000,True),('large-path',prefix+"repeat('x',2049)"+suffix,10000,False),('global-remaining',prefix+"'raw/synthetic-metadata-key'"+suffix,1,False),('large-row-count',prefix+"'raw/synthetic-metadata-key'"+suffix+' FROM generate_series(1,2049)',1048576,False)]:
                        sql=cap.profile_envelope_query(inner);row=conn.execute(sql,(limit,)).fetchone();assert (row[0] is not None)==accepted,label
                        outcomes.append({'case':label,'admitted':accepted,'serverRowCount':row[1],'serverEncodedBytes':row[2],'sql':sql,'sourceCalls':0})
                    actual={'outcomes':outcomes,'fixtures':'SELECT-only synthetic resource metadata; no sports facts or rows inserted'}
                elif case=='private_origin_configuration':actual=private_config_boundary()
                elif case=='real_core_import':
                    cap=load('approved_real_capture',DOC/'capture.py');candidate=load('approved_real_candidate',DOC/'candidate.py');snapshot=cap.fetch_snapshot(args.source_socket);parts=unpack_independent(snapshot);actual=candidate.import_candidate(conn,run,snapshot,core_only=True);assert not actual['core']['reused'];report['sourceCaptureBudget']=snapshot['captureBudget'];report['sourceMemberCounts']={t:sum(len(x['tables'].get(t,[])) for x in parts) for t in ['fixtures','matches','performances','shots']}
                elif case=='independent_native31':
                    actual,ok=native_oracle(conn,parts);report['realNativeStatesCompared']=actual['typedSlots'];assert ok,{'errors':actual['errors'],'expectedSlots':actual['expectedSlots'],'typedSlots':actual['typedSlots']}
                elif case=='real_spatial_import_and_oracle':
                    result=candidate.import_candidate(conn,run,snapshot);actual,ok=spatial_oracle(conn,snapshot);actual['phaseReceipt']=result['spatial'];report['realTripletsCompared']=actual['typedCells'];assert ok,actual['errors']
                else:
                    before=fingerprint(conn);command=[sys.executable,str(Path(__file__)),'--worker','--source-socket',str(args.source_socket),'--evidence',str(run)];env=os.environ.copy();env['ORION_PILOT_DATABASE_URL']=pg.dsn
                    result=subprocess.run(command,text=True,capture_output=True,env=env,timeout=600);(run/'fresh-worker.stdout.log').write_text(result.stdout);(run/'fresh-worker.stderr.log').write_text(result.stderr);after=fingerprint(conn);assert result.returncode==0 and before==after;worker=json.loads(result.stdout);assert worker['coreReused'] and worker['spatialReused'];actual={'command':command,'worker':worker,'before':before,'after':after,'unchanged':True}
                report['cases'].append({'case':case,'status':'pass','actual':actual});print('PASS '+case,flush=True)
            except Exception as error:
                report['cases'].append({'case':case,'status':'fail','error':str(error) if isinstance(error,AssertionError) else type(error).__name__,'sqlstate':getattr(error,'sqlstate',None)});print('FAIL '+case+': '+type(error).__name__,flush=True);blocked='Prerequisite '+case+' failed'
    finally:
        if conn:conn.close()
        report['cleanup']=pg.cleanup();report['oldLedgerByteIdentical']=sha(old_ledger)==before_old;assert report['oldLedgerByteIdentical'];report['counts']={s:sum(c['status']==s for c in report['cases']) for s in ['pass','fail','unverified']};report['status']='fail' if report['counts']['fail'] else 'prepared_real_unverified' if args.prepare_only else 'pass';(run/'result.json').write_text(json.dumps(report,indent=2,default=str)+'\n');print(json.dumps({'status':report['status'],'counts':report['counts'],'evidence':str(run)}),flush=True)
    return 1 if report['status']=='fail' else 0
if __name__=='__main__':raise SystemExit(main())
