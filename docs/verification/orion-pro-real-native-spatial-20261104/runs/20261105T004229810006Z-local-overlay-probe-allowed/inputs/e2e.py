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
WRITER_OPTIONS='-c statement_timeout=8000 -c lock_timeout=1000'
OVERLAY_PATH=REPO/'docs/verification/orion-validator-membership-20261105/candidate.sql'
OVERLAY_SHA='e0810f8670b2cb627ade2c76e3c8eb527ab31fd595d5cf939fd63bfc5cf649d6'
OVERLAY_APPLIED_SHA='30f86fa262fd4cf10307e78431350f25b9d7a5b353d0c76abc0594340edb5d20'
MODEL_PATH=REPO/'docs/architecture/orion-plan-20261104/target-schema.proposed.json'
MODEL_SHA='18da43f940870b7a3a3cb49323c847dd5e5174e5eea1f8ff0c8a159cf373cb08'
SEALED_013_PATH=REPO/'dashboard/backend/migrations/013_orion_pro_integrity.sql'
SEALED_013_SHA='85525221cad51b32aff79a777098211b4112f9f00ea7161ac93945654eeb6968'

class LocalOverlayError(ValueError):pass
class LocalWorkerDSNError(ValueError):pass

def local_worker_parameters(dsn):
    from psycopg.conninfo import conninfo_to_dict
    try:params=conninfo_to_dict(dsn)
    except Exception:raise LocalWorkerDSNError() from None
    host=params.get('host');loopback={'127.0.0.1','::1'}
    if host not in loopback|{'localhost'}:raise LocalWorkerDSNError()
    address=params['hostaddr'] if 'hostaddr' in params else os.environ.get('PGHOSTADDR')
    if address is not None and address not in loopback:raise LocalWorkerDSNError()
    if host in loopback and address is not None and address!=host:raise LocalWorkerDSNError()
    # Pin the effective address as well as the name; libpq environment/service
    # defaults must not route an allowed localhost name to an external address.
    params['hostaddr']=address if address is not None else '127.0.0.1' if host=='localhost' else host
    params['options']=WRITER_OPTIONS
    return params

def validator_body(sql):
    prefix='CREATE OR REPLACE FUNCTION "ingest"."validate_generation"(g bigint) RETURNS void'
    start=sql.find(prefix)
    if start<0:raise LocalOverlayError('Known validator signature is absent')
    tail=sql[start:];marker='$orion_pro$';parts=tail.split(marker,2)
    if len(parts)!=3:raise LocalOverlayError('Known validator body delimiter is absent')
    return parts[1]

def local_overlay_choice(path,expected_sha):
    if path is None and expected_sha is None:return None
    if path is None or expected_sha is None:raise LocalOverlayError('Explicit local overlay requires both exact path and SHA')
    supplied=path if path.is_absolute() else REPO/path
    if supplied!=OVERLAY_PATH or supplied.is_symlink():raise LocalOverlayError('Only the exact approved local validator path is allowed')
    if expected_sha!=OVERLAY_SHA:raise LocalOverlayError('Local validator supplied SHA is not the approved candidate')
    raw=supplied.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=OVERLAY_SHA:raise LocalOverlayError('Local validator file differs from the approved candidate')
    if sha(MODEL_PATH)!=MODEL_SHA:raise LocalOverlayError('Model differs from the frozen18da contract')
    if sha(SEALED_013_PATH)!=SEALED_013_SHA:raise LocalOverlayError('Sealed013file differs from its approved bytes')
    sql=raw.decode().strip()
    if hashlib.sha256(sql.encode()).hexdigest()!=OVERLAY_APPLIED_SHA:raise LocalOverlayError('Applied local validator text differs from its approved SHA')
    return {'policy':'local_candidate_membership_e0810f','path':str(supplied),'fileSha256':OVERLAY_SHA,'appliedSqlSha256':OVERLAY_APPLIED_SHA,'bodySha256':hashlib.sha256(validator_body(sql).encode()).hexdigest(),'baselineBodySha256':hashlib.sha256(validator_body(SEALED_013_PATH.read_text()).encode()).hexdigest(),'raw':raw,'sql':sql}

def validator_metadata(conn):
    sql="""SELECT p.oid::bigint,p.proowner::bigint,pg_get_userbyid(p.proowner),p.proacl::text,p.prosecdef,p.proconfig,
    pg_get_function_identity_arguments(p.oid),pg_get_function_result(p.oid),l.lanname,
    encode(sha256(convert_to(p::text,'UTF8')),'hex'),encode(sha256(convert_to(pg_get_functiondef(p.oid),'UTF8')),'hex'),encode(sha256(convert_to(p.prosrc,'UTF8')),'hex')
    FROM pg_proc p JOIN pg_language l ON l.oid=p.prolang WHERE p.oid='ingest.validate_generation(bigint)'::regprocedure"""
    row=conn.execute(sql).fetchone()
    if row is None:raise LocalOverlayError('Fresh database has no expected validator')
    keys=['oid','ownerOid','owner','acl','securityDefiner','config','identityArguments','resultType','language','pgProcRowSha256','definitionSha256','bodySha256']
    return dict(zip(keys,row))

