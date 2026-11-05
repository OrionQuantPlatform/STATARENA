#!/usr/bin/env python3
"""Independent metadata-only census of the already captured RAM; no SQL or HTTP."""
from __future__ import annotations
import hashlib,importlib.util,json,math,os,sys
from collections import Counter,defaultdict
from datetime import datetime,timezone
from decimal import Decimal
from pathlib import Path

sys.dont_write_bytecode=True
DOC=Path(__file__).resolve().parent
REPO=DOC.parents[2]
SOCKET=Path('/tmp/orion-real-native-spatial-20261105-v2/source.sock')
ABSENT=object()
SIGNED={'rating','goalsPrevented'}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value

def decimal_text(value):
    sign,digits,exponent=value.as_tuple()
    if not any(digits):return '0'
    text=''.join(map(str,digits))
    if exponent>=0:number=text+'0'*exponent
    else:
        point=len(text)+exponent
        integer,fraction=(text[:point],text[point:]) if point>0 else ('0','0'*(-point)+text)
        fraction=fraction.rstrip('0');number=integer+('.'+fraction if fraction else '')
    return ('-' if sign else '')+number

def native(value):
    if value is ABSENT:return ['absent']
    if value is None:return ['null']
    if isinstance(value,bool):return ['boolean',value]
    if isinstance(value,str):return ['string',value]
    if isinstance(value,(int,Decimal)) and not isinstance(value,bool):
        number=Decimal(value)
        return ['number',decimal_text(number)] if number.is_finite() else ['nonfinite_number']
    return ['unsupported_'+type(value).__name__]

def feed(target,value):target.update(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()+b'\n')
def digest(values):
    out=hashlib.sha256()
    for value in values:feed(out,value)
    return out.hexdigest()

def numeric_reason(value,sql_type,field):
    if not isinstance(value,(int,Decimal)) or isinstance(value,bool):return None
    number=Decimal(value)
    if not number.is_finite():return 'nonfinite_numeric'
    if field not in SIGNED and number<0:return 'negative_contract'
    if sql_type=='integer':
        if number!=number.to_integral_value():return 'fractional_int32'
        if not 0<=number<2**31:return 'int32_range'
    elif sql_type=='double precision':
        try:floating=float(number)
        except (OverflowError,ValueError):return 'double_nonfinite'
        if not math.isfinite(floating):return 'double_nonfinite'
        if Decimal(str(floating))!=number:return 'double_round_trip'
    elif sql_type!='numeric':return 'unknown_projection_contract'
    return None

def leaf_states(value,path='$'):
    if isinstance(value,dict):
        if not value:yield path,'empty_object'
        for key,child in value.items():yield from leaf_states(child,path+'.'+str(key))
    elif isinstance(value,list):
        if not value:yield path,'empty_list'
        for child in value:yield from leaf_states(child,path+'[]')
    else:
        token=native(value);kind=token[0]
        if kind=='string' and value=='':kind='empty_string'
        yield path,kind

