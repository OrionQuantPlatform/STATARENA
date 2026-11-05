"""Before-code HTTP expectations for four normalized player period routes."""
from decimal import Decimal
from urllib.parse import urlencode

from fixture_publisher import FixturePublisher
from http_cases import decoded, exact, route as native_route
from player_period_fixture import CONTRACT, ENV, LABELS, MIDS, PlayerPeriodFixture, StatisticsFixturePublisher, inputs

CONTENT = '/*orion:match-statistics:payload:'
PUBLISHED = 'STATISTICS_PUBLICATION_UNQUALIFIED'
UNAVAILABLE = 'STATISTICS_COHORT_UNAVAILABLE'
POSITION = {'full_match': 'All', 'first_half': 'FirstHalf', 'second_half': 'SecondHalf',
            'extra_time_first_half': 'ExtraFirstHalf', 'extra_time_second_half': 'ExtraSecondHalf'}
PERIOD_ORDER = list(POSITION)


def path(match, family, v, player=None, **extra):
    tail = '/players' + (('/' + player) if player else '') + ('/halves' if family == 'player_halves' else '')
    params = {'representation': CONTRACT, 'v': v, **extra}
    query = urlencode({k: x for k, x in params.items() if x is not None})
    return '/api/pitchapi/matches/' + match + tail + ('?' + query if query else '')


def expected(edition, family, player=None, corrected=False):
    rows = []
    for record in inputs(corrected=corrected)[edition, family]:
        profile = {key: value for key, value in record['profile'].items() if key != 'id'}
        profile['id'] = record['public']
        team = {'A': {'home': 't_000001', 'away': 't_000002'},
                'B': {'home': 't_000001'}, 'C': {}}[edition][record['team']]
        row = {'player': profile, 'team_id': team}
        periods = []
        for code, metrics in sorted(record['periods'], key=lambda p: PERIOD_ORDER.index(p[0])):
            values = {LABELS[key]: {'key': key, 'stat': metrics[key]} for key in sorted(metrics)}
            periods.append({'period': POSITION[code], 'stats': [{'key': 'top_stats', 'stats': values}] if values else []})
        if family == 'players':
            row['stats'] = periods[0]['stats']
        else:
            row['periods'] = periods
        rows.append(row)
    if player:
        item = next(r for r in rows if r['player']['id'] == player)
        return item if family == 'players' else {'match_id': MIDS[edition], **item}
    return rows if family == 'players' else {'match_id': MIDS[edition], 'players': rows}


def meta_only(response):
    assert len(response['sql']) <= 2
    assert not any(CONTENT in q['sql'] or 'numeric_value' in q['sql'] or 'display_name' in q['sql']
                   for q in response['sql']), response['sql']


def failure(response, status, code):
    assert response['status'] == status and response['headers']['cache-control'] == 'no-store', response
    meta_only(response)
    assert decoded(response)['error']['code'] == code, response


