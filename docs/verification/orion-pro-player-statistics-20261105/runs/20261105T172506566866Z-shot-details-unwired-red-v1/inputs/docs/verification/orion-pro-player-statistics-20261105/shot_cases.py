"""Pre-code actual HTTP cases for two normalized shot detail routes."""
from decimal import Decimal
import json
from urllib.parse import urlencode

REP = 'shot-detail-normalized-v1'
A = 'm_000001'
B = 'm_000004'
C = 'm_000005'
SHOT1 = 's_000001'
SHOT2 = 's_000002'
UNRESOLVED = 's_000009'
PLAYER1 = 'p_000001'
PLAYER3 = 'p_000003'
ALIAS = 'p_0000zz'
CONTENT = '/*orion:shot-detail:payload*/'


def path(match, suffix, token, **params):
    args = {'representation': REP, 'v': token, **params}
    return f'/api/pitchapi/matches/{match}/{suffix}?' + urlencode({k: v for k, v in args.items() if v is not None})


def body(r):
    def invalid(value):
        raise AssertionError('Invalid numeric token: ' + value)
    return json.loads(r['body'], parse_float=Decimal, parse_constant=invalid)


def okay(r):
    assert r['status'] == 200, (r['status'], r['body'])
    return body(r)


def only_metadata(r):
    assert len(r['sql']) <= 2
    for query in r['sql']:
        assert CONTENT not in query['sql'] and 'x_m' not in query['sql'] and 'xg,' not in query['sql'], query


def fail(r, status, code):
    assert r['status'] == status and r['headers']['cache-control'] == 'no-store', r
    only_metadata(r)
    assert body(r)['error']['code'] == code, r