def other_validator_functions(conn):
    return conn.execute("SELECT count(*),encode(sha256(convert_to(coalesce(string_agg(h,'' ORDER BY oid),''),'UTF8')),'hex') FROM (SELECT p.oid,encode(sha256(convert_to(p::text,'UTF8')),'hex') h FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname IN ('ingest','football','analytics') AND p.oid<>'ingest.validate_generation(bigint)'::regprocedure) x").fetchone()

def overlay_protected(meta):return {k:meta[k] for k in ['oid','ownerOid','owner','acl','securityDefiner','config','identityArguments','resultType','language']}

def verify_local_overlay_installed(conn,spec,expected=None):
    if conn.info.host not in ('127.0.0.1','localhost','::1'):raise LocalOverlayError('Validator overlay requires owned LOCAL PostgreSQL')
    version=conn.execute("SELECT current_setting('server_version_num'),current_setting('statement_timeout'),current_setting('lock_timeout')").fetchone()
    if version!=('180006','8s','1s'):raise LocalOverlayError('Validator candidate requires localPG18.6 and exact8s/1s')
    checksum=conn.execute("SELECT content_sha256 FROM ingest.schema_migrations WHERE version='013'").fetchone()
    if checksum!=(SEALED_013_SHA,):raise LocalOverlayError('Database sealed013receipt differs')
    actual=validator_metadata(conn)
    if actual['bodySha256']!=spec['bodySha256'] or actual['securityDefiner'] is not True or actual['config']!=['search_path=pg_catalog']:
        raise LocalOverlayError('Installed local validator body/security context differs from the explicit candidate')
    if expected is not None and actual!=expected:raise LocalOverlayError('Fresh worker validator pg_proc metadata differs from the main receipt')
    return actual

def apply_local_overlay(conn,spec,run):
    if conn.info.host not in ('127.0.0.1','localhost','::1'):raise LocalOverlayError('Validator overlay requires owned LOCAL PostgreSQL')
    settings=conn.execute("SELECT current_setting('server_version_num'),current_setting('statement_timeout'),current_setting('lock_timeout'),(SELECT rolsuper FROM pg_roles WHERE rolname=current_user)").fetchone()
    if settings!=('180006','8s','1s',True):raise LocalOverlayError('Overlay requires localPG18.6 administrator with8s/1s')
    if conn.execute("SELECT content_sha256 FROM ingest.schema_migrations WHERE version='013'").fetchone()!=(SEALED_013_SHA,):raise LocalOverlayError('Database sealed013receipt differs')
    before=validator_metadata(conn)
    if before['bodySha256']!=spec['baselineBodySha256']:raise LocalOverlayError('Fresh database validator is not the sealed013baseline')
    other_before=other_validator_functions(conn);facts_before=fingerprint(conn)
    with conn.transaction():
        conn.execute(spec['sql']);after=verify_local_overlay_installed(conn,spec)
        other_after=other_validator_functions(conn);facts_after=fingerprint(conn)
        if overlay_protected(before)!=overlay_protected(after):raise LocalOverlayError('Candidate replacement changed protected pg_proc metadata')
        if other_before!=other_after:raise LocalOverlayError('Candidate replacement changed another function')
        if facts_before!=facts_after:raise LocalOverlayError('Candidate replacement changed a business table or sequence')
    report={k:spec[k] for k in ['policy','path','fileSha256','appliedSqlSha256','bodySha256']}
    report.update(overlayApplied=True,localOnly=True,modelSha256=MODEL_SHA,sealed013Sha256=SEALED_013_SHA,before=before,after=after,protectedMetadataPreserved=True,otherFunctionsUnchanged=True,otherFunctionsBefore=other_before,otherFunctionsAfter=other_after,businessTablesUnchanged=True,businessFingerprintBefore=facts_before['sha256'],businessFingerprintAfter=facts_after['sha256'])
    (run/'local-validator-overlay.json').write_text(json.dumps(report,indent=2)+'\n');return report

def overlay_flags(spec):return ['--local-validator-overlay',spec['path'],'--local-validator-overlay-sha256',spec['fileSha256']] if spec else []

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
    wide_sql="SELECT d.legacy_object_path,r.external_key,r.locator,s.source_record_id,s.revision_id,s.match_id,s.player_id,s.team_id,s.match_player_revision_id,s.source_id,s.period_code,s.period_definition_version,s.variant_key,s.recorded_from_gen,"+columns+",ma.public_key,pa.public_key,ta.public_key FROM football.player_match_stats s JOIN ingest.source_records r ON r.id=s.source_record_id JOIN ingest.source_documents d ON d.id=r.document_id JOIN ingest.public_aliases_current ma ON ma.route_kind='match' AND ma.match_id=s.match_id JOIN ingest.public_aliases_current pa ON pa.route_kind='player' AND pa.player_id=s.player_id JOIN ingest.public_aliases_current ta ON ta.route_kind='team' AND ta.team_id=s.team_id WHERE s.is_canonical AND s.recorded_to_gen IS NULL ORDER BY s.source_record_id"
    wide=list(conn.execute(wide_sql));by_record={};errors=Counter();source_states=Counter();typed_states=Counter();source_hash=hashlib.sha256();typed_hash=hashlib.sha256()
    for row in wide:
        key=(row[0],row[1])
        if key not in wanted:errors['unexpected_wide_identity']+=1;continue
        ordinal,source=wanted[key]
        if row[2]!='/tables/performances/rows/'+str(ordinal):errors['performance_locator']+=1
        if row[-3:]!=(source['matchId'],source['playerId'],source['teamId']):errors['source_provider_identity_binding']+=1
        if row[10:13]!=(MANIFEST['coreContext']['period'],MANIFEST['coreContext']['periodDefinitionVersion'],MANIFEST['coreContext']['variant']):errors['common_period_variant']+=1
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
    record_sql="SELECT r.locator,r.source_id,d.source_id,d.legacy_object_path FROM ingest.source_records r JOIN ingest.source_documents d ON d.id=r.document_id WHERE d.legacy_object_path=%s ORDER BY r.locator"
    records=list(conn.execute(record_sql,(n['path'],)));wanted_locators=sorted(['']+list(expected)+['/data/players','/data/teams'])
    if [r[0] for r in records]!=wanted_locators or any(r[1]!=r[2] for r in records):errors['root_collection_slot_source_records']+=1
    result={'expectedParents':len(expected),'typedParents':len(rows),'expectedTriplets':count,'typedCells':observed_cells,'historical1344Confirmed':count==1344,'sourceSha256':digest(source_rows),'typedSha256':digest(typed_rows),'errors':dict(errors),'sql':{'parents':sql,'cells':'SELECT cell_ordinal,column_index,row_index,action_count FROM football.match_heatmap_cells WHERE heatmap_id=%s ORDER BY cell_ordinal','slots':slot_sql,'sourceRecords':record_sql},'sourceRecordLocators':[r[0] for r in records],'slots':slots,'nameShirtFullFidelityAccepted':False}
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

