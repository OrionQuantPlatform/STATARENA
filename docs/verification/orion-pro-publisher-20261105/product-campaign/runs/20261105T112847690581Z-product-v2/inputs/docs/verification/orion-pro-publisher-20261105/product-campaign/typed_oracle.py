"""Independent typed SQL selection/digest oracle, written before the publisher."""
from __future__ import annotations
from datetime import date,datetime,timezone
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import re

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[3]
SCHEME='orion-four-readers-dependencies-v1'
REPRESENTATION='summary-v1-shots-v1'
TRANSFORM='orion_pro_publish_v1'
METRICS='orion_pro_four_readers_v1'
LOCAL_COMMIT='local-owned-e2e-v1'
TARGET=ROOT/'dashboard/scripts/orion_pro_publish.py'
POLICY='pilot_priority_v1'
MODEL=ROOT/'docs/architecture/orion-plan-20261104/target-schema.proposed.json'
MODEL_SHA='18da43f940870b7a3a3cb49323c847dd5e5174e5eea1f8ff0c8a159cf373cb08'


def compact(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False)


def sha(value):
    return hashlib.sha256(value if isinstance(value,bytes) else compact(value).encode()).hexdigest()


def tagged(value):
    if value is None:return ['null']
    if type(value) is bool:return ['bool',value]
    if type(value) is int:
        assert -(2**63)<=value<2**63
        return ['i64',str(value)]
    if type(value) is float:
        assert math.isfinite(value),'Nonfinite value is outside this synthetic admitted contract'
        return ['f64',value.hex()]
    if isinstance(value,Decimal):return ['decimal',format(value,'f')]
    if isinstance(value,datetime):
        assert value.tzinfo is not None
        return ['timestamp',value.astimezone(timezone.utc).isoformat(timespec='microseconds')]
    if isinstance(value,date):return ['date',value.isoformat()]
    if isinstance(value,str):return ['text',value]
    if isinstance(value,(list,tuple)):return ['array',[tagged(v) for v in value]]
    if isinstance(value,dict):return ['object',[[k,tagged(v)] for k,v in sorted(value.items())]]
    raise AssertionError('Unsupported typed oracle value: '+type(value).__name__)


def ident(value):
    assert re.fullmatch(r'[a-z_][a-z0-9_]*',value)
    return '"'+value+'"'


def environment():
    files=[MODEL,ROOT/'dashboard/backend/migrations/012_orion_pro_domain.sql',ROOT/'dashboard/backend/migrations/013_orion_pro_integrity.sql',
      ROOT/'dashboard/backend/services/orion-pro.js',*[ROOT/'dashboard/scripts'/n for n in ['orion_pro_integrity.py','orion_pro_schema.py','orion_pro_migrate.py']]]
    body={'scheme':SCHEME,'postgresVersion':180006,'representationVersion':REPRESENTATION,
      'transformVersion':TRANSFORM,'metricsContractVersion':METRICS,
      'files':{str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in files}}
    return {'descriptor':body,'sha256':sha(body)}


