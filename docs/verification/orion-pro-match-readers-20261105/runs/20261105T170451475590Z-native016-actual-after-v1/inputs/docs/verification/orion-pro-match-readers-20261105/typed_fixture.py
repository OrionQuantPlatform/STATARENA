"""Owned SQL fixture for six match readers; written before serving code.

It inserts typed observations from independent synthetic_inputs.py. It does not
fabricate READY builds or publication digests: a separate ordinary writer
computes the joint digest from actual sealed typed tuples for this fixture.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'docs/verification/orion-pro-readers-20261104'))
from fixture import ReaderFixture, NOW, hashed
from synthetic_inputs import source_descriptors, stats, match

CONTRACT = 'match-native-v1'
TRANSFORM = 'native_match_http_fixture_v1'
CODE_SHA = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
PRIMARY = {'A': 'm_000001', 'B': 'm_000004', 'C': 'm_000005'}
ARRAY_KEYS = {'events': 'events', 'h2h': 'recent_matches', 'stats': 'periods', 'momentum': 'points'}


def state(data, key, value_state='value'):
    return 'absent' if key not in data else 'null' if data[key] is None else value_state


def fields(data, mapping):
    return {key: value for source, (column, state_column) in mapping.items()
            for key, value in [(column, data.get(source)), (state_column, state(data, source))]}


def array(data, key):
    kind = state(data, key, 'present')
    if kind != 'present':
        return kind, None
    return ('present', len(data[key])) if data[key] else ('empty', 0)


def native_code(data, source, target):
    value = data.get(source)
    kind = state(data, source)
    if kind == 'value':
        assert type(value) in (str, int, Decimal), (source, type(value))
        kind = 'string' if type(value) is str else 'number'
    return {target: str(value) if kind in ('string', 'number') else None,
            target + '_state': kind,
            target + '_source_number': Decimal(value) if kind == 'number' else None}


class MatchReaderFixture(ReaderFixture):
    def _insert(self, table, **values):
        # Give the canonical league a separately stored delivery asset. The
        # native core's observed league URL must never resolve from this row.
        if table == 'football.competitions' and not getattr(self, 'delivery_asset', None):
            content = hashed('owned native HTTP delivery decoy A')
            self.delivery_asset = super()._insert('ingest.media_assets', storage_bucket='source-free-no-cloud',
                storage_key='raw/media/' + content + '.png', content_sha256=content,
                source_url='https://delivery-fixture.invalid/asset-source-A.png',
                content_type='image/png', author='Synthetic fixture', license_code='CC0', retrieved_at=NOW)
            values['image_asset_id'] = self.delivery_asset['id']
        return super()._insert(table, **values)

    def bind_extended_model(self, path):
        self.model = json.loads(Path(path).read_text())
        self.tables = {t['qualified_name']: t for s in self.model['schemas'] for t in s['tables']}
        assert len(self.tables) == 107
        self.has_core017 = 'source_has_playoff' in self.tables['football.match_observation_details']['columns']
        self.native_coverage = {}
        self.stat_refs = {}
        self.payloads = source_descriptors()
        self.core_anchor = {}
        self.core_scores = {}
        self.fault = None
        with self.conn.transaction():
            for name, t in self.tables.items():
                if t['phase'] != 'models' and 'relation_code' in t['columns']:
                    self.conn.execute('''INSERT INTO ingest.relation_contracts
                        (relation_code,relation_name,contract_version,grain_definition)
                        VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING''',
                        (name, name, CONTRACT, t['grain']))
        self.dataset_id = self.conn.execute('''SELECT id FROM ingest.source_datasets
            WHERE source_id=%s ORDER BY id LIMIT 1''', (self.ids['source'],)).fetchone()[0]

    def extend_core_model(self, path):
        self.model = json.loads(Path(path).read_text())
        self.tables = {t['qualified_name']: t for schema in self.model['schemas'] for t in schema['tables']}
        self.has_core017 = 'source_has_playoff' in self.tables['football.match_observation_details']['columns']
        assert self.has_core017

    def put(self, table, **values):
        if 'contract_version' in self.tables[table]['columns']:
            values.update(contract_version=CONTRACT, transform_version=TRANSFORM, transform_code_sha256=CODE_SHA)
        if self.fault == 'global_profile' and table == 'football.match_events' and values.get('player_profile_version_id'):
            values['player_profile_version_id'] = self.player_profiles[0]['id']
        if self.fault == 'unrecorded' and table == 'ingest.match_coverage':
            values['source_match_id_state'] = 'unrecorded'
        if self.fault == 'count_mismatch' and table == 'ingest.match_coverage':
            values['observed_row_count'] += 1
        if self.fault == 'lineup_shirt_disagreement' and table == 'football.match_players' and values.get('shirt_number_state') == 'number':
            values.update(shirt_number='77', shirt_number_source_number=77)
        if self.fault == 'core_pair' and table == 'football.match_observation_details':
            values['source_referee_label'] = 'contradictory typed value'
            values['source_referee_state'] = 'null'
        return self._insert(table, **values)

    def record(self, doc, locator, kind, ordinal=None, external=None):
        if self.fault == 'leading_zero' and kind == 'native_event' and ordinal == 0:
            locator += '0'
        return self.put('ingest.source_records', document_id=doc['id'], source_id=doc['source_id'],
                        locator_kind='json_pointer', locator=locator, ordinal=ordinal,
                        record_kind=kind, external_key=external)

    def profile(self, actor, record, data, *, player, id_key='id'):
        values = dict(source_id=record['source_id'], source_record_id=record['id'], observed_at=NOW,
                      profile_context='native_match_observation_v1:' + str(record['id']),
                      variant_key='source:exact', source_external_id_state=state(data, id_key),
                      **fields(data, {'name': ('display_name', 'source_name_state'),
                                      'image_url': ('source_image_url', 'source_image_url_state')}))
        if player:
            values.update(player_id=actor, external_profile_version_id='native-observation:' + str(record['id']),
                          profile_content_sha256=hashed(['synthetic native profile', record['id']]),
                          **native_code(data, 'position_id', 'raw_position_code'),
                          **native_code(data, 'shirt_number', 'shirt_number'))
        else:
            values['team_id'] = actor
        return self.put('football.player_profile_versions' if player else 'football.team_profile_versions', **values)

    def match_context(self, mid):
        return self.match_rows[mid], self.sides[mid], self.ids['source']

    def new_family(self, edition, family, data, *, label='initial', prior=None):
        mid = PRIMARY[edition]
        m, sides, source = self.match_context(mid)
        doc, _ = self._record(source, self.dataset_id, f'native-http-{edition}-{family}-{label}')
        id_key = 'id' if family == 'match' else 'match_id'
        record = self.record(doc, '/data', 'native_family_root', external=data.get(id_key))
        if prior is not None:
            keys = ('match_id', 'source_id', 'feature_code', 'variant_key', 'recorded_from_gen')
            where = ' AND '.join(k + '=%s' for k in keys)
            self.conn.execute('UPDATE ingest.match_coverage SET recorded_to_gen=%s WHERE ' + where,
                              (self.g, *(prior[k] for k in keys)))
        team_fields = {}
        for side in ('home', 'away'):
            name = side + '_team'
            observed = state(data, name, 'object')
            profile_id = None
            if observed == 'object':
                sr = self.record(doc, '/data/' + name, 'native_team_object', external=data[name].get('id'))
                profile_id = self.profile(sides[side]['team_id'], sr, data[name], player=False)['id']
            team_fields['source_' + name + '_state'] = observed
            team_fields['source_' + name + '_profile_version_id'] = profile_id
        if family in ARRAY_KEYS:
            collection, observed_count = array(data, ARRAY_KEYS[family])
        else:
            collection, observed_count = 'present', (2 if family == 'lineups' else 1)
        anchor = self.native_core(mid, doc, record, data) if family == 'match' else m
        coverage = self.put('ingest.match_coverage', match_id=m['id'], match_revision_id=anchor['revision_id'],
                            source_id=source, source_record_id=record['id'], document_id=doc['id'],
                            feature_code=family, variant_key='source:exact', is_canonical=True,
                            coverage_state='empty_response' if collection == 'empty' else 'available',
                            collection_state=collection, observed_row_count=observed_count, checked_at=NOW,
                            source_match_id_state=state(data, id_key), **team_fields)
        key = {k: coverage[k] for k in ('match_id', 'source_id', 'feature_code', 'variant_key', 'recorded_from_gen')}
        if family != 'match':
            getattr(self, 'native_' + family)(mid, doc, data, key, corrected=prior is not None)
        self.native_coverage[edition, family] = coverage
        return coverage

    def native_events(self, mid, doc, data, key, *, corrected):
        m, sides, source = self.match_context(mid)
        simple = {name: (name, 'source_' + name + '_state') for name in
                  ('event_type', 'minute', 'minute_added', 'second', 'is_penalty', 'is_own_goal', 'score_home', 'score_away')}
        for i, item in enumerate(data.get('events') or []):
            sr = self.record(doc, f'/data/events/{i}', 'native_event', i, item.get('id'))
            values = fields(item, {**simple, 'period': ('source_period_label', 'source_period_label_state'),
                                   'id': ('source_event_id', 'source_event_id_state')})
            values.update(source_team_id_state=state(item, 'team_id'), event_seq=i, source_ordinal=i,
                          match_revision_id=m['revision_id'], source_record_id=sr['id'])
            if 'team_id' in item:
                self.record(doc, sr['locator'] + '/team_id', 'native_identifier', external=item['team_id'])
                values.update(team_id=sides['home']['team_id'], match_team_revision_id=sides['home']['revision_id'])
            if state(item, 'period') == 'value':
                values.update(period_code='first_half', period_definition_version='bootstrap_v1')
            for field, index in (('player', 0), ('sub_in_player', 1)):
                kind = state(item, field, 'object')
                values['source_' + field + '_state'] = kind
                if kind == 'object':
                    obj = item[field]
                    actor = self.ids['players'][index]['id']
                    pr = self.record(doc, sr['locator'] + '/' + field, 'native_player_object', external=obj.get('id'))
                    values[field + '_id'] = actor
                    values[field + '_profile_version_id'] = self.profile(actor, pr, obj, player=True)['id']
            if i == 1:
                values['related_player_id'] = self.ids['players'][2]['id']
            self.put('football.match_events', **key, **values)

    def native_lineups(self, mid, doc, data, key, *, corrected):
        m, sides, source = self.match_context(mid)
        for side in ('home', 'away'):
            kind = state(data, side, 'object')
            body = data[side] if kind == 'object' else {}
            sr = self.record(doc, '/data/' + side, 'native_lineup_side')
            team = sides[side]['team_id']
            starters, starters_count = array(body, 'starters')
            subs, subs_count = array(body, 'subs')
            coach_kind = state(body, 'coach', 'object')
            coach = body['coach'] if coach_kind == 'object' else {}
            lineup = self.put('football.match_lineups', match_id=m['id'], team_id=team,
                              match_team_revision_id=sides[side]['revision_id'], source_id=source,
                              source_record_id=sr['id'], variant_key=key['variant_key'], is_canonical=False,
                              lineup_type='observed' if kind == 'object' else 'unknown',
                              source_collection_from_gen=key['recorded_from_gen'], source_feature_code='lineups',
                              source_object_state=kind, source_starters_state=starters, source_starters_count=starters_count,
                              source_subs_state=subs, source_subs_count=subs_count, source_coach_state=coach_kind,
                              **fields(body, {'formation': ('formation', 'source_formation_state'),
                                              'confirmed': ('confirmed', 'source_confirmed_state'),
                                              'lineup_type': ('source_lineup_type', 'source_lineup_type_state')}),
                              **fields(coach, {'name': ('source_coach_name', 'source_coach_name_state')}))
            for section, squad in (('starters', 'starter'), ('subs', 'substitute')):
                for i, member in enumerate(body.get(section) or []):
                    mr = self.record(doc, f"{sr['locator']}/{section}/{i}", 'native_lineup_member', i, member['player_id'])
                    actor = self.ids['players'][2 if member['player_id'].endswith('third') else 0]['id']
                    profile = self.profile(actor, mr, member, player=True, id_key='player_id')
                    coords = fields(member, {'pitch_x': ('raw_pitch_x', 'source_raw_pitch_x_state'),
                                             'pitch_y': ('raw_pitch_y', 'source_raw_pitch_y_state'),
                                             'is_captain': ('is_captain', 'source_is_captain_state')})
                    frame = 'unknown' if any(coords[c] is not None for c in ('raw_pitch_x', 'raw_pitch_y')) else None
                    self.put('football.match_players', match_id=m['id'], team_id=team, player_id=actor,
                             match_team_revision_id=sides[side]['revision_id'], lineup_revision_id=lineup['revision_id'],
                             profile_version_id=profile['id'], source_id=source, source_record_id=mr['id'],
                             variant_key=f'native:lineup:{side}:{section}:{i}', is_canonical=False, squad_status=squad,
                             is_starter=(section == 'starters'), coordinate_frame=frame,
                             **native_code(member, 'position_id', 'raw_position_code'),
                             **native_code(member, 'shirt_number', 'shirt_number'), **coords)

    def register_stats(self):
        self.metric_defs = {}
        for raw in ('fixture_duplicate', 'fixture_other'):
            code = 'native_http_' + raw
            md = self.put('football.metric_definitions', code=code, label=raw,
                          definition='Synthetic native match layout metric', unit='source_native',
                          scope='team', aggregation='none', allows_negative=True, definition_version=TRANSFORM)
            self.metric_defs[raw] = md
            self.put('football.source_metric_mappings', source_id=self.ids['source'], family_code='standard',
                     raw_key=raw, mapping_version=TRANSFORM, metric_code=code, metric_definition_version=TRANSFORM,
                     period_rule={'native107': {'value:Source full match': 'full_match'}})

    def native_stats(self, mid, doc, data, key, *, corrected):
        m, sides, source = self.match_context(mid)
        for pi, period in enumerate(data.get('periods') or []):
            pr = self.record(doc, f'/data/periods/{pi}', 'native_stat_period', pi)
            groups, ng = array(period, 'groups')
            self.put('football.match_team_stat_periods', **key, source_record_id=pr['id'],
                     groups_state=groups, groups_count=ng,
                     **fields(period, {'period': ('source_period_label', 'source_period_label_state')}))
            for gi, group in enumerate(period.get('groups') or []):
                gr = self.record(doc, f"{pr['locator']}/groups/{gi}", 'native_stat_group', gi)
                items, ni = array(group, 'items')
                self.put('football.match_team_stat_groups', **key, source_record_id=gr['id'],
                         period_source_record_id=pr['id'], items_state=items, items_count=ni,
                         **fields(group, {'group_name': ('group_name', 'group_name_state')}))
                for ii, item in enumerate(group.get('items') or []):
                    ir = self.record(doc, f"{gr['locator']}/items/{ii}", 'native_stat_item', ii)
                    refs = {}
                    for side in ('home', 'away'):
                        original_index = (1 - ii) if corrected and pi == 0 and gi == 0 and ii < 2 else ii
                        ref_key = (mid, pi, gi, original_index, side)
                        if corrected:
                            refs[side] = self.stat_refs[ref_key]
                            continue
                        sr = self.record(doc, ir['locator'] + '/' + side, 'native_stat_scalar')
                        value = item.get(side)
                        kind = state(item, side)
                        if kind == 'value':
                            kind = {bool: 'boolean', str: 'string', int: 'number', Decimal: 'number'}[type(value)]
                        md = self.metric_defs[item['key']]
                        row = self.put('football.team_match_metric_values', match_id=m['id'],
                                       team_id=sides[side]['team_id'], match_team_revision_id=sides[side]['revision_id'],
                                       source_id=source, source_record_id=sr['id'], period_code='full_match',
                                       period_definition_version='bootstrap_v1', family_code='standard', metric_code=md['code'],
                                       metric_definition_version=md['definition_version'], value_kind=kind,
                                       numeric_value=value if kind == 'number' else None,
                                       text_value=value if kind == 'string' else None,
                                       boolean_value=value if kind == 'boolean' else None,
                                       variant_key=f'native:stat:{doc["id"]}:{pi}:{gi}:{ii}:{side}', is_canonical=False)
                        refs[side] = self.stat_refs[ref_key] = row['revision_id']
                    if self.fault == 'scalar_wrong_side' and (pi, gi, ii) == (0, 0, 0):
                        refs['home'], refs['away'] = refs['away'], refs['home']
                    self.put('football.match_team_stat_items', **key, source_record_id=ir['id'],
                             group_source_record_id=gr['id'], home_metric_revision_id=refs['home'],
                             away_metric_revision_id=refs['away'],
                             **fields(item, {'key': ('raw_key', 'raw_key_state'), 'title': ('title', 'title_state'),
                                             'format_type': ('format_type', 'format_type_state')}))

    def native_h2h(self, mid, doc, data, key, *, corrected):
        m, sides, source = self.match_context(mid)
        self.put('football.match_h2h_summaries', **key,
                 **fields(data, {n: (n, n + '_state') for n in ('home_wins', 'away_wins', 'draws', 'total_matches')}))
        for i, item in enumerate(data.get('recent_matches') or []):
            sr = self.record(doc, f'/data/recent_matches/{i}', 'native_h2h_entry', i, item.get('id'))
            values = fields(item, {'id': ('external_match_id', 'source_external_match_id_state'),
                                   'finished': ('source_finished', 'source_finished_state'),
                                   'time_utc': ('time_utc_source', 'source_time_utc_source_state'),
                                   'status': ('status_source', 'source_status_source_state'),
                                   'score_home': ('home_score', 'source_home_score_state'),
                                   'score_away': ('away_score', 'source_away_score_state')})
            for side in ('home', 'away'):
                obj_state = state(item, side, 'object')
                obj = item[side] if obj_state == 'object' else {}
                values['source_' + side + '_state'] = obj_state
                id_state = state(obj, 'id')
                values['source_' + side + '_id_state'] = id_state
                if id_state == 'value':
                    self.record(doc, sr['locator'] + '/' + side + '/id', 'native_identifier', external=obj['id'])
                values.update(fields(obj, {'name': (side + '_label', 'source_' + side + '_label_state'),
                                           'image_url': ('source_' + side + '_image_url', 'source_' + side + '_image_url_state')}))
            self.put('football.match_h2h_entries', **key, entry_ordinal=i, source_record_id=sr['id'],
                     match_revision_id=m['revision_id'], **values)

    def native_momentum(self, mid, doc, data, key, *, corrected):
        m, sides, source = self.match_context(mid)
        for i, point in enumerate(data.get('points') or []):
            sr = self.record(doc, f'/data/points/{i}', 'native_momentum_point', i)
            self.put('football.match_momentum', **key, series_code='provider_native', sample_index=i,
                     minute=point['minute'], value=point['value'], source_record_id=sr['id'], match_revision_id=m['revision_id'])

    def native_core(self, mid, doc, record, data):
        assert self.has_core017, 'Exact native core fixture requires the six approved 017 columns'
        m, sides, source = self.match_context(mid)
        if mid in self.core_anchor:
            self.conn.execute('UPDATE football.matches SET recorded_to_gen=%s WHERE revision_id=%s',
                              (self.g, self.core_anchor[mid]['revision_id']))
            for side in ('home', 'away'):
                self.conn.execute('UPDATE football.match_scores SET recorded_to_gen=%s WHERE revision_id=%s',
                                  (self.g, self.core_scores[mid, side]['revision_id']))
        clone = {k: v for k, v in m.items() if k not in ('revision_id', 'recorded_from_gen', 'recorded_to_gen')}
        clone.update(status=data['status'], source_record_id=record['id'], variant_key='source:match-root', is_canonical=False)
        anchor = self.put('football.matches', **clone)
        self.core_anchor[mid] = anchor
        league = data['league']
        self.record(doc, '/data/league/id', 'native_identifier', external=league['id'])
        self.put('football.match_observation_details', source_record_id=record['id'], match_id=m['id'],
                 match_revision_id=anchor['revision_id'], source_match_key=data['id'], source_competition_label=league['name'],
                 source_season_label=data['season'], source_home_label=data['home_team']['name'],
                 source_away_label=data['away_team']['name'], source_date_text=data['date'], source_time_text=data['time_utc'],
                 source_round_label=data['round_name'], source_venue_label=data['stadium'], resolution_state='resolved',
                 **fields(data, {'referee': ('source_referee_label', 'source_referee_state'),
                                 'has_playoff': ('source_has_playoff', 'source_has_playoff_state')}),
                 **fields(league, {'image_url': ('source_league_image_url', 'source_league_image_url_state')}))
        for side in ('home', 'away'):
            self.core_scores[mid, side] = self.put('football.match_scores', match_id=m['id'], side=side,
                score_scope='final_without_shootout', score_basis='played', goals=data['score_' + side],
                match_team_revision_id=sides[side]['revision_id'], source_id=source, source_record_id=record['id'],
                variant_key='source:match-root', is_canonical=False)
        return anchor

    def install_observations(self):
        with self._generation('match_reader_native_inputs') as g:
            self.register_stats()
            for edition, families in self.payloads.items():
                for family, payload in families.items():
                    if family != 'match' or self.has_core017:
                        self.new_family(edition, family, payload)
        self.native_generation = g
        return {'generation': g, 'matchKeys': PRIMARY, 'core017': self.has_core017,
                'coverageCount': len(self.native_coverage), 'scalarRefs': len(self.stat_refs)}

    def install_core_observations(self):
        assert self.has_core017
        with self._generation('match_reader_native_core_inputs') as generation:
            for edition in 'ABC':
                self.new_family(edition, 'match', self.payloads[edition]['match'], label='core017')
        return {'generation': generation, 'newCoverage': 3}

    def change_delivery_media(self):
        asset = self.delivery_asset
        changed = hashed('owned native HTTP delivery decoy B')
        with self.conn.transaction():
            value = self.conn.execute('''UPDATE ingest.media_assets SET
                content_sha256=%s,storage_key=%s,source_url=%s WHERE id=%s
                RETURNING content_sha256,storage_key,source_url''',
                (changed, 'raw/media/' + changed + '.png', 'https://delivery-fixture.invalid/asset-source-B.png',
                 asset['id'])).fetchone()
        return {'id': asset['id'], 'before': [asset[k] for k in ('content_sha256', 'storage_key', 'source_url')],
                'after': list(value)}

    def correct_layout(self):
        old = self.native_coverage['A', 'stats']
        updated = stats('A', layout_correction=True)
        with self._generation('native_http_layout_correction') as g:
            new = self.new_family('A', 'stats', updated, label='layout-v2', prior=old)
        return {'generation': g, 'coverage': new, 'expected': updated}

    def correct_two_families(self):
        momentum = deepcopy(self.payloads['A']['momentum'])
        momentum['points'][1]['value'] = -91
        events = {'match_id': self.payloads['B']['events']['match_id'],
                  'events': [{'event_type': 'Observed correction', 'minute': 0, 'is_own_goal': False}]}
        with self._generation('native_http_two_family_correction') as g:
            self.new_family('A', 'momentum', momentum, label='momentum-v2', prior=self.native_coverage['A', 'momentum'])
            self.new_family('B', 'events', events, label='events-v2', prior=self.native_coverage['B', 'events'])
        return {'generation': g, 'A': momentum, 'B': events}

    def correct_core(self):
        updated = match('A', playoff_correction=True)
        with self._generation('native_http_core017_correction') as g:
            self.new_family('A', 'match', updated, label='core-v2', prior=self.native_coverage['A', 'match'])
        return {'generation': g, 'expected': updated}

    def reject_native(self, fault):
        """Try one invalid draft; never publish it or bypass native guards."""
        saved_coverage, saved_refs = dict(self.native_coverage), dict(self.stat_refs)
        saved_anchors, saved_scores = dict(self.core_anchor), dict(self.core_scores)
        self.fault = fault
        try:
            if fault == 'nonfinite':
                def action():
                    key = (PRIMARY['A'], 0, 0, 0, 'home')
                    old = self._row('football.team_match_metric_values', 'revision_id=%s', (self.stat_refs[key],))
                    new = self._replace('football.team_match_metric_values', old, numeric_value=Decimal('NaN'))
                    self.stat_refs[key] = new['revision_id']
                    self.new_family('A', 'stats', stats('A', layout_correction=True), label='reject-nonfinite',
                                    prior=saved_coverage['A', 'stats'])
            else:
                family = {'lineup_shirt_disagreement': 'lineups', 'scalar_wrong_side': 'stats',
                          'core_pair': 'match'}.get(fault, 'events')
                payload = stats('A', layout_correction=True) if family == 'stats' else self.payloads['A'][family]
                def action():
                    self.new_family('A', family, payload, label='reject-' + fault, prior=saved_coverage['A', family])
            return self._reject('native_http_' + fault, action, states={'23514'})
        finally:
            self.native_coverage, self.stat_refs, self.fault = saved_coverage, saved_refs, None
            self.core_anchor, self.core_scores = saved_anchors, saved_scores
    
    def oversize_events(self):
        payload = {'match_id': self.payloads['B']['events']['match_id'],
                   'events': [{'event_type': 'x' * (1024 * 1024 + 1)}]}
        with self._generation('native_http_oversize_value') as g:
            self.new_family('B', 'events', payload, label='oversize-value', prior=self.native_coverage['B', 'events'])
        return {'generation': g, 'sourceTextBytes': len(payload['events'][0]['event_type'])}
