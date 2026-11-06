"""Before-code HTTP expectations for the six typed match readers."""
from decimal import Decimal
import json
import re
from urllib.parse import urlencode

from fixture_publisher import FixturePublisher
from synthetic_inputs import LARGE_INTEGER, LONG_DECIMAL, source_descriptors
from typed_fixture import PRIMARY

REP = 'match-native-v1'
FAMILIES = ('momentum', 'events', 'lineups', 'h2h', 'stats')
CODES = dict(unavailable='NATIVE_MATCH_UNAVAILABLE', version='NATIVE_MATCH_VERSION_INVALID',
             unrecorded='NATIVE_CORE_FIELDS_UNRECORDED', unknown='NATIVE_MATCH_NOT_FOUND')
MISSING_CORE = ['referee', 'has_playoff', 'league.image_url']
CONTENT = re.compile(r'/\*orion:native-match:payload:')
FORBIDDEN = re.compile(r'\bstatarena(?:_app)?\.|\b(?:football|ingest|analytics)\.\w+_current\b', re.I)


def qs(**params):
    return urlencode({k: v for k, v in params.items() if v is not None})


def route(family, edition='A', tokens=None, *, public_id=None, discover=False, **params):
    path = '/api/pitchapi/matches/' + (public_id or PRIMARY[edition])
    if family != 'match':
        path += '/' + family
    args = {'representation': REP, 'v': tokens['v'] if tokens else None,
            'nv': tokens.get('nv') if tokens and not discover else None, **params}
    query = qs(**args)
    return path + ('?' + query if query else '')


def exact(expected, actual, path='$'):
    """Compare source numbers without binary rounding, and preserve key presence."""
    if type(expected) is dict:
        assert type(actual) is dict and expected.keys() == actual.keys(), (path, expected, actual)
        for name, value in expected.items():
            exact(value, actual[name], path + '.' + name)
    elif type(expected) is list:
        assert type(actual) is list and len(expected) == len(actual), (path, expected, actual)
        for index, (a, b) in enumerate(zip(expected, actual)):
            exact(a, b, path + f'[{index}]')
    elif type(expected) in (Decimal, int):
        assert type(actual) is Decimal and actual.is_finite() and actual == expected, (path, expected, actual)
    else:
        assert type(expected) is type(actual) and expected == actual, (path, expected, actual)


def decoded(response):
    def invalid(value):
        raise AssertionError('Nonfinite token in HTTP JSON: ' + value)
    return json.loads(response['body'], parse_int=Decimal, parse_float=Decimal, parse_constant=invalid)


def metadata(response):
    assert len(response['sql']) <= 2 and not any(CONTENT.search(q['sql'] or '') for q in response['sql']), response['sql']


def failure(response, status, code=None, *, only_metadata=True):
    assert response['status'] == status, (response['status'], response['body'])
    assert response['headers'].get('cache-control') == 'no-store', response
    if only_metadata:
        metadata(response)
    if code:
        assert decoded(response)['error']['code'] == code, response