def resource_error_guard(run,pg_bin):
    """Real capture branch + verbatim NEON_SQL on a separate metadata-only PG."""
    import psycopg
    from psycopg.types.json import Jsonb
    from harness import LocalPostgres
    evidence=run/'resource-error-guard';evidence.mkdir();pg=LocalPostgres(pg_bin,evidence);admin=None
    cap=load('actual_capture_resource_error',DOC/'capture.py');normalizer_before=sha(NORMALIZER);source_budget_before=sha(DOC/'budget.json')
    result={'scope':'separate owned LOCAL PostgreSQL metadata fixtures; no real source or sports candidate writes','sourceCalls':0,'httpRequests':0,'captureSha256':sha(DOC/'capture.py'),'neonSql':cap.NEON_SQL,'neonSqlSha256':hashlib.sha256(cap.NEON_SQL.encode()).hexdigest(),'cases':[]}
    try:
        pg.start();pg.migration(REPO);admin=psycopg.connect(pg.dsn,autocommit=True)
        admin.execute('CREATE SCHEMA statarena')
        admin.execute('CREATE TABLE statarena.objects(path text PRIMARY KEY,size bigint NOT NULL,sha256 bytea NOT NULL,updated_at timestamptz NOT NULL)')
        admin.execute("CREATE TABLE statarena.resources(endpoint text NOT NULL,params text NOT NULL,status smallint NOT NULL,ref jsonb,error jsonb,updated_at timestamptz NOT NULL,PRIMARY KEY(endpoint,params))")
        admin.execute('GRANT USAGE ON SCHEMA statarena TO orion_pro_ingest');admin.execute('GRANT SELECT ON ALL TABLES IN SCHEMA statarena TO orion_pro_ingest')
        n=MANIFEST['neon'];updated=datetime(2020,1,1,tzinfo=timezone.utc)
        admin.execute('INSERT INTO statarena.objects VALUES(%s,%s,%s,%s)',(n['path'],n['physicalBytes'],bytes.fromhex(n['physicalSha256']),updated))
        fixtures=[('sql_null',None,200,True),('json_null','null',200,True),('object','{"synthetic_error":"present"}',200,False),('empty_object','{}',200,False),('string','"synthetic_error"',200,False),('empty_string','""',200,False),('false','false',200,False),('true','true',200,False),('empty_array','[]',200,False),('array','[1]',200,False),('zero','0',200,False),('number','1',200,False),('status404_sql_null',None,404,False),('status404_json_null','null',404,False)]
        original_execute=cap.execute;observed={};reached=[];aws_calls=[]
        m=json.loads(json.dumps(MANIFEST));m['neon'].update(database='postgres',user='orion_pro_ingest')
        def local_connect(origin,manifest,private):
            if origin=='aws':
                class MetadataOnly:
                    def rollback(self):pass
                    def close(self):pass
                return MetadataOnly()
            connection=psycopg.connect(pg.dsn,options=cap.OPTIONS,autocommit=False);connection.execute('SET ROLE orion_pro_ingest');return connection
        def local_verify(connection,origin,manifest,row):
            if origin=='neon':assert row[:6]==('postgres','orion_pro_ingest','on','repeatable read','8s','1s')
        def execute_adapter(connection,budget,origin,name,sql,params=(),body_column=None):
            if origin=='neon':
                assert sql==cap.NEON_SQL,'Must execute actual NEON_SQL, not a substitute'
                rows=original_execute(connection,budget,origin,name,sql,params,body_column);observed.update(flag=rows[0][14],localIdentity=rows[0][:6]);return rows
            aws_calls.append(name)
            if name=='identity':return [('statarena_prod','statarena_ingest','on','repeatable read','8s','1s','synthetic_control_plane_snapshot',updated,True)]
            if name=='three_exact_current_indexed_documents':
                pointers=m['aws']['partitions'];docs=[(m['aws']['manifest']['path'],m['aws']['manifest']['physicalSha256'],{'pointers':pointers})]+[(p['path'],p['sha256'],{'tables':{'players':{'keys':['playerId'],'rows':[]},'teams':{'keys':['id'],'rows':[]}}}) for p in pointers]
                return [(path,h,'ready',0,0,updated,json.dumps(body)) for path,h,body in docs]
            if name=='exact_scoped_profile_resource_metadata':return [('[]',0,2)]
            raise AssertionError('Unexpected synthetic AWS control-plane request')
        def no_http(manifest,budget,private):
            reached.append(True);return {'data':{'match_id':n['matchId'],'grid':{'frame':n['frame']}}},{'head':{'VersionId':None},'sourceUrl':'https://synthetic-control-plane.invalid/no-request'}
        cap.connect=local_connect;cap.verify_connection=local_verify;cap.execute=execute_adapter;cap.neon_object=no_http
        for label,literal,status,expected in fixtures:
            admin.execute('DELETE FROM statarena.resources')
            error=None if literal is None else Jsonb(json.loads(literal))
            admin.execute('INSERT INTO statarena.resources VALUES(%s,%s,%s,%s,%s,%s)',(n['endpoint'],n['params'],status,Jsonb({'path':n['path']}),error,updated))
            ledger=evidence/('local-'+label+'-budget.json');ledger.write_text(json.dumps(initial_budget())+'\n');budget=cap.Budget(ledger,expected_selects=0,expected_decoded_bytes=0);budget.claim();reached.clear();observed.clear();aws_calls.clear();reason=None
            try:
                snapshot=cap.capture(m,budget,{});snapshot.clear();accepted=True
            except cap.CaptureError as error:accepted=False;reason=str(error)
            assert accepted==bool(reached),'HTTP reach sentinel must reflect actual capture branch'
            budget.finish('local_fixture_complete')
            result['cases'].append({'case':label,'jsonErrorLiteral':literal,'status':status,'expectedAccepted':expected,'actualAccepted':accepted,'passed':accepted==expected,'projectedErrorFlag':observed['flag'],'actualLocalIdentity':observed['localIdentity'],'httpSentinelReached':bool(reached),'actualHttpRequests':0,'reason':reason,'actualNeonSqlExecuted':True,'awsFixtureCalls':list(aws_calls)})
        result['mismatches']=[c['case'] for c in result['cases'] if not c['passed']];result['status']='pass' if not result['mismatches'] else 'fail'
        return result
    finally:
        if admin:admin.close()
        result['cleanup']=pg.cleanup();result['normalizerUnchanged']=sha(NORMALIZER)==normalizer_before;result['failedSourceBudgetUnchanged']=sha(DOC/'budget.json')==source_budget_before
        (evidence/'result.json').write_text(json.dumps(result,indent=2,default=str)+'\n')

