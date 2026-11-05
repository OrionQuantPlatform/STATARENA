"""Representative typed/native31 inputs authored before the appearance reader.

All source descriptors are synthetic; no source/provider/cloud data is read.
"""
from datetime import date,timedelta
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'docs/verification/orion-pro-entities-20261105'),
             str(ROOT/'docs/verification/orion-pro-entity-batch-media-20261105'),
             str(ROOT/'docs/verification/orion-pro-pilot-20261104')]
from entity_fixture import EntityFixture
from fixtures import NOW,hashed
from media_fixture import png

VERSION='real_source_core_v2_native31'
SHA=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
MISSING=object()
NATIVE={
    'goals':'goals','assists':'assists','shots':'shots','shotsOnTarget':'shots_on_target',
    'chancesCreated':'chances_created','bigChancesCreated':'big_chances_created',
    'passesAccurate':'passes_completed','passesAttempted':'passes_attempted','passesFinalThird':'passes_final_third',
    'defensiveActions':'defensive_actions','interceptions':'interceptions','tackles':'tackles','recoveries':'recoveries',
    'duelsWon':'duels_won','duelsLost':'duels_lost','aerialsWon':'aerial_duels_won','aerialDuels':'aerial_duels_attempted',
    'touches':'touches','touchesBox':'touches_box','clearances':'clearances','blocks':'blocks',
    'dribbles':'dribbles_completed','dribblesAttempted':'dribbles_attempted','saves':'saves',
    'xg':'xg','npxg':'non_penalty_xg','xa':'xa','xgot':'xgot','minutes':'minutes_played',
    'rating':'provider_rating','goalsPrevented':'goals_prevented',
}

def state(value):
    if value is MISSING:return ['absent',None]
    if value is None:return ['null',None]
    if isinstance(value,bool):return ['boolean',value]
    if isinstance(value,str):return ['string',value]
    return ['number',str(value)]


