"""Independent synthetic typed inputs/oracles; no hand-built analytical output."""
from __future__ import annotations
from contextlib import contextmanager
from datetime import date
import json
from pathlib import Path
import sys

BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[2]
sys.path[:0]=[str(ROOT/'docs/verification/orion-pro-readers-20261104'),str(ROOT/'docs/verification/orion-pro-pilot-20261104')]
from fixture import ReaderFixture
from fixtures import NOW,hashed
from workflow_budget import digest


class TypedInputs(ReaderFixture):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.suppressed=[];self.expected={};self.markers={'A':0,'shared':0,'C':0}

    def build(self,*args):self.suppressed.append({'hook':'build','args':args});return None
    def publish(self,*args):self.suppressed.append({'hook':'publish','builds':args[0]});return None

    def prepare_inputs(self):
        super().prepare()
        self.catalog_generation=self.data1
        with self._generation('publisher_shared_input_and_shootout') as g:
            self.data_generation=g
            b=self.match_rows['m_000004'];team=self.ids['teams'][0];player=self.ids['players'][0]
            self._insert('football.match_players',match_id=b['id'],team_id=team['id'],player_id=player['id'],profile_version_id=self.player_profiles[0]['id'],
                match_team_revision_id=self.sides['m_000004']['home']['revision_id'],squad_status='bench',played=False,
                participation_evidence='Synthetic explicitly admitted shared A/B squad observation; no appearance claimed',source_id=self.ids['source'],source_record_id=self.ids['record'])
            self.shared_b_shot=self._insert('football.shots',match_id=b['id'],team_id=team['id'],match_team_revision_id=self.sides['m_000004']['home']['revision_id'],
                player_id=player['id'],player_profile_version_id=self.player_profiles[0]['id'],external_shot_id='s_000002',period_code='second_half',period_definition_version='bootstrap_v1',
                minute=60,xg=.21,xgot=0,is_goal=False,is_own_goal=False,is_on_target=False,source_event_type='',x_m=20,y_m=10,coordinate_frame='acting_ltr',
                pitch_length_m=105,pitch_width_m=68,source_ordinal=1,source_id=self.ids['source'],source_record_id=self.ids['record'])
            self.coverages['m_000004']=self._replace('ingest.match_coverage',self.coverages['m_000004'],observed_row_count=2)
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
        metadata=self.conn.execute('SELECT r.id,r.source_id,r.document_id,d.content_sha256,r.locator_kind,r.locator FROM ingest.source_records r JOIN ingest.source_documents d ON d.id=r.document_id WHERE r.source_id=%s ORDER BY r.id',(self.ids['source'],)).fetchall()
        self.source_evidence=[{'recordId':r[0],'sourceId':r[1],'documentId':r[2],'contentSha256':r[3],'locatorKind':r[4],'locator':r[5]} for r in metadata]
        return self.input_oracle()

    def input_oracle(self):
        assert len(self.suppressed)==4 and all(v is None for v in self.initial_builds.values())
        assert self.conn.execute('SELECT count(*) FROM analytics.aggregation_builds').fetchone()[0]==0
        assert self.conn.execute('SELECT count(*) FROM analytics.publication_versions').fetchone()[0]==0
        observed={}
        for mid,want in self.expected.items():
            m=self.match_rows[mid]
            row=self.conn.execute('SELECT match_date,status,publication_state,competition_season_id FROM football.matches WHERE revision_id=%s',(m['revision_id'],)).fetchone()
            assert (row[0].isoformat() if row[0] else None,row[1],row[2],row[3])==(want['date'],want['status'],'published',self.editions[want['key']]['id'])
            for side in ['home','away']:
                score=self.conn.execute("SELECT goals FROM football.match_scores WHERE match_id=%s AND side=%s AND score_scope='final_without_shootout' AND is_canonical AND recorded_to_gen IS NULL",(m['id'],side)).fetchone()
                assert (score[0] if score else None)==want[side]
            observed[mid]={'matchId':m['id'],'revision':m['revision_id'],'expectedSha256':digest(want)}
        counts={'A':{'matches':3,'finished':2,'teams':2,'players':1},'B':{'matches':1,'finished':1,'teams':2,'players':2},'C':{'matches':1,'finished':1,'teams':2,'players':1}}
        for key,e in self.editions.items():
            actual=self.conn.execute('SELECT count(*) FROM football.competition_teams WHERE competition_season_id=%s AND recorded_to_gen IS NULL AND is_canonical AND NOT is_deleted',(e['id'],)).fetchone()[0]
            assert actual==counts[key]['teams']
            actual=self.conn.execute('SELECT count(DISTINCT p.player_id) FROM football.match_players p JOIN football.matches m ON m.id=p.match_id AND m.recorded_to_gen IS NULL WHERE m.competition_season_id=%s AND p.recorded_to_gen IS NULL AND p.is_canonical AND NOT p.is_deleted',(e['id'],)).fetchone()[0]
            assert actual==counts[key]['players']
        return {'suppressedHooks':self.suppressed,'noAnalyticalOutputs':True,'matches':observed,'expectedCounters':counts,
                'dataGeneration':self.data_generation,'catalogGeneration':self.catalog_generation,'expectedStateSha256':digest(self.expected)}

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
                    'coverageRevision':coverage['revision_id'] if coverage else None,'selectedShotObservations':observations,
                    'declaredShotsCount':(2 if mid=='m_000004' else 1) if w['shots']=='present' else 0 if w['shots']=='empty' else None})
            scopes.append({'fixtureKey':key,'editionId':e['id'],'editionRevision':e['revision_id'],'season':e['season_key'],'intendedMatches':members})
        return {'schemaVersion':1,'kind':'synthetic_declared_business_admission','fixtureOnly':True,
          'businessDecision':'Explicit synthetic software-test scope; not authorization or evidence of real source acceptance',
          'representationVersion':'summary-v1-shots-v1','sourcePolicy':'pilot_priority_v1','allowedSourceIds':[self.ids['source']],
          'sourceEvidence':self.source_evidence,
          'datasetGeneration':self.data_generation,'catalogGeneration':self.catalog_generation,'editions':scopes,
          'declaredTypes':{'match_date':['date','null'],'score':['integer','null'],'shot_expected_goals':['number','null'],
            'source_event_type':['string','null'],'is_goal':['boolean','null'],'shots_state':['present','empty','unavailable','unknown']},
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
            self.scores[('m_000001','home')]=self._replace('football.match_scores',self.scores[('m_000001','home')],goals=goals)
            self.shot_rows['m_000001']=self._replace('football.shots',self.shot_rows['m_000001'],xg=xg)
            self.mark_dirty('A',g)
        self.expected['m_000001']['home']=goals;self.markers['A']+=1
        return {'affectedKeys':['A'],'dataGeneration':g,'catalogGeneration':self.catalog_generation}

    def correct_shared_catalogue(self):
        with self._generation('publisher_shared_catalogue_via_B') as g:
            self.catalog_generation=g
            self.team_profiles[0]=self._replace('football.team_profile_versions',self.team_profiles[0],display_name='Shared team corrected')
            self.player_profiles[0]=self._replace('football.player_profile_versions',self.player_profiles[0],display_name='Shared striker corrected',
                external_profile_version_id='publisher-corrected-shared',profile_content_sha256=hashed('publisher corrected shared'))
            self.mark_dirty('B',g)
        for value in self.expected.values():
            if value['key'] in ['A','B']:value['homeName']='Shared team corrected'
        self.markers['shared']+=1
        return {'affectedKeys':['A','B'],'dataGeneration':self.data_generation,'catalogGeneration':g,'dirtyHintOnly':'B'}

    def correct_C_data(self):
        goals=3 if self.markers['C']==0 else self.expected['m_000005']['home']+1
        with self._generation('publisher_C_independent_correction') as g:
            self.data_generation=g
            self.scores[('m_000005','home')]=self._replace('football.match_scores',self.scores[('m_000005','home')],goals=goals)
            self.mark_dirty('C',g)
        self.expected['m_000005']['home']=goals;self.markers['C']+=1
        return {'affectedKeys':['C'],'dataGeneration':g,'catalogGeneration':self.catalog_generation}

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
                    row=self._row('football.competition_teams','competition_season_id=%s AND team_id=%s AND recorded_to_gen IS NULL',(self.editions['C']['id'],self.ids['teams'][3]['id']))
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
                    if kind=='draft':self._replace('football.matches',changed,is_deleted=True)
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