class PlayerPeriodCases:
    def __init__(self, harness):
        self.h = harness
        self.published = {}
        self.snapshots = {}

    def publish(self, stage, generation, *, statistics):
        writer = self.h.writer
        publisher = (StatisticsFixturePublisher if statistics else FixturePublisher)(self.f, writer, self.h.binding017)
        result = publisher.publish(generation, 'ABC', stage)
        self.published[stage] = result
        self.h.report['publications'][stage] = result
        if statistics:
            assert all(t['row']['environment_sha256'] == ENV for t in result['tokens'].values())
        return result

    def token(self, key, stage='combined'):
        return self.published[stage]['tokens'][key]['v']

    def request(self, family='players', edition='A', player=None, stage='combined', method='GET', headers=None):
        return self.h.http(path(MIDS[edition], family, self.token(edition, stage), player), method=method, headers=headers)

    def verify(self, response, edition, family, player=None, stage='combined', corrected=False):
        assert response['status'] == 200, (response['status'], response['body'])
        value, headers = decoded(response), response['headers']
        exact(expected(edition, family, player, corrected), value['data'])
        assert value['representation'] == {'version': CONTRACT, 'sourceToken': self.token(edition, stage),
                                           'family': family, 'origin': 'published-player-period-metrics'}
        assert headers['x-orion-representation'] == self.token(edition, stage)
        assert headers['x-orion-statistics-representation'] == CONTRACT
        assert headers['etag'].startswith('W/"orion-statistics1-') and response['bytes'] <= 1024**2
        assert len(response['sql']) <= 5 and all(not q.get('error') for q in response['sql'])
        return response

    def same(self, original):
        current = self.h.http(original['path'])
        assert (current['status'], current['body'], current['headers'].get('etag')) == (
            original['status'], original['body'], original['headers'].get('etag'))

    def p01(self):
        info = self.h.start_http('1')
        assert info['identity'] == [{'role': 'statarena_runtime', 'readonly': 'on'}]
        assert info['runtime'] == self.h.report['runtime']
        manifest = self.h.http('/api/dashboard/manifest')
        assert manifest['status'] == 200
        legacy = next(e['representationToken'] for e in decoded(manifest)['editions']
                      if e['season'] == self.h.fixture.editions['A']['season_key'])
        self.legacy = self.h.http('/api/matches/' + MIDS['A'] + '/summary?v=' + legacy)
        assert self.legacy['status'] == 200
        self.h.install016()
        self.h.install017()
        self.f = self.h.fixture = PlayerPeriodFixture.from_prepared(self.h.fixture)
        self.f.register_contract(self.h.admin)
        native = self.f.install_observations()
        self.publish('prior-native017', native['generation'], statistics=False)
        t = self.published['prior-native017']['tokens']['A']
        r = self.h.http(native_route('events', tokens=t))
        assert r['status'] == 200 and r['headers']['x-orion-native-representation'] == t['nv']
        self.old_native = r
        if self.h.phase != 'red':
            failure(self.request(stage='prior-native017'), 503, PUBLISHED)

    def p02(self):
        generation = self.f.install_stats()
        self.h.report['statInputsGeneration'] = generation
        self.publish('combined', generation, statistics=True)
        self.h.count_rows('combined')
        r = self.request()
        if self.h.phase == 'red':
            failure(r, 501, 'PRO_ROUTE_NOT_IMPLEMENTED')
            assert r['sql'] == []
            return 'observed-red'
        self.snapshots['full'] = self.verify(r, 'A', 'players')

    def p03(self):
        r = self.snapshots['full']
        data = decoded(r)['data']
        assert [row['player']['name'] for row in data] == ['Observed player A', '']
        assert list(data[0]['stats'][0]['stats']) == [LABELS[key] for key in sorted(LABELS)]
        assert all('Shared striker v1' not in row['player']['name'] for row in data)

    def p04(self):
        r = self.request(player='p_000001')
        self.snapshots['single'] = self.verify(r, 'A', 'players', 'p_000001')
        alias = self.request(player='p_0000zz')
        self.verify(alias, 'A', 'players', 'p_000001')
        assert alias['headers']['etag'] != r['headers']['etag']
        failure(self.request(player='p_000002'), 404, 'STATISTICS_PLAYER_NOT_FOUND')

    def p05(self):
        r = self.request('player_halves')
        self.snapshots['halves'] = self.verify(r, 'A', 'player_halves')
        rows = decoded(r)['data']['players']
        assert [x['period'] for x in rows[0]['periods']] == ['FirstHalf', 'SecondHalf']
        assert [x['period'] for x in rows[1]['periods']] == ['SecondHalf']

    def p06(self):
        r = self.request('player_halves', player='p_000001')
        self.snapshots['single_halves'] = self.verify(r, 'A', 'player_halves', 'p_000001')
        assert decoded(r)['data']['player']['name'] == 'Observed halves player A'

    def p07(self):
        r = self.snapshots['full']
        for value in ('9007199254740993', '0.8200000000000000001'):
            assert value in r['body'] and '"' + value + '"' not in r['body']
        stats = decoded(r)['data'][0]['stats'][0]['stats']
        assert type(stats['Goals']['stat']['value']) is Decimal and stats['Goals']['stat']['value'] == 0
        assert stats['Observed marker']['stat']['value'] is False
        assert stats['Known null']['stat']['value'] is None and 'value' not in stats['Known absent']['stat']
        assert stats['Observed text']['stat']['value'] == ''

    def p08(self):
        stats = decoded(self.snapshots['full'])['data'][0]['stats'][0]['stats']
        assert stats['Accurate passes']['stat'] == {'value': 5, 'total': 7}
        assert 'total' not in stats['Expected goals (xG)']['stat']

    def p09(self):
        for family in ('players', 'player_halves'):
            r = self.request(family, edition='C')
            self.snapshots['C-' + family] = self.verify(r, 'C', family)
        failure(self.request('player_halves', edition='B'), 503, UNAVAILABLE)
        failure(self.request(edition='C', player='p_000003'), 404, 'STATISTICS_PLAYER_NOT_FOUND')
        assert decoded(self.snapshots['full'])['data'][1]['stats'] == []

    def p10(self):
        bad = self.f.invalid_stats()
        before = self.h.admin.execute('SELECT count(*) FROM analytics.aggregation_builds').fetchone()[0]
        try:
            self.publish('bad-profile', bad, statistics=True)
        except AssertionError as exc:
            assert str(exc) == 'Wrong observed profile context', str(exc)
            self.h.report['rejectedStatisticsAdmission'] = {'generation': bad, 'reason': str(exc)}
        else:
            raise AssertionError('Synthetic publisher accepted a global profile in an exact observed cohort')
        after = self.h.admin.execute('SELECT count(*) FROM analytics.aggregation_builds').fetchone()[0]
        assert before == after
        self.same(self.snapshots['full'])

    def p11(self):
        for original in [self.snapshots[key] for key in ('full', 'single', 'halves', 'single_halves', 'C-players')]:
            tag = original['headers']['etag']
            for r, status in [
                (self.h.http(original['path'], method='HEAD'), 200),
                (self.h.http(original['path'], headers={'If-None-Match': 'W/"other", ' + tag}), 304),
            ]:
                assert r['status'] == status and r['bytes'] == 0 and r['headers']['etag'] == tag
                meta_only(r)
        original = self.snapshots['halves']
        r = self.h.http(original['path'], headers={'If-None-Match': 'W/"other"'})
        assert (r['status'], r['body'], r['headers']['etag']) == (200, original['body'], original['headers']['etag'])

    def p12(self):
        v = self.token('A')
        for p in [path(MIDS['A'], 'players', 'bad'), path(MIDS['A'], 'players', None),
                  path(MIDS['A'], 'players', v, representation='summary-v1-shots-v1'),
                  path(MIDS['A'], 'players', v) + '&v=' + v, path(MIDS['A'], 'players', v, nv='fake')]:
            failure(self.h.http(p), 400, 'STATISTICS_VERSION_INVALID')
        failure(self.h.http(path(MIDS['B'], 'players', v)), 404, 'RESOURCE_NOT_FOUND')
        failure(self.h.http(path(MIDS['A'], 'players', v), method='POST'), 405, 'METHOD_NOT_ALLOWED')

    def p13(self):
        g = self.f.correct_stats()
        fresh = self.publish('stats-only-correction', g, statistics=True)
        assert fresh['created'].keys() == {'A'}
        old, new = self.published['combined']['componentProof']['A'], fresh['componentProof']['A']
        assert old['joint']['v1ClosureSha256'] == new['joint']['v1ClosureSha256']
        assert old['originalNative017ClosureSha256'] == new['originalNative017ClosureSha256']
        assert old['statisticsClosureSha256'] != new['statisticsClosureSha256']
        assert old['joint']['nativeClosureSha256'] != new['joint']['nativeClosureSha256']
        assert self.token('C') == self.token('C', 'stats-only-correction')
        r = self.verify(self.request(stage='stats-only-correction'), 'A', 'players', stage='stats-only-correction', corrected=True)
        assert r['headers']['etag'] != self.snapshots['full']['headers']['etag']
        for key in ('full', 'C-players', 'halves'):
            self.same(self.snapshots[key])
        self.h.count_rows('corrected')

    def p14(self):
        self.same(self.legacy)
        self.same(self.old_native)
        tokens = self.published['stats-only-correction']['tokens']['A']
        native = self.h.http(native_route('events', tokens=tokens))
        assert native['status'] == 200 and native['headers']['x-orion-native-representation'] == tokens['nv']
        exact(decoded(self.old_native)['data'], decoded(native)['data'])
        for key in ('full', 'halves', 'single', 'single_halves'):
            r = self.snapshots[key]
            assert len(r['sql']) <= 5 and r['bytes'] < 4096
        self.h.boundary()
        self.h.runtime_write_denied()