class AppearanceFixture(EntityFixture):
    def source_record(self,locator,kind,key,ordinal=None):
        return self._insert('ingest.source_records',document_id=self.doc['id'],source_id=self.ids['source'],
            locator_kind='json_pointer',locator=locator,record_kind=kind,external_key=key,ordinal=ordinal)

    def values(self,player,round_no):
        values={field:(player%5)+1 for field in NATIVE}
        values.update(minutes=90,rating=Decimal('6.0')+Decimal(player%7)/10,
            goals=int((player+round_no)%5==0),assists=int((player+round_no)%7==0),
            shots=3+player%3,shotsOnTarget=1+player%2,passesAccurate=30+player,passesAttempted=50+player,
            aerialsWon=player%3,aerialDuels=2+player%3,dribbles=player%3,dribblesAttempted=2+player%3,
            xg=Decimal(player%7+1)/10,npxg=Decimal(player%7+1)/10,xa=Decimal(player%3)/10,
            xgot=Decimal(player%4)/10,goalsPrevented=Decimal('-0.2') if player%3==0 else Decimal('0.1'))
        if player==0:
            values['minutes']=45 if round_no==0 else 90
            values['rating']=10 if round_no==0 else 6
        if player==1 and round_no==0:
            values.update(assists=MISSING,xa=None,shots='07',dribbles='',duelsLost=False)
        if player==2 and round_no==0:values['goals']=False
        if player==3 and round_no==0:values['xg']=Decimal('0.8200000000000000001')
        if player==8 and round_no==0:values['goalsPrevented']='Infinity'
        if player==9 and round_no==0:values['xgot']='NaN'
        if player==31 and round_no==0:values['minutes']=None
        return values

    def prepare_appearances(self):
        baseline=super().prepare_entities()
        dataset=self.conn.execute('SELECT id FROM ingest.source_datasets WHERE source_id=%s ORDER BY id LIMIT 1',(self.ids['source'],)).fetchone()[0]
        with self.conn.transaction():
            self.doc,self.contract_record=self._record(self.ids['source'],dataset,'appearance_native31_synthetic')
            for relation in ['football.player_match_stats','football.player_match_metric_values']:
                self.conn.execute('''INSERT INTO ingest.relation_contracts(relation_code,relation_name,contract_version,grain_definition)
                    VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING''',(relation,relation,VERSION,'Synthetic complete native31 normalized performance'))
        self.cohort_teams=[];self.cohort_players=[];self.observed_profiles=[];self.performance_rows=[];self.native_copy=[];self.cohort_stats=[]
        self.cohort_coverages=[];self.expected=[];self.team_stat_rows=[]
        media_folder=self.evidence/'inputs/media';media_folder.mkdir(parents=True,exist_ok=True)
        self.media={}
        for key,pixel in [('A',(255,128,0,255)),('B',(0,128,255,255))]:
            blob=png(pixel);digest=hashlib.sha256(blob).hexdigest();(media_folder/(key+'.png')).write_bytes(blob)
            self.media[key]={'sha256':digest,'key':'raw/media/'+digest+'.png','bytes':len(blob),'path':'inputs/media/'+key+'.png'}
        a=self.media['A']
        self.asset=self._insert('ingest.media_assets',storage_bucket='source-free-no-cloud',storage_key=a['key'],content_sha256=a['sha256'],
            content_type='image/png',source_url='https://provenance.fixture.invalid/appearance.png',author='Synthetic appearance E2E',license_code='CC0',retrieved_at=NOW)
        with self._generation('appearance_native31_fixture') as g:
            self.appearance_g=g
            for field in NATIVE:
                self._insert('football.metric_definitions',code='legacy_normalized_'+field,label=field,
                    definition='Synthetic normalized '+field+'; exact scalar type and presence are retained',unit='source_native',scope='player',aggregation='none',
                    allows_negative=field in ['rating','goalsPrevented'],definition_version=VERSION,source_id=self.ids['source'],source_record_id=self.contract_record['id'])
            self.editions['E']=self._insert('football.competition_seasons',competition_id=self.competition['id'],competition_revision_id=self.competition['revision_id'],
                season_key='2023/2024',label='Representative native31 cohort',status='completed')
            for index in range(12):
                team=self._insert('football.teams',slug=f'cohort-team-{index}',name=f'MUTABLE identity team{index}',team_type='club',gender='men')
                self.cohort_teams.append(team)
                self._insert('ingest.public_aliases',route_kind='team',public_key=f't_{100001+index:06d}',team_id=team['id'])
                self._insert('football.team_profile_versions',team_id=team['id'],display_name=f'Cohort club {index+1:02d}',observed_at=NOW,
                    source_id=self.ids['source'],source_record_id=self.contract_record['id'],profile_context='provider_global',variant_key='provider:exact')
                self._insert('football.competition_teams',competition_season_id=self.editions['E']['id'],competition_season_revision_id=self.editions['E']['revision_id'],team_id=team['id'])
            for index in range(32):
                player=self._insert('football.players',display_name=f'MUTABLE identity player{index}')
                self.cohort_players.append(player)
                profile=self._insert('football.player_profile_versions',player_id=player['id'],external_profile_version_id=f'cohort_observed_{index+1:02d}',
                    display_name=f'Cohort player {index+1:02d}',observed_at=NOW,profile_context='normalized_performance_observation_v1',variant_key='source:exact',
                    image_asset_id=self.asset['id'] if index==0 else None,profile_content_sha256=hashed(['appearance observed',index]),
                    source_id=self.ids['source'],source_record_id=self.contract_record['id'])
                self.observed_profiles.append(profile)
                self._insert('ingest.public_aliases',route_kind='player',public_key=f'p_{100001+index:06d}',player_id=player['id'])
                self._insert('ingest.public_aliases',route_kind='profile',public_key=profile['external_profile_version_id'],player_id=player['id'],profile_version_id=profile['id'])
                if index<2:
                    self._insert('football.player_profile_versions',player_id=player['id'],external_profile_version_id=f'cohort_global_decoy_{index}',
                        display_name=f'WRONG preferred resource {index}',observed_at=NOW,profile_context='provider_global',variant_key='provider:exact',
                        profile_content_sha256=hashed(['appearance global decoy',index]),source_id=self.ids['source'],source_record_id=self.contract_record['id'])
            for round_no in range(6):
                for pair in range(6):
                    number=round_no*6+pair;mid=f'm_{100001+number:06d}';day=None if number==35 else date(2023,9,1)+timedelta(days=round_no*7+pair)
                    record=self.source_record(f'/matches/{number}','fixture',mid,number)
                    match=self._insert('football.matches',competition_season_id=self.editions['E']['id'],competition_season_revision_id=self.editions['E']['revision_id'],
                        match_date=day,kickoff_precision='date' if day else 'unknown',status='finished',publication_state='published',source_id=self.ids['source'],source_record_id=record['id'])
                    self.match_rows[mid]=match;self.match_keys[mid]='E';self.sides[mid]={}
                    self._insert('ingest.public_aliases',route_kind='match',public_key=mid,match_id=match['id'],match_revision_id=match['revision_id'])
                    team_indices=[pair*2,pair*2+1];members=[]
                    for side,team_index in zip(['home','away'],team_indices):
                        team=self.cohort_teams[team_index]
                        parent=self._insert('football.match_teams',match_id=match['id'],match_revision_id=match['revision_id'],team_id=team['id'],side=side,
                            participant_label=f'Cohort club {team_index+1:02d}',source_id=self.ids['source'],source_record_id=record['id'])
                        self.sides[mid][side]=parent
                        goals=sum(int(v['goals']) for p in range(32) if p%12==team_index and isinstance((v:=self.values(p,round_no))['goals'],(int,Decimal)) and not isinstance(v['goals'],bool))
                        self._insert('football.match_scores',match_id=match['id'],side=side,score_scope='final_without_shootout',score_basis='played',goals=goals,
                            match_team_revision_id=parent['revision_id'],source_id=self.ids['source'],source_record_id=record['id'])
                        team_stats=self._insert('football.team_match_stats',match_id=match['id'],team_id=team['id'],match_team_revision_id=parent['revision_id'],
                            period_code='full_match',period_definition_version='bootstrap_v1',shots=8+team_index,shots_on_target=3+team_index%3,
                            xg=1.0+team_index/10,possession_pct=50.0,passes_completed=300+team_index,passes_attempted=400+team_index,
                            touches_box=15+team_index,corners=3,duels_won=20+team_index,tackles=10+team_index,interceptions=8+team_index,
                            saves=2,quality_flags={'stats_reliable':not(round_no==0 and pair==0)},
                            source_id=self.ids['source'],source_record_id=record['id'])
                        self.team_stat_rows.append(team_stats)
                        for player_index in range(32):
                            if player_index%12!=team_index:continue
                            values=self.values(player_index,round_no);pid=f'p_{100001+player_index:06d}';performance=f'performance_{round_no+1}_{player_index+1:02d}'
                            sr=self.source_record(f'/performances/{round_no}/{player_index}','performance',performance,player_index)
                            position=MISSING if player_index==5 and round_no==0 else '91' if player_index==4 and round_no==0 else 91
                            shirt=MISSING if player_index==6 and round_no==0 else None if player_index==7 and round_no==0 else '07' if player_index==1 else player_index%10
                            raw=lambda value:({'raw_position_code':str(value),'raw_position_code_state':'string' if isinstance(value,str) else 'number',
                                                'raw_position_code_source_number':None if isinstance(value,str) else value} if value is not MISSING else {})
                            shirt_fields={} if shirt is MISSING else {'shirt_number':None if shirt is None else str(shirt),'shirt_number_state':'null' if shirt is None else 'string' if isinstance(shirt,str) else 'number',
                                                                    'shirt_number_source_number':shirt if isinstance(shirt,int) else None}
                            starter=None if player_index==29 and round_no==0 else True
                            captain=None if player_index==28 and round_no==0 else player_index<12
                            quality={} if player_index==30 and round_no==0 else {'stats_reliable':not(player_index==0 and round_no==0)}
                            participant=self._insert('football.match_players',match_id=match['id'],team_id=team['id'],player_id=self.cohort_players[player_index]['id'],
                                profile_version_id=self.observed_profiles[player_index]['id'],match_team_revision_id=parent['revision_id'],squad_status='starter' if starter is True else 'observed',is_starter=starter,
                                played=True,participation_evidence='Synthetic complete normalized performance',is_captain=captain,
                                raw_pitch_x=30.0 if player_index==0 else None,raw_pitch_y=40.0 if player_index==0 else None,
                                coordinate_frame='fixture_raw_untransformed' if player_index==0 else None,
                                source_id=self.ids['source'],source_record_id=sr['id'],**raw(position),**shirt_fields)
                            projections={target:(value if isinstance((value:=values[field]),(int,float,Decimal)) and not isinstance(value,bool) else None) for field,target in NATIVE.items()}
                            stats=self._insert('football.player_match_stats',match_id=match['id'],player_id=participant['player_id'],team_id=team['id'],
                                match_player_revision_id=participant['revision_id'],period_code='full_match',period_definition_version='bootstrap_v1',
                                contract_version=VERSION,transform_version=VERSION,transform_code_sha256=SHA,quality_flags=quality,
                                source_id=self.ids['source'],source_record_id=sr['id'],**projections)
                            self.cohort_stats.append(stats);members.append(stats)
                            structural={'id':performance,'playerId':pid,'playerRef':self.observed_profiles[player_index]['external_profile_version_id'],
                                'name':f'Cohort player {player_index+1:02d}','teamId':f't_{100001+team_index:06d}','team':f'Cohort club {team_index+1:02d}',
                                'matchId':mid,'leagueId':'l_000001','league':'Reader league','country':None,'season':'2023/2024','date':day.isoformat() if day else None,
                                'starter':starter,'isCaptain':captain,'rawPitchX':30.0 if player_index==0 else None,'rawPitchY':40.0 if player_index==0 else None,
                                'coordinateFrame':'fixture_raw_untransformed' if player_index==0 else None,
                                'imageUrl':('https://cdn.fixture.invalid/data/'+a['key']) if player_index==0 else None}
                            if 'stats_reliable' in quality:structural['statsReliable']=quality['stats_reliable']
                            if position is not MISSING:structural['positionId']=position
                            if shirt is not MISSING:structural['shirtNumber']=shirt
                            descriptor={'structural':structural,'native':[[field,*state(values[field])] for field in NATIVE]}
                            self.expected.append(descriptor)
                            for field in NATIVE:
                                kind,value=state(values[field])
                                self.native_copy.append((match['id'],participant['player_id'],team['id'],'full_match','bootstrap_v1','standard','legacy_normalized_'+field,VERSION,
                                    kind,Decimal(value) if kind=='number' else None,value if kind=='string' else None,value if kind=='boolean' else None,
                                    sr['id'],self.ids['source'],'pilot:primary',True,g,VERSION,VERSION,SHA,'provider',participant['revision_id']))
                    self.cohort_coverages.append(self._insert('ingest.match_coverage',match_id=match['id'],match_revision_id=match['revision_id'],source_id=self.ids['source'],source_record_id=record['id'],
                        feature_code='normalized_performance',coverage_state='available',collection_state='present',observed_row_count=len(members),checked_at=NOW))
            columns='match_id,player_id,team_id,period_code,period_definition_version,family_code,metric_code,metric_definition_version,value_kind,numeric_value,text_value,boolean_value,source_record_id,source_id,variant_key,is_canonical,recorded_from_gen,contract_version,transform_version,transform_code_sha256,provenance_kind,match_player_revision_id'
            for start in range(0,len(self.native_copy),1000):
                with self.conn.cursor().copy('COPY football.player_match_metric_values ('+columns+') FROM STDIN') as copy:
                    for row in self.native_copy[start:start+1000]:copy.write_row(row)
        self.cohort_build=self.build('E',g,g);self.publish({'E':self.cohort_build},'appearance_native31_publication')
        source=self.evidence/'inputs/source-descriptors.json';source.write_text(json.dumps({'kind':'synthetic-input-not-real-source','producerVersion':VERSION,'rows':self.expected},indent=2)+'\n')
        return {'baseline':baseline,'generation':g,'build':self.cohort_build,'edition':self.editions['E']['id'],'matches':36,'performances':192,'nativeValues':len(self.native_copy),
                'sourceDescriptors':str(source.relative_to(self.evidence)),'sourceDescriptorSha256':hashlib.sha256(source.read_bytes()).hexdigest(),'media':self.media}

    def publish_data(self,g,label):
        build=self.build('E',g,self.appearance_g)
        self.publish({'E':build},label)
        return {'generation':g,'build':build}

    def native_row(self,field='xg'):
        stats=self.cohort_stats[0]
        return self._row('football.player_match_metric_values',
            "source_record_id=%s AND metric_code=%s AND is_canonical AND recorded_to_gen IS NULL AND family_code='standard' AND variant_key='pilot:primary'",
            (stats['source_record_id'],'legacy_normalized_'+field))

    def block_native(self):
        with self._generation('appearance_missing_native_state') as g:
            self.blocked_native=self._replace('football.player_match_metric_values',self.native_row(),is_canonical=False)
        return self.publish_data(g,'appearance_missing_native_publication')

    def restore_native(self):
        with self._generation('appearance_restore_native_state') as g:
            self._replace('football.player_match_metric_values',self.blocked_native,is_canonical=True)
        return self.publish_data(g,'appearance_restored_native_publication')

    def block_coverage(self):
        with self._generation('appearance_missing_coverage') as g:
            self.blocked_coverage=self._replace('ingest.match_coverage',self.cohort_coverages[0],is_canonical=False)
            self.cohort_coverages[0]=self.blocked_coverage
        return self.publish_data(g,'appearance_missing_coverage_publication')

    def restore_coverage(self):
        with self._generation('appearance_restore_coverage') as g:
            self.cohort_coverages[0]=self._replace('ingest.match_coverage',self.blocked_coverage,is_canonical=True)
        return self.publish_data(g,'appearance_restored_coverage_publication')

    def correction(self,value=Decimal('1.75')):
        with self._generation('appearance_correction') as g:
            self.cohort_stats[0]=self._replace('football.player_match_stats',self.cohort_stats[0],xg=value)
            self._replace('football.player_match_metric_values',self.native_row(),numeric_value=value)
        return self.publish_data(g,'appearance_correction_publication')

    def add_decoy(self):
        original=self.native_row()
        with self._generation('appearance_noncanonical_decoy') as g:
            copy={k:v for k,v in original.items() if k not in ['revision_id','recorded_from_gen','recorded_to_gen']}
            copy.update(variant_key='synthetic:decoy',is_canonical=False,numeric_value=Decimal('99.0'))
            self._insert('football.player_match_metric_values',**copy)
            other={**copy,'variant_key':'pilot:primary','is_canonical':True,'family_code':'advanced','numeric_value':Decimal('88.0')}
            self._insert('football.player_match_metric_values',**other)
        return self.publish_data(g,'appearance_decoy_publication')

    def change_media(self,key):
        media=self.media[key]
        self.conn.execute('UPDATE ingest.media_assets SET storage_key=%s,content_sha256=%s WHERE id=%s',
            (media['key'],media['sha256'],self.asset['id']))
        return {'assetId':self.asset['id'],**media}

    def invalid_nonfinite(self):
        self.bad_numbers=[]
        with self._generation('appearance_invalid_nonfinite') as g:
            for index,value in enumerate([Decimal('NaN'),Decimal('Infinity'),Decimal('-Infinity')]):
                old_stats=self.cohort_stats[index]
                old_native=self._row('football.player_match_metric_values','source_record_id=%s AND metric_code=%s AND is_canonical AND recorded_to_gen IS NULL AND family_code=%s',
                    (old_stats['source_record_id'],'legacy_normalized_goalsPrevented','standard'))
                bad_native=self._replace('football.player_match_metric_values',old_native,numeric_value=value)
                self.bad_numbers.append((index,old_stats,old_native,bad_native))
        return self.publish_data(g,'appearance_invalid_nonfinite_publication')

    def restore_numbers(self):
        with self._generation('appearance_restore_finite') as g:
            for index,old_stats,old_native,bad_native in self.bad_numbers:
                self._replace('football.player_match_metric_values',bad_native,numeric_value=old_native['numeric_value'])
        return self.publish_data(g,'appearance_restore_finite_publication')