def local_writer_deadlines(conn,pg,run):
    """Actual local settings, actual candidate gate and fresh exec worker."""
    import psycopg
    candidate=load('actual_candidate_deadline_gate',DOC/'candidate.py');before=fingerprint(conn);outcomes=[];mismatches=[]
    sql="SELECT current_user,current_setting('statement_timeout'),current_setting('lock_timeout')"
    actual=conn.execute(sql).fetchone();main_ok=actual==('orion_pro_ingest','8s','1s')
    outcomes.append({'case':'main_writer','expected':['orion_pro_ingest','8s','1s'],'actual':actual,'passed':main_ok})
    if not main_ok:mismatches.append('main_writer')
    for statement,lock in [('0','1s'),('7s','1s'),('9s','1s'),('8s','0'),('8s','999ms'),('8s','2s')]:
        with psycopg.connect(pg.dsn,options='-c statement_timeout='+statement+' -c lock_timeout='+lock,autocommit=True) as local:
            local.execute('SET ROLE orion_pro_ingest');settings=local.execute(sql).fetchone();refused=False;reason=None
            try:candidate.import_candidate(local,run,{})
            except candidate.CandidateError as error:refused=True;reason=str(error)
            ok=refused and reason=='Local candidate requires statement_timeout=8s and lock_timeout=1s before writes'
            label='nonconforming:'+statement+':'+lock;outcomes.append({'case':label,'actual':settings,'refused':refused,'reason':reason,'passed':ok})
            if not ok:mismatches.append(label)
    with psycopg.connect(pg.dsn,options='-c statement_timeout=8000 -c lock_timeout=1000',autocommit=True) as local:
        local.execute('SET ROLE orion_pro_ingest');reason=None
        try:candidate.import_candidate(local,run,{})
        except candidate.CandidateError as error:reason=str(error)
        ok=reason=='Candidate source manifest/normalizer binding differs';outcomes.append({'case':'compliant_reaches_source_binding','actual':local.execute(sql).fetchone(),'reason':reason,'passed':ok})
        if not ok:mismatches.append('compliant_reaches_source_binding')
    with psycopg.connect(pg.dsn,options='-c statement_timeout=8000 -c lock_timeout=1000',autocommit=True) as local:
        reason=None
        try:candidate.import_candidate(local,run,{})
        except candidate.CandidateError as error:reason=str(error)
        ok=reason=='Candidate requires actual ingest role on an owned LOCAL PostgreSQL connection';outcomes.append({'case':'wrong_role_refused','actual':local.execute(sql).fetchone(),'reason':reason,'passed':ok})
        if not ok:mismatches.append('wrong_role_refused')
    command=[sys.executable,str(Path(__file__)),'--worker','--deadlines-only','--evidence',str(run)];env=os.environ.copy();env.update(ORION_PILOT_DATABASE_URL=pg.dsn,STATARENA_SOURCE_FORBIDDEN='1');worker=subprocess.run(command,text=True,capture_output=True,env=env,timeout=30)
    (run/'deadline-worker.stdout.log').write_text(worker.stdout);(run/'deadline-worker.stderr.log').write_text(worker.stderr)
    worker_value=json.loads(worker.stdout) if worker.returncode==0 else None;worker_ok=worker.returncode==0 and worker_value.get('writerSettings')=={'host':'127.0.0.1','role':'orion_pro_ingest','statementTimeout':'8s','lockTimeout':'1s'} and worker_value.get('sourceCalls')==0
    outcomes.append({'case':'fresh_exec_worker','command':command,'exitCode':worker.returncode,'actual':worker_value,'passed':worker_ok})
    if not worker_ok:mismatches.append('fresh_exec_worker')
    after=fingerprint(conn);unchanged=before==after
    if not unchanged:mismatches.append('candidate_tables_changed')
    result={'scope':'owned LOCAL database,metadata/settings only; no source or synthetic sports rows','status':'pass' if not mismatches else 'fail','sql':sql,'outcomes':outcomes,'mismatches':mismatches,'before':before,'after':after,'unchanged':unchanged,'sourceCalls':0,'syntheticSportsRowsInserted':0}
    (run/'local-deadlines-result.json').write_text(json.dumps(result,indent=2,default=str)+'\n');return result