class ShotCases:
    def __init__(self, harness):
        self.h = harness
        self.f = harness.fixture
        self.original = {}

    def parent(self, match, v):
        r = self.h.http(f'/api/pitchapi/matches/{match}/shots?' + urlencode({'v': v}))
        data = okay(r)['data']
        assert data['representationToken'] == v
        return r, [shot for period in data['periods'] for shot in period['shots']]

    def manifest(self):
        response = self.h.http('/api/dashboard/manifest')
        values = okay(response)['editions']
        return {key: next(v['representationToken'] for v in values if v['season'] == self.f.editions[key]['season_key'])
                for key in 'ABC'}

    def read(self, match, suffix, edition='A', **kwargs):
        token = kwargs.pop('token', self.tokens[edition])
        return self.h.http(path(match, suffix, token), **kwargs)

    def assert_success(self, response, expected, token):
        out = okay(response)
        assert out['status'] == 200 and out['data'] == expected, (out, expected)
        assert out['representation'] == {'version': REP, 'sourceToken': token, 'origin': 'edition-shots'}
        headers = response['headers']
        assert headers['x-orion-representation'] == token
        assert headers['x-orion-statistics-representation'] == REP
        assert headers['etag'].startswith('W/"orion-shot-detail1-') and headers['x-data-source'] == 'AWS'
        assert len(response['sql']) <= 4 and response['bytes'] <= 1024**2
        return response

    def add_shot(self, mid, shot_id, player, *, period, xg, ordinal):
        f = self.f
        match, home, source = f.match_rows[mid], f.sides[mid]['home'], f.ids['source']
        source_doc = f._row('ingest.source_records', 'id=%s', (f.ids['record'],))['document_id']
        record = f._insert('ingest.source_records', document_id=source_doc, source_id=source,
            locator_kind='json_pointer', locator='/synthetic/shots/' + shot_id, ordinal=ordinal,
            record_kind='normalized_shot', external_key=shot_id)
        return f._insert('football.shots', match_id=match['id'], team_id=home['team_id'],
            match_team_revision_id=home['revision_id'], player_id=f.ids['players'][player]['id'] if player is not None else None,
            player_profile_version_id=f.player_profiles[player]['id'] if player is not None else None,
            external_shot_id=shot_id, period_code=period, period_definition_version='bootstrap_v1',
            minute=53 if ordinal else 12, minute_added=0, x_m=0.0, y_m=35.0, xg=xg, xgot=0.0,
            is_goal=False, is_own_goal=False, is_on_target=False, source_event_type='',
            coordinate_frame='acting_ltr', pitch_length_m=105.0, pitch_width_m=68.0,
            source_ordinal=ordinal, source_id=source, source_record_id=record['id'])

    def seed(self):
        f = self.f
        f.conn = self.h.writer
        with f._generation('shot_detail_fixture') as generation:
            player = f.ids['players'][2]['id']
            profile = f.player_profiles[2]['id']
            for mid in [A, 'm_000002']:
                match, home = f.match_rows[mid], f.sides[mid]['home']
                f._insert('football.match_players', match_id=match['id'], team_id=home['team_id'],
                    player_id=player, profile_version_id=profile, match_team_revision_id=home['revision_id'],
                    squad_status='starter', played=True, participation_evidence='synthetic proved player',
                    source_id=f.ids['source'], source_record_id=f.ids['record'])
            f._insert('ingest.public_aliases', route_kind='player', public_key=ALIAS, player_id=f.ids['players'][0]['id'])
            self.add_shot(A, SHOT2, 0, period='second_half', xg=0.0, ordinal=1)
            f.coverages[A] = f._replace('ingest.match_coverage', f.coverages[A], observed_row_count=2)
        build = f.build('A', generation, generation)
        f.publish({'A': build}, 'shot_detail_fixture_publication')
        return generation

    def s01(self):
        info = self.h.start_http('1')
        assert info['identity'] == [{'role': 'statarena_runtime', 'readonly': 'on'}]
        assert info['runtime'] == self.h.report['runtime']
        self.h.report['shotFixtureGeneration'] = self.seed()
        self.h.count_rows('seeded')
        self.tokens = self.manifest()
        self.parents = {}
        for match, edition in [(A, 'A'), (B, 'B'), ('m_000002', 'A')]:
            self.parents[match] = self.parent(match, self.tokens[edition])
        a, b = self.parents[A][1], self.parents[B][1]
        assert [row['id'] for row in a] == [SHOT1, SHOT2] and [row['id'] for row in b] == [SHOT1]
        assert a[0]['expected_goals'] == Decimal('0.82') and a[0]['event_type'] == ''
        assert a[1]['expected_goals'] == 0 and a[1]['x'] == 0 and a[1]['is_goal'] is False
        assert b[0]['expected_goals'] == Decimal('0.99') and b[0]['x'] is None
        assert b[0]['source_coordinates']['x_m'] == Decimal('52.5')
        assert self.parents['m_000002'][1] == []
        self.old_summary = self.h.http('/api/matches/' + A + '/summary?v=' + self.tokens['A'])
        assert okay(self.old_summary)['data']['match']['home']['name'] == 'Shared team v1'
        self.old_fixtures = self.h.http('/api/fixtures?v=' + self.tokens['A'])
        self.old_manifest = self.h.http('/api/dashboard/manifest?v=' + self.tokens['A'])
        assert okay(self.old_fixtures)['data']['matches'][0]['id'] == A
        assert okay(self.old_manifest)['schemaVersion'] == 4

    def s02(self):
        r = self.read(A, 'shots/' + SHOT1)
        if self.h.phase == 'red':
            fail(r, 501, 'PRO_ROUTE_NOT_IMPLEMENTED')
            assert r['sql'] == []
            return 'observed-red'
        self.original['single'] = self.assert_success(r, self.parents[A][1][0], self.tokens['A'])

    def s03(self):
        r = self.read(B, 'shots/' + SHOT1, 'B')
        self.original['B'] = self.assert_success(r, self.parents[B][1][0], self.tokens['B'])
        assert r['headers']['etag'] != self.original['single']['headers']['etag']

    def s04(self):
        expected = {'player': {'id': PLAYER1, 'name': 'Shared striker v1'}, 'shots': self.parents[A][1]}
        r = self.read(A, 'players/' + PLAYER1 + '/shots')
        self.original['player'] = self.assert_success(r, expected, self.tokens['A'])

    def s05(self):
        r = self.read(A, 'players/' + ALIAS + '/shots')
        self.assert_success(r, body(self.original['player'])['data'], self.tokens['A'])
        assert r['headers']['etag'] != self.original['player']['headers']['etag']

    def s06(self):
        for match in (A, 'm_000002'):
            r = self.read(match, 'players/' + PLAYER3 + '/shots')
            self.original['empty' + match] = self.assert_success(
                r, {'player': {'id': PLAYER3, 'name': 'Striker 2 v1'}, 'shots': []}, self.tokens['A'])

    def s07(self):
        for match, suffix, edition, code in [
            (C, 'shots/' + SHOT1, 'C', 'NOT_COLLECTED'),
            ('m_000003', 'shots/' + SHOT1, 'A', 'NOT_COLLECTED'),
            ('m_000002', 'shots/' + SHOT1, 'A', 'SHOT_NOT_FOUND'),
            (A, 'shots/s_999999', 'A', 'SHOT_NOT_FOUND'),
            (A, 'players/p_999999/shots', 'A', 'SHOT_PLAYER_NOT_FOUND'),
            (A, 'players/p_000002/shots', 'A', 'SHOT_PLAYER_NOT_FOUND'),
            (A, 'shots/' + SHOT1, 'B', 'RESOURCE_NOT_FOUND'),
        ]:
            fail(self.read(match, suffix, edition), 404, code)

    def s08(self):
        f = self.f
        with f._generation('shot_detail_unresolved_shooter') as generation:
            self.add_shot(A, UNRESOLVED, None, period='second_half', xg=0.0, ordinal=2)
            f.coverages[A] = f._replace('ingest.match_coverage', f.coverages[A], observed_row_count=3)
        build = f.build('A', generation, generation)
        f.publish({'A': build}, 'unresolved_shooter_publication')
        self.unresolved = self.manifest()['A']
        _, parent = self.parent(A, self.unresolved)
        expected = next(row for row in parent if row['id'] == UNRESOLVED)
        assert expected['player'] is None
        self.assert_success(self.read(A, 'shots/' + UNRESOLVED, token=self.unresolved), expected, self.unresolved)
        fail(self.read(A, 'players/' + PLAYER1 + '/shots', token=self.unresolved), 503, 'SHOT_ACTOR_UNRESOLVED')
        self.h.count_rows('unknown-shooter')

    def s09(self):
        self.h.report['correction'] = self.f.correct()
        corrected = self.manifest()
        _, rows = self.parent(A, corrected['A'])
        shot = next(row for row in rows if row['id'] == SHOT1)
        assert shot['expected_goals'] == Decimal('0.67') and shot['player']['name'] == 'Shared striker corrected'
        fresh = self.assert_success(self.read(A, 'shots/' + SHOT1, token=corrected['A']), shot, corrected['A'])
        assert fresh['headers']['etag'] != self.original['single']['headers']['etag']
        assert corrected['C'] == self.tokens['C']
        for key in ('single', 'player', 'B'):
            old = self.original[key]
            new = self.h.http(old['path'])
            assert new['body'] == old['body'] and new['headers']['etag'] == old['headers']['etag']

    def s10(self):
        for key in ('single', 'player', 'empty' + A, 'empty' + 'm_000002'):
            previous = self.original[key]
            tag = previous['headers']['etag']
            for response, status in [
                (self.h.http(previous['path'], method='HEAD'), 200),
                (self.h.http(previous['path'], headers={'If-None-Match': '"unmatched", ' + tag}), 304),
            ]:
                assert response['status'] == status and response['bytes'] == 0 and response['headers']['etag'] == tag
                only_metadata(response)

    def s11(self):
        previous = self.original['single']
        r = self.h.http(previous['path'], headers={'If-None-Match': 'W/"unmatched"'})
        assert (r['status'], r['body'], r['headers']['etag']) == (200, previous['body'], previous['headers']['etag'])

    def s12(self):
        base = self.original['single']['path']
        for req in [
            base + '&v=' + self.tokens['A'], base + '&limit=1',
            path(A, 'shots/' + SHOT1, None), path(A, 'shots/' + SHOT1, self.tokens['A'], representation=None),
            path(A, 'shots/' + SHOT1, 'bad'), path(A, 'shots/' + SHOT1, self.tokens['A'][:-1] + ('0' if self.tokens['A'][-1] != '0' else '1')),
        ]:
            r = self.h.http(req)
            fail(r, 400, 'SHOT_VERSION_INVALID')
        fail(self.h.http(base, method='POST'), 405, 'METHOD_NOT_ALLOWED')

    def s13(self):
        # The selected SQL projects one physical shot or a bounded actor cohort;
        # identity/count-only metadata uses the separate query and no V1 body SQL.
        single, player = self.original['single'], self.original['player']
        for response, expect in [(single, SHOT1), (player, PLAYER1)]:
            statements = [q for q in response['sql'] if CONTENT in q['sql']]
            assert len(statements) == 1, response['sql']
            assert '/*orion:shots*/' not in ' '.join(q['sql'] for q in response['sql'])
            assert len(response['sql']) <= 4 and response['bytes'] < 4096
            assert expect in statements[0]['values'], statements[0]

    def s14(self):
        for original in (self.old_summary, self.old_fixtures, self.old_manifest, self.parents[A][0], self.parents[B][0]):
            r = self.h.http(original['path'])
            assert r['body'] == original['body'] and r['headers']['etag'] == original['headers']['etag']
        self.h.boundary()
        self.h.runtime_write_denied()
        self.h.stop_http()
        self.h.start_http('0')
        fail(self.h.http(self.original['single']['path']), 400, 'INVALID_PARAMETER')
        self.h.boundary()
