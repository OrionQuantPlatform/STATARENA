"""Synthetic typed native107 graphs, written before migration016.

Only metadata document witnesses are stored. Values below are synthetic SQL
fixtures, never real source bodies. The old reader fixture remains unchanged.
"""
from __future__ import annotations
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'docs/verification/orion-pro-readers-20261104'))
from fixture import ReaderFixture, NOW, hashed

CONTRACT='match-native-v1'
TRANSFORM='native107_fixture_v1'
SELF_SHA=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()

class NativeFixture(ReaderFixture):
    def bind107(self):
        self.model=json.loads((ROOT/'docs/architecture/orion-native-details-107-20261105/target-schema.approved-107.json').read_text())
        self.tables={t['qualified_name']:t for s in self.model['schemas'] for t in s['tables']}
        self.overrides={};self.observed={};self.allocated=[]
        for name,t in self.tables.items():
            if t['phase']!='models' and 'relation_code' in t['columns']:
                self.conn.execute('INSERT INTO ingest.relation_contracts(relation_code,relation_name,contract_version,grain_definition) VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING',(name,name,CONTRACT,t['grain']))

    def put(self, table, tag, **values):
        if 'contract_version' in self.tables[table]['columns']:
            values.update(contract_version=CONTRACT,transform_version=TRANSFORM,transform_code_sha256=SELF_SHA)
        values.update(self.overrides.get(tag,{}))
        row=self._insert(table,**values);self.observed[tag]=row
        for column,spec in self.tables[table]['columns'].items():
            if spec.get('identity'):self.allocated.append({'table':table,'column':column,'value':row[column]})
        return row

    def record(self, tag, doc, locator, ordinal=None, external=None):
        return self.put('ingest.source_records',tag,source_id=doc['source_id'],document_id=doc['id'],locator_kind='json_pointer',locator=locator,ordinal=ordinal,record_kind='native107_fixture',external_key=external)

    def profile(self, tag, record, actor, player=False, name='Synthetic observed actor'):
        common=dict(source_id=record['source_id'],source_record_id=record['id'],observed_at=NOW,
                    profile_context='native_match_observation_v1:'+str(record['id']),variant_key='source:exact',
                    display_name=name,source_name_state='null' if name is None else 'value',source_image_url_state='absent',source_external_id_state='value')
        if player:
            common.update(player_id=actor['id'],external_profile_version_id='native-observation:'+str(record['id']),profile_content_sha256=hashed([tag,record['id']]))
        else:common.update(team_id=actor['id'])
        return self.put('football.player_profile_versions' if player else 'football.team_profile_versions',tag,**common)

    def family(self, feature, label, overrides=None, *, empty=False):
        self.overrides=overrides or {};self.observed={};self.allocated=[]
        m=self.match_rows['m_000001'];sides=self.sides['m_000001'];source=self.ids['source']
        dataset=self.conn.execute('SELECT id FROM ingest.source_datasets WHERE source_id=%s ORDER BY id LIMIT 1',(source,)).fetchone()[0]
        doc,_=self._record(source,dataset,'native107-'+label)
        root=self.record('root',doc,'/data',external='m_000001')
        profile_ids={}
        for index,side in enumerate(('home','away')):
            actor=self.ids['teams'][index]
            record=self.record(side+'_root_record',doc,'/data/'+side+'_team',external='t_'+str(index+1).zfill(6))
            profile_ids[side]=self.profile(side+'_root_profile',record,actor)['id']
        count=0 if empty else {'events':2,'h2h':1,'stats':2,'lineups':2}[feature]
        if feature=='lineups':count=2
        coverage=self.put('ingest.match_coverage','coverage',match_id=m['id'],match_revision_id=m['revision_id'],source_id=source,source_record_id=root['id'],document_id=doc['id'],
                          feature_code=feature,variant_key='source:exact',is_canonical=True,coverage_state='available' if count else 'empty_response',collection_state='present' if count else 'empty',observed_row_count=count,checked_at=NOW,
                          source_match_id_state='value',source_home_team_state='object',source_away_team_state='object',source_home_team_profile_version_id=profile_ids['home'],source_away_team_profile_version_id=profile_ids['away'])
        key={k:coverage[k] for k in ('match_id','source_id','feature_code','variant_key','recorded_from_gen')}
        if feature=='events':
            for index in range(count):
                event=self.record('event_record_'+str(index),doc,'/data/events/'+str(index),index)
                team=self.record('event_team_'+str(index),doc,event['locator']+'/team_id',external='t_000001')
                actor_record=self.record('event_actor_record_'+str(index),doc,event['locator']+'/player',external='p_000001')
                profile=self.profile('event_profile_'+str(index),actor_record,self.ids['players'][0],True,name=None if index else '')
                self.put('football.match_events','event_'+str(index),**key,event_seq=index,source_ordinal=index,event_type=None if index else '',
                         source_event_type_state='null' if index else 'value',source_record_id=event['id'],minute=12,source_minute_state='value',
                         source_minute_added_state='absent',source_second_state='absent',source_is_penalty_state='value',is_penalty=False,source_is_own_goal_state='value',is_own_goal=False,
                         source_score_home_state='null',source_score_away_state='absent',source_period_label_state='value',source_period_label='first_half',
                         period_code='first_half',period_definition_version='bootstrap_v1',player_id=self.ids['players'][0]['id'],player_profile_version_id=profile['id'],source_player_state='object',
                         source_sub_in_player_state='absent',source_event_id_state='absent',source_team_id_state='value',team_id=self.ids['teams'][0]['id'],match_team_revision_id=sides['home']['revision_id'],match_revision_id=m['revision_id'])
        elif feature=='lineups':
            for index,side in enumerate(('home','away')):
                header=self.record(side+'_header_record',doc,'/data/'+side)
                n=0 if empty or side=='away' else 2
                lineup=self.put('football.match_lineups',side+'_lineup',match_id=m['id'],team_id=self.ids['teams'][index]['id'],match_team_revision_id=sides[side]['revision_id'],source_id=source,source_record_id=header['id'],variant_key='source:exact',lineup_type='observed',
                    source_collection_from_gen=self.g,source_object_state='object',formation='',source_formation_state='value',confirmed=False,source_confirmed_state='value',
                    source_lineup_type_state='absent',source_coach_state='null',source_coach_name_state='absent',source_starters_state='present' if n else 'empty',source_starters_count=n,source_subs_state='empty',source_subs_count=0)
                for ordinal in range(n):
                    record=self.record('member_record_'+str(ordinal),doc,header['locator']+'/starters/'+str(ordinal),ordinal,external='p_000001')
                    profile=self.profile('member_profile_'+str(ordinal),record,self.ids['players'][0],True)
                    self.put('football.match_players','member_'+str(ordinal),match_id=m['id'],team_id=self.ids['teams'][index]['id'],player_id=self.ids['players'][0]['id'],
                        profile_version_id=profile['id'],lineup_revision_id=lineup['revision_id'],match_team_revision_id=sides[side]['revision_id'],source_id=source,source_record_id=record['id'],
                        variant_key='native:slot:'+str(ordinal),is_canonical=False,squad_status='starter',is_starter=True,played=None,source_is_captain_state='value',is_captain=False,
                        source_raw_pitch_x_state='value',raw_pitch_x=Decimal('0.8200000000000000001'),source_raw_pitch_y_state='null',raw_pitch_y=None,coordinate_frame='unknown')
        elif feature=='stats':
            metric=self.put('football.metric_definitions','definition',code='native107_'+label.replace('-','_'),label='Synthetic exact metric',definition='Synthetic raw observation',unit='unknown',scope='team',aggregation='none',allows_negative=True,definition_version=label)
            mapping=self.put('football.source_metric_mappings','mapping',source_id=source,family_code='native107',raw_key='repeated',mapping_version=label,metric_code=metric['code'],metric_definition_version=label)
            for ordinal in range(count):
                period=self.record('period_record_'+str(ordinal),doc,'/data/periods/'+str(ordinal),ordinal)
                groups=0 if ordinal else 1
                self.put('football.match_team_stat_periods','period_'+str(ordinal),**key,source_record_id=period['id'],source_period_label='first_half',source_period_label_state='value',groups_state='present' if groups else 'empty',groups_count=groups)
                if not groups:continue
                group=self.record('group_record',doc,period['locator']+'/groups/0',0)
                self.put('football.match_team_stat_groups','group',**key,source_record_id=group['id'],period_source_record_id=period['id'],group_name='',group_name_state='value',items_state='present',items_count=2)
                for i in range(2):
                    item=self.record('item_record_'+str(i),doc,group['locator']+'/items/'+str(i),i)
                    refs={}
                    for side,index in [('home',0),('away',1)]:
                        scalar_record=self.record('scalar_record_'+side+str(i),doc,item['locator']+'/'+side)
                        refs[side]=self.put('football.team_match_metric_values','scalar_'+side+str(i),match_id=m['id'],team_id=self.ids['teams'][index]['id'],match_team_revision_id=sides[side]['revision_id'],
                            source_id=source,source_record_id=scalar_record['id'],period_code='first_half',period_definition_version='bootstrap_v1',family_code='native107',metric_code=metric['code'],metric_definition_version=label,
                            value_kind='number' if side=='home' else 'string',numeric_value=Decimal('9007199254740993') if side=='home' else None,text_value='' if side=='away' else None,
                            variant_key='native:item:'+str(i),is_canonical=False)['revision_id']
                    self.put('football.match_team_stat_items','item_'+str(i),**key,source_record_id=item['id'],group_source_record_id=group['id'],raw_key='repeated',raw_key_state='value',title='',title_state='value',format_type=None,format_type_state='null',home_metric_revision_id=refs['home'],away_metric_revision_id=refs['away'])
        elif feature=='h2h':
            self.put('football.match_h2h_summaries','summary',**key,home_wins=Decimal('9007199254740993'),home_wins_state='value',away_wins=None,away_wins_state='null',draws=Decimal('0'),draws_state='value',total_matches=Decimal('9007199254740993'),total_matches_state='value')
            for ordinal in range(count):
                entry=self.record('h2h_record_'+str(ordinal),doc,'/data/recent_matches/'+str(ordinal),ordinal)
                self.record('h2h_home_id',doc,entry['locator']+'/home/id',external='unresolved-home')
                self.record('h2h_away_id',doc,entry['locator']+'/away/id',external='')
                self.put('football.match_h2h_entries','h2h_'+str(ordinal),**key,source_record_id=entry['id'],entry_ordinal=ordinal,match_revision_id=m['revision_id'],external_match_id=None,source_external_match_id_state='absent',
                    source_finished=False,source_finished_state='value',home_score=None,source_home_score_state='null',away_score=None,source_away_score_state='absent',
                    time_utc_source='',source_time_utc_source_state='value',status_source=None,source_status_source_state='absent',home_label='',source_home_label_state='value',away_label=None,source_away_label_state='null',
                    source_home_state='object',source_away_state='object',source_home_image_url_state='null',source_away_image_url_state='absent',source_home_id_state='value',source_away_id_state='value')
        return {'coverage':coverage,'rows':self.observed,'allocated':self.allocated}