def local_overlay_contract(run,pg_bin):
    allowed=REPO/'docs/verification/orion-validator-membership-20261105/candidate.sql';expected='e0810f8670b2cb627ade2c76e3c8eb527ab31fd595d5cf939fd63bfc5cf649d6';folder=run/'overlay-cli';folder.mkdir();copy=folder/'arbitrary-copy.sql';shutil.copy2(allowed,copy);alias=folder/'alias.sql';alias.symlink_to(allowed)
    base=[sys.executable,str(Path(__file__)),'--prepare-only','--overlay-probe-only','--pg-bin',str(pg_bin)];outcomes=[];mismatches=[];values={}
    cases=[('default',[],True),('allowed',['--local-validator-overlay',str(allowed),'--local-validator-overlay-sha256',expected],True),('arbitrary-copy',['--local-validator-overlay',str(copy),'--local-validator-overlay-sha256',expected],False),('symlink-alias',['--local-validator-overlay',str(alias),'--local-validator-overlay-sha256',expected],False),('wrong-hash',['--local-validator-overlay',str(allowed),'--local-validator-overlay-sha256','0'*64],False),('missing-hash',['--local-validator-overlay',str(allowed)],False),('missing-path',['--local-validator-overlay-sha256',expected],False)]
    for label,flags,positive in cases:
        command=base+['--label','local-overlay-probe-'+label]+flags;env=os.environ.copy();env['STATARENA_SOURCE_FORBIDDEN']='1';result=subprocess.run(command,text=True,capture_output=True,env=env,timeout=120);(folder/(label+'.stdout.log')).write_text(result.stdout);(folder/(label+'.stderr.log')).write_text(result.stderr);actual=None;ok=result.returncode==0 if positive else result.returncode==2
        result_evidence=None
        if positive and result.returncode==0:
            final=json.loads(result.stdout.strip().splitlines()[-1]);result_evidence=str(Path(final['evidence'])/'result.json');actual=json.loads(Path(result_evidence).read_text());values[label]=actual;policy=actual['validatorPolicy'];probe=next(c['actual'] for c in actual['cases'] if c['case']=='local_overlay_probe');ok=actual['counts']=={'pass':1,'fail':0,'unverified':0} and not any(probe['businessRows'].values()) and probe['sourceCalls']==0
            ok=ok and policy['policy']==('sealed_013' if label=='default' else 'local_candidate_membership_e0810f') and policy['overlayApplied']==(label=='allowed')
            if label=='allowed':ok=ok and policy['protectedMetadataPreserved'] and policy['otherFunctionsUnchanged'] and policy['businessTablesUnchanged'] and policy['before']['pgProcRowSha256']!=policy['after']['pgProcRowSha256'] and probe.get('overlayWorkerVerified') is True
        elif not positive and result.returncode==2:
            try:refusal=json.loads(result.stdout.strip());ok=refusal.get('status')=='local_overlay_refused' and refusal.get('pgStarted') is False
            except (ValueError,AttributeError):ok=False
        if not ok:mismatches.append(label)
        outcomes.append({'case':label,'command':command,'expectedAccepted':positive,'exitCode':result.returncode,'passed':ok,'resultEvidence':result_evidence})
    report={'scope':'source-free CLI and owned PG overlay policy only','status':'pass' if not mismatches else 'fail','cases':outcomes,'mismatches':mismatches,'newSourceCalls':0};(run/'local-overlay-contract.json').write_text(json.dumps(report,indent=2)+'\n');return report

