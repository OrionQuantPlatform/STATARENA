"""Operational LOCAL candidate only; frozen mapper, genuine sources, no demo mutations."""
from __future__ import annotations
from collections import Counter
from datetime import datetime,timezone
import hashlib,importlib.util,json,sys
from pathlib import Path

sys.dont_write_bytecode=True
DOC=Path(__file__).resolve().parent
REPO=DOC.parents[2]
NORMALIZER=REPO/'dashboard/scripts/orion_pro_normalize.py'
MANIFEST=json.loads((DOC/'MANIFEST.json').read_text())
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()

class CandidateError(ValueError):pass

def validate_local_writer(conn):
    if conn.info.host not in ('127.0.0.1','localhost','::1'):
        raise CandidateError('Candidate requires actual ingest role on an owned LOCAL PostgreSQL connection')
    role,statement,lock=conn.execute("SELECT current_user,current_setting('statement_timeout'),current_setting('lock_timeout')").fetchone()
    if role!='orion_pro_ingest':raise CandidateError('Candidate requires actual ingest role on an owned LOCAL PostgreSQL connection')
    if (statement,lock)!=('8s','1s'):raise CandidateError('Local candidate requires statement_timeout=8s and lock_timeout=1s before writes')
    return {'host':conn.info.host,'role':role,'statementTimeout':statement,'lockTimeout':lock}

def module():
    if sha(NORMALIZER)!=MANIFEST['normalizerSha256']:raise CandidateError('Candidate normalizer is not the frozen approved code')
    spec=importlib.util.spec_from_file_location('frozen_genuine_source_normalizer',NORMALIZER);out=importlib.util.module_from_spec(spec);spec.loader.exec_module(out)
    class NoRemote:
        def __init__(self,*a,**kw):raise CandidateError('Remote reader and old source ledger are forbidden in candidate')
    out.SourceReader=NoRemote;return out

def parts_from_source(source,n):
    parts=[]
    for p in MANIFEST['aws']['partitions']:
        doc=source.documents({p['path']:p['sha256']})[p['path']]
        parts.append({'season':p['season'],'path':p['path'],'tables':{name:n.unpack(table) for name,table in doc['tables'].items()}})
    return parts

def leaves(value,path='$'):
    if isinstance(value,dict):
        if not value:yield path,'empty_object'
        for key,child in value.items():yield from leaves(child,path+'.'+str(key))
    elif isinstance(value,list):
        if not value:yield path,'empty_list'
        for child in value:yield from leaves(child,path+'[]')
    else:yield path,'null' if value is None else 'boolean' if isinstance(value,bool) else 'empty_string' if isinstance(value,str) and value=='' else 'string' if isinstance(value,str) else 'number'

