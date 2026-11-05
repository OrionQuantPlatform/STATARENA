"""Independent before-code HTTP expectations for five spatial/advanced forms."""
from decimal import Decimal
from urllib.parse import urlencode

from http_cases import decoded, exact, route as native_route
from player_period_cases import PlayerPeriodCases, path as player_path
from player_period_fixture import CONTRACT, MIDS
from spatial_advanced_fixture import FULL_ENV, FullStatisticsPublisher, SpatialAdvancedFixture


CONTENT = '/*orion:spatial-advanced:payload:'
UNQUALIFIED = 'STATISTICS_PUBLICATION_UNQUALIFIED'
UNAVAILABLE = 'STATISTICS_COHORT_UNAVAILABLE'


def path(match, suffix, v, **parameters):
    args = {'representation': CONTRACT, 'v': v, **parameters}
    q = urlencode({key: value for key, value in args.items() if value is not None})
    return '/api/pitchapi/matches/' + match + '/' + suffix + ('?' + q if q else '')


def meta(r):
    assert len(r['sql']) <= 2 and not any(
        CONTENT in q['sql'] or any(field in q['sql'] for field in ('avg_x', 'numeric_value', 'column_index', 'display_name'))
        for q in r['sql']), r['sql']


def fail(r, code, status=503):
    assert r['status'] == status and r['headers']['cache-control'] == 'no-store', (r['status'], r['body'])
    assert decoded(r)['error']['code'] == code, r
    meta(r)


def heat(frame='acting_ltr', corrected=False):
    grid = {'length': 16, 'width': 12, 'cell_length_m': Decimal('6.5'), 'cell_width_m': Decimal('5.5'), 'frame': frame}
    if frame == 'home_ltr':
        return {'match_id': MIDS['A'], 'grid': grid, 'teams': [
            {'team': {'id': 't_000001', 'name': 'Separate home oriented grid'}, 'side': 'home', 'actions': 3, 'cells': []}], 'players': []}
    return {'match_id': MIDS['A'], 'grid': grid,
        'teams': [
            {'team': {'id': 't_000001', 'name': 'Observed home grid'}, 'side': 'home', 'actions': None, 'cells': [[15, 11, 0], [0, 0, 4]]},
            {'team': {'id': 't_000002', 'name': 'Observed away grid'}, 'side': 'away', 'actions': 2, 'cells': None},
        ],
        'players': [
            {'team': {'id': 't_000001', 'name': 'Observed team at player slot'}, 'side': 'home',
             'player': {'id': 'p_000001', 'name': 'Observed map player', 'shirt_number': '09'},
             'actions': 5 if corrected else 4, 'cells': [[3, 7, 2]]},
            {'team': {'id': 't_000002', 'name': 'Observed away at player slot'}, 'side': 'away',
             'player': {'id': 'p_000003', 'name': 'Observed away map player', 'shirt_number': '09'}, 'actions': 0},
        ],
    }


def network():
    p = {'id': 'p_000001', 'name': 'Observed network passer', 'shirt_number': '08'}
    q = {'id': 'p_000003', 'name': 'Observed network runner', 'shirt_number': 9}
    return {'match_id': MIDS['A'], 'networks': [
        {'team': {'id': 't_000001', 'name': 'Observed network home'}, 'centralization': Decimal('0.25'),
         'coordinate_frame': 'metric_105x68_acting_ltr', 'window': {'kind': 'first_substitution', 'from_seconds': 0, 'until_seconds': 2530},
         'nodes': [{'player': p, 'avg_x': 0, 'avg_y': 34, 'passes': 12, 'passes_received': 0},
                   {'player': q, 'avg_x': Decimal('90.5'), 'avg_y': 0, 'passes': 3, 'passes_received': 0}],
         'edges': [{'from': p, 'to': q, 'passes': 3}]},
    ]}


def advanced_teams():
    return {'match_id': MIDS['A'], 'teams': [
        {'team': {'id': 't_000001', 'name': 'Observed advanced home'}, 'actions': 5,
         'passing': {'passes': 21}, 'possession_value': {'xt_total': 0},
         'defending': {'ppda': Decimal('7.25')}, 'territory': {'field_tilt': 50}},
        {'team': {'id': 't_000002', 'name': 'Observed advanced away'}, 'actions': 5,
         'passing': {'passes': 21}, 'possession_value': {'xt_total': 0}},
    ]}