def worker_dsn_preconnect_boundary(run):
    folder=run/'worker-dsn-tripwire';folder.mkdir();site=folder/'sitecustomize.py'
    site.write_text("import os\nfrom pathlib import Path\nimport psycopg\ndef no_network_connect(*args,**kwargs):\n    Path(os.environ['ORION_CONNECT_TRIPWIRE']).write_text('driver_connect_attempted\\n')\n    raise RuntimeError('local_worker_connect_tripwire_no_network')\npsycopg.connect=no_network_connect\n")
    secret='explicit_synthetic_dsn_secret';suffix=' dbname=unconnected user=synthetic_worker password='+secret
    cases=[('external_uri','postgresql://synthetic_worker:'+secret+'@remote.invalid/unconnected',None),('missing_host','dbname=unconnected user=synthetic_worker password='+secret,None),('empty_host',"host=''"+suffix,None),('multihost','host=127.0.0.1,remote.invalid'+suffix,None),('all_loopback_multihost','host=127.0.0.1,localhost'+suffix,None),('external_hostaddr','host=localhost hostaddr=192.0.2.10'+suffix,None),('mismatched_v4_v6','host=127.0.0.1 hostaddr=::1'+suffix,None),('mismatched_v6_v4','host=::1 hostaddr=127.0.0.1'+suffix,None),('multihostaddr','host=localhost hostaddr=127.0.0.1,::1'+suffix,None),('empty_hostaddr',"host=localhost hostaddr=''"+suffix,None),('external_env_hostaddr','host=127.0.0.1'+suffix,'198.51.100.10'),('unix_socket','host=/tmp/unconnected-local-socket'+suffix,None),('malformed_uri','postgresql://%'+secret,None)]
    outcomes=[];mismatches=[]
    for label,dsn,env_addr in cases:
        marker=folder/(label+'.marker');env=os.environ.copy();env.update(PYTHONPATH=str(folder)+os.pathsep+env.get('PYTHONPATH',''),PYTHONDONTWRITEBYTECODE='1',ORION_PILOT_DATABASE_URL=dsn,ORION_CONNECT_TRIPWIRE=str(marker),STATARENA_SOURCE_FORBIDDEN='1');env.pop('PGHOSTADDR',None)
        if env_addr is not None:env['PGHOSTADDR']=env_addr
        command=[sys.executable,str(Path(__file__)),'--worker','--deadlines-only','--evidence',str(run)];result=subprocess.run(command,text=True,capture_output=True,env=env,timeout=20);no_secret=secret not in result.stdout and secret not in result.stderr
        if no_secret:(folder/(label+'.stdout.log')).write_text(result.stdout);(folder/(label+'.stderr.log')).write_text(result.stderr)
        else:(folder/(label+'.output-redacted.json')).write_text(json.dumps({'stdoutBytes':len(result.stdout.encode()),'stderrBytes':len(result.stderr.encode()),'stdoutSha256':hashlib.sha256(result.stdout.encode()).hexdigest(),'stderrSha256':hashlib.sha256(result.stderr.encode()).hexdigest(),'secretFound':True})+'\n')
        try:refusal=json.loads(result.stdout.strip())
        except ValueError:refusal={}
        ok=result.returncode==2 and refusal.get('status')=='local_worker_dsn_refused' and refusal.get('driverConnectAttempted') is False and not marker.exists() and no_secret
        if not ok:mismatches.append(label)
        outcomes.append({'case':label,'command':command,'exitCode':result.returncode,'driverConnectTripwireReached':marker.exists(),'secretAbsentFromOutput':no_secret,'passed':ok,'actualNetworkAttempts':0})
    report={'status':'pass' if not mismatches else 'fail','scope':'genuine worker CLI subprocess + driver tripwire; no external connection','cases':outcomes,'mismatches':mismatches,'actualNetworkAttempts':0,'sourceCalls':0};(run/'worker-dsn-boundary.json').write_text(json.dumps(report,indent=2)+'\n');return report