def spatial_phase(conn,actor,source,n):
    s=MANIFEST['neon'];path=s['path'];doc=source.documents({path:s['physicalSha256']})[path];data=doc['data'];origin=source.meta[path]
    selectors={'sourceOrigin':'neon','storageHost':s['storageHost'],'bucket':s['bucket'],'key':s['key'],'resource':{'endpoint':s['endpoint'],'params':s['params'],'status':s['status'],'recordLocator':s['recordLocator'],'dataRoot':s['dataRoot']},'manifestSha256':sha(DOC/'MANIFEST.json'),'wrapperSha256':sha(Path(__file__))}
    binding=actor.phase_binding('qualified_real_native_spatial_heatmap',[path],selectors)
    with conn.transaction():
        conn.execute('SELECT pg_advisory_xact_lock(20261104,1)');existing=actor.phase_receipt(binding)
        if existing:return {**existing['report'],'reused':True,'phaseReceipt':{k:v for k,v in existing.items() if k!='report'}}
        # Bound cross-origin identity/cohort check; never fill an AWS participant gap.
        requested=[(row['player']['id'],row['team']['id']) for row in data.get('players',[])];missing_id=sorted({p for p,t in requested if p not in actor.people});missing_team=sorted({t for p,t in requested if t not in actor.teams})
        if missing_id or missing_team:raise CandidateError('Spatial identity gap:'+json.dumps({'playerIds':missing_id,'teamIds':missing_team},sort_keys=True))
        match=actor.matches[s['matchId']]
        rows=list(conn.execute('SELECT player_id,team_id,match_team_revision_id FROM football.match_players WHERE match_id=%s AND source_id=%s AND is_canonical AND recorded_to_gen IS NULL',(match['id'],actor.ids['source'])))
        selected=Counter(tuple(row) for row in rows);bad=[]
        for pid,tid in requested:
            side=actor.sides.get((s['matchId'],tid));binding_row=(actor.people[pid]['id'],actor.teams[tid]['id'],side['revision_id'] if side else None)
            if selected[binding_row]!=1:bad.append({'playerId':pid,'teamId':tid,'selectedCohortRows':selected[binding_row]})
        if bad:raise CandidateError('Spatial selected cohort gap:'+json.dumps(bad,sort_keys=True))
        actor.begin_phase(binding);actor.active_run=actor.insert('ingest.import_runs',mode='rebuild',transform_version=n.VERSION,code_commit=n.SHA)['id']
        dataset=actor.insert('ingest.source_datasets',source_id=actor.ids['source'],dataset_key='explicit-neon-existing-home-ltr-heatmap',contract_version=n.VERSION)
        # Existing remote blob provenance, never a newly stored body nor a fake HTTP collection.
        document=actor.insert('ingest.source_documents',source_id=actor.ids['source'],dataset_id=dataset['id'],content_sha256=s['physicalSha256'],retrieved_at=datetime.fromisoformat(origin['retrievedAt']),source_updated_at=origin['updatedAt'],
            storage_provider='neon_s3',storage_bucket=s['bucket'],storage_key=s['key'],storage_version=origin.get('storageVersion'),source_url=origin['sourceUrl'],origin_kind='legacy_file',retention_state='staged',legacy_object_path=path,byte_length=s['physicalBytes'],import_run_id=actor.active_run)
        actor.documents[path]=document['id'];record=actor.record(path,s['recordLocator'],'explicit_neon_existing_heatmap',s['matchId']);variant='source:'+s['physicalSha256']+':heatmaps:'+s['frame']
        written=actor.import_sparse_heatmaps(s['matchId'],data,record,variant,data_root=s['dataRoot'])
        counts=Counter(leaves(data));report={'localOnly':True,'fullAcceptance':False,'mappedSpatialRows':written,'sourceCollections':sum(len(data.get(k,[])) for k in ['teams','players']),'sourceTriplets':sum(len(r.get('cells') or []) for k in ['teams','players'] for r in data.get(k,[])),
            'unverifiedFields':dict(sorted(actor.unverified.items())),'leafDispositions':[{'path':p,'nativeState':state,'observations':count,'status':'spatial_projection_only_full_leaf_fidelity_unverified'} for (p,state),count in sorted(counts.items())]}
        receipt=actor.finish_phase(binding,report,[path],actor.active_run)
    return {**report,'reused':False,'phaseReceipt':receipt}

def import_candidate(conn,evidence,snapshot,*,core_only=False):
    validate_local_writer(conn)
    if snapshot.get('captureKind')!='orion_real_native_spatial_ram_v1' or snapshot.get('manifestSha256')!=sha(DOC/'MANIFEST.json') or snapshot.get('normalizerSha256')!=sha(NORMALIZER):raise CandidateError('Candidate source manifest/normalizer binding differs')
    n=module();source=n.MemorySource(snapshot);parts=parts_from_source(source,n);actor=n.TypedCore(conn,evidence,source);core=actor.import_core(parts)
    counts=Counter((table,path,state) for part in parts for table,rows in part['tables'].items() for row in rows for path,state in leaves(row))
    result={'core':core,'fullAcceptance':False,'localOnly':True,'sourceCalls':0,'originalFamiliesOutsideThisLot':['advanced_players','advanced_teams','events','h2h','lineups','match','momentum','pass_networks','player_halves','players','shots','stats'],'fullProfileBodiesCaptured':0,'exactProfileResourceLookupGaps':source.profile_gaps,
        'sourceLeafDispositions':[{'table':table,'path':path,'nativeState':state,'observations':count,'status':'requires_independent_native31_oracle' if table=='performances' and path[2:] in n.COMMON_NATIVE else 'unverified_full_leaf_fidelity_core_projection_only'} for (table,path,state),count in sorted(counts.items())]}
    if not core_only:result['spatial']=spatial_phase(conn,actor,source,n)
    return result
