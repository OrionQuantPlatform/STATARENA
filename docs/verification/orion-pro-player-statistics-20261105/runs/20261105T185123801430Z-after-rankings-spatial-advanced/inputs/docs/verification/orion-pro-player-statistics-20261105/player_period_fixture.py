"""Pre-code typed player period fixture and independent composite SQL closure."""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
import hashlib
import json
from pathlib import Path

from fixture_publisher import FixturePublisher, digest
from typed_fixture import MatchReaderFixture, NOW, hashed, native_code, state

DOC = Path(__file__).resolve().parent
BINDING = json.loads((DOC / 'STATISTICS_PUBLICATION.json').read_text())
ENV = BINDING['environmentSha256']
CONTRACT = 'match-statistics-v1'
VARIANT = 'source:match-statistics-v1'
PROFILE = 'match_statistics_observation_v1:'
CODE = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
FAMILIES = ('players', 'player_halves')
MIDS = {'A': 'm_000001', 'B': 'm_000004', 'C': 'm_000005'}
LABELS = {'goals': 'Goals', 'passes': 'Accurate passes', 'xg': 'Expected goals (xG)',
          'huge': 'Exact count', 'nullable': 'Known null', 'absent': 'Known absent',
          'captain': 'Observed marker', 'text': 'Observed text'}


def inputs(corrected=False):
    """Source descriptors; transport derives typed rows independently of the API."""
    big = 9007199254740993
    xg = Decimal('0.6500000000000000001') if corrected else Decimal('0.8200000000000000001')
    main = {'actor': 0, 'public': 'p_000001', 'team': 'home',
            'profile': {'id': 'observed-A-player', 'name': 'Observed player A',
                        'image_url': None, 'position_id': '09'}}
    other = {'actor': 2, 'public': 'p_000003', 'team': 'away',
             'profile': {'id': 'observed-away-player', 'name': '', 'position_id': None}}
    full = [
        {**main, 'periods': [('full_match', {'goals': {'value': 0}, 'passes': {'value': 5, 'total': 7},
            'xg': {'value': xg}, 'huge': {'value': big}, 'nullable': {'value': None},
            'absent': {}, 'captain': {'value': False}, 'text': {'value': ''}})]},
        {**other, 'periods': [('full_match', {})]},
    ]
    halves = [
        {**main, 'profile': {**main['profile'], 'name': 'Observed halves player A'},
         'periods': [('second_half', {'goals': {'value': 0}, 'passes': {'value': 2, 'total': 3}}),
                     ('first_half', {'goals': {'value': 1}})]},
        {**other, 'periods': [('second_half', {})]},
    ]
    b = {'actor': 1, 'public': 'p_000002', 'team': 'home',
         'profile': {'id': 'observed-B-player', 'name': 'Observed player B', 'position_id': 12},
         'periods': [('full_match', {'goals': {'value': 1}})]}
    return {('A', 'players'): full, ('A', 'player_halves'): halves,
            ('B', 'players'): [b], ('C', 'players'): [], ('C', 'player_halves'): []}