def main():
    p=argparse.ArgumentParser();p.add_argument('--label',default='prepare');p.add_argument('--prepare-only',action='store_true');p.add_argument('--source-socket',type=Path);p.add_argument('--worker',action='store_true');p.add_argument('--deadlines-only',action='store_true');p.add_argument('--evidence',type=Path);p.add_argument('--local-validator-overlay',type=Path);p.add_argument('--local-validator-overlay-sha256');p.add_argument('--overlay-probe-only',action='store_true');p.add_argument('--pg-bin',type=Path,default=Path('/tmp/statarena-cache-test-tools/node_modules/@embedded-postgres/darwin-arm64/native/bin'));args=p.parse_args()
    if args.deadlines_only and not args.worker:p.error('--deadlines-only requires --worker')
    if args.overlay_probe_only and (not args.prepare_only or args.worker):p.error('--overlay-probe-only requires source-free preparation')
    try:overlay=local_overlay_choice(args.local_validator_overlay,args.local_validator_overlay_sha256)
    except (LocalOverlayError,OSError,UnicodeError) as error:
        print(json.dumps({'status':'local_overlay_refused','reason':str(error) if isinstance(error,LocalOverlayError) else type(error).__name__,'pgStarted':False}));return 2
    if args.worker:
        candidate=load('real_candidate_worker',DOC/'candidate.py')
        import psycopg
        try:worker_params=local_worker_parameters(os.environ.get('ORION_PILOT_DATABASE_URL',''))
        except LocalWorkerDSNError:
            print(json.dumps({'status':'local_worker_dsn_refused','reason':'Worker requires one explicit coherent loopback host/address','driverConnectAttempted':False,'sourceCalls':0}));return 2
        with psycopg.connect(**worker_params,autocommit=True) as conn:
            conn.execute('SET ROLE orion_pro_ingest')
            validator_policy={'policy':'sealed_013','overlayApplied':False}
            if overlay:
                expected=json.loads((args.evidence/'local-validator-overlay.json').read_text())['after'];installed=verify_local_overlay_installed(conn,overlay,expected);validator_policy={'policy':overlay['policy'],'overlayApplied':True,'installed':installed,'fileSha256':overlay['fileSha256'],'appliedSqlSha256':overlay['appliedSqlSha256']}
            if args.deadlines_only:
                result={'status':'pass','mode':'source_free_writer_deadlines','writerSettings':candidate.validate_local_writer(conn),'sourceCalls':0}
                if overlay:result['validatorPolicy']=validator_policy
                print(json.dumps(result));return 0
            cap=load('real_capture_worker',DOC/'capture.py');snapshot=cap.fetch_snapshot(args.source_socket);result=candidate.import_candidate(conn,args.evidence,snapshot)
        print(json.dumps({'status':'pass','coreReused':result['core']['reused'],'spatialReused':result['spatial'].get('reused',False),'sourceCalls':0,'validatorPolicy':validator_policy}));return 0
    if not args.prepare_only and args.source_socket is None:p.error('Explicit --prepare-only or --source-socket required; no source fallback')
    run=DOC/'runs'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-'+args.label);run.mkdir(parents=True);(run/'inputs').mkdir()
    for q in [Path(__file__),DOC/'PLAN.md',DOC/'PROTOCOL.md',DOC/'ERROR_GUARD_PROTOCOL.md',DOC/'LOCAL_DEADLINES_PROTOCOL.md',DOC/'LOCAL_VALIDATOR_OVERLAY_PROTOCOL.md',DOC/'MANIFEST.json',DOC/'FIELDS.json',DOC/'capture.py',DOC/'candidate.py',NORMALIZER,PILOT/'harness.py']:
        if q.exists():shutil.copy2(q,run/'inputs'/q.name)
    if overlay:(run/'inputs/local-validator-overlay.sql').write_bytes(overlay['raw'])
    old_ledger=REPO/MANIFEST['oldLedger']['path'];before_old=sha(old_ledger);assert before_old==MANIFEST['oldLedger']['sha256'];failed_budget_before=sha(DOC/'budget.json');root_metadata=DOC/'neon-error-metadata/result.json';root_metadata_before=sha(root_metadata)
    sys.path.insert(0,str(PILOT));from harness import LocalPostgres
    import psycopg
    pg=LocalPostgres(args.pg_bin,run);conn=None;blocked=None;snapshot=None;parts=None
    report={'command':'PYTHONPATH=/tmp/statarena-publication-test-python '+shlex.join([sys.executable,*sys.argv]),'environment':'owned LOCAL PG18.6; real candidate has source-derived facts only','normalizerSha256':sha(NORMALIZER),'testSha256':sha(Path(__file__)),'manifestSha256':sha(DOC/'MANIFEST.json'),'fullAcceptance':False,'sourceCallsByTest':0,'realNativeStatesCompared':0,'realTripletsCompared':0,'cases':[]}
    cases=['empty_local_bootstrap','worker_dsn_preconnect_boundary','local_validator_overlay_contract','local_writer_deadlines','source_startup_contract','future_captured_ledger_guard','capture_checkpoint_cli','global_budget_guards','profile_metadata_admission','private_origin_configuration','resource_error_null_contract','real_core_import','independent_native31','real_spatial_import_and_oracle','fresh_process_noop']
    if args.overlay_probe_only:cases=['local_overlay_probe']
    try:
        pg.start();pg.migration(REPO);report['validatorPolicy']={'policy':'sealed_013','overlayApplied':False}
        if overlay:
            with psycopg.connect(pg.dsn,options=WRITER_OPTIONS,autocommit=True) as admin:report['validatorPolicy']=apply_local_overlay(admin,overlay,run)
        conn=psycopg.connect(pg.dsn,options=WRITER_OPTIONS,autocommit=True);conn.execute('SET ROLE orion_pro_ingest')
        for case in cases:
            if blocked or (args.prepare_only and case.startswith(('real_','independent_','fresh_'))):report['cases'].append({'case':case,'status':'unverified','reason':blocked or 'Awaiting separately approved single real capture'});continue
            try:
                if case=='empty_local_bootstrap':
                    assert conn.execute('SELECT current_user').fetchone()[0]=='orion_pro_ingest';counts={t:conn.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in ['football.players','football.teams','football.matches','football.player_match_stats','football.match_heatmaps']};assert not any(counts.values());actual={'role':'orion_pro_ingest','businessRows':counts,'syntheticSportsRowsInserted':0}
                elif case=='worker_dsn_preconnect_boundary':
                    actual=worker_dsn_preconnect_boundary(run);assert actual['status']=='pass',{'preconnectDsnMismatches':actual['mismatches']}
                elif case=='local_overlay_probe':
                    counts={t:conn.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in ['football.players','football.teams','football.matches','football.player_match_stats','football.match_heatmaps']};assert not any(counts.values());actual={'validatorMetadata':validator_metadata(conn),'businessRows':counts,'sourceCalls':0,'writerSettings':load('probe_candidate_deadline',DOC/'candidate.py').validate_local_writer(conn)}
                    if overlay:
                        verify_local_overlay_installed(conn,overlay,report['validatorPolicy']['after']);command=[sys.executable,str(Path(__file__)),'--worker','--deadlines-only','--evidence',str(run),*overlay_flags(overlay)];env=os.environ.copy();env.update(ORION_PILOT_DATABASE_URL=pg.dsn,STATARENA_SOURCE_FORBIDDEN='1');worker=subprocess.run(command,text=True,capture_output=True,env=env,timeout=30);(run/'overlay-worker.stdout.log').write_text(worker.stdout);(run/'overlay-worker.stderr.log').write_text(worker.stderr);assert worker.returncode==0,'Overlay worker refused the installed candidate';value=json.loads(worker.stdout);assert value['validatorPolicy']['installed']==report['validatorPolicy']['after'] and value['validatorPolicy']['policy']==overlay['policy'] and value['writerSettings']=={'host':'127.0.0.1','role':'orion_pro_ingest','statementTimeout':'8s','lockTimeout':'1s'} and value['sourceCalls']==0
                        actual.update(overlayWorkerVerified=True,overlayWorker=value,workerCommand=command)
                elif case=='local_validator_overlay_contract':
                    actual=local_overlay_contract(run,args.pg_bin);assert actual['status']=='pass',{'localOverlayMismatches':actual['mismatches']}
                elif case=='local_writer_deadlines':
                    actual=local_writer_deadlines(conn,pg,run);assert actual['status']=='pass',{'localDeadlineMismatches':actual['mismatches']}
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
                elif case=='resource_error_null_contract':
                    actual=resource_error_guard(run,args.pg_bin);assert actual['status']=='pass',{'realCaptureGuardMismatches':actual.get('mismatches')}
                elif case=='real_core_import':
                    cap=load('approved_real_capture',DOC/'capture.py');candidate=load('approved_real_candidate',DOC/'candidate.py');snapshot=cap.fetch_snapshot(args.source_socket);parts=unpack_independent(snapshot);actual=candidate.import_candidate(conn,run,snapshot,core_only=True);assert not actual['core']['reused'];report['sourceCaptureBudget']=snapshot['captureBudget'];report['sourceMemberCounts']={t:sum(len(x['tables'].get(t,[])) for x in parts) for t in ['fixtures','matches','performances','shots']}
                elif case=='independent_native31':
                    actual,ok=native_oracle(conn,parts);report['realNativeStatesCompared']=actual['typedSlots'];assert ok,{'errors':actual['errors'],'expectedSlots':actual['expectedSlots'],'typedSlots':actual['typedSlots']}
                elif case=='real_spatial_import_and_oracle':
                    result=candidate.import_candidate(conn,run,snapshot);actual,ok=spatial_oracle(conn,snapshot);actual['phaseReceipt']=result['spatial'];report['realTripletsCompared']=actual['typedCells'];assert ok,actual['errors']
                else:
                    before=fingerprint(conn);command=[sys.executable,str(Path(__file__)),'--worker','--source-socket',str(args.source_socket),'--evidence',str(run),*overlay_flags(overlay)];env=os.environ.copy();env['ORION_PILOT_DATABASE_URL']=pg.dsn
                    result=subprocess.run(command,text=True,capture_output=True,env=env,timeout=600);(run/'fresh-worker.stdout.log').write_text(result.stdout);(run/'fresh-worker.stderr.log').write_text(result.stderr);after=fingerprint(conn);assert result.returncode==0 and before==after;worker=json.loads(result.stdout);assert worker['coreReused'] and worker['spatialReused'];actual={'command':command,'worker':worker,'before':before,'after':after,'unchanged':True}
                report['cases'].append({'case':case,'status':'pass','actual':actual});print('PASS '+case,flush=True)
            except Exception as error:
                report['cases'].append({'case':case,'status':'fail','error':str(error) if isinstance(error,AssertionError) else type(error).__name__,'sqlstate':getattr(error,'sqlstate',None)});print('FAIL '+case+': '+type(error).__name__,flush=True);blocked='Prerequisite '+case+' failed'
    finally:
        if conn:conn.close()
        report['cleanup']=pg.cleanup();report['oldLedgerByteIdentical']=sha(old_ledger)==before_old;report['failedSourceBudgetByteIdentical']=sha(DOC/'budget.json')==failed_budget_before;report['rootMetadataReceiptByteIdentical']=sha(root_metadata)==root_metadata_before;assert report['oldLedgerByteIdentical'] and report['failedSourceBudgetByteIdentical'] and report['rootMetadataReceiptByteIdentical'];report['counts']={s:sum(c['status']==s for c in report['cases']) for s in ['pass','fail','unverified']};report['status']='fail' if report['counts']['fail'] else 'prepared_real_unverified' if args.prepare_only else 'pass';(run/'result.json').write_text(json.dumps(report,indent=2,default=str)+'\n');print(json.dumps({'status':report['status'],'counts':report['counts'],'evidence':str(run)}),flush=True)
    return 1 if report['status']=='fail' else 0
if __name__=='__main__':raise SystemExit(main())