def advanced_players():
    players = []
    for alias, team, name, shirt in [('p_000001', 't_000002', 'Observed advanced away', '08'),
                                      ('p_000003', 't_000001', 'Observed advanced home', 9)]:
        players.append({'player': {'id': alias, 'name': name, 'shirt_number': shirt}, 'team_id': team,
            'actions': 0, 'goalkeeping': None,
            'passing': {'pass_accuracy': Decimal('0.8200000000000000001'), 'progressive_passes': 0},
            'creation': {'sca': 1, 'sca_breakdown': {'pass_live': 1}, 'xag': Decimal('0.25')}})
    return {'match_id': MIDS['A'], 'sorted_by': 'player_id', 'players': players}


class SpatialAdvancedCases:
    def __init__(self, harness):
        self.h = harness
        self.period = PlayerPeriodCases(harness)
        self.receipts = {}
        self.baseline = {}

    def v(self, edition='A', stage='full'):
        return self.receipts[stage]['tokens'][edition]['v']

    def request(self, suffix, edition='A', stage='full', **kw):
        return self.h.http(path(MIDS[edition], suffix, self.v(edition, stage), **kw))

    def publish(self, stage, generation):
        result = FullStatisticsPublisher(self.f, self.h.writer, self.h.binding017).publish(generation, 'ABC', stage)
        self.receipts[stage] = self.h.report['publications'][stage] = result
        assert all(t['row']['environment_sha256'] == FULL_ENV for t in result['tokens'].values())
        return result

    def verify(self, r, expected, family, edition='A', stage='full'):
        assert r['status'] == 200, (r['status'], r['body'])
        out, headers = decoded(r), r['headers']
        exact(expected, out['data'])
        assert out['representation'] == {'version': CONTRACT, 'sourceToken': self.v(edition, stage),
                                         'family': family, 'origin': 'published-spatial-advanced-facts'}
        assert headers['x-orion-representation'] == self.v(edition, stage)
        assert headers['x-orion-statistics-representation'] == CONTRACT
        assert headers['etag'].startswith('W/"orion-spatial-advanced1-')
        assert r['bytes'] <= 1024**2 and len(r['sql']) <= 5
        return r

    def same(self, original):
        r = self.h.http(original['path'])
        assert (r['status'], r['body'], r['headers'].get('etag')) == (
            original['status'], original['body'], original['headers'].get('etag'))

    def x01(self):
        self.period.p01()
        gen = self.period.f.install_stats()
        self.period.publish('combined', gen, statistics=True)
        self.old_period = self.period.verify(self.period.request(), 'A', 'players')
        self.f = self.h.fixture = SpatialAdvancedFixture.from_prepared(self.period.f)
        if self.h.phase != 'red':
            fail(self.h.http(path(MIDS['A'], 'heatmaps', self.period.token('A'))), UNQUALIFIED)

    def x02(self):
        self.publish('full', self.f.install_additional())
        self.h.count_rows('full')
        r = self.request('heatmaps')
        if self.h.phase == 'red':
            fail(r, 'PRO_ROUTE_NOT_IMPLEMENTED', 501)
            assert r['sql'] == []
            return 'observed-red'
        self.baseline['heat'] = self.verify(r, heat(), 'heatmaps')

    def x03(self):
        data = decoded(self.baseline['heat'])['data']
        assert data['teams'][0]['actions'] is None and data['teams'][0]['cells'][0] == [15, 11, 0]
        assert data['teams'][0]['team']['name'] != data['players'][0]['team']['name']

    def x04(self):
        response = self.verify(self.request('heatmaps', frame='home_ltr'), heat('home_ltr'), 'heatmaps')
        assert response['headers']['etag'] != self.baseline['heat']['headers']['etag']
        fail(self.request('heatmaps', 'B', frame='home_ltr'), UNAVAILABLE)
        fail(self.request('heatmaps', frame='unverified'), 'STATISTICS_VERSION_INVALID', 400)

    def x05(self):
        self.verify(self.request('heatmaps', 'B'), {'match_id': MIDS['B'], 'teams': None}, 'heatmaps', 'B')
        self.baseline['empty'] = self.verify(self.request('heatmaps', 'C'),
            {'match_id': MIDS['C'], 'teams': [], 'players': []}, 'heatmaps', 'C')
        assert 'cells' not in decoded(self.baseline['heat'])['data']['players'][1]

    def x06(self):
        self.baseline['network'] = self.verify(self.request('advanced/network'), network(), 'pass_networks')

    def rejected(self, key, setup, message):
        f = self.f
        before = self.h.admin.execute('SELECT count(*) FROM analytics.aggregation_builds').fetchone()[0]
        saved = dict(f.additional)

        class RollbackExpected(Exception):
            pass

        try:
            with f.conn.transaction():
                with f._generation('owned_invalid_' + key) as g:
                    setup()
                try:
                    self.publish('invalid-' + key, g)
                except AssertionError as err:
                    assert str(err) == message, str(err)
                    self.h.report.setdefault('rejectedCandidates', {})[key] = {'generation': g, 'reason': str(err)}
                    raise RollbackExpected()
                raise AssertionError('Invalid additional family published')
        except RollbackExpected:
            pass
        finally:
            f.additional = saved
        after = self.h.admin.execute('SELECT count(*) FROM analytics.aggregation_builds').fetchone()[0]
        assert before == after

    def x07(self):
        self.rejected('network-frame', lambda: self.f.network('A', 'bad-frame', invalid=True), 'Unqualified network frame or window')
        self.same(self.baseline['network'])

    def x08(self):
        self.baseline['teams'] = self.verify(self.request('advanced'), advanced_teams(), 'advanced_teams')

    def x09(self):
        expected = advanced_players()
        self.baseline['players'] = self.verify(self.request('advanced/players'), expected, 'advanced_players')
        self.baseline['subject'] = self.verify(self.request('advanced/players/p_000001'), expected['players'][0], 'advanced_players')
        fail(self.request('advanced/players/p_000002'), 'STATISTICS_PLAYER_NOT_FOUND', 404)

    def x10(self):
        r = self.baseline['players']
        assert '0.8200000000000000001' in r['body'] and '"0.8200000000000000001"' not in r['body']
        assert decoded(r)['data']['players'][0]['goalkeeping'] is None
        self.rejected('advanced-conflict', lambda: self.f.advanced('A', 'advanced_teams', 'bad-conflict', invalid=True),
                      'Conflicting typed advanced values')
        self.same(self.baseline['teams'])

    def x11(self):
        for key in ('heat', 'network', 'teams', 'players', 'subject'):
            old = self.baseline[key]
            tag = old['headers']['etag']
            for r, status in [(self.h.http(old['path'], method='HEAD'), 200),
                              (self.h.http(old['path'], headers={'If-None-Match': 'W/"other", ' + tag}), 304)]:
                assert r['status'] == status and r['bytes'] == 0 and r['headers']['etag'] == tag
                meta(r)
        original = self.baseline['heat']
        r = self.h.http(original['path'], headers={'If-None-Match': 'W/"other"'})
        assert (r['status'], r['body'], r['headers']['etag']) == (200, original['body'], original['headers']['etag'])

    def x12(self):
        publication = self.publish('heat-correction', self.f.correction())
        assert publication['created'].keys() == {'A'} and self.v('C') == self.v('C', 'heat-correction')
        before = self.receipts['full']['componentProof']['A']
        after = publication['componentProof']['A']
        for field in ('originalNative017ClosureSha256', 'playerPeriodClosureSha256'):
            assert before[field] == after[field]
        assert before['joint']['v1ClosureSha256'] == after['joint']['v1ClosureSha256']
        assert before['spatialAdvancedClosureSha256'] != after['spatialAdvancedClosureSha256']
        current = self.verify(self.request('heatmaps', stage='heat-correction'), heat(corrected=True), 'heatmaps', stage='heat-correction')
        assert current['headers']['etag'] != self.baseline['heat']['headers']['etag']
        self.same(self.baseline['heat'])
        self.same(self.baseline['empty'])
        self.same(self.old_period)
        r = self.h.http(player_path(MIDS['A'], 'players', self.v(stage='heat-correction')))
        assert r['status'] == 200
        exact(decoded(self.old_period)['data'], decoded(r)['data'])
        self.h.count_rows('corrected')

    def x13(self):
        fail(self.request('advanced/network', 'B'), UNAVAILABLE)
        self.verify(self.request('advanced/network', 'C'), {'match_id': MIDS['C'], 'networks': []}, 'pass_networks', 'C')
        self.verify(self.request('advanced', 'C'), {'match_id': MIDS['C'], 'teams': []}, 'advanced_teams', 'C')
        for url in [path(MIDS['A'], 'heatmaps', self.v(), unknown='x'),
                    path(MIDS['A'], 'advanced', self.v(), frame='home_ltr'),
                    path(MIDS['A'], 'advanced', None), path(MIDS['A'], 'advanced', self.v()) + '&v=bad']:
            fail(self.h.http(url), 'STATISTICS_VERSION_INVALID', 400)

    def x14(self):
        self.same(self.period.legacy)
        t = self.receipts['full']['tokens']['A']
        current = self.h.http(native_route('events', tokens=t))
        assert current['status'] == 200 and current['headers']['x-orion-native-representation'] == t['nv']
        exact(decoded(self.period.old_native)['data'], decoded(current)['data'])
        self.h.boundary()
        self.h.runtime_write_denied()
