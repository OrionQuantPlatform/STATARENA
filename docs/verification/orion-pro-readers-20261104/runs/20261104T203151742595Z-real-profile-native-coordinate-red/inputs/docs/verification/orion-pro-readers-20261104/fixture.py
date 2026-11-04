"""Complete source-free typed publication fixture, specified before readers."""
from __future__ import annotations

from datetime import date
import hashlib
import json
from pathlib import Path
import sys

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[2]
PILOT=ROOT/'docs/verification/orion-pro-pilot-20261104'
sys.path.insert(0,str(PILOT))
from fixtures import PilotWorkflow,NOW,hashed

SELF_SHA=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


class ReaderFixture(PilotWorkflow):
    def prepare(self):
        with self.conn.transaction():
            for name,t in self.tables.items():
                if t['phase']!='models' and 'relation_code' in t['columns']:
                    self.conn.execute("INSERT INTO ingest.relation_contracts(relation_code,relation_name,contract_version,grain_definition) VALUES(%s,%s,'pilot_v1',%s) ON CONFLICT DO NOTHING",(name,name,t['grain']))
            src=self._insert('ingest.sources',code='reader_fixture',name='Synthetic reader fixture')
            dataset=self._insert('ingest.source_datasets',source_id=src['id'],dataset_key='reader_fixture',contract_version='pilot_v1')
            doc,record=self._record(src['id'],dataset['id'],'reader_fixture_metadata_only')
            other=self._insert('ingest.sources',code='reader_other_source',name='Synthetic competing source')
            other_dataset=self._insert('ingest.source_datasets',source_id=other['id'],dataset_key='reader_other_source',contract_version='pilot_v1')
            _,other_record=self._record(other['id'],other_dataset['id'],'reader_competing_metadata_only')
            self.ids.update(source=src['id'],record=record['id'],other_source=other['id'],other_record=other_record['id'])
        self.match_rows={};self.match_keys={};self.coverages={};self.scores={};self.shot_rows={}
        self.team_profiles=[];self.player_profiles=[]
        with self._generation('reader_initial') as g:
            self.data1=g
            self.ids['teams']=[self._insert('football.teams',slug=f'reader-team-{i}',name=f'Team identity {i}',team_type='club',gender='men') for i in range(5)]
            self.ids['players']=[self._insert('football.players',display_name=f'Player identity {i}') for i in range(3)]
            for i,t in enumerate(self.ids['teams']):
                desired='Shared team v1' if i==0 else f'Team {i} v1'
                common=dict(team_id=t['id'],observed_at=NOW,slug=t['slug'],team_type='club',gender='men')
                manual=self._insert('football.team_profile_versions',**common,display_name=desired if i==2 else f'Manual team {i}',profile_context='global',variant_key='manual:curated')
                legacy=None
                if i in (0,1):legacy=self._insert('football.team_profile_versions',**common,display_name=desired if i==1 else 'Legacy shared team',profile_context='legacy_normalized_global',variant_key='legacy:primary',source_id=src['id'],source_record_id=record['id'])
                provider=None
                if i!=2:provider=self._insert('football.team_profile_versions',**common,display_name='WRONG other-source team' if i==1 else desired,profile_context='provider_global',variant_key='provider:exact',source_id=other['id'] if i==1 else src['id'],source_record_id=other_record['id'] if i==1 else record['id'])
                self.team_profiles.append(legacy if i==1 else provider or manual)
                if i==0:self._insert('football.team_profile_versions',**common,display_name='WRONG noncanonical team',profile_context='provider_global',variant_key='provider:decoy',is_canonical=False,source_id=src['id'],source_record_id=record['id'])
                self._insert('ingest.public_aliases',route_kind='team',public_key=f't_{i+1:06d}',team_id=t['id'])
            for i,p in enumerate(self.ids['players']):
                desired='Shared striker v1' if i==0 else f'Striker {i} v1'
                common=dict(player_id=p['id'],observed_at=NOW)
                manual=self._insert('football.player_profile_versions',**common,external_profile_version_id=f'reader-manual-{i}',display_name=desired if i==2 else f'Manual striker {i}',profile_context='global',variant_key='manual:curated',profile_content_sha256=hashed(['manual-profile',i]))
                legacy=None
                if i in (0,1):legacy=self._insert('football.player_profile_versions',**common,external_profile_version_id=f'reader-legacy-{i}',display_name=desired if i==1 else 'Legacy shared striker',profile_context='legacy_normalized_global',variant_key=f'legacy-profile-{i}',profile_content_sha256=hashed(['legacy-profile',i]),source_id=src['id'],source_record_id=record['id'])
                provider=None
                if i!=2:provider=self._insert('football.player_profile_versions',**common,external_profile_version_id=f'reader-provider-{i}',display_name='WRONG other-source striker' if i==1 else desired,profile_context='provider_global',variant_key='provider:exact',profile_content_sha256=hashed(['provider-profile',i]),source_id=other['id'] if i==1 else src['id'],source_record_id=other_record['id'] if i==1 else record['id'])
                self.player_profiles.append(legacy if i==1 else provider or manual)
                if i==0:self._insert('football.player_profile_versions',**common,external_profile_version_id='reader-noncanonical-profile',display_name='WRONG noncanonical striker',profile_context='provider_global',variant_key='provider:decoy',is_canonical=False,profile_content_sha256=hashed('profile decoy'),source_id=src['id'],source_record_id=record['id'])
                self._insert('ingest.public_aliases',route_kind='player',public_key=f'p_{i+1:06d}',player_id=p['id'])
            competition=self._insert('football.competitions',slug='reader-league',name='Reader league',competition_type='league',gender='men')
            self.competition=competition
            self._insert('ingest.public_aliases',route_kind='competition',public_key='l_000001',competition_id=competition['id'],competition_revision_id=competition['revision_id'])
            seasons={'A':'2024/2025','B':'2025/2026','C':'2026/2027'}
            ordinal=0
            for key in 'ABC':
                edition=self._insert('football.competition_seasons',competition_id=competition['id'],competition_revision_id=competition['revision_id'],season_key=seasons[key],label='Reader '+key,status='completed')
                self.editions[key]=edition
                teams=(self.ids['teams'][0],self.ids['teams'][1 if key=='A' else 2]) if key!='C' else (self.ids['teams'][3],self.ids['teams'][4])
                for t in teams:self._insert('football.competition_teams',competition_season_id=edition['id'],competition_season_revision_id=edition['revision_id'],team_id=t['id'],status='confirmed')
                for i in range(3 if key=='A' else 1):
                    ordinal+=1;mid=f'm_{ordinal:06d}';unknown=key=='A' and i==2
                    match=self._insert('football.matches',competition_season_id=edition['id'],competition_season_revision_id=edition['revision_id'],match_date=None if unknown else date(2026,11,4),kickoff_precision='unknown' if unknown else 'date',status='not_started' if unknown else 'finished',publication_state='published',source_id=src['id'],source_record_id=record['id'])
                    self.match_rows[mid]=match;self.match_keys[mid]=key
                    self._insert('ingest.public_aliases',route_kind='match',public_key=mid,match_id=match['id'],match_revision_id=match['revision_id'])
                    sides={}
                    for side,t in zip(('home','away'),teams):
                        sides[side]=self._insert('football.match_teams',match_id=match['id'],match_revision_id=match['revision_id'],side=side,team_id=t['id'],participant_label=f'{side} observed label',source_id=src['id'],source_record_id=record['id'])
                        if not unknown:
                            goals=(1 if i==0 else 0) if side=='home' else 0
                            self.scores[(mid,side)]=self._insert('football.match_scores',match_id=match['id'],side=side,match_team_revision_id=sides[side]['revision_id'],score_scope='final_without_shootout',goals=goals,score_basis='played',source_id=src['id'],source_record_id=record['id'])
                    self.sides[mid]=sides
                    if i==0:
                        player=self.ids['players'][{'A':0,'B':1,'C':2}[key]]
                        profile=self.player_profiles[{'A':0,'B':1,'C':2}[key]]
                        self._insert('football.match_players',match_id=match['id'],team_id=teams[0]['id'],player_id=player['id'],profile_version_id=profile['id'],match_team_revision_id=sides['home']['revision_id'],squad_status='starter',played=True,participation_evidence='synthetic reader fixture',source_id=src['id'],source_record_id=record['id'])
                    state='present' if mid in ('m_000001','m_000004') else 'empty' if mid=='m_000002' else 'unavailable'
                    if key!='C':
                        self.coverages[mid]=self._insert('ingest.match_coverage',match_id=match['id'],match_revision_id=match['revision_id'],source_id=src['id'],source_record_id=record['id'],feature_code='shots',coverage_state='available' if state=='present' else 'empty_response' if state=='empty' else 'unavailable',collection_state=state,observed_row_count=1 if state=='present' else 0 if state=='empty' else None,checked_at=NOW)
                    if state=='present':
                        shot=self._insert('football.shots',match_id=match['id'],team_id=teams[0]['id'],match_team_revision_id=sides['home']['revision_id'],player_id=player['id'],player_profile_version_id=profile['id'],external_shot_id='s_000001',period_code='first_half',period_definition_version='bootstrap_v1',minute=12,xg=0.82 if key=='A' else 0.99,xgot=0.0,is_goal=True,is_own_goal=False,source_event_type='' if key=='A' else 'Goal',x_m=52.5,y_m=34.0,coordinate_frame='acting_ltr' if key=='A' else 'home_ltr',pitch_length_m=105.0,pitch_width_m=68.0,source_ordinal=0,source_id=src['id'],source_record_id=record['id'])
                        self.shot_rows[mid]=shot
                        if key=='A':
                            decoy={k:v for k,v in shot.items() if not self.tables['football.shots']['columns'][k].get('identity') and k not in ('recorded_from_gen','recorded_to_gen')}
                            decoy.update(variant_key='reader:decoy',is_canonical=False,xg=0.01)
                            self._insert('football.shots',**decoy)
                            self._insert('ingest.match_coverage',match_id=match['id'],match_revision_id=match['revision_id'],source_id=src['id'],source_record_id=record['id'],feature_code='shots',coverage_state='available',collection_state='present',observed_row_count=1,checked_at=NOW,variant_key='reader:decoy',is_canonical=False)
        self.initial_builds={key:self.build(key,self.data1,self.data1) for key in 'ABC'}
        self.publish(self.initial_builds,'reader_initial_publication')
        return self.describe()

    def build(self,key,data_gen,catalog_gen):
        data_id=self.conn.execute('SELECT id FROM ingest.dataset_snapshots WHERE generation=%s',(data_gen,)).fetchone()[0]
        cat_id=self.conn.execute('SELECT id FROM ingest.dataset_snapshots WHERE generation=%s',(catalog_gen,)).fetchone()[0]
        edition=self.editions[key]
        with self.conn.transaction():
            b=self._insert('analytics.aggregation_builds',competition_season_id=edition['id'],competition_season_revision_id=edition['revision_id'],dataset_snapshot_id=data_id,catalog_snapshot_id=cat_id,representation_version='summary-v1-shots-v1',code_commit=SELF_SHA,code_content_sha256=SELF_SHA,dependencies_sha256=hashed({'key':key,'data':data_gen,'catalogue':catalog_gen}),environment_sha256=hashed({'engine':'18.6','fixture':'reader'}),metrics_contract_version='reader_v1',status='building')
            rows=[]
            for mid,m in self.match_rows.items():
                if self.match_keys[mid]!=key:continue
                scores={side:self.conn.execute("SELECT goals FROM football.match_scores WHERE match_id=%s AND side=%s AND score_scope='final_without_shootout' AND is_canonical AND NOT is_deleted AND recorded_from_gen<=%s AND (recorded_to_gen IS NULL OR %s<recorded_to_gen)",(m['id'],side,data_gen,data_gen)).fetchone() for side in ('home','away')}
                sides=self.sides[mid]
                self._insert('analytics.match_summary',build_id=b['id'],competition_season_id=edition['id'],match_id=m['id'],match_revision_id=m['revision_id'],match_date=m['match_date'],kickoff_at=m['kickoff_at'],status=m['status'],home_team_id=sides['home']['team_id'],away_team_id=sides['away']['team_id'],home_label=sides['home']['participant_label'],away_label=sides['away']['participant_label'],score_scope='final_without_shootout' if scores['home'] else None,home_goals=scores['home'][0] if scores['home'] else None,away_goals=scores['away'][0] if scores['away'] else None)
                rows.append(m)
            self._insert('analytics.competition_summary',build_id=b['id'],competition_season_id=edition['id'],matches_count=len(rows),finished_matches_count=sum(m['status']=='finished' for m in rows),teams_count=2,players_count=1)
            self.conn.execute("UPDATE analytics.aggregation_builds SET status='ready',finished_at=CURRENT_TIMESTAMP WHERE id=%s",(b['id'],))
        return b['id']

    def publish(self,builds,label):
        self._publish(builds,label)

    def correct(self):
        with self._generation('reader_data_correction') as g:
            self.data2=g
            self.shot_rows['m_000001']=self._replace('football.shots',self.shot_rows['m_000001'],xg=0.67)
            self.scores[('m_000001','home')]=self._replace('football.match_scores',self.scores[('m_000001','home')],goals=2)
        with self._generation('reader_later_catalogue_correction') as g:
            self.catalog2=g
            self.team_profiles[0]=self._replace('football.team_profile_versions',self.team_profiles[0],display_name='Shared team corrected')
            self.player_profiles[0]=self._replace('football.player_profile_versions',self.player_profiles[0],display_name='Shared striker corrected',profile_content_sha256=hashed('reader corrected profile'),external_profile_version_id='reader-profile-corrected')
        self.corrected_builds={key:self.build(key,self.data2,self.catalog2) for key in 'AB'}
        self.publish(self.corrected_builds,'reader_corrected_publication')
        return self.describe()

    def republish(self):
        names=('analytics.aggregation_builds','analytics.publication_versions','ingest.dataset_snapshots','football.shots')
        before={name:self.conn.execute(f'SELECT count(*) FROM {name}').fetchone()[0] for name in names}
        rejected=None
        try:self.publish(self.corrected_builds,'reader_identical_build_republication')
        except self.psycopg.Error as exc:
            assert exc.sqlstate=='23514' and 'Identical typed reimport' in str(exc),str(exc)
            rejected={'sqlstate':exc.sqlstate,'message':exc.diag.message_primary}
        assert rejected,'An equal publication should retain the existing typed version'
        after={name:self.conn.execute(f'SELECT count(*) FROM {name}').fetchone()[0] for name in names}
        assert before==after
        return {'sameBuilds':self.corrected_builds,'before':before,'after':after,'noOpGuard':rejected}

    def describe(self):
        return {'data1':self.data1,'data2':getattr(self,'data2',None),'catalog2':getattr(self,'catalog2',None),
                'initialBuilds':self.initial_builds,'correctedBuilds':getattr(self,'corrected_builds',{}),
                'editions':{k:{'id':v['id'],'season':v['season_key']} for k,v in self.editions.items()},
                'matches':{mid:{'id':m['id'],'revision':m['revision_id'],'edition':self.match_keys[mid]} for mid,m in self.match_rows.items()}}
