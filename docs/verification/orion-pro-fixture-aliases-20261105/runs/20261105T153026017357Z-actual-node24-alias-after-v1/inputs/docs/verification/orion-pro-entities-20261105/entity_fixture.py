"""Synthetic typed entity input and correction workflow, authored before readers."""
from datetime import date
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
READERS = ROOT / 'docs/verification/orion-pro-readers-20261104'
PILOT = ROOT / 'docs/verification/orion-pro-pilot-20261104'
sys.path[:0] = [str(READERS), str(PILOT)]
from fixture import ReaderFixture
from fixtures import NOW, hashed


class EntityFixture(ReaderFixture):
    def _insert(self, table, **values):
        if table == 'analytics.competition_summary':
            # ReaderFixture's fixed 2teams/1player corpus no longer applies to
            # the extra missing-profile participant and player-free D edition.
            # Derive only this synthetic build's counters from selected facts.
            generation = self.conn.execute('''SELECT d.generation
                FROM analytics.aggregation_builds b JOIN ingest.dataset_snapshots d ON d.id=b.dataset_snapshot_id
                WHERE b.id=%s''', (values['build_id'],)).fetchone()[0]
            edition = values['competition_season_id']
            teams = self.conn.execute('''SELECT count(*) FROM football.competition_teams t
                WHERE t.competition_season_id=%s AND t.is_canonical AND NOT t.is_deleted
                AND ingest.selected_at(%s,t.recorded_from_gen,t.recorded_to_gen)''', (edition,generation)).fetchone()[0]
            players = self.conn.execute('''SELECT count(DISTINCT p.player_id) FROM football.match_players p
                JOIN football.matches m ON m.id=p.match_id WHERE m.competition_season_id=%s
                AND m.publication_state='published' AND m.is_canonical AND NOT m.is_deleted
                AND ingest.selected_at(%s,m.recorded_from_gen,m.recorded_to_gen)
                AND p.is_canonical AND NOT p.is_deleted AND ingest.selected_at(%s,p.recorded_from_gen,p.recorded_to_gen)''',
                (edition,generation,generation)).fetchone()[0]
            values.update(teams_count=teams, players_count=players)
        return super()._insert(table, **values)

    def prepare_entities(self):
        super().prepare()
        with self._generation('entity_contract_inputs') as g:
            self.entity_generation = g
            self.player_profiles[0] = self._replace('football.player_profile_versions', self.player_profiles[0],
                short_name='', country_code_source='', raw_position_code='07', raw_position_code_state='string',
                shirt_number=None, shirt_number_state='null', profile_content_sha256=hashed('entity string profile'),
                external_profile_version_id='entity-string-profile')
            self.player_profiles[1] = self._replace('football.player_profile_versions', self.player_profiles[1],
                raw_position_code='0', raw_position_code_state='number', raw_position_code_source_number=0,
                shirt_number='', shirt_number_state='string', profile_content_sha256=hashed('entity numeric profile'),
                external_profile_version_id='entity-numeric-profile')
            self.team_profiles[0] = self._replace('football.team_profile_versions', self.team_profiles[0],
                short_name='', country_code_source='')
            self.missing_player = self._insert('football.players', display_name='MUTABLE hidden identity')
            self._insert('ingest.public_aliases', route_kind='player', public_key='p_000009', player_id=self.missing_player['id'])
            m = self.match_rows['m_000001']
            self._insert('football.match_players', match_id=m['id'], team_id=self.ids['teams'][0]['id'],
                player_id=self.missing_player['id'], match_team_revision_id=self.sides['m_000001']['home']['revision_id'],
                squad_status='unused_substitute', played=False, participation_evidence='synthetic missing-profile case',
                source_id=self.ids['source'], source_record_id=self.ids['record'])
            outsider = self._insert('football.players', display_name='MUTABLE unscoped identity')
            self._insert('ingest.public_aliases', route_kind='player', public_key='p_000008', player_id=outsider['id'])
            comp = self._insert('football.competitions', slug='entity-second-league', name='Entity second league', competition_type='league', gender='men')
            self._insert('ingest.public_aliases', route_kind='competition', public_key='l_000002',
                competition_id=comp['id'], competition_revision_id=comp['revision_id'])
            edition = self._insert('football.competition_seasons', competition_id=comp['id'], competition_revision_id=comp['revision_id'],
                season_key='2026/2027', label='Entity D', status='active')
            self.editions['D'] = edition
            for team in self.ids['teams'][:2]:
                self._insert('football.competition_teams', competition_season_id=edition['id'], competition_season_revision_id=edition['revision_id'], team_id=team['id'])
            mid = 'm_000006'
            match = self._insert('football.matches', competition_season_id=edition['id'], competition_season_revision_id=edition['revision_id'],
                match_date=date(2026,11,5), kickoff_precision='date', status='not_started', publication_state='published',
                source_id=self.ids['source'], source_record_id=self.ids['record'])
            self.match_rows[mid] = match; self.match_keys[mid] = 'D'
            self._insert('ingest.public_aliases', route_kind='match', public_key=mid, match_id=match['id'], match_revision_id=match['revision_id'])
            self.sides[mid] = {}
            for side, team in zip(('home','away'), self.ids['teams'][:2]):
                self.sides[mid][side] = self._insert('football.match_teams', match_id=match['id'], match_revision_id=match['revision_id'],
                    side=side, team_id=team['id'], participant_label='Synthetic '+side,
                    source_id=self.ids['source'], source_record_id=self.ids['record'])
        self.entity_builds = {key:self.build(key,g,g) for key in 'ABCD'}
        self.publish(self.entity_builds, 'entity_initial_publication')
        return {'generation':g,'builds':self.entity_builds, 'missingProfilePublicId':'p_000009', 'unscopedPublicId':'p_000008'}

    def unsafe_number(self):
        with self._generation('entity_unsafe_number') as g:
            self.player_profiles[0] = self._replace('football.player_profile_versions', self.player_profiles[0],
                raw_position_code='9007199254740993', raw_position_code_state='number', raw_position_code_source_number=9007199254740993,
                profile_content_sha256=hashed('entity unsafe number'), external_profile_version_id='entity-unsafe-number')
        b = self.build('A',g,g)
        self.publish({'A':b}, 'entity_unsafe_publication')
        return {'generation':g,'build':b}

    def ambiguous(self):
        tables = ['football.player_profile_versions','ingest.dataset_snapshots','analytics.publication_versions']
        before = {table:self.conn.execute('SELECT count(*) FROM '+table).fetchone()[0] for table in tables}
        try:
            with self._generation('entity_rejected_ambiguous_profile'):
                self._insert('football.player_profile_versions', player_id=self.ids['players'][2]['id'],
                    external_profile_version_id='entity-conflicting-global', display_name='Rejected duplicate global', observed_at=NOW,
                    profile_context='global', variant_key='manual:conflict', profile_content_sha256=hashed('entity rejected conflict'))
        except self.psycopg.Error as exc:
            assert exc.sqlstate=='23505',str(exc)
            assert exc.diag.constraint_name=='football_player_profile_versions_sv_canonical_current_idx',str(exc)
            rejection = {'sqlstate':exc.sqlstate,'constraint':exc.diag.constraint_name,'message':exc.diag.message_primary}
        else:
            raise AssertionError('Conflicting canonical profile was accepted')
        after = {table:self.conn.execute('SELECT count(*) FROM '+table).fetchone()[0] for table in tables}
        assert before==after,(before,after)
        return {'rejected':rejection,'rowsBefore':before,'rowsAfter':after,'rolledBack':True}
