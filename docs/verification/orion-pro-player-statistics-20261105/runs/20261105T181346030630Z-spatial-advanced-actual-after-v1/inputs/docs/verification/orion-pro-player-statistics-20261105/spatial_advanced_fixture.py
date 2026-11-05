"""Before-code typed fixture for spatial and advanced match projections."""
from copy import deepcopy
from decimal import Decimal
import json

from player_period_fixture import (
    DOC, CONTRACT, VARIANT, PROFILE, NOW, MIDS, PlayerPeriodFixture,
    StatisticsFixturePublisher, digest, hashed, state, native_code,
)

FULL = json.loads((DOC / 'FULL_STATISTICS_PUBLICATION.json').read_text())
FULL_ENV = FULL['environmentSha256']
SPATIAL = ('heatmaps.teams', 'heatmaps.players', 'pass_networks', 'advanced_teams', 'advanced_players')
FRAME = 'metric_105x68_acting_ltr'
GRID = {'length': 16, 'width': 12, 'cell_length_m': 6.5, 'cell_width_m': 5.5}
LONG = Decimal('0.8200000000000000001')
MAPPED = {'advanced_teams': {'possession_value.xt_total': 'xt_total'},
          'advanced_players': {'passing.progressive_passes': 'progressive_passes'}}


class SpatialAdvancedFixture(PlayerPeriodFixture):
    @classmethod
    def from_prepared(cls, prior):
        new = cls(prior.conn, prior.dsn, prior.evidence, prior.psycopg)
        new.__dict__.update(vars(prior))
        new.additional = {}
        new.metric_defs = {}
        return new

    def make_source(self, edition, family, label):
        doc, _ = self._record(self.ids['source'], self.dataset_id, f'owned-spatial-advanced-{edition}-{family}-{label}')
        return doc

    def cov(self, edition, feature, doc, record, value, *, variant=VARIANT, canonical=True):
        key = edition, feature, variant
        old = self.additional.get(key)
        if old:
            self.conn.execute('''UPDATE ingest.match_coverage SET recorded_to_gen=%s
                WHERE match_id=%s AND source_id=%s AND feature_code=%s AND variant_key=%s AND recorded_from_gen=%s''',
                (self.g, old['match_id'], old['source_id'], old['feature_code'], old['variant_key'], old['recorded_from_gen']))
        m = self.match_rows[MIDS[edition]]
        state, count = value
        row = self.put_stat('ingest.match_coverage', match_id=m['id'], match_revision_id=m['revision_id'],
            source_id=doc['source_id'], document_id=doc['id'], source_record_id=record['id'],
            feature_code=feature, variant_key=variant, is_canonical=canonical, collection_state=state,
            coverage_state='empty_response' if state == 'empty' else 'available',
            observed_row_count=count, checked_at=NOW, source_match_id_state='value',
            source_home_team_state='absent', source_away_team_state='absent')
        self.additional[key] = row
        return row

    def close(self, table, mid, source, variant):
        self.conn.execute('UPDATE ' + table + ''' SET recorded_to_gen=%s
            WHERE match_id=%s AND source_id=%s AND variant_key=%s AND recorded_to_gen IS NULL''',
            (self.g, mid, source, variant))

    def team(self, doc, base, actor, name):
        record = self.stat_record(doc, base + '/team', 'statistics_team_actor', external='observed-team-' + str(actor))
        return self.put_stat('football.team_profile_versions', team_id=actor, source_id=doc['source_id'],
            source_record_id=record['id'], observed_at=NOW, profile_context=PROFILE + str(record['id']),
            variant_key='source:exact', display_name=name, source_name_state='value',
            source_image_url_state='absent', source_external_id_state='value')

    def athlete(self, doc, base, index, name, shirt):
        actor = self.ids['players'][index]['id']
        record = self.stat_record(doc, base + '/player', 'statistics_player_actor', external='observed-player-' + str(actor))
        p = self.put_stat('football.player_profile_versions', player_id=actor, source_id=doc['source_id'],
            source_record_id=record['id'], observed_at=NOW, profile_context=PROFILE + str(record['id']),
            variant_key='source:exact', display_name=name, source_name_state='value',
            source_image_url_state='absent', source_external_id_state='value',
            external_profile_version_id='observed-stats-' + str(record['id']),
            profile_content_sha256=hashed(['observed stats profile', record['id']]),
            **native_code({'shirt_number': shirt}, 'shirt_number', 'shirt_number'))
        return actor, p['id']

    def heatmaps(self, edition, frame, label, *, corrected=False):
        mid = MIDS[edition]
        match, sides, source = self.match_context(mid)
        v = VARIANT + ':heatmap:' + frame
        doc = self.make_source(edition, 'heatmap-' + frame, label)
        if (edition, 'heatmaps.teams', v) in self.additional:
            self.close('football.match_heatmaps', match['id'], source, v)
        definitions = {
            ('A', 'acting_ltr'): {
                'teams': [('home', None, 'Observed home grid', None, 'available', [(15, 11, 0), (0, 0, 4)]),
                          ('away', None, 'Observed away grid', 2, 'null', [])],
                'players': [('home', 0, 'Observed team at player slot', 5 if corrected else 4, 'available', [(3, 7, 2)]),
                            ('away', 2, 'Observed away at player slot', 0, 'absent', [])],
            },
            ('A', 'home_ltr'): {
                'teams': [('home', None, 'Separate home oriented grid', 3, 'empty', [])], 'players': [],
            },
            ('B', 'acting_ltr'): {'teams': None, 'players': False},
            ('C', 'acting_ltr'): {'teams': [], 'players': []},
        }[edition, frame]
        for family, maps in definitions.items():
            field = 'heatmaps.' + family
            root = self.stat_record(doc, '/data/' + family, 'heatmap_coverage', external=mid)
            shape = ('null', None) if maps is None else ('absent', None) if maps is False else (
                ('present', len(maps)) if maps else ('empty', 0))
            self.cov(edition, field, doc, root, shape, variant=v, canonical=frame == 'acting_ltr')
            for i, (side, actor_index, team_name, actions, cells_state, triplets) in enumerate(maps or []):
                t = sides[side]
                base = '/data/' + family + '/' + str(i)
                record = self.stat_record(doc, base, 'heatmap_map', i)
                self.team(doc, base, t['team_id'], team_name)
                player = None
                if actor_index is not None:
                    player, _ = self.athlete(doc, base, actor_index, 'Observed map player' if actor_index == 0 else 'Observed away map player', '09')
                h = self.put_stat('football.match_heatmaps', match_id=match['id'], team_id=t['team_id'],
                    match_team_revision_id=t['revision_id'], player_id=player, source_id=source, source_record_id=record['id'],
                    variant_key=v, is_canonical=frame == 'acting_ltr', period_code='full_match',
                    period_definition_version='bootstrap_v1', map_kind='source_actions', grid_columns=GRID['length'],
                    grid_rows=GRID['width'], cell_length_m=GRID['cell_length_m'], cell_width_m=GRID['cell_width_m'],
                    coordinate_frame=frame, actions=actions, cells_state=cells_state)
                for ordinal, (x, y, n) in enumerate(triplets):
                    self.put_stat('football.match_heatmap_cells', heatmap_id=h['id'], cell_ordinal=ordinal,
                        column_index=x, row_index=y, action_count=n)

    def network(self, edition, label, *, invalid=False):
        match, sides, source = self.match_context(MIDS[edition])
        doc = self.make_source(edition, 'network', label)
        record = self.stat_record(doc, '/data', 'network_root', external=MIDS[edition])
        self.close('football.pass_networks', match['id'], source, VARIANT)
        self.cov(edition, 'pass_networks', doc, record, ('present', 1) if edition == 'A' else ('empty', 0))
        if edition != 'A':
            return
        team = sides['home']
        base = '/data/networks/0'
        record = self.stat_record(doc, base, 'network_parent', 0)
        self.team(doc, base, team['team_id'], 'Observed network home')
        n = self.put_stat('football.pass_networks', match_id=match['id'], team_id=team['team_id'],
            match_team_revision_id=team['revision_id'], source_id=source, source_record_id=record['id'],
            variant_key=VARIANT, is_canonical=False, window_kind='first_substitution',
            from_seconds=0, until_seconds=2530, centralization=0.25,
            coordinate_frame='pitchapi_native_unverified' if invalid else FRAME)
        actors = []
        for i, (idx, name, shirt, x, y, passes) in enumerate([
            (2, 'Observed network runner', 9, 90.5, 0.0, 3), (0, 'Observed network passer', '08', 0.0, 34.0, 12),
        ]):
            slot = base + '/nodes/' + str(i)
            self.stat_record(doc, slot, 'network_node', i)
            actor, _ = self.athlete(doc, slot, idx, name, shirt)
            self.put_stat('football.pass_network_nodes', network_id=n['id'], player_id=actor,
                avg_x=x, avg_y=y, passes=passes, passes_received=0)
            actors.append(actor)
        self.put_stat('football.pass_network_edges', network_id=n['id'], from_player_id=actors[1], to_player_id=actors[0], passes=3)

    def define_advanced(self):
        for family, keys in {
            'advanced_teams': ['actions', 'passing.passes', 'possession_value.xt_total'],
            'advanced_players': ['actions', 'goalkeeping', 'passing.pass_accuracy'],
        }.items():
            for key in keys:
                code = 'owned_' + family + '_' + key.replace('.', '_')
                definition = self.put_stat('football.metric_definitions', code=code, label=key,
                    definition='Synthetic retained advanced value', unit='source_native', scope='team' if family.endswith('teams') else 'player',
                    aggregation='none', allows_negative=True, definition_version=CONTRACT)
                self.metric_defs[family, key] = definition
                self.put_stat('football.source_metric_mappings', source_id=self.ids['source'], family_code=family,
                    raw_key=key, mapping_version=CONTRACT, metric_code=code, metric_definition_version=CONTRACT)

    def advanced(self, edition, family, label, *, invalid=False):
        team = family == 'advanced_teams'
        match, sides, source = self.match_context(MIDS[edition])
        doc = self.make_source(edition, family, label)
        prefix = 'team' if team else 'player'
        v = VARIANT + ':' + family
        root = self.stat_record(doc, '/data', 'advanced_root', external=MIDS[edition])
        for table in (f'football.{prefix}_match_advanced', f'football.{prefix}_match_metric_values') + (() if team else ('football.match_players',)):
            self.close(table, match['id'], source, v)
        self.cov(edition, family, doc, root, ('present', 2) if edition == 'A' else ('empty', 0))
        if edition != 'A':
            return
        for ordinal, side in enumerate(('home', 'away')):
            anchor = sides[side]
            base = '/data/' + ('teams' if team else 'players') + '/' + str(ordinal)
            record = self.stat_record(doc, base, 'advanced_subject', ordinal)
            typed = {'match_team_revision_id': anchor['revision_id']}
            if team:
                self.team(doc, base, anchor['team_id'], 'Observed advanced ' + side)
                facts = dict(ppda=7.25 if not ordinal else None, xt_total=0, field_tilt=50 if not ordinal else None)
                scalars = {'actions': 5, 'passing.passes': 21, 'possession_value.xt_total': 1 if invalid else 0}
            else:
                actor, profile = self.athlete(doc, base, [2, 0][ordinal], 'Observed advanced ' + side, [9, '08'][ordinal])
                member = self.put_stat('football.match_players', match_id=match['id'], team_id=anchor['team_id'], player_id=actor,
                    match_team_revision_id=anchor['revision_id'], profile_version_id=profile,
                    source_id=source, source_record_id=record['id'], variant_key=v, squad_status='unknown', is_canonical=False)
                typed = {'player_id': actor, 'match_player_revision_id': member['revision_id']}
                facts = dict(progressive_passes=0, sca=1, sca_pass_live=1, xag=0.25)
                scalars = {'actions': 0, 'goalkeeping': None, 'passing.pass_accuracy': LONG}
            common = dict(match_id=match['id'], team_id=anchor['team_id'], source_id=source, variant_key=v,
                          is_canonical=False, period_code='full_match', period_definition_version='bootstrap_v1', **typed)
            self.put_stat(f'football.{prefix}_match_advanced', **common, source_record_id=record['id'], **facts)
            for index, (key, value) in enumerate(scalars.items()):
                scalar_record = self.stat_record(doc, base + '/' + key.replace('.', '/'), 'advanced_scalar', external=key)
                definition = self.metric_defs[family, key]
                self.put_stat(f'football.{prefix}_match_metric_values', **common, source_record_id=scalar_record['id'],
                    family_code='advanced', metric_code=definition['code'], metric_definition_version=CONTRACT,
                    value_kind='null' if value is None else 'number', numeric_value=value)

    def install_additional(self):
        with self._generation('owned_full_match_stats') as g:
            self.define_advanced()
            for key in 'ABC':
                self.heatmaps(key, 'acting_ltr', 'v1')
            self.heatmaps('A', 'home_ltr', 'v1')
            for key in 'AC':
                self.network(key, 'v1')
                self.advanced(key, 'advanced_teams', 'v1')
                self.advanced(key, 'advanced_players', 'v1')
        return g

    def correction(self):
        with self._generation('owned_heatmap_actions_correction') as g:
            self.heatmaps('A', 'acting_ltr', 'v2', corrected=True)
        return g


