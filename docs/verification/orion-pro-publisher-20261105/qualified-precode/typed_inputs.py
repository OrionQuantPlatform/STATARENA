"""Independent synthetic typed inputs/oracles; no hand-built analytical output."""
from __future__ import annotations
from contextlib import contextmanager
from datetime import date
import json
import hashlib
from pathlib import Path
import sys

BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[3]
sys.path[:0]=[str(ROOT/'docs/verification/orion-pro-readers-20261104'),str(ROOT/'docs/verification/orion-pro-pilot-20261104')]
from fixture import ReaderFixture
from fixtures import NOW,hashed
from workflow_budget import digest
from typed_oracle import TypedOracle,SCHEME,POLICY

def hashed_fixture_code():
    return hashlib.sha256((ROOT/'docs/verification/orion-pro-pilot-20261104/fixtures.py').read_bytes()).hexdigest()


class TypedInputs(ReaderFixture):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.suppressed=[];self.expected={};self.markers={'A':0,'shared':0,'C':0};self.input_epoch=0

    @contextmanager
    def _generation(self,label):
        with super()._generation(label) as g:yield g
        self.input_epoch+=1

    def build(self,*args):self.suppressed.append({'hook':'build','args':args});return None
    def publish(self,*args):self.suppressed.append({'hook':'publish','builds':args[0]});return None

    def prepare_inputs(self):
        super().prepare()
        self.catalog_generation=self.data1
        with self._generation('publisher_shared_input_and_shootout') as g:
            self.data_generation=g
            b=self.match_rows['m_000004'];team=self.ids['teams'][0];player=self.ids['players'][0]
            self._insert('football.match_players',match_id=b['id'],team_id=team['id'],player_id=player['id'],profile_version_id=self.player_profiles[0]['id'],
                match_team_revision_id=self.sides['m_000004']['home']['revision_id'],squad_status='starter',played=True,
                participation_evidence='Synthetic declared B starter; both selected B shots prove participation',source_id=self.ids['source'],source_record_id=self.ids['record'])
            prior_b_player=self._row('football.match_players',
                'match_id=%s AND player_id=%s AND team_id=%s AND is_canonical AND NOT is_deleted AND recorded_from_gen<=%s AND (recorded_to_gen IS NULL OR %s<recorded_to_gen)',
                (b['id'],self.ids['players'][1]['id'],team['id'],g,g))
            assert prior_b_player is not None
            self._replace('football.match_players',prior_b_player,squad_status='unused_substitute',played=False,
                participation_evidence='Synthetic declared unused B substitute; no selected B shot belongs to this actor',
                data_revision=prior_b_player['data_revision']+1)
            self.shot_rows['m_000004']=self._replace('football.shots',self.shot_rows['m_000004'],
                player_id=player['id'],player_profile_version_id=self.player_profiles[0]['id'],
                data_revision=self.shot_rows['m_000004']['data_revision']+1)
            self.shared_b_shot=self._insert('football.shots',match_id=b['id'],team_id=team['id'],match_team_revision_id=self.sides['m_000004']['home']['revision_id'],
                player_id=player['id'],player_profile_version_id=self.player_profiles[0]['id'],external_shot_id='s_000002',period_code='second_half',period_definition_version='bootstrap_v1',
                minute=60,xg=.21,xgot=0,is_goal=False,is_own_goal=False,is_on_target=False,source_event_type='',x_m=20,y_m=10,coordinate_frame='acting_ltr',
                pitch_length_m=105,pitch_width_m=68,source_ordinal=1,source_id=self.ids['source'],source_record_id=self.ids['record'])
            self.coverages['m_000004']=self._replace('ingest.match_coverage',self.coverages['m_000004'],observed_row_count=2,data_revision=self.coverages['m_000004']['data_revision']+1)
            for side,goals in [('home',4),('away',3)]:
                self._insert('football.match_scores',match_id=self.match_rows['m_000002']['id'],side=side,
                    match_team_revision_id=self.sides['m_000002'][side]['revision_id'],score_scope='shootout',goals=goals,score_basis='played',
                    source_id=self.ids['source'],source_record_id=self.ids['record'])
            for key,e in self.editions.items():
                self._insert('ingest.dirty_editions',competition_season_id=e['id'],competition_season_revision_id=e['revision_id'],generation=g,changed_at=NOW,reason='Synthetic declared input '+key)
        self.expected={
          'm_000001':{'key':'A','date':'2026-11-04','status':'finished','home':1,'away':0,'homePenalty':None,'awayPenalty':None,'homeName':'Shared team v1','awayName':'Team 1 v1','shots':'present'},
          'm_000002':{'key':'A','date':'2026-11-04','status':'finished','home':0,'away':0,'homePenalty':4,'awayPenalty':3,'homeName':'Shared team v1','awayName':'Team 1 v1','shots':'empty'},
          'm_000003':{'key':'A','date':None,'status':'not_started','home':None,'away':None,'homePenalty':None,'awayPenalty':None,'homeName':'Shared team v1','awayName':'Team 1 v1','shots':'unavailable'},
          'm_000004':{'key':'B','date':'2026-11-04','status':'finished','home':1,'away':0,'homePenalty':None,'awayPenalty':None,'homeName':'Shared team v1','awayName':'Team 2 v1','shots':'present'},
          'm_000005':{'key':'C','date':'2026-11-04','status':'finished','home':1,'away':0,'homePenalty':None,'awayPenalty':None,'homeName':'Team 3 v1','awayName':'Team 4 v1','shots':'unknown'},
        }
        for mid,w in self.expected.items():w['scoreObserved']=mid!='m_000003'
        player=self.ids['players'][0]['id']
        self.expected_shots={
          'm_000001':[{'external_shot_id':'s_000001','player_id':player,'period_code':'first_half','period_definition_version':'bootstrap_v1',
            'source_event_type':'','is_goal':True,'is_own_goal':False,'is_on_target':None,'xg':.82,'xgot':0.,'x_m':52.5,'y_m':34.,'coordinate_frame':'acting_ltr'}],
          'm_000004':[{'external_shot_id':'s_000001','player_id':player,'period_code':'first_half','period_definition_version':'bootstrap_v1',
            'source_event_type':'Goal','is_goal':True,'is_own_goal':False,'is_on_target':None,'xg':.99,'xgot':0.,'x_m':52.5,'y_m':34.,'coordinate_frame':'home_ltr'},
            {'external_shot_id':'s_000002','player_id':player,'period_code':'second_half','period_definition_version':'bootstrap_v1',
            'source_event_type':'','is_goal':False,'is_own_goal':False,'is_on_target':False,'xg':.21,'xgot':0.,'x_m':20.,'y_m':10.,'coordinate_frame':'acting_ltr'}],
        }
        self.oracle=TypedOracle(self.conn,self.model);self.source_evidence=[]
        return {'typedInputsPrepared':True,'buildPublishHooksSuppressed':self.suppressed}

    def input_oracle(self):
        assert len(self.suppressed)==4 and all(v is None for v in self.initial_builds.values())
        assert self.conn.execute('SELECT count(*) FROM analytics.aggregation_builds').fetchone()[0]==0
        assert self.conn.execute('SELECT count(*) FROM analytics.publication_versions').fetchone()[0]==0
        metadata=self.conn.execute('SELECT r.id,r.source_id,r.document_id,d.content_sha256,r.locator_kind,r.locator FROM ingest.source_records r JOIN ingest.source_documents d ON d.id=r.document_id WHERE r.source_id=%s ORDER BY r.id',(self.ids['source'],)).fetchall()
        self.source_evidence=[{'recordId':r[0],'sourceId':r[1],'documentId':r[2],'contentSha256':r[3],'locatorKind':r[4],'locator':r[5]} for r in metadata]
        actual=self.oracle.assert_inputs(self,initial=True)
        actual.update(suppressedHooks=self.suppressed,noAnalyticalOutputs=True,dataGeneration=self.data_generation,
          catalogGeneration=self.catalog_generation,expectedStateSha256=digest(self.expected))
        return actual

    def coverage_declaration(self,row):
        if row is None:return None
        table=self.tables['ingest.match_coverage']
        return {'key':{column:row[column] for column in table['primary_key']['columns']},
          'dataRevision':row['data_revision'],'matchRevisionId':row['match_revision_id'],
          'recordedToGeneration':row['recorded_to_gen'],'sourceRecordId':row['source_record_id'],
          'documentId':row['document_id'],'coverageState':row['coverage_state'],
          'collectionState':row['collection_state'],'observedRowCount':row['observed_row_count'],
          'isCanonical':row['is_canonical'],'isStale':row['is_stale']}

    def admission(self):
        scopes=[]
        for key,e in self.editions.items():
            members=[]
            for mid,w in self.expected.items():
                if w['key']!=key:continue
                m=self.match_rows[mid]
                coverage=self.coverages.get(mid)
                observations=[]
                for shot in [self.shot_rows.get(mid),self.shared_b_shot if mid=='m_000004' else None]:
                    if shot:observations.append({'shotId':shot['id'],'revision':shot['revision_id'],'sourceId':shot['source_id'],
                        'sourceRecordId':shot['source_record_id'],'externalShotId':shot['external_shot_id'],
                        'period':shot['period_code'],'periodDefinitionVersion':shot['period_definition_version'],
                        'playerId':shot['player_id'],'teamId':shot['team_id'],'variant':shot['variant_key']})
                members.append({'publicId':mid,'matchId':m['id'],'matchRevision':m['revision_id'],'publicationState':'published',
                    'sourceId':self.ids['source'],'sourceRecordId':m['source_record_id'],'declaredShotsState':w['shots'],
                    'coverage':self.coverage_declaration(coverage),'selectedShotObservations':observations,
                    'finalScoreObservation':{'present':w['scoreObserved'],'scope':'final_without_shootout' if w['scoreObserved'] else None},
                    'declaredShotsCount':(2 if mid=='m_000004' else 1) if w['shots']=='present' else 0 if w['shots']=='empty' else None})
            scopes.append({'fixtureKey':key,'editionId':e['id'],'editionRevision':e['revision_id'],'season':e['season_key'],'intendedMatches':members})
        return {'schemaVersion':1,'kind':'synthetic_declared_business_admission','fixtureOnly':True,
          'businessDecision':'Explicit synthetic software-test scope; not authorization or evidence of real source acceptance',
          'representationVersion':'summary-v1-shots-v1','sourcePolicy':'pilot_priority_v1','allowedSourceIds':[self.ids['source']],
          'dependencyScheme':SCHEME,'snapshotPolicyColumn':'source_priority_version',
          'upstreamRowContracts':{'contractVersion':'pilot_v1','transformVersion':'pilot_v1','canonicalPolicyVersion':'pilot_v1',
            'transformCodeSha256':hashed_fixture_code(),'bootstrapDefinitionVersion':'bootstrap_v1','bootstrapCodeSha256':self.bootstrap_code},
          'sourceEvidence':self.source_evidence,
          'datasetGeneration':self.data_generation,'catalogGeneration':self.catalog_generation,'editions':scopes,
          'declaredTypes':{'match_date':['date','null'],'score':['integer','null'],'shot_expected_goals':['number','null'],
            'source_event_type':['string','null'],'is_goal':['boolean','null'],'shots_state':['present','empty','unavailable','unknown','absent','null']},
          'requirements':{'noUsefulDraftOmission':True,'explicitEngagements':True,'exactSourceRevisionTypes':True,'scoreScope':'final_without_shootout'},
          'oracleMetadataSha256':digest(self.expected)}

    def mark_dirty(self,key,g):
        e=self.editions[key]
        self.conn.execute('UPDATE ingest.dirty_editions SET generation=%s,changed_at=%s,reason=%s,competition_season_revision_id=%s WHERE competition_season_id=%s',
            (g,NOW,'Synthetic relevant correction '+key,e['revision_id'],e['id']))

    def correct_A_data(self):
        goals=self.expected['m_000001']['home']+1
        xg=.67-self.markers['A']*.01
        with self._generation('publisher_A_data_correction') as g:
            self.data_generation=g
            self.scores[('m_000001','home')]=self._replace('football.match_scores',self.scores[('m_000001','home')],goals=goals,data_revision=self.scores[('m_000001','home')]['data_revision']+1)
            self.shot_rows['m_000001']=self._replace('football.shots',self.shot_rows['m_000001'],xg=xg,data_revision=self.shot_rows['m_000001']['data_revision']+1)
            if not self.expected['m_000003']['scoreObserved']:
                for side in ['home','away']:
                    self.scores[('m_000003',side)]=self._insert('football.match_scores',match_id=self.match_rows['m_000003']['id'],side=side,
                      match_team_revision_id=self.sides['m_000003'][side]['revision_id'],score_scope='final_without_shootout',goals=None,score_basis='unknown',
                      source_id=self.ids['source'],source_record_id=self.ids['record'])
            self.mark_dirty('A',g)
        self.expected['m_000001']['home']=goals;self.expected['m_000003']['scoreObserved']=True
        self.expected_shots['m_000001'][0]['xg']=xg;self.markers['A']+=1
        return {'affectedKeys':['A'],'dataGeneration':g,'catalogGeneration':self.catalog_generation}

    def correct_shared_catalogue(self):
        with self._generation('publisher_shared_catalogue_via_B') as g:
            self.catalog_generation=g
            self.team_profiles[0]=self._replace('football.team_profile_versions',self.team_profiles[0],display_name='Shared team corrected')
            self.player_profiles[0]=self._replace('football.player_profile_versions',self.player_profiles[0],display_name='Shared striker corrected',
                external_profile_version_id='publisher-corrected-shared',profile_content_sha256=hashed('publisher corrected shared'),data_revision=self.player_profiles[0]['data_revision']+1)
            self.mark_dirty('B',g)
        for value in self.expected.values():
            if value['key'] in ['A','B']:value['homeName']='Shared team corrected'
        self.markers['shared']+=1
        return {'affectedKeys':['A','B'],'dataGeneration':self.data_generation,'catalogGeneration':g,'dirtyHintOnly':'B'}

    def correct_C_data(self):
        goals=3 if self.markers['C']==0 else self.expected['m_000005']['home']+1
        with self._generation('publisher_C_independent_correction') as g:
            self.data_generation=g
            self.scores[('m_000005','home')]=self._replace('football.match_scores',self.scores[('m_000005','home')],goals=goals,data_revision=self.scores[('m_000005','home')]['data_revision']+1)
            if self.markers['C']>=1:
                self.catalog_generation=g
                self.team_profiles[4]=self._replace('football.team_profile_versions',self.team_profiles[4],display_name=None)
                self.coverages['m_000005']=self._insert('ingest.match_coverage',match_id=self.match_rows['m_000005']['id'],match_revision_id=self.match_rows['m_000005']['revision_id'],
                  source_id=self.ids['source'],source_record_id=self.ids['record'],feature_code='shots',coverage_state='available',collection_state='present',observed_row_count=1,checked_at=NOW)
                self.shot_rows['m_000005']=self._insert('football.shots',match_id=self.match_rows['m_000005']['id'],team_id=self.ids['teams'][3]['id'],
                  match_team_revision_id=self.sides['m_000005']['home']['revision_id'],player_id=None,player_profile_version_id=None,external_shot_id='s_000001',
                  period_code=None,period_definition_version=None,minute=None,xg=None,xgot=None,is_goal=None,is_own_goal=None,is_on_target=None,
                  source_event_type=None,x_m=None,y_m=None,coordinate_frame=None,pitch_length_m=None,pitch_width_m=None,source_ordinal=0,
                  source_id=self.ids['source'],source_record_id=self.ids['record'])
            self.mark_dirty('C',g)
        self.expected['m_000005']['home']=goals
        if self.markers['C']>=1:
            self.expected['m_000005'].update(awayName=None,shots='present')
            self.expected_shots['m_000005']=[{'external_shot_id':'s_000001','player_id':None,'period_code':None,'period_definition_version':None,
              'source_event_type':None,'is_goal':None,'is_own_goal':None,'is_on_target':None,'xg':None,'xgot':None,'x_m':None,'y_m':None,'coordinate_frame':None}]
        self.markers['C']+=1
        return {'affectedKeys':['C'],'dataGeneration':g,'catalogGeneration':self.catalog_generation}

    def collection_successor(self,state):
        assert state in ['absent','null']
        with self._generation('publisher_A_collection_'+state) as g:
            self.data_generation=g
            self.coverages['m_000003']=self._replace('ingest.match_coverage',self.coverages['m_000003'],collection_state=state,
              observed_row_count=None,coverage_state='unavailable',data_revision=self.coverages['m_000003']['data_revision']+1)
            self.mark_dirty('A',g)
        self.expected['m_000003']['shots']=state
        return {'affectedKeys':['A'],'dataGeneration':g,'catalogGeneration':self.catalog_generation,'state':state}

    @contextmanager
    def negative_input(self,kind):
        """Committed synthetic fault visible to the CLI, restored by new versions."""
        changed=None;committed=False
        try:
            with self._generation('publisher_negative_'+kind) as g:
                self.data_generation=g
                if kind=='draft':
                    changed=self._insert('football.matches',competition_season_id=self.editions['A']['id'],competition_season_revision_id=self.editions['A']['revision_id'],
                        match_date=date(2026,11,5),kickoff_precision='date',status='not_started',publication_state='draft',source_id=self.ids['source'],source_record_id=self.ids['record'])
                elif kind=='engagement':
                    row=self._row('football.competition_teams','competition_season_id=%s AND team_id=%s AND is_canonical AND NOT is_deleted AND recorded_from_gen<=%s AND (recorded_to_gen IS NULL OR %s<recorded_to_gen)',(self.editions['C']['id'],self.ids['teams'][3]['id'],g,g))
                    changed=self._replace('football.competition_teams',row,is_canonical=False)
                else:raise ValueError(kind)
            committed=True
            declaration=self.admission()
            if kind=='draft':
                declaration['editions'][0]['intendedMatches'].append({'publicId':'m_000006','matchId':changed['id'],
                    'matchRevision':changed['revision_id'],'publicationState':'draft','sourceId':self.ids['source'],'sourceRecordId':self.ids['record'],
                    'declaredShotsState':'unknown','declaredShotsCount':None})
            yield declaration
        finally:
            if committed:
                with self._generation('publisher_restore_negative_'+kind) as g:
                    self.data_generation=g
                    if kind=='draft':self._replace('football.matches',changed,is_deleted=True,data_revision=changed['data_revision']+1)
                    else:self._replace('football.competition_teams',changed,is_canonical=True)

    def oracle_groups(self):
        return {'A':{'data':self.markers['A'],'sharedCatalogue':self.markers['shared']},
                'B':{'data':0,'sharedCatalogue':self.markers['shared']},'C':{'data':self.markers['C'],'sharedCatalogue':0}}

    def reject_illegal_typed_collection(self,kind):
        """Exercise existing source guards, never disable a012/013 constraint."""
        before=self.conn.execute('SELECT count(*) FROM football.shots').fetchone()[0]
        def action():
            if kind=='duplicate_coverage':
                row=self.coverages['m_000001'];values={k:v for k,v in row.items() if not self.tables['ingest.match_coverage']['columns'][k].get('identity') and k not in ['recorded_from_gen','recorded_to_gen']}
                values['variant_key']='publisher:duplicate-best';self._insert('ingest.match_coverage',**values)
            elif kind=='wrong_period':self._replace('football.shots',self.shot_rows['m_000001'],period_code='not_a_period')
            elif kind=='wrong_actor':self._replace('football.shots',self.shot_rows['m_000001'],team_id=self.ids['teams'][4]['id'])
            else:raise ValueError(kind)
        rejection=self._reject('publisher_illegal_'+kind,action,states={'23503','23505','23514'})
        assert self.conn.execute('SELECT count(*) FROM football.shots').fetchone()[0]==before
        return rejection