def main():
    cap=module('capture_ram_inspection',DOC/'capture.py');oracle=module('independent_source_oracle',DOC/'e2e.py');manifest=json.loads((DOC/'MANIFEST.json').read_text());fields=json.loads((DOC/'FIELDS.json').read_text())['fields']
    tracked=[DOC/'budget-v2.json',DOC/'budget.json',REPO/'docs/verification/orion-pro-pilot-20261104/real-source-budget.json',DOC/'capture.py',DOC/'candidate.py',DOC/'e2e.py',REPO/'dashboard/scripts/orion_pro_normalize.py']
    before={str(p):sha(p) for p in tracked};snapshot=cap.fetch_snapshot(SOCKET);parts=oracle.unpack_independent(snapshot)
    report={'atUtc':datetime.now(timezone.utc).isoformat(),'kind':'SOURCE_ONLY_RAM_INSPECTION_V2','command':'PYTHONPATH=/tmp/statarena-publication-test-python python3 docs/verification/orion-pro-real-native-spatial-20261104/inspect_ram_v2.py','inspectorSha256':sha(Path(__file__)),'captureBudget':snapshot['captureBudget'],'sourceOrigins':snapshot['sourceIdentity'],'manifestSha256':snapshot['manifestSha256'],'sourceDocumentCount':len(snapshot['cache']),'sourceDocuments':[{'path':p,'origin':snapshot['meta'][p]['origin'],'physicalSha256':snapshot['meta'][p]['physicalSha256'],'decodedCanonicalSha256':snapshot['meta'][p]['decodedCanonicalSha256']} for p in sorted(snapshot['cache'])],'independentDecoderSha256':sha(DOC/'e2e.py'),'fieldRegistrySha256':sha(DOC/'FIELDS.json'),'newRemoteSelects':0,'newHttpRequests':0,'typedNativeStatesCompared':0,'typedHeatmapCellsCompared':0,'pgImportExecuted':False,'fullAcceptance':False}
    report['partitions']=[{'season':p['season'],'path':p['path'],'tableRowCounts':{t:len(rows) for t,rows in sorted(p['tables'].items())}} for p in parts]
    table_rows=defaultdict(list)
    for part in parts:
        for name,rows in part['tables'].items():table_rows[name].extend(rows)
    fixtures={str(r['id']):r for r in table_rows['fixtures']};finished={str(r['id']) for r in table_rows['matches']};players={r['playerId'] for r in table_rows['players']};teams={r['id'] for r in table_rows['teams']}
    report['sourceCounts']={t:len(table_rows[t]) for t in ['fixtures','matches','performances','shots','players','teams']}
    report['identityCounts']={'uniqueFixtureIds':len(fixtures),'uniqueFinishedMatchIds':len(finished),'uniquePlayerIds':len(players),'uniqueTeamIds':len(teams)}
    report['identityDigests']={'fixtures':digest(sorted(fixtures)),'finishedMatches':digest(sorted(finished)),'players':digest(sorted(players)),'teams':digest(sorted(teams))}
    report['identityGaps']={'normalizedMatchesWithoutFixtureIds':sorted(finished-set(fixtures)),'fixturesWithoutNormalizedFinishedMatchCount':len(set(fixtures)-finished)}
    profile_metadata=snapshot['profile_metadata'];report['profileLookup']={'resourceRows':len(profile_metadata),'exactPlayerLookupGapCount':len(snapshot['profile_gaps']),'exactPlayerLookupGapIds':snapshot['profile_gaps'],'profileBodyCountCaptured':0,'meaning':'Exact lookup quality gap only; no global biography/source loss inferred'}
    states={f['sourceField']:Counter() for f in fields};numeric_meta={f['sourceField']:{'numericObservations':0,'maximumDecimalPlaces':0,'maximumIntegerDigits':0} for f in fields};special={f['sourceField']:Counter() for f in fields};blocked=[];pairs=[];h=hashlib.sha256();member_keys=[];participants=defaultdict(list)
    for part in parts:
        for ordinal,row in enumerate(part['tables']['performances']):
            identity={'sourcePath':part['path'],'sourceOrdinal':ordinal,'performanceId':str(row['id']),'matchId':row['matchId'],'playerId':row['playerId'],'teamId':row['teamId']};member_keys.append([part['path'],str(row['id'])]);participants[(row['matchId'],row['playerId'])].append(row['teamId'])
            for field in fields:
                name=field['sourceField'];raw=row.get(name,ABSENT);token=native(raw);kind=token[0];states[name][kind]+=1;feed(h,[part['path'],str(row['id']),name,token]);reason=None
                if kind=='number':
                    number=Decimal(raw);item=numeric_meta[name];item['numericObservations']+=1;item['maximumDecimalPlaces']=max(item['maximumDecimalPlaces'],max(0,-number.as_tuple().exponent));item['maximumIntegerDigits']=max(item['maximumIntegerDigits'],max(1,number.adjusted()+1));special[name]['zero']+=number==0;reason=numeric_reason(raw,field['commonSqlType'],name)
                elif kind=='string':special[name]['emptyString']+=raw==''
                elif kind=='boolean':special[name]['false' if raw is False else 'true']+=1
                elif kind not in ('absent','null'):reason='unsupported_native_kind'
                if reason:blocked.append({**identity,'field':name,'commonSqlType':field['commonSqlType'],'nativeKind':kind,'reason':reason})
            for complete,attempt in [('passesAccurate','passesAttempted'),('aerialsWon','aerialDuels'),('dribbles','dribblesAttempted')]:
                a,b=row.get(complete),row.get(attempt)
                if native(a)[0]=='number' and native(b)[0]=='number' and Decimal(a)>Decimal(b):pairs.append({**identity,'fields':[complete,attempt],'reason':'completed_greater_than_attempted'})
    slots=sum(sum(c.values()) for c in states.values());aggregate=sum(states.values(),Counter())
    report['native31']={'performanceRows':len(table_rows['performances']),'registeredFields':len(fields),'sourceSlotsInspected':slots,'historical478547Confirmed':slots==478547,'states':{k:aggregate[k] for k in sorted(set(aggregate)|{'absent','null','number','string','boolean'})},'specialObservationCounts':{k:sum(c[k] for c in special.values()) for k in ['zero','emptyString','false','true']},'perField':[{'field':f['sourceField'],'commonColumn':f['commonColumn'],'commonSqlType':f['commonSqlType'],'states':dict(states[f['sourceField']]),'specialCounts':dict(special[f['sourceField']]),'precisionMetadata':numeric_meta[f['sourceField']]} for f in fields],'sourceSlotSha256':h.hexdigest(),'sourceMemberIdsSha256':digest(sorted(member_keys)),'duplicatePerformanceIdCount':len(member_keys)-len({tuple(k) for k in member_keys}),'unrepresentableCount':len(blocked),'unrepresentable':blocked,'commonCountPairViolationCount':len(pairs),'commonCountPairViolations':pairs,'representabilityPass':not blocked and not pairs,'sqlStorageVerified':False,'unitContract':'source_native; no provider-unit semantic reconciliation claimed'}
    n=manifest['neon'];data=snapshot['cache'][n['path']]['data'];grid=data.get('grid',{});mid=n['matchId'];fixture=fixtures.get(mid);parent_count=0;cell_count=0;by_kind={};spatial_gaps=[];cohort_gaps=[];side_gaps=[];zero=Counter();cell_hash=hashlib.sha256();parent_hash=hashlib.sha256();seen_parents=set();parent_ids=defaultdict(set)
    def spatial_issue(kind,index,reason,**meta):spatial_gaps.append({'collection':kind,'sourceOrdinal':index,'reason':reason,**meta})
    def exact_int(value):return isinstance(value,(int,Decimal)) and not isinstance(value,bool) and Decimal(value).is_finite() and Decimal(value)==Decimal(value).to_integral_value()
    columns=grid.get('length');rows=grid.get('width');dimensions_valid=exact_int(columns) and exact_int(rows) and 0<columns<32768 and 0<rows<32768
    if not dimensions_valid:spatial_gaps.append({'reason':'invalid_explicit_grid_dimensions'})
    if grid.get('frame') not in ('acting_ltr','home_ltr'):spatial_gaps.append({'reason':'unqualified_coordinate_frame'})
    metre_checks={k:{'nativeKind':native(grid.get(k,ABSENT))[0],'representable':native(grid.get(k,ABSENT))[0]=='number' and Decimal(grid[k])>0 and numeric_reason(grid[k],'double precision',k) is None} for k in ['cell_length_m','cell_width_m']}
    for key,value in metre_checks.items():
        if not value['representable']:spatial_gaps.append({'reason':'invalid_or_unrepresentable_grid_metres','field':key})
    for kind in ('teams','players'):
        collections=data.get(kind,ABSENT);state='absent' if collections is ABSENT else 'null' if collections is None else 'empty' if collections==[] else 'present';items=collections if isinstance(collections,list) else []
        by_kind[kind]={'collectionState':state,'parents':len(items),'triplets':0,'cellsStates':Counter(),'actionsKinds':Counter()}
        if collections is not ABSENT and collections is not None and not isinstance(collections,list):spatial_gaps.append({'collection':kind,'reason':'invalid_collection_kind'})
        for index,row in enumerate(items):
            parent_count+=1;tid=(row.get('team') or {}).get('id');pid=(row.get('player') or {}).get('id') if kind=='players' else None;side=row.get('side');locator='/data/'+kind+'/'+str(index)
            
            if (tid,pid) in seen_parents:spatial_issue(kind,index,'duplicate_logical_parent',teamId=tid,playerId=pid)
            seen_parents.add((tid,pid));parent_ids[kind].add((tid,pid))
            feed(parent_hash,[locator,tid,pid,native(row.get('actions',ABSENT))]);by_kind[kind]['actionsKinds'][native(row.get('actions',ABSENT))[0]]+=1
            if tid not in teams:cohort_gaps.append({'collection':kind,'sourceOrdinal':index,'teamId':tid,'reason':'team_identity_missing'})
            expected_tid=(fixture.get(side+'_team') or {}).get('id') if fixture and side in ('home','away') else None
            if tid!=expected_tid:side_gaps.append({'collection':kind,'sourceOrdinal':index,'teamId':tid,'reason':'side_does_not_match_normalized_fixture'})
            if kind=='players':
                observed=participants.get((mid,pid),[])
                if pid not in players:cohort_gaps.append({'collection':kind,'sourceOrdinal':index,'playerId':pid,'teamId':tid,'reason':'player_identity_missing'})
                if observed!=[tid]:cohort_gaps.append({'collection':kind,'sourceOrdinal':index,'playerId':pid,'teamId':tid,'normalizedPerformanceRows':len(observed),'normalizedTeamIds':sorted(observed),'reason':'normalized_participant_cohort_missing_or_ambiguous'})
            actions=row.get('actions',ABSENT)
            if actions is ABSENT or (actions is not None and (not exact_int(actions) or not 0<=actions<2**31)):spatial_issue(kind,index,'invalid_or_absent_actions')
            cells=row.get('cells',ABSENT);cell_state='absent' if cells is ABSENT else 'null' if cells is None else 'empty' if cells==[] else 'available';by_kind[kind]['cellsStates'][cell_state]+=1;seen=set()
            if cells is ABSENT or cells is None:continue
            if not isinstance(cells,list):spatial_issue(kind,index,'invalid_cells_kind');continue
            for ordinal,cell in enumerate(cells):
                cell_count+=1;by_kind[kind]['triplets']+=1
                if not isinstance(cell,list) or len(cell)!=3 or not all(exact_int(v) for v in cell):spatial_issue(kind,index,'invalid_sparse_triplet',cellOrdinal=ordinal);continue
                x,y,count=map(int,cell);feed(cell_hash,[locator,tid,pid,ordinal,[native(v) for v in cell]]);zero['columnZero']+=x==0;zero['rowZero']+=y==0;zero['actionZero']+=count==0
                if not dimensions_valid or not (0<=x<int(columns) and 0<=y<int(rows) and 0<=count<2**31):spatial_issue(kind,index,'sparse_coordinate_or_count_bounds',cellOrdinal=ordinal)
                if (x,y) in seen:spatial_issue(kind,index,'duplicate_sparse_coordinate',cellOrdinal=ordinal)
                seen.add((x,y))
    dispositions=Counter(leaf_states(data));useful_gaps=[{'path':p,'nativeState':state,'observations':count,'disposition':'qualified_unmapped_spatial_importer'} for (p,state),count in sorted(dispositions.items()) if '.name' in p or '.shirt_number' in p]
    report['heatmap']={'matchId':mid,'sourceDataRoot':'/data','expectedNormalizedFixturePresent':fixture is not None,'parentCollections':parent_count,'uniqueParentCounts':{k:len(v) for k,v in parent_ids.items()},'sparseTriplets':cell_count,'historical32Parents1344TripletsConfirmed':parent_count==32 and cell_count==1344,'collections':by_kind,'gridMetadata':{'columns':int(columns) if dimensions_valid else None,'rows':int(rows) if dimensions_valid else None,'coordinateFrame':grid.get('frame'),'dimensionsValid':dimensions_valid,'metreContracts':metre_checks},'zeroCoordinateActionCounts':dict(zero),'sourceOrderedCellsSha256':cell_hash.hexdigest(),'sourceParentObservationsSha256':parent_hash.hexdigest(),'sparseFormGapCount':len(spatial_gaps),'sparseFormGaps':spatial_gaps,'normalizedCohortGapCount':len(cohort_gaps),'normalizedCohortGaps':cohort_gaps,'sideGapCount':len(side_gaps),'sideGaps':side_gaps,'qualifiedUsefulFieldGaps':useful_gaps,'spatialShapePass':not spatial_gaps,'normalizedCohortPass':not cohort_gaps and not side_gaps,'typedFullFidelityAccepted':False}
    report['limitations']=['No typed SQL comparison or import has run.','Native numeric inventory is against indexed normalized JSON semantics,not original gzip lexical number spellings.','Original families beyond this one heatmap and full profile bodies remain outside the capture.','Name/shirt useful leaves remain qualified/unmapped.','No supplier freshness ordering inferred across AWS/Neon.','Large whole-seal8s performance review remains ROOT-owned.']
    after={str(p):sha(p) for p in tracked};assert before==after,'Read-only inspection changed a protected file';ready=json.loads((DOC/'capture-v2/capture.json').read_text());os.kill(ready['pid'],0);assert ready['ready'] and SOCKET.exists()
    report['immutability']={'trackedSha256':before,'unchanged':True};report['ramServer']={'pid':ready['pid'],'socket':str(SOCKET),'alive':True,'stopAuthorized':False};report['status']='source_inventory_complete_pg_unverified'
    output=DOC/'capture-v2/source-only-inventory.json';output.write_text(json.dumps(report,indent=2,default=str)+'\n');snapshot.clear()
    print(json.dumps({'status':report['status'],'output':str(output),'sourceSlots':slots,'nativeRepresentabilityPass':report['native31']['representabilityPass'],'nativeUnrepresentable':len(blocked),'heatmapParents':parent_count,'heatmapTriplets':cell_count,'heatmapCohortGaps':len(cohort_gaps),'heatmapSideGaps':len(side_gaps),'sparseFormGaps':len(spatial_gaps),'newSourceRequests':0,'pgImportExecuted':False,'ramPid':ready['pid'],'ramAlive':True,'fullAcceptance':False}),flush=True)
    return 0
if __name__=='__main__':raise SystemExit(main())