class TypedOracle:
    def __init__(self,conn,model):
        assert sha(MODEL.read_bytes())==MODEL_SHA
        self.conn=conn;self.tables={t['qualified_name']:t for s in model['schemas'] for t in s['tables'] if t['phase']!='models'}
        assert len(self.tables)==94 and sum(len(t['columns']) for t in self.tables.values())==1709
        self.queries=0;self.cache={}

    def rows(self,table,where='TRUE',params=(),generation=None):
        assert table in self.tables
        spec=self.tables[table];columns=spec['columns'];parts=[];values=[]
        if 'recorded_from_gen' in columns:
            assert type(generation) is int
            parts.append('r.recorded_from_gen<=%s AND (r.recorded_to_gen IS NULL OR %s<r.recorded_to_gen)');values.extend([generation,generation])
        if 'is_canonical' in columns:parts.append('r.is_canonical')
        if 'is_deleted' in columns:parts.append('NOT r.is_deleted')
        parts.append('('+where+')');values.extend(params)
        relation='.'.join(ident(p) for p in table.split('.'))
        order=','.join('r.'+ident(c) for c in spec['primary_key']['columns'])
        self.queries+=1
        cursor=self.conn.execute(f"SELECT r.* FROM {relation} r WHERE {' AND '.join(parts)} ORDER BY {order} LIMIT 5001",values)
        names=[c.name for c in cursor.description];rows=[dict(zip(names,r)) for r in cursor.fetchall()]
        assert len(rows)<=5000 and set(names)==set(columns)
        return rows

    def winner(self,table,actor_column,actor,source,cg,candidates_rows=None):
        candidates=[]
        rows=self.rows(table,'r.'+ident(actor_column)+'=%s',(actor,),cg) if candidates_rows is None else candidates_rows
        for row in rows:
            if row[actor_column]!=actor:continue
            rank=None
            if row['profile_context']=='provider_global' and row['variant_key']=='provider:exact' and row['source_id']==source:rank=0
            elif row['profile_context']=='legacy_normalized_global' and row['source_id']==source:rank=1
            elif row['profile_context']=='global' and row['provenance_kind']=='manual' and row['source_id'] is None:rank=2
            if rank is not None:candidates.append((rank,row))
        best=min((x[0] for x in candidates),default=None)
        selected=[r for rank,r in candidates if rank==best]
        assert len(selected)<=1,'Ambiguous best source profile'
        return selected,{'table':table,'actor':actor,'source':source,'priority':best,'winnerIds':[r['id'] for r in selected]}

    def closure(self,eid,dg,cg):
        cache_key=(eid,dg,cg)
        if cache_key in self.cache:return self.cache[cache_key]
        tables={};selections=[]
        def put(table,rows):
            existing=tables.setdefault(table,[]);keys=self.tables[table]['primary_key']['columns']
            known={tuple(r[k] for k in keys) for r in existing}
            for row in rows:
                if tuple(row[k] for k in keys) not in known:existing.append(row);known.add(tuple(row[k] for k in keys))
            return rows
        edition=put('football.competition_seasons',self.rows('football.competition_seasons','r.id=%s',(eid,),dg))
        assert len(edition)==1
        matches=put('football.matches',self.rows('football.matches','r.competition_season_id=%s',(eid,),dg))
        mids=[m['id'] for m in matches];by_match={m['id']:m for m in matches}
        sides=put('football.match_teams',self.rows('football.match_teams','r.match_id=ANY(%s)',(mids,),dg))
        squad=put('football.match_players',self.rows('football.match_players','r.match_id=ANY(%s)',(mids,),dg))
        engagements=put('football.competition_teams',self.rows('football.competition_teams','r.competition_season_id=%s',(eid,),dg))
        put('football.match_scores',self.rows('football.match_scores','r.match_id=ANY(%s)',(mids,),dg))
        coverage=put('ingest.match_coverage',self.rows('ingest.match_coverage',"r.match_id=ANY(%s) AND r.feature_code='shots'",(mids,),dg))
        assert len({r['match_id'] for r in coverage})==len(coverage),'Ambiguous canonical coverage'
        coverage_by={r['match_id']:r for r in coverage}
        shots=put('football.shots',self.rows('football.shots','r.match_id=ANY(%s)',(mids,),dg))
        for shot in shots:
            parent=coverage_by.get(shot['match_id'])
            assert parent and parent['source_id']==shot['source_id'] and parent['variant_key']==shot['variant_key'] and parent['collection_state']=='present'
        for parent in coverage:
            children=[r for r in shots if r['match_id']==parent['match_id'] and r['source_id']==parent['source_id'] and r['variant_key']==parent['variant_key']]
            if parent['collection_state']=='present':assert parent['observed_row_count']==len(children)>0
            else:assert not children
        tids=sorted({r['team_id'] for r in sides+engagements+shots if r['team_id'] is not None})
        pids=sorted({r['player_id'] for r in squad+shots if r['player_id'] is not None})
        put('football.competitions',self.rows('football.competitions','r.id=%s',(edition[0]['competition_id'],),cg))
        put('football.teams',self.rows('football.teams','r.id=ANY(%s)',(tids,),cg))
        put('football.players',self.rows('football.players','r.id=ANY(%s)',(pids,),cg))
        put('ingest.public_aliases',self.rows('ingest.public_aliases',
          "(r.route_kind='competition' AND r.competition_id=%s) OR (r.route_kind='match' AND r.match_id=ANY(%s)) OR (r.route_kind='team' AND r.team_id=ANY(%s)) OR (r.route_kind='player' AND r.player_id=ANY(%s))",
          (edition[0]['competition_id'],mids,tids,pids),cg))
        team_pairs={(r['team_id'],by_match[r['match_id']]['source_id']) for r in sides if r['team_id'] is not None}
        player_pairs={(r['player_id'],r['source_id'] if r['source_id'] is not None else by_match[r['match_id']]['source_id']) for r in squad+shots if r['player_id'] is not None}
        for table,col,pairs in [('football.team_profile_versions','team_id',team_pairs),('football.player_profile_versions','player_id',player_pairs)]:
            put(table,[])
            candidates=self.rows(table,'r.'+ident(col)+'=ANY(%s)',(sorted({p[0] for p in pairs}),),cg)
            for actor,source in sorted(pairs):
                winners,selection=self.winner(table,col,actor,source,cg,candidates);put(table,winners);selections.append(selection)
        periods=sorted({(r['period_code'],r['period_definition_version']) for r in shots if r['period_code'] is not None})
        if periods:put('football.periods',self.rows('football.periods',' OR '.join('(r.code=%s AND r.definition_version=%s)' for _ in periods),tuple(v for pair in periods for v in pair),dg))
        records=sorted({r['source_record_id'] for rows in tables.values() for r in rows if r.get('source_record_id') is not None})
        source_records=put('ingest.source_records',self.rows('ingest.source_records','r.id=ANY(%s)',(records,)))
        documents=sorted({r['document_id'] for r in source_records}|{r['document_id'] for r in coverage if r['document_id'] is not None})
        docs=put('ingest.source_documents',self.rows('ingest.source_documents','r.id=ANY(%s)',(documents,)))
        datasets=sorted({r['dataset_id'] for r in docs})
        put('ingest.source_datasets',self.rows('ingest.source_datasets','r.id=ANY(%s)',(datasets,)))
        sources=sorted({r['source_id'] for rows in tables.values() for r in rows if r.get('source_id') is not None})
        put('ingest.sources',self.rows('ingest.sources','r.id=ANY(%s)',(sources,)))
        contracts=sorted({(r['relation_code'],r['contract_version']) for rows in tables.values() for r in rows if r.get('relation_code') is not None})
        if contracts:put('ingest.relation_contracts',self.rows('ingest.relation_contracts',' OR '.join('(r.relation_code=%s AND r.contract_version=%s)' for _ in contracts),tuple(v for pair in contracts for v in pair)))
        snapshots=self.rows('ingest.dataset_snapshots','r.generation=ANY(%s)',(sorted({dg,cg}),))
        by_g={r['generation']:r for r in snapshots}
        assert dg in by_g and cg in by_g and all(r['status']=='sealed' for r in snapshots)
        policies={'dataset':by_g[dg]['source_priority_version'],'catalogue':by_g[cg]['source_priority_version']}
        physical={'storage_provider','storage_bucket','storage_key','storage_version','legacy_object_path','retention_state','content_verified_at','deleted_at'}
        entries={}
        for table,rows in sorted(tables.items()):
            excluded={'recorded_to_gen','updated_at'}|(physical if table=='ingest.source_documents' else set())
            columns=sorted(set(self.tables[table]['columns'])-excluded);pk=self.tables[table]['primary_key']['columns']
            encoded=[]
            for row in rows:
                body={c:row[c] for c in columns}
                encoded.append({'key':{c:tagged(row[c]) for c in pk},'sha256':sha(tagged(body))})
            entries[table]={'columns':columns,'rows':sorted(encoded,key=compact)}
        manifest={'scheme':SCHEME,'representation':REPRESENTATION,'editionId':str(eid),'policies':policies,
          'profilePolicy':'same-source-provider-exact-normalized-manual-v1','tables':entries,'profileSelections':sorted(selections,key=compact)}
        result={'sha256':sha(manifest),'manifest':manifest,'rows':tables,'snapshots':{'dg':by_g[dg],'cg':by_g[cg]}}
        self.cache[cache_key]=result
        return result

    def public_closure(self,value):
        return {'sha256':value['sha256'],'manifest':value['manifest'],
          'effectiveSnapshots':{k:{'id':r['id'],'generation':r['generation'],'status':r['status'],'sourcePriorityVersion':r['source_priority_version']} for k,r in value['snapshots'].items()}}

    def coverage_at_declaration(self,declaration,dg):
        key=declaration['key'];columns=self.tables['ingest.match_coverage']['primary_key']['columns']
        assert set(key)==set(columns)
        rows=self.rows('ingest.match_coverage',' AND '.join('r.'+ident(c)+'=%s' for c in columns),tuple(key[c] for c in columns),dg)
        assert len(rows)==1,'Coverage key is not selected at declared generation'
        row=rows[0]
        mapping={'dataRevision':'data_revision','matchRevisionId':'match_revision_id','sourceRecordId':'source_record_id',
          'documentId':'document_id','coverageState':'coverage_state','collectionState':'collection_state',
          'observedRowCount':'observed_row_count','isCanonical':'is_canonical','isStale':'is_stale'}
        for external,column in mapping.items():assert declaration[external]==row[column]
        claimed=declaration['recordedToGeneration'];actual=row['recorded_to_gen']
        if claimed is not None:assert claimed==actual
        else:assert actual is None or actual>dg
        return {'key':key,'declaredGeneration':dg,'declaredEnd':claimed,'actualEnd':actual,'selected':True,
          'closedAfterDeclaration':claimed is None and actual is not None}

    def assert_inputs(self,inputs,initial=False):
        evidence={'editions':{},'policies':{},'queriesAtStart':self.queries}
        counts={'A':(3,2,2,1),'B':(1,1,2,2),'C':(1,1,2,1)}
        fixture_sha=sha((ROOT/'docs/verification/orion-pro-pilot-20261104/fixtures.py').read_bytes())
        for key,e in inputs.editions.items():
            closure=self.closure(e['id'],inputs.data_generation,inputs.catalog_generation);tables=closure['rows']
            assert closure['manifest']['policies']=={'dataset':POLICY,'catalogue':POLICY}
            assert all(r['publication_state']=='published' for r in tables['football.matches'])
            got=(len(tables['football.matches']),sum(r['status']=='finished' for r in tables['football.matches']),len(tables['football.competition_teams']),len({r['player_id'] for r in tables['football.match_players']}))
            assert got==counts[key],(key,got)
            assert any(r['route_kind']=='competition' and r['public_key']=='l_000001' and r['competition_id']==inputs.competition['id'] for r in tables['ingest.public_aliases'])
            for participant in tables['football.match_players']:
                index=next(i for i,p in enumerate(inputs.ids['players']) if p['id']==participant['player_id'])
                public='p_'+str(index+1).zfill(6)
                assert any(r['route_kind']=='player' and r['public_key']==public and r['player_id']==participant['player_id'] for r in tables['ingest.public_aliases'])
            actual={};coverage_by={r['match_id']:r for r in tables['ingest.match_coverage']}
            for mid,w in inputs.expected.items():
                if w['key']!=key:continue
                handle=inputs.match_rows[mid];m=next(r for r in tables['football.matches'] if r['id']==handle['id'])
                assert m['revision_id']==handle['revision_id'] and m['status']==w['status']
                assert (m['match_date'].isoformat() if m['match_date'] else None)==w['date'] and m['kickoff_at'] is None
                aliases=[r for r in tables['ingest.public_aliases'] if r['route_kind']=='match' and r['public_key']==mid]
                assert len(aliases)==1 and aliases[0]['match_id']==m['id'] and aliases[0]['match_revision_id']==m['revision_id']
                side_rows=[r for r in tables['football.match_teams'] if r['match_id']==m['id']]
                assert {r['side'] for r in side_rows}=={'home','away'} and len({r['team_id'] for r in side_rows})==2
                score_rows=[r for r in tables['football.match_scores'] if r['match_id']==m['id']]
                for side in ['home','away']:
                    participant=next(r for r in side_rows if r['side']==side)
                    assert any(r['team_id']==participant['team_id'] for r in tables['football.competition_teams'])
                    final=[r for r in score_rows if r['side']==side and r['score_scope']=='final_without_shootout']
                    assert len(final)==int(w['scoreObserved'])
                    assert (final[0]['goals'] if final else None)==w[side]
                    if final:assert final[0]['match_team_revision_id']==participant['revision_id']
                    penalty=[r for r in score_rows if r['side']==side and r['score_scope']=='shootout']
                    assert len(penalty)==int(w[side+'Penalty'] is not None)
                    assert (penalty[0]['goals'] if penalty else None)==w[side+'Penalty']
                    winners,selection=self.winner('football.team_profile_versions','team_id',participant['team_id'],m['source_id'],inputs.catalog_generation,tables['football.team_profile_versions'])
                    assert len(winners)==1 and winners[0]['display_name']==w[side+'Name']
                    team_key=('t_000004' if side=='home' else 't_000005') if key=='C' else ('t_000001' if side=='home' else 't_000002' if key=='A' else 't_000003')
                    assert any(r['public_key']==team_key and r['team_id']==participant['team_id'] for r in tables['ingest.public_aliases'])
                parent=coverage_by.get(m['id']);state=parent['collection_state'] if parent else 'unknown'
                assert state==w['shots']
                selected=[r for r in tables['football.shots'] if r['match_id']==m['id']]
                expected=inputs.expected_shots.get(mid,[]);assert len(selected)==len(expected)
                for want in expected:
                    shot=next(r for r in selected if r['external_shot_id']==want['external_shot_id'])
                    for column,value in want.items():
                        assert shot[column]==value,(mid,column,shot[column],value)
                        if isinstance(value,bool):assert type(shot[column]) is bool
                    for column in ['is_goal','is_own_goal','is_on_target']:
                        assert shot[column] is None or type(shot[column]) is bool
                    if shot['player_id'] is not None:
                        actor=next(r for r in tables['football.match_players'] if r['match_id']==m['id'] and r['player_id']==shot['player_id'])
                        assert actor['played'] is True and actor['squad_status']!='unused_substitute'
                        assert any(r['public_key']=='p_000001' and r['player_id']==shot['player_id'] for r in tables['ingest.public_aliases'])
                if parent:
                    assert parent['source_id']==inputs.ids['source'] and parent['match_revision_id']==m['revision_id'] and parent['variant_key']=='pilot:primary'
                    assert parent['observed_row_count']==(len(expected) if state in ['present','empty'] else None)
                    assert type(parent['is_stale']) is bool and parent['is_stale'] is False
                    if initial and mid=='m_000004':assert parent['data_revision']==2
                actual[mid]={'matchId':m['id'],'revision':m['revision_id'],'finalScoreRows':len([r for r in score_rows if r['score_scope']=='final_without_shootout']),
                  'coverage':inputs.coverage_declaration(parent),'shotNativeWitnesses':[{k:r[k] for k in ['external_shot_id','revision_id','player_id','period_code','source_event_type','is_goal','is_own_goal','is_on_target','xg','xgot','x_m','y_m','coordinate_frame']} for r in selected]}
            for table,rows in tables.items():
                for row in rows:
                    if 'transform_code_sha256' in row:
                        want=inputs.bootstrap_code if table=='football.periods' else fixture_sha
                        assert row['transform_code_sha256']==want,(table,'upstream transform SHA')
                    if 'contract_version' in row and table not in ['ingest.source_datasets','ingest.relation_contracts']:
                        assert row['contract_version']==('bootstrap_v1' if table=='football.periods' else 'pilot_v1')
                    if 'canonical_policy_version' in row:assert row['canonical_policy_version']==('bootstrap_v1' if table=='football.periods' else 'pilot_v1')
                    if 'quality_flags' in row:assert row['quality_flags']=={}
            if key=='B':
                squad=tables['football.match_players'];assert len({r['player_id'] for r in squad if r['played'] is True})==1
                assert any(r['player_id']==inputs.ids['players'][1]['id'] and r['squad_status']=='unused_substitute' and r['played'] is False for r in squad)
            evidence['editions'][key]={'counters':list(got),'matches':actual,'closure':self.public_closure(closure)}
            evidence['policies'][key]=closure['manifest']['policies']
        if initial:assert (inputs.data_generation,inputs.catalog_generation)==(3,2)
        evidence['queriesUsed']=self.queries-evidence.pop('queriesAtStart')
        evidence['environmentBinding']=environment();evidence['futurePublisherCodeSha256']=sha(TARGET.read_bytes()) if TARGET.exists() else None
        evidence['upstreamFixtureCodeSha256']=fixture_sha
        return evidence