class PlayerPeriodFixture(MatchReaderFixture):
    @classmethod
    def from_prepared(cls, f):
        new = cls(f.conn, f.dsn, f.evidence, f.psycopg)
        new.__dict__.update(vars(f))
        new.statistics_coverage = {}
        new.definitions = {}
        return new

    def put_stat(self, table, **values):
        if 'contract_version' in self.tables[table]['columns']:
            values.update(contract_version=CONTRACT, transform_version=CONTRACT,
                          transform_code_sha256=CODE)
        return self._insert(table, **values)

    def register_contract(self, owner):
        with owner.transaction():
            for name, spec in self.tables.items():
                if spec['phase'] != 'models' and 'relation_code' in spec['columns']:
                    owner.execute('''INSERT INTO ingest.relation_contracts
                        (relation_code,relation_name,contract_version,grain_definition)
                        VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING''',
                        (name, name, CONTRACT, spec['grain']))

    def register_metrics(self):
        for key, label in LABELS.items():
            definition = self.put_stat('football.metric_definitions', code='fixture_period_' + key, label=label,
                definition='Synthetic observed metric, no calculation', unit='source_native', scope='player',
                aggregation='none', allows_negative=True, definition_version=CONTRACT)
            self.definitions[key] = definition
            for family in FAMILIES:
                self.put_stat('football.source_metric_mappings', source_id=self.ids['source'], family_code=family,
                    raw_key=key, mapping_version=CONTRACT, metric_code=definition['code'],
                    metric_definition_version=definition['definition_version'])

    def stat_record(self, doc, locator, kind, ordinal=None, external=None):
        return self.put_stat('ingest.source_records', document_id=doc['id'], source_id=doc['source_id'],
            locator_kind='json_pointer', locator=locator, ordinal=ordinal, record_kind=kind, external_key=external)

    def stat_profile(self, actor, record, raw):
        return self.put_stat('football.player_profile_versions', player_id=actor, source_id=record['source_id'],
            source_record_id=record['id'], observed_at=NOW, profile_context=PROFILE + str(record['id']),
            variant_key='source:exact', external_profile_version_id='stats-observed-' + str(record['id']),
            profile_content_sha256=hashed(['owned-stat-profile', record['id']]),
            source_external_id_state=state(raw, 'id'), display_name=raw.get('name'), source_name_state=state(raw, 'name'),
            source_image_url=raw.get('image_url'), source_image_url_state=state(raw, 'image_url'),
            **native_code(raw, 'position_id', 'raw_position_code'))

    def close_family(self, old):
        params = (self.g, old['match_id'], old['source_id'], old['variant_key'], old['recorded_from_gen'], old['feature_code'])
        self.conn.execute('''UPDATE ingest.match_coverage SET recorded_to_gen=%s WHERE match_id=%s
            AND source_id=%s AND variant_key=%s AND recorded_from_gen=%s AND feature_code=%s''', params)
        for table in ('player_match_metric_values', 'player_match_stats', 'match_players'):
            self.conn.execute('UPDATE football.' + table + ''' SET recorded_to_gen=%s
                WHERE match_id=%s AND source_id=%s AND variant_key=%s AND recorded_to_gen IS NULL''',
                (self.g, old['match_id'], old['source_id'], old['variant_key'] + ':' + old['feature_code']))

    def add_family(self, edition, family, members, label, *, invalid_profile=False):
        mid = MIDS[edition]
        match, sides, source = self.match_context(mid)
        prior = self.statistics_coverage.get((edition, family))
        if prior:
            self.close_family(prior)
        doc, _ = self._record(source, self.dataset_id, f'player-statistics-{edition}-{family}-{label}')
        root = self.stat_record(doc, '/data', 'normalized_player_statistics_root', external=mid)
        self.statistics_coverage[edition, family] = self.put_stat('ingest.match_coverage',
            match_id=match['id'], match_revision_id=match['revision_id'], source_id=source, source_record_id=root['id'],
            document_id=doc['id'], feature_code=family, variant_key=VARIANT,
            collection_state='present' if members else 'empty', observed_row_count=len(members),
            coverage_state='available' if members else 'empty_response', checked_at=NOW,
            source_match_id_state='value', source_home_team_state='absent', source_away_team_state='absent')
        variant = VARIANT + ':' + family
        for index, data in enumerate(members):
            actor, side = self.ids['players'][data['actor']]['id'], sides[data['team']]
            base = ('/data/' if family == 'players' else '/data/players/') + str(index)
            r = self.stat_record(doc, base, 'player_stat_member', index, data['profile']['id'])
            ar = self.stat_record(doc, base + '/player', 'player_stat_profile', external=data['profile']['id'])
            profile = self.stat_profile(actor, ar, data['profile'])
            member = self.put_stat('football.match_players', match_id=match['id'], team_id=side['team_id'],
                player_id=actor, match_team_revision_id=side['revision_id'], squad_status='unknown',
                profile_version_id=(self.player_profiles[data['actor']]['id'] if invalid_profile else profile['id']),
                source_id=source, source_record_id=r['id'], variant_key=variant, is_canonical=False)
            for i, (period, metrics) in enumerate(data['periods']):
                period_path = base if family == 'players' else base + '/periods/' + str(i)
                witness = r if family == 'players' else self.stat_record(doc, period_path, 'player_stat_period', i, period)
                self.put_stat('football.player_match_stats', match_id=match['id'], team_id=side['team_id'],
                    player_id=actor, match_player_revision_id=member['revision_id'], source_id=source,
                    source_record_id=witness['id'], period_code=period, period_definition_version='bootstrap_v1',
                    variant_key=variant, is_canonical=False)
                for j, (key, scalar) in enumerate(metrics.items()):
                    value = scalar.get('value')
                    kind = 'absent' if 'value' not in scalar else 'null' if value is None else {
                        bool: 'boolean', str: 'string', int: 'number', Decimal: 'number'}[type(value)]
                    sr = self.stat_record(doc, period_path + '/metrics/' + str(j), 'player_stat_scalar', j, key)
                    definition = self.definitions[key]
                    self.put_stat('football.player_match_metric_values', match_id=match['id'], team_id=side['team_id'],
                        player_id=actor, match_player_revision_id=member['revision_id'], source_id=source,
                        source_record_id=sr['id'], period_code=period, period_definition_version='bootstrap_v1',
                        variant_key=variant, is_canonical=False, family_code='standard',
                        metric_code=definition['code'], metric_definition_version=definition['definition_version'],
                        value_kind=kind, numeric_value=value if kind == 'number' else None,
                        text_value=value if kind == 'string' else None, boolean_value=value if kind == 'boolean' else None,
                        numerator=value if 'total' in scalar else None, denominator=scalar.get('total'))

    def install_stats(self):
        assert self.has_core017
        with self._generation('owned_player_statistics_inputs') as generation:
            self.register_metrics()
            self._insert('ingest.public_aliases', route_kind='player', public_key='p_0000zz', player_id=self.ids['players'][0]['id'])
            for (edition, family), members in inputs().items():
                self.add_family(edition, family, members, 'v1')
        return generation

    def correct_stats(self):
        with self._generation('owned_statistics_only_correction') as generation:
            self.add_family('A', 'players', inputs(corrected=True)['A', 'players'], 'v2')
        return generation

    def invalid_stats(self):
        with self._generation('owned_unqualified_statistics_retention') as generation:
            self.add_family('A', 'players', inputs()['A', 'players'], 'global-profile', invalid_profile=True)
        return generation


