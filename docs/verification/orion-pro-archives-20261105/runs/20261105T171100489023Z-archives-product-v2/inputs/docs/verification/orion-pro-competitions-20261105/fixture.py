"""Synthetic competitions on immutable103; specified before the reader."""
from __future__ import annotations
from datetime import date
from decimal import Decimal
import hashlib
from pathlib import Path
import importlib.util

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('competition_base_reader_fixture',ROOT/'docs/verification/orion-pro-readers-20261104/fixture.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
ReaderFixture,NOW,hashed=base.ReaderFixture,base.NOW,base.hashed
CODE=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()

class CompetitionFixture(ReaderFixture):
    def prepare_competitions(self):
        self.snapshots=[];self.match_rows={};self.match_keys={};self.scores={};self.competitions={}
        with self.conn.transaction():
            for name,t in self.tables.items():
                if t['phase']!='models' and 'relation_code' in t['columns']:
                    self.conn.execute("INSERT INTO ingest.relation_contracts(relation_code,relation_name,contract_version,grain_definition) VALUES(%s,%s,'pilot_v1',%s) ON CONFLICT DO NOTHING",(name,name,t['grain']))
            for prefix in ('','other_'):
                src=self._insert('ingest.sources',code='competition_fixture_'+prefix+'source',name='Synthetic cup source '+prefix)
                dataset=self._insert('ingest.source_datasets',source_id=src['id'],dataset_key='cups',contract_version='pilot_v1',source_url='https://fixture.invalid/cups',license_code='fixture-license')
                _,record=self._record(src['id'],dataset['id'],'competition_fixture_'+prefix+'metadata')
                self.ids.update({prefix+'source':src['id'],prefix+'record':record['id']})
        observed=dict(source_id=self.ids['source'],source_record_id=self.ids['record'])
        with self._generation('competition_route_inputs') as g:
            self.route_generation=g;self.data1=g
            self.ids['teams']=[self._insert('football.teams',slug=f'cup-team-{i}',name=f'Identity {i}',team_type='club',gender='men') for i in range(1,9)]
            for i,t in enumerate(self.ids['teams'],1):
                self._insert('football.team_profile_versions',team_id=t['id'],observed_at=NOW,display_name=f'Profile {i}',profile_context='provider_global',variant_key='provider:exact',**observed)
                self._insert('ingest.public_aliases',route_kind='team',public_key=f't_{i:06d}',team_id=t['id'])
            player=self._insert('football.players',display_name='Fixture striker')
            profile=self._insert('football.player_profile_versions',player_id=player['id'],observed_at=NOW,external_profile_version_id='cup-fixture-striker',display_name='Observed striker',profile_content_sha256=hashed('cup-fixture-striker'),profile_context='provider_global',variant_key='provider:exact',**observed)
            self._insert('ingest.public_aliases',route_kind='player',public_key='p_000001',player_id=player['id'])
            for index,(key,kind,slug,name) in enumerate([('A','cup','ESP_CUP_fixture','Fixture Cup'),('B','tournament','nations-league','Fixture Nations'),('C','league','fixture-league','Fixture League')],1):
                comp=self._insert('football.competitions',competition_type=kind,slug=slug,name=name,gender='men',**observed)
                self.competitions[key]=comp
                self._insert('ingest.public_aliases',route_kind='competition',public_key=f'l_{index:06d}',competition_id=comp['id'],competition_revision_id=comp['revision_id'])
                edition=self._insert('football.competition_seasons',competition_id=comp['id'],competition_revision_id=comp['revision_id'],season_key='2026/2027',label='Observed 2026/2027',status='active',**observed)
                self.editions[key]=edition
                members=self.ids['teams'][(index-1)*2:index*2]+(self.ids['teams'][6:] if key=='B' else [])
                for t in members:self._insert('football.competition_teams',competition_season_id=edition['id'],competition_season_revision_id=edition['revision_id'],team_id=t['id'],status='confirmed',**observed)
            def stage(key,code,kind,name,order):
                edition=self.editions[key]
                return self._insert('football.competition_stages',competition_season_id=edition['id'],competition_season_revision_id=edition['revision_id'],stage_key=code,stage_type=kind,name=name,sequence_no=order,**observed)
            def group(key,stage_row,code,name):
                return self._insert('football.competition_groups',competition_season_id=self.editions[key]['id'],stage_id=stage_row['id'],stage_revision_id=stage_row['revision_id'],group_key=code,name=name,**observed)
            group_stage=stage('A','groups','group','Observed group phase',1)
            semi=stage('A','semi','knockout','Semi-finals',2);final=stage('A','final','final','Final',3)
            self.groups=[group('A',group_stage,str(i+1),'Observed group '+str(i+1)) for i in range(2)]
            nations=stage('B','B','group','League B',1);nations_group=group('B',nations,'1','Group 1')
            nations_a=stage('B','A','group','League A',2);nations_group_a=group('B',nations_a,'1','Group 1')
            cases=[('A',semi,None,1,date(2026,11,1),1,'finished',(0,1),(1,0)),('A',semi,None,1,date(2026,11,8),2,'finished',(1,0),(1,0)),('A',final,None,None,None,None,'not_started',(0,1),None),('B',nations,nations_group,1,date(2026,11,4),None,'finished',(2,3),(2,0)),('C',None,None,None,date(2026,11,4),None,'finished',(4,5),(None,None)),('B',nations_a,nations_group_a,1,date(2026,11,5),None,'finished',(6,7),(1,1))]
            for i,(key,st,grp,number,day,leg,status,team_indices,score) in enumerate(cases,1):
                mid=f'm_{i:06d}';edition=self.editions[key]
                m=self._insert('football.matches',competition_season_id=edition['id'],competition_season_revision_id=edition['revision_id'],stage_id=st['id'] if st else None,stage_revision_id=st['revision_id'] if st else None,group_id=grp['id'] if grp else None,group_revision_id=grp['revision_id'] if grp else None,round_label=st['name'] if st else None,round_number=number,match_date=day,kickoff_precision='date' if day else 'unknown',leg_number=leg,tie_key='fixture-tie' if leg else None,status=status,publication_state='published',**observed)
                self.match_rows[mid]=m;self.match_keys[mid]=key;self.sides[mid]={}
                self._insert('ingest.public_aliases',route_kind='match',public_key=mid,match_id=m['id'],match_revision_id=m['revision_id'])
                for n,(side,index) in enumerate(zip(('home','away'),team_indices)):
                    t=self.ids['teams'][index]
                    mt=self._insert('football.match_teams',match_id=m['id'],match_revision_id=m['revision_id'],side=side,team_id=t['id'],participant_label=f'Observed team {index+1}',**observed)
                    self.sides[mid][side]=mt
                    if score is not None:
                        self.scores[(mid,side)]=self._insert('football.match_scores',match_id=m['id'],side=side,match_team_revision_id=mt['revision_id'],score_scope='final_without_shootout',goals=score[n],score_basis='played',**observed)
                    if i in (1,2):
                        periods={'regulation':score[n]}
                        if i==2:periods.update(after_extra_time=score[n],shootout=(3,4)[n])
                        for scope,goals in periods.items():self._insert('football.match_scores',match_id=m['id'],side=side,match_team_revision_id=mt['revision_id'],score_scope=scope,goals=goals,score_basis='played',**observed)
                if i==1:
                    home=self.sides[mid]['home']
                    self._insert('football.match_players',match_id=m['id'],team_id=home['team_id'],player_id=player['id'],profile_version_id=profile['id'],match_team_revision_id=home['revision_id'],squad_status='starter',is_starter=True,played=True,participation_evidence='Synthetic observed starter',**observed)
                    self._insert('football.shots',match_id=m['id'],team_id=home['team_id'],match_team_revision_id=home['revision_id'],player_id=player['id'],player_profile_version_id=profile['id'],external_shot_id='s_000001',minute=12,source_ordinal=0,is_goal=True,xg=0.82,**observed)
                    self._insert('ingest.match_coverage',match_id=m['id'],match_revision_id=m['revision_id'],feature_code='shots',coverage_state='available',collection_state='present',observed_row_count=1,checked_at=NOW,**observed)
            for i,grp in enumerate(self.groups):self.snapshots.append(self.add_standing(grp,i))
        self.initial_builds={key:self.build(key,g,g) for key in 'ABC'}
        self.publish(self.initial_builds,'competition_routes_published')
        return self.describe()

    def build(self,key,dg,cg):
        e=self.editions[key];data=self.conn.execute('SELECT id FROM ingest.dataset_snapshots WHERE generation=%s',(dg,)).fetchone()[0];cat=self.conn.execute('SELECT id FROM ingest.dataset_snapshots WHERE generation=%s',(cg,)).fetchone()[0]
        with self.conn.transaction():
            b=self._insert('analytics.aggregation_builds',competition_season_id=e['id'],competition_season_revision_id=e['revision_id'],dataset_snapshot_id=data,catalog_snapshot_id=cat,transform_version='competition_fixture_v1',metrics_contract_version='competition_fixture_v1',representation_version='summary-v1-shots-v1',code_commit='owned-competition-fixture-v1',code_content_sha256=CODE,dependencies_sha256=hashed([key,dg,cg]),environment_sha256=hashed('owned-competition-fixture-v1'),status='building')
            matches=[]
            for mid,m in self.match_rows.items():
                if self.match_keys[mid]!=key:continue
                matches.append(m);h=self.sides[mid]['home'];a=self.sides[mid]['away']
                goal=lambda side:self.scores.get((mid,side),{}).get('goals')
                self._insert('analytics.match_summary',build_id=b['id'],competition_season_id=e['id'],match_id=m['id'],match_revision_id=m['revision_id'],match_date=m['match_date'],kickoff_at=m['kickoff_at'],status=m['status'],home_team_id=h['team_id'],away_team_id=a['team_id'],home_label=h['participant_label'],away_label=a['participant_label'],score_scope='final_without_shootout' if (mid,'home') in self.scores else None,home_goals=goal('home'),away_goals=goal('away'),home_shootout_goals=3 if mid=='m_000002' else None,away_shootout_goals=4 if mid=='m_000002' else None)
            self._insert('analytics.competition_summary',build_id=b['id'],competition_season_id=e['id'],matches_count=len(matches),finished_matches_count=sum(m['status']=='finished' for m in matches),teams_count=4 if key=='B' else 2,players_count=int(key=='A'))
            self.conn.execute("UPDATE analytics.aggregation_builds SET status='ready',finished_at=CURRENT_TIMESTAMP WHERE id=%s",(b['id'],))
        return b['id']

    def add_standing(self,group,index,*,source=None,revision=1,scope='overall',record=None,points=Decimal('3.125')):
        edition=self.editions['A']
        snap=self._insert('football.standing_snapshots',competition_season_id=edition['id'],competition_season_revision_id=edition['revision_id'],stage_id=group['stage_id'],stage_revision_id=group['stage_revision_id'],group_id=group['id'],group_revision_id=group['revision_id'],scope=scope,group_label=group['name'],observed_at=NOW,source_id=source or self.ids['source'],source_record_id=record or self.ids['record'],data_revision=revision)
        for team,rank,played,value in [(self.ids['teams'][0],1,0,points),(self.ids['teams'][1],1,None,None)]:
            self._insert('football.standing_rows',snapshot_id=snap['id'],team_id=team['id'],rank=rank,played=played,wins=None,draws=0,losses=None,goals_for=2,goals_against=1,points=value,points_adjustment=Decimal('-0.125') if value is not None else None,source_label=('Observed '+str(index)+' '+str(team['id'])))
        return snap

    def correction(self,*,ambiguous=False):
        with self._generation('competition_route_standing_correction') as g:
            if ambiguous:
                snap=self.add_standing(self.groups[0],0,source=self.ids['other_source'],record=self.ids['other_record'])
            else:
                snap=self.add_standing(self.groups[0],0,revision=self.snapshots[0]['data_revision']+1,points=Decimal('7.875'))
                self.add_standing(self.groups[0],0,scope='home',points=Decimal('99.000'))
        build=self.build('A',g,g);self.publish({'A':build},'competition_route_corrected')
        return {'generation':g,'build':build,'snapshot':snap['id']}

    def home_only(self):
        with self._generation('competition_home_only_snapshot') as g:
            snap=self.add_standing(self.groups[0],0,scope='home',points=Decimal('99.000'))
        build=self.build('A',g,g);self.publish({'A':build},'competition_home_only_published')
        return {'generation':g,'build':build,'snapshot':snap['id']}

    def missing_match_alias(self):
        with self._generation('competition_alias_closed') as g:
            self.conn.execute("UPDATE ingest.public_aliases SET recorded_to_gen=%s WHERE route_kind='match' AND public_key='m_000005' AND recorded_to_gen IS NULL",(g,))
        build=self.build('C',g,g);self.publish({'C':build},'competition_missing_alias_published')
        return {'generation':g,'build':build}

    def large_competition_label(self):
        with self._generation('competition_large_label') as g:
            row=self._row('football.competitions','id=%s AND recorded_to_gen IS NULL AND is_canonical',(self.editions['B']['competition_id'],))
            self._replace('football.competitions',row,name='X'*(2*1024**2+1))
        build=self.build('B',g,g);self.publish({'B':build},'competition_large_label_published')
        return {'generation':g,'build':build}