class Cases:
    def __init__(self, harness):
        self.h = harness
        self.payloads = source_descriptors()
        self.responses = {}
        self.receipts = {}
        self.baselines = {}

    def tokens(self, edition, stage='native016'):
        return self.receipts[stage]['tokens'][edition]

    def get(self, family, edition='A', stage='native016', **kw):
        return self.h.http(route(family, edition, self.tokens(edition, stage), **kw))

    def verify(self, response, edition, family, stage='native016', expected=None):
        assert response['status'] == 200, (response['status'], response['body'])
        tokens = self.tokens(edition, stage)
        headers = response['headers']
        assert headers['x-orion-representation'] == tokens['v']
        assert headers['x-orion-native-version'] == REP
        assert headers['x-orion-native-representation'] == tokens['nv']
        assert headers['x-data-source'] == 'AWS' and headers['etag'].startswith('W/"orion-native1-')
        assert len(response['sql']) <= 6 and response['bytes'] <= 1024 * 1024, response['sql']
        exact(self.payloads[edition][family] if expected is None else expected, decoded(response)['data'])
        return response

    def captured(self, family, edition='A', stage='native016'):
        key = (family, edition, stage)
        if key not in self.responses:
            self.responses[key] = self.verify(self.get(family, edition, stage), edition, family, stage)
        return self.responses[key]

    def validators(self, original):
        tag = original['headers']['etag']
        head = self.h.http(original['path'], method='HEAD')
        conditional = self.h.http(original['path'], headers={'If-None-Match': 'W/"other", ' + tag})
        for expected, response in [(200, head), (304, conditional)]:
            assert response['status'] == expected and response['bytes'] == 0, response
            for header in ('etag', 'x-orion-representation', 'x-orion-native-version', 'x-orion-native-representation'):
                assert response['headers'][header] == original['headers'][header]
            metadata(response)

    def same(self, old, *, conditional=False):
        new = self.h.http(old['path'])
        assert (new['status'], new['body'], new['headers'].get('etag')) == (
            old['status'], old['body'], old['headers'].get('etag')), (old['id'], new['id'])
        if conditional:
            unchanged = self.h.http(old['path'], headers={'If-None-Match': old['headers']['etag']})
            assert unchanged['status'] == 304 and unchanged['bytes'] == 0
            metadata(unchanged)

    def publish(self, stage, generation, editions, binding=None):
        publisher = FixturePublisher(self.h.fixture, self.h.writer, binding or self.h.binding016)
        receipt = self.receipts[stage] = publisher.publish(generation, editions, stage)
        self.h.report['publications'][stage] = receipt
        return receipt

    def r01(self):
        h = self.h
        info = h.start_http('1')
        assert info['identity'] == [{'role': 'statarena_runtime', 'readonly': 'on'}], info
        assert info['handler'] == 'actual-aws-app.handleRequest'
        assert info['runtime'] == h.report['runtime']
        manifest = h.http('/api/dashboard/manifest')
        assert manifest['status'] == 200, manifest
        editions = decoded(manifest)['editions']
        self.legacy_tokens = {key: next(e['representationToken'] for e in editions
            if e['season'] == h.fixture.editions[key]['season_key']) for key in 'ABC'}
        assert all(re.fullmatch(r'pro1\.[1-9][0-9]{0,18}\.[0-9a-f]{64}', value) for value in self.legacy_tokens.values())
        params = '?' + qs(v=self.legacy_tokens['A'])
        self.baselines = {path: h.http(path + params) for path in (
            '/api/dashboard/manifest', '/api/fixtures', '/api/matches/m_000001/summary',
            '/api/pitchapi/matches/m_000001/shots')}
        assert all(r['status'] == 200 and r['headers'].get('etag') for r in self.baselines.values())
        assert decoded(self.baselines['/api/dashboard/manifest'])['schemaVersion'] == 4
        assert decoded(self.baselines['/api/fixtures'])['data']['matches'][0]['id'] == PRIMARY['A']
        assert decoded(self.baselines['/api/matches/m_000001/summary'])['data']['match']['home']['name'] == 'Shared team v1'
        assert decoded(self.baselines['/api/pitchapi/matches/m_000001/shots'])['data']['periods'][0]['shots']
        # OFF only checks the legacy branch/param contract, with no invented data.
        h.stop_http()
        h.start_http('0')
        legacy_rejection = h.http(route('events', tokens={'v': self.legacy_tokens['A']}))
        assert legacy_rejection['status'] == 400 and not legacy_rejection['sql'], legacy_rejection
        h.stop_http()
        h.start_http('1')
        h.install016()
        fixture = h.fixture.install_observations()
        h.report['fixture016'] = fixture
        h.count_rows('native016')
        self.publish('native016', fixture['generation'], 'ABC')

    def r02(self):
        response = self.get('events')
        if self.h.phase == 'red':
            failure(response, 501, 'PRO_ROUTE_NOT_IMPLEMENTED')
            assert not response['sql']
            return 'observed-red'
        self.responses['events', 'A', 'native016'] = self.verify(response, 'A', 'events')

    def r03(self):
        discovered = self.h.http(route('events', tokens=self.tokens('A'), discover=True), method='HEAD')
        assert discovered['status'] == 200 and discovered['bytes'] == 0, discovered
        assert discovered['headers']['x-orion-representation'] == self.tokens('A')['v']
        assert discovered['headers']['x-orion-native-representation'] == self.tokens('A')['nv']
        assert discovered['headers']['x-orion-native-version'] == REP
        metadata(discovered)

    def r04(self):
        response = self.get('match')
        failure(response, 503, CODES['unrecorded'])
        assert decoded(response)['error']['fields'] == MISSING_CORE
        self.same(self.baselines['/api/matches/m_000001/summary'])

    def r05(self):
        self.captured('momentum')
        self.captured('momentum', 'B')

    def r06(self):
        self.captured('events')

    def r07(self):
        rows = decoded(self.captured('events'))['data']['events']
        assert len(rows) == 3 and rows[0]['minute'] == rows[1]['minute'] == 0 and rows[0]['player'] == rows[1]['player']

    def r08(self):
        rows = decoded(self.captured('events'))['data']['events']
        assert rows[0]['sub_in_player']['id'] == 'vendor-sub-A' and 'sub_in_player' not in rows[1]

    def r09(self):
        result = self.h.fixture.reject_native('global_profile')
        assert result['sqlstate'] == '23514' and 'profile event actor observation' in result['message'], result
        self.same(self.captured('events'), conditional=True)

    def r10(self):
        self.captured('lineups')
        self.captured('stats')

    def r11(self):
        for key in 'ABC':
            self.captured('lineups', key)

    def r12(self):
        members = decoded(self.captured('lineups'))['data']['home']['starters']
        assert len(members) == 3 and members[0]['player_id'] == members[1]['player_id']

    def r13(self):
        r = self.captured('lineups')
        assert str(LONG_DECIMAL) in r['body'] and '"' + str(LONG_DECIMAL) + '"' not in r['body']

    def r14(self):
        result = self.h.fixture.reject_native('lineup_shirt_disagreement')
        assert result['sqlstate'] == '23514' and 'lineup member, physical profile or scalar differs' in result['message'], result
        self.same(self.captured('lineups'))

    def r15(self):
        self.captured('stats')

    def r16(self):
        r = self.captured('stats')
        for value in (LARGE_INTEGER, LONG_DECIMAL):
            assert str(value) in r['body'] and '"' + str(value) + '"' not in r['body']

    def r17(self):
        d = self.h.fixture.native_coverage['A', 'stats']
        wrong_canonical = self.h.admin.execute('''SELECT count(*) FROM football.match_team_stat_items i
            JOIN football.team_match_metric_values v ON v.revision_id=i.home_metric_revision_id
            WHERE i.match_id=%s AND i.recorded_from_gen=%s AND v.is_canonical''',
            (d['match_id'], d['recorded_from_gen'])).fetchone()[0]
        assert wrong_canonical == 0
        result = self.h.fixture.reject_native('scalar_wrong_side')
        assert result['sqlstate'] == '23514' and 'scalar' in result['message'], result
        self.same(self.captured('stats'))

    def r18(self):
        self.captured('h2h')

    def r19(self):
        self.captured('h2h', 'B')

    def r20(self):
        for key, families in [('B', ('events', 'stats')), ('C', ('events', 'stats', 'h2h'))]:
            for family in families:
                self.captured(family, key)

    def r21(self):
        tokens = self.tokens('A')
        for path, status, code in [
            (route('events', tokens=tokens, public_id='m_000002'), 503, CODES['unavailable']),
            (route('events', tokens={'v': self.legacy_tokens['A']}), 503, CODES['unavailable']),
            (route('events', tokens=tokens, public_id='m_999999'), 404, CODES['unknown']),
            (route('events', tokens=tokens, public_id=PRIMARY['B']), 404, CODES['unknown']),
        ]:
            failure(self.h.http(path), status, code)
        result = self.h.fixture.reject_native('unrecorded')
        assert result['sqlstate'] == '23514' and 'recorded root and collection' in result['message'], result

    def r22(self):
        for fault, marker in [('leading_zero', 'locator event'), ('count_mismatch', 'event order')]:
            result = self.h.fixture.reject_native(fault)
            assert result['sqlstate'] == '23514' and marker in result['message'], result
        self.same(self.captured('events'))

    def r23(self):
        for family in FAMILIES:
            self.validators(self.captured(family))
        head = self.h.http(route('match', tokens=self.tokens('A')), method='HEAD')
        failure(head, 503)
        assert head['bytes'] == 0 and head['headers']['x-orion-native-error'] == CODES['unrecorded']

    def r24(self):
        previous = self.captured('stats')
        changed = self.h.http(previous['path'], headers={'If-None-Match': 'W/"unmatched"'})
        self.verify(changed, 'A', 'stats')
        assert (changed['body'], changed['headers']['etag']) == (previous['body'], previous['headers']['etag'])

    def r25(self):
        a, b = self.tokens('A'), self.tokens('B')
        path = route('events', tokens=a)
        for bad, method, status in [
            (path + '&v=' + a['v'], 'GET', 400), (path + '&unknown=1', 'GET', 400),
            (route('events', tokens=a, v='bad'), 'GET', 400),
            (route('events', tokens=a, nv='native1.9999999999999999999.' + '0' * 64), 'GET', 400),
            (route('events', tokens=a, nv=b['nv']), 'GET', 400),
            (route('events', tokens=a, nv=a['nv'][:-1] + ('1' if a['nv'][-1] == '0' else '0')), 'GET', 400),
            (route('events', tokens=a, representation=None), 'GET', 400),
            (route('events', tokens=a, v=None), 'GET', 400),
            (path, 'POST', 405),
        ]:
            failure(self.h.http(bad, method=method), status)

    def r26(self):
        update = self.h.fixture.correct_layout()
        self.layout = update
        self.h.count_rows('layout')
        self.publish('layout', update['generation'], 'ABC')
        self.verify(self.get('stats', stage='layout'), 'A', 'stats', 'layout', update['expected'])
        first = self.receipts['native016']['componentProof']['A']['joint']
        second = self.receipts['layout']['componentProof']['A']['joint']
        assert first['v1ClosureSha256'] == second['v1ClosureSha256']
        assert first['nativeClosureSha256'] != second['nativeClosureSha256']
        assert self.receipts['layout']['created'].keys() == {'A'}
        assert all(self.tokens('A')[field] != self.tokens('A', 'layout')[field] for field in ('v', 'nv'))
        self.same(self.captured('stats'), conditional=True)

    def r27(self):
        sql = '''SELECT i.home_metric_revision_id,i.away_metric_revision_id
            FROM football.match_team_stat_items i JOIN ingest.source_records r ON r.id=i.source_record_id
            WHERE i.match_id=%s AND i.recorded_from_gen=%s AND r.locator LIKE '/data/periods/0/groups/0/items/%%'
            ORDER BY r.ordinal'''
        mid = self.layout['coverage']['match_id']
        old = self.h.admin.execute(sql, (mid, self.tokens('A')['row']['dataset_generation'])).fetchall()
        new = self.h.admin.execute(sql, (mid, self.layout['generation'])).fetchall()
        assert len(old) == 4 and new == [old[1], old[0], old[2], old[3]], (old, new)

    def r28(self):
        change = self.h.fixture.correct_two_families()
        self.two = self.publish('two-families', change['generation'], 'ABC')
        assert self.two['created'].keys() == {'A', 'B'} and self.tokens('C') == self.tokens('C', 'two-families')
        self.verify(self.get('momentum', 'A', 'two-families'), 'A', 'momentum', 'two-families', change['A'])
        self.verify(self.get('events', 'B', 'two-families'), 'B', 'events', 'two-families', change['B'])
        for family, edition in [('momentum', 'A'), ('events', 'B'), ('stats', 'C')]:
            self.same(self.captured(family, edition), conditional=True)
        self.two_generation = change['generation']
        self.h.count_rows('two-families')

    def r29(self):
        before = self.h.count_rows('before-noop'), self.h.sequences()
        retry = self.publish('same-typed-input', self.two_generation, 'ABC')
        after = self.h.count_rows('after-noop'), self.h.sequences()
        assert before == after and retry['created'] == {} and retry['tokens'] == self.two['tokens']

    def r30(self):
        # Existing separate appearance qualification covers the closed physical
        # legacy profile. This actual app reruns all four old V1 representations.
        for response in self.baselines.values():
            self.same(response, conditional=True)

    def r31(self):
        rejected = self.h.fixture.reject_native('nonfinite')
        assert rejected['sqlstate'] == '23514' and 'scalar' in rejected['message'], rejected
        size = self.h.fixture.oversize_events()
        assert size['sourceTextBytes'] == 1024 * 1024 + 1
        self.publish('oversize', size['generation'], 'B')
        response = self.get('events', 'B', 'oversize')
        failure(response, 413, 'PAGE_TOO_LARGE', only_metadata=False)
        assert len(response['sql']) <= 6 and response['bytes'] < 1024
        self.h.count_rows('oversize')

    def r32(self):
        self.h.boundary()
        self.h.runtime_write_denied()

    def c01(self):
        self.r04()
        for family in FAMILIES:
            self.same(self.captured(family))

    def c02(self):
        self.h.install017()
        fixture = self.h.fixture.install_core_observations()
        self.h.report['fixture017'] = fixture
        self.publish('native017', fixture['generation'], 'ABC', self.h.binding017)
        self.h.count_rows('native017')

    def c03(self):
        self.captured('match', stage='native017')

    def c04(self):
        self.captured('match', 'B', 'native017')

    def c05(self):
        self.captured('match', 'C', 'native017')

    def c06(self):
        rejected = self.h.fixture.reject_native('core_pair')
        assert rejected['sqlstate'] == '23514' and 'referee' in (rejected['constraint'] or ''), rejected
        self.same(self.captured('match', stage='native017'), conditional=True)

    def c07(self):
        native = decoded(self.captured('match', stage='native017'))['data']
        old = decoded(self.baselines['/api/matches/m_000001/summary'])['data']['match']
        assert native['id'] != old['id'] and native['home_team']['name'] != old['home']['name']
        assert native['score_home'] == 0 and native['score_away'] == 1
        assert native['league']['image_url'].startswith('https://observed.fixture.invalid/')

    def c08(self):
        update = self.h.fixture.correct_core()
        corrected = self.publish('core-correction', update['generation'], 'ABC', self.h.binding017)
        old = self.captured('match', stage='native017')
        new = self.verify(self.get('match', stage='core-correction'), 'A', 'match', 'core-correction', update['expected'])
        assert old['headers']['etag'] != new['headers']['etag']
        assert corrected['created'].keys() == {'A'} and self.tokens('C', 'native017') == self.tokens('C', 'core-correction')
        assert self.receipts['native017']['componentProof']['A']['joint']['v1ClosureSha256'] == corrected['componentProof']['A']['joint']['v1ClosureSha256']
        self.same(old, conditional=True)
        self.same(self.captured('match', 'C', 'native017'), conditional=True)

    def c09(self):
        change = self.h.fixture.change_delivery_media()
        assert change['before'] != change['after']
        self.h.report['deliveryMetadataChange'] = change
        self.same(self.captured('match', stage='native017'), conditional=True)

    def c10(self):
        self.validators(self.captured('match', stage='native017'))
        for family in FAMILIES:
            self.captured(family, stage='native017')
            self.same(self.captured(family))
        self.r04()
        self.r30()
        self.r32()