class FullStatisticsPublisher(StatisticsFixturePublisher):
    def __init__(self, fixture, writer, binding):
        super().__init__(fixture, writer, binding)
        assert digest(FULL['environmentDescriptor']) == FULL_ENV
        self.environment = FULL_ENV

    def closures(self, edition, dg, cg):
        base = super().closures(edition, dg, cg)
        f = self.fixture
        mids = [r['id'] for public, r in f.match_rows.items() if f.match_keys[public] == edition]
        window = 'recorded_from_gen<=%s AND (recorded_to_gen IS NULL OR %s<recorded_to_gen)'
        cover = self.rows('ingest.match_coverage',
            'match_id=ANY(%s) AND feature_code=ANY(%s) AND contract_version=%s AND ' + window,
            (mids, list(SPATIAL), CONTRACT, dg, dg))
        assert cover
        graph = {'ingest.match_coverage': cover}
        docs = {c['document_id'] for c in cover}
        records = self.rows('ingest.source_records', 'document_id=ANY(%s)', (sorted(docs),))
        by_doc = {d: {r['id']: r for r in records if r['document_id'] == d} for d in docs}
        side_refs, players, teams, metric_defs, periods = set(), set(), set(), set(), set()

        def put(table, rows):
            graph.setdefault(table, []).extend(rows)

        for c in cover:
            feature = c['feature_code']
            source_records = by_doc[c['document_id']]
            assert source_records[c['source_record_id']]['source_id'] == c['source_id']
            params = (c['match_id'], c['source_id'], dg, dg)
            scope = 'match_id=%s AND source_id=%s AND ' + window
            wanted = c['observed_row_count'] or 0
            if feature.startswith('heatmaps.'):
                part = feature.split('.')[1]
                rows = self.rows('football.match_heatmaps', scope + ' AND variant_key=%s', (*params, c['variant_key']))
                rows = [r for r in rows if r['source_record_id'] in source_records
                        and source_records[r['source_record_id']]['locator'].startswith('/data/' + part + '/')]
                assert len(rows) == wanted
                for row in rows:
                    assert row['coordinate_frame'] == c['variant_key'].rsplit(':', 1)[-1]
                    cells = self.rows('football.match_heatmap_cells', 'heatmap_id=%s', (row['id'],))
                    assert (row['cells_state'] == 'available') == bool(cells)
                    put('football.match_heatmap_cells', cells)
                    if row['player_id'] is not None:
                        players.add(row['player_id'])
                    teams.add(row['team_id'])
                    side_refs.add(row['match_team_revision_id'])
                put('football.match_heatmaps', rows)
            elif feature == 'pass_networks':
                rows = self.rows('football.pass_networks', scope + ' AND variant_key=%s', (*params, VARIANT))
                assert len(rows) == wanted
                for row in rows:
                    assert row['coordinate_frame'] == FRAME and row['window_kind'] == 'first_substitution', 'Unqualified network frame or window'
                    assert row['source_record_id'] in source_records
                    nodes = self.rows('football.pass_network_nodes', 'network_id=%s', (row['id'],))
                    edges = self.rows('football.pass_network_edges', 'network_id=%s', (row['id'],))
                    ids = {r['player_id'] for r in nodes}
                    assert all(r['from_player_id'] in ids and r['to_player_id'] in ids for r in edges)
                    players.update(ids)
                    teams.add(row['team_id'])
                    side_refs.add(row['match_team_revision_id'])
                    put('football.pass_network_nodes', nodes)
                    put('football.pass_network_edges', edges)
                put('football.pass_networks', rows)
            else:
                team = feature == 'advanced_teams'
                prefix, actor = ('team', 'match_team_revision_id') if team else ('player', 'match_player_revision_id')
                parent = f'football.{prefix}_match_advanced'
                scalar = f'football.{prefix}_match_metric_values'
                variant = VARIANT + ':' + feature
                rows = self.rows(parent, scope + ' AND variant_key=%s AND NOT is_deleted', (*params, variant))
                values = self.rows(scalar, scope + ' AND variant_key=%s AND NOT is_deleted', (*params, variant))
                assert len(rows) == wanted
                by_actor = {r[actor]: r for r in rows}
                for row in rows:
                    assert row['source_record_id'] in source_records
                    teams.add(row['team_id'])
                    periods.add((row['period_code'], row['period_definition_version']))
                for value in values:
                    parent_row = by_actor[value[actor]]
                    assert value['source_record_id'] in source_records
                    path = source_records[value['source_record_id']]['external_key']
                    direct = MAPPED[feature].get(path)
                    if direct and parent_row[direct] is not None:
                        assert value['value_kind'] == 'number' and Decimal(str(parent_row[direct])) == value['numeric_value'], 'Conflicting typed advanced values'
                    metric_defs.add((value['metric_code'], value['metric_definition_version'], feature, c['source_id']))
                if team:
                    side_refs.update(by_actor)
                else:
                    members = self.rows('football.match_players', 'revision_id=ANY(%s)', (sorted(by_actor),))
                    for member in members:
                        players.add(member['player_id'])
                        side_refs.add(member['match_team_revision_id'])
                    put('football.match_players', members)
                put(parent, rows)
                put(scalar, values)

        put('ingest.source_records', records)
        put('ingest.source_documents', self.rows('ingest.source_documents', 'id=ANY(%s)', (sorted(docs),)))
        put('football.matches', self.rows('football.matches', 'revision_id=ANY(%s)', (sorted({c['match_revision_id'] for c in cover}),)))
        put('football.match_teams', self.rows('football.match_teams', 'revision_id=ANY(%s)', (sorted(side_refs),)))
        ids = sorted(r['id'] for r in records)
        for kind in ('player', 'team'):
            put(f'football.{kind}_profile_versions', self.rows(f'football.{kind}_profile_versions',
                'source_record_id=ANY(%s) AND NOT is_deleted AND ' + window, (ids, cg, cg)))
        put('ingest.public_aliases', self.rows('ingest.public_aliases',
            '(player_id=ANY(%s) OR team_id=ANY(%s) OR match_id=ANY(%s)) AND NOT is_deleted AND ' + window,
            (sorted(players), sorted(teams), mids, cg, cg)))
        for code, version, family, source in sorted(metric_defs):
            put('football.metric_definitions', self.rows('football.metric_definitions',
                'code=%s AND definition_version=%s AND ' + window, (code, version, dg, dg)))
            put('football.source_metric_mappings', self.rows('football.source_metric_mappings',
                'metric_code=%s AND metric_definition_version=%s AND family_code=%s AND source_id=%s AND ' + window,
                (code, version, family, source, dg, dg)))
        for code, version in sorted(periods | {('full_match', 'bootstrap_v1')}):
            put('football.periods', self.rows('football.periods', 'code=%s AND definition_version=%s AND ' + window,
                  (code, version, dg, dg)))
        for table, rows in graph.items():
            pk = f.tables[table]['primary_key']['columns']
            unique = {tuple(r[k] for k in pk): r for r in rows}
            graph[table] = [unique[key] for key in sorted(unique)]
        component = digest(graph)
        statistics = digest({'playerPeriodClosureSha256': base['statisticsClosureSha256'],
            'spatialAdvancedClosureSha256': component, 'scheme': 'orion-match-statistics-typed-family-union-v1'})
        joint = deepcopy(base['joint'])
        joint['nativeClosureSha256'] = digest({'matchNative017ClosureSha256': base['originalNative017ClosureSha256'],
            'matchStatisticsClosureSha256': statistics,
            'scheme': FULL['environmentDescriptor']['publication']['compositeNativeScheme']})
        return {**base, 'joint': joint, 'dependenciesSha256': digest(joint),
                'playerPeriodClosureSha256': base['statisticsClosureSha256'],
                'statisticsClosureSha256': statistics, 'spatialAdvancedClosureSha256': component,
                'spatialAdvancedRows': {key: len(rows) for key, rows in graph.items()}}
