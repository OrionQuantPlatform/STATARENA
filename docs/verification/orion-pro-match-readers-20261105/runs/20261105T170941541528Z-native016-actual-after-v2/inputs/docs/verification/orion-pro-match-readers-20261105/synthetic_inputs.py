"""Independent synthetic native payload expectations, authored before readers.

These are not real source bodies. An owned SQL fixture will retain only the
typed fields, state/shape declarations, source-record metadata and physical
bindings. Reader output must equal these data shapes, including absent keys.
"""
from copy import deepcopy
from decimal import Decimal


LONG_DECIMAL = Decimal('0.8200000000000000001')
LARGE_INTEGER = Decimal('9007199254740993')


def teams(edition):
    return {
        'home_team': {'id': f'vendor-{edition}-home', 'name': f'Observed {edition} home',
                      'image_url': f'https://observed.fixture.invalid/{edition}/home.png'},
        'away_team': {'id': f'vendor-{edition}-away', 'name': '', 'image_url': None},
    }


def root(edition, with_teams=False):
    data = {'match_id': f'vendor-match-{edition}'}
    if with_teams:
        data.update(teams(edition))
    return data


def events(edition):
    data = root(edition)
    if edition == 'B':
        return {**data, 'events': []}
    if edition == 'C':
        return {**data, 'events': None}
    player = {'id': 'vendor-player-A', 'name': '', 'position_id': '09', 'image_url': None}
    first = {
        'id': '', 'event_type': '', 'period': 'First source half', 'minute': 0,
        'minute_added': 0, 'second': 0, 'is_penalty': False, 'is_own_goal': False,
        'score_home': 0, 'score_away': 0, 'team_id': 'vendor-A-home', 'player': player,
        'sub_in_player': {'id': 'vendor-sub-A', 'name': 'Captured substitute',
                          'position_id': 91, 'image_url': 'https://observed.fixture.invalid/sub.png'},
    }
    # Equal display values are distinct physical source occurrences. The second
    # has no native ID or sub-in property even if a generic related actor exists.
    second = {key: deepcopy(value) for key, value in first.items() if key not in ('id', 'sub_in_player')}
    third = {'event_type': None, 'minute_added': None, 'is_penalty': False,
             'player': None, 'sub_in_player': None}
    return {**data, 'events': [first, second, third]}


def lineups(edition):
    data = root(edition, True)
    if edition == 'B':
        return {**data, 'home': None, 'away': {
            'formation': '', 'lineup_type': 'standard', 'subs': [
                {'player_id': 'vendor-B-sub', 'name': None, 'position_id': 0,
                 'is_captain': False, 'pitch_x': None, 'pitch_y': 0},
            ],
        }}
    if edition == 'C':
        data.pop('home_team')
        return {**data, 'away': None}
    first = {'player_id': 'vendor-A-shared', 'name': '', 'position_id': '09',
             'shirt_number': 0, 'is_captain': False, 'pitch_x': LONG_DECIMAL, 'pitch_y': 0}
    second = {'player_id': 'vendor-A-shared', 'name': 'Same actor, second occurrence',
              'position_id': 91, 'shirt_number': '09', 'is_captain': None, 'pitch_x': None}
    third = {'player_id': 'vendor-A-third', 'name': 'Third observed member', 'shirt_number': None}
    return {**data,
            'home': {'formation': '4-3-3', 'confirmed': False, 'lineup_type': 'standard',
                     'coach': {'name': 'Coach name without a provider ID'},
                     'starters': [first, second, third], 'subs': []},
            'away': {'formation': None, 'confirmed': None, 'lineup_type': '',
                     'coach': {}, 'starters': [], 'subs': None}}


def stats(edition, layout_correction=False):
    data = root(edition, True)
    if edition == 'B':
        return {**data, 'periods': []}
    if edition == 'C':
        return data  # The source-declared periods property is absent.
    items = [
        {'key': 'fixture_duplicate', 'title': 'First source title', 'format_type': '',
         'home': LARGE_INTEGER, 'away': False},
        {'key': 'fixture_duplicate', 'title': 'Second source title', 'format_type': None,
         'home': '07', 'away': None},
        {'key': 'fixture_other', 'title': None, 'home': LONG_DECIMAL, 'away': ''},
        {'key': 'fixture_other', 'format_type': 'raw', 'away': 'NaN'},
    ]
    if layout_correction:
        items[1]['title'] = 'Corrected source title, unchanged scalar'
        items[0], items[1] = items[1], items[0]
    return {**data, 'periods': [
        {'period': 'Source full match', 'groups': [
            {'group_name': '', 'items': items},
            {'group_name': None, 'items': []},
            {'group_name': 'Known null items', 'items': None},
        ]},
        {'period': 'Empty period', 'groups': []},
        {'period': 'Groups property omitted'},
        {'period': None, 'groups': None},
    ]}


def h2h(edition):
    data = root(edition, True)
    if edition == 'A':
        return {**data, 'home_wins': 5, 'draws': 2, 'away_wins': 0,
                'total_matches': 7, 'recent_matches': []}
    if edition == 'C':
        return {**data, 'home_wins': None, 'total_matches': 0, 'recent_matches': None}
    return {**data, 'home_wins': 1, 'draws': 0, 'away_wins': 0,
            'total_matches': 1, 'recent_matches': [
                {'id': 'unresolved-native-prior-match', 'time_utc': '', 'status': '',
                 'finished': False, 'score_home': 0, 'score_away': 0,
                 'home': {'id': 'unresolved-prior-home', 'name': 'Observed prior home', 'image_url': ''},
                 'away': {'id': 'unresolved-prior-away', 'name': None, 'image_url': None}},
            ]}


def momentum(edition):
    if edition != 'A':
        return {**root(edition), 'points': []}
    # Nonmonotone minutes prove that sample order, rather than a time sort,
    # controls the native array. All admitted numbers fit the observed domain.
    return {**root(edition), 'points': [
        {'minute': Decimal('0.25'), 'value': 0},
        {'minute': Decimal('0.20'), 'value': -92},
        {'minute': Decimal('45.25'), 'value': 100},
    ]}


def match(edition, playoff_correction=False):
    data = {'id': f'vendor-match-{edition}', 'date': '2026-11-04', 'time_utc': '18:00:00',
            'status': 'finished', 'score_home': 0, 'score_away': 1, **teams(edition),
            'league': {'id': f'vendor-league-{edition}', 'name': f'Observed league {edition}'},
            'season': {'A': '2024/2025', 'B': '2025/2026', 'C': '2026/2027'}[edition],
            'round_name': 'Observed round', 'stadium': 'Observed ground'}
    if edition == 'A':
        data.update(referee='', has_playoff=playoff_correction)
        data['league']['image_url'] = 'https://observed.fixture.invalid/source-league.png'
    elif edition == 'B':
        data.update(referee=None, has_playoff=None)
        data['league']['image_url'] = None
    return data


FAMILIES = {'events': events, 'lineups': lineups, 'stats': stats,
            'h2h': h2h, 'momentum': momentum, 'match': match}


def source_descriptors():
    return {edition: {name: fixture(edition) for name, fixture in FAMILIES.items()}
            for edition in 'ABC'}