class StatisticsFixturePublisher(FixturePublisher):
    def __init__(self, fixture, writer, base_binding):
        super().__init__(fixture, writer, base_binding)
        assert digest(BINDING['environmentDescriptor']) == ENV
        self.environment = ENV

    def closures(self, edition, dg, cg):
        base = super().closures(edition, dg, cg)
        f = self.fixture
        mids = [row['id'] for mid, row in f.match_rows.items() if f.match_keys[mid] == edition]
        window = 'recorded_from_gen<=%s AND (recorded_to_gen IS NULL OR %s<recorded_to_gen)'
        cov = self.rows('ingest.match_coverage', 'match_id=ANY(%s) AND feature_code=ANY(%s) AND is_canonical AND ' + window,
                        (mids, list(FAMILIES), dg, dg))
        assert cov, 'No typed player statistics family in edition'
        graph = {'ingest.match_coverage': cov}
        witnesses, documents, defs, periods, player_ids, team_ids, match_revs, side_revs = (set() for _ in range(8))

        def append(table, rows):
            graph.setdefault(table, []).extend(rows)
            witnesses.update(r['source_record_id'] for r in rows if r.get('source_record_id') is not None)

        for c in cov:
            assert c['contract_version'] == CONTRACT and c['variant_key'] == VARIANT
            documents.add(c['document_id'])
            match_revs.add(c['match_revision_id'])
            witnesses.add(c['source_record_id'])
            pair = (c['match_id'], c['source_id'], c['variant_key'] + ':' + c['feature_code'], dg, dg)
            scope = 'match_id=%s AND source_id=%s AND variant_key=%s AND NOT is_deleted AND ' + window
            members = self.rows('football.match_players', scope, pair)
            rows = self.rows('football.player_match_stats', scope, pair)
            cells = self.rows('football.player_match_metric_values', scope, pair)
            by_member = {m['revision_id']: m for m in members}
            assert len(members) == c['observed_row_count'] and len({m['player_id'] for m in members}) == len(members)
            assert c['collection_state'] == ('present' if members else 'empty')
            assert {r['match_player_revision_id'] for r in rows} == set(by_member)
            row_keys = {(r['match_player_revision_id'], r['period_code'], r['period_definition_version']) for r in rows}
            assert len(rows) == len(row_keys)
            for cell in cells:
                assert (cell['match_player_revision_id'], cell['period_code'], cell['period_definition_version']) in row_keys
                defs.add((cell['metric_code'], cell['metric_definition_version'], c['feature_code'], c['source_id']))
            for member in members:
                profiles = self.rows('football.player_profile_versions', 'id=%s AND NOT is_deleted AND ' + window,
                                     (member['profile_version_id'], cg, cg))
                assert len(profiles) == 1
                profile = profiles[0]
                assert profile['player_id'] == member['player_id'] and profile['source_id'] == c['source_id']
                assert profile['profile_context'] == PROFILE + str(profile['source_record_id']) and profile['variant_key'] == 'source:exact', 'Wrong observed profile context'
                append('football.player_profile_versions', profiles)
                player_ids.add(member['player_id'])
                team_ids.add(member['team_id'])
                side_revs.add(member['match_team_revision_id'])
            periods.update((r['period_code'], r['period_definition_version']) for r in rows)
            append('football.match_players', members)
            append('football.player_match_stats', rows)
            append('football.player_match_metric_values', cells)
        append('football.matches', self.rows('football.matches', 'revision_id=ANY(%s)', (sorted(match_revs),)))
        append('football.match_teams', self.rows('football.match_teams', 'revision_id=ANY(%s)', (sorted(side_revs),)))
        append('ingest.source_records', self.rows('ingest.source_records', 'id=ANY(%s)', (sorted(witnesses),)))
        assert documents <= {row['document_id'] for row in graph['ingest.source_records']}
        append('ingest.source_documents', self.rows('ingest.source_documents', 'id=ANY(%s)', (sorted(documents),)))
        append('ingest.public_aliases', self.rows('ingest.public_aliases', '(player_id=ANY(%s) OR team_id=ANY(%s) OR match_id=ANY(%s)) AND NOT is_deleted AND ' + window,
               (sorted(player_ids), sorted(team_ids), mids, cg, cg)))
        for code, version, family, source in sorted(defs):
            append('football.metric_definitions', self.rows('football.metric_definitions',
                'code=%s AND definition_version=%s AND ' + window, (code, version, dg, dg)))
            append('football.source_metric_mappings', self.rows('football.source_metric_mappings',
                'metric_code=%s AND metric_definition_version=%s AND family_code=%s AND source_id=%s AND ' + window,
                (code, version, family, source, dg, dg)))
        for code, version in sorted(periods):
            append('football.periods', self.rows('football.periods', 'code=%s AND definition_version=%s AND ' + window,
                  (code, version, dg, dg)))
        # Set semantics for reused physical definitions/profile rows, sorted
        # independently of the route queries and source traversal order.
        for table, rows in graph.items():
            pk = f.tables[table]['primary_key']['columns']
            unique = {tuple(r[k] for k in pk): r for r in rows}
            graph[table] = [unique[key] for key in sorted(unique)]
        stats = digest(graph)
        native = base['joint']['nativeClosureSha256']
        joint = deepcopy(base['joint'])
        joint['nativeClosureSha256'] = digest({'matchNative017ClosureSha256': native,
            'matchStatisticsClosureSha256': stats, 'scheme': BINDING['environmentDescriptor']['publication']['compositeNativeScheme']})
        return {**base, 'joint': joint, 'dependenciesSha256': digest(joint),
                'statisticsClosureSha256': stats, 'originalNative017ClosureSha256': native,
                'statisticsRows': {k: len(v) for k, v in graph.items()}}
