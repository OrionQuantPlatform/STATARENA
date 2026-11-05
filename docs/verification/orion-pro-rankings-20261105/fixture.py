"""Owned synthetic FIFA and UEFA observations, authored before the adapter."""
from __future__ import annotations
from datetime import date, datetime, timezone
from decimal import Decimal
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location(
    'rankings_competition_base', ROOT / 'docs/verification/orion-pro-competitions-20261105/fixture.py',
)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
NOW = base.NOW
UEFA_ID = '0000012345'
REP = 'summary-v1-shots-v1'
ROLE = {'fifa': 'FIFA', 'uefa': 'UEFA', 'sportsapi': 'SportsAPI'}
UEFA_URL = 'https://comp.uefa.com/v2/coefficients?coefficientRange=OVERALL&coefficientType=MEN_ASSOCIATION&language=EN&page=1&pagesize=50&seasonYear=2026'
FIFA_URL = 'https://inside.fifa.com/api/ranking-overview?locale=en&dateId=FRS_20261012&rankingType=football'


class RankingFixture(base.CompetitionFixture):
    def _catalogue_id(self, generation):
        return self.conn.execute('SELECT id FROM ingest.dataset_snapshots WHERE generation=%s', (generation,)).fetchone()[0]

    def set_catalogue(self, generation):
        sid = self._catalogue_id(generation)
        self.conn.execute(
            'INSERT INTO analytics.catalog_publication(singleton,catalog_snapshot_id,representation_version,published_at) '
            'VALUES(true,%s,%s,%s) ON CONFLICT(singleton) DO UPDATE SET '
            'catalog_snapshot_id=excluded.catalog_snapshot_id,representation_version=excluded.representation_version,published_at=excluded.published_at',
            (sid, REP, NOW),
        )
        return sid

    def publish_rankings(self, generation):
        build = self.build('A', generation, generation)
        self.publish({'A': build}, 'rankings_catalogue_published')
        return {'generation': generation, 'snapshot': self.set_catalogue(generation), 'build': build}

    def _system(self, code, source, method='fixture-observed-v1'):
        return self._insert('football.ranking_systems', code=code, authority=ROLE[source],
                            subject_kind='association' if code == 'uefa-associations' else 'team',
                            gender='men', methodology_version=method)

    def _document(self, source, kind, tag, url):
        key = (source, kind)
        if source not in self.ranking_sources:
            found = self._row('ingest.sources', 'code=%s', (source,))
            self.ranking_sources[source] = found or self._insert('ingest.sources', code=source, name=ROLE[source])
        source_id = self.ranking_sources[source]['id']
        if key not in self.ranking_datasets:
            self.ranking_datasets[key] = self._insert(
                'ingest.source_datasets', source_id=source_id, dataset_key='rankings:' + kind,
                contract_version='orion-rankings-v1',
            )
        return self._insert(
            'ingest.source_documents', source_id=source_id, dataset_id=self.ranking_datasets[key]['id'],
            source_url=url, retrieved_at=NOW, byte_length=19,
            content_sha256=base.hashed(['ranking-document', tag]),
            request_fingerprint=base.hashed(['ranking-request', tag]),
        )

    def _source_record(self, doc, key, ordinal, record_kind='ranking_entry_v1'):
        return self._insert(
            'ingest.source_records', source_id=doc['source_id'], document_id=doc['id'], external_key=key,
            locator_kind='json_pointer', locator='/rows/' + str(ordinal), ordinal=ordinal, record_kind=record_kind,
        )

    def _bind_rankings(self, documents):
        sid = self._catalogue_id(self.g)
        for doc in documents:
            self._insert('ingest.dataset_snapshot_documents', snapshot_id=sid, document_id=doc['id'])

    def _ranking(self, system, key, doc, *, period=None, complete=True, official=True, revision=1, **dates):
        return self._insert(
            'football.ranking_snapshots', system_id=system['id'], subject_kind=system['subject_kind'],
            edition_key=key, period_label=period, official_edition=official, revision=revision,
            source_document_id=doc['id'], retrieved_at=NOW, quality_flags={'ranking_collection_complete': complete},
            **dates,
        )

    def _entry(self, system, snapshot, doc, actor, external, ordinal, name, country, rank, points,
               *, earned=None, previous=None, has_profile=True, captured=None):
        category = snapshot['subject_kind']
        fk = category + '_id'
        record = captured or self._source_record(doc, external, ordinal)
        provenance = {'source_id': record['source_id'], 'source_record_id': record['id']}
        mapping = self._row('football.' + category + '_source_ids',
                            'source_id=%s AND external_id=%s AND recorded_to_gen IS NULL',
                            (record['source_id'], external))
        if not mapping:
            self._insert('football.' + category + '_source_ids', **{fk: actor},
                         external_id=external, first_seen_at=NOW, **provenance)
        if has_profile:
            table = 'football.' + category + '_profile_versions'
            context = 'ranking:' + system['code'] + ':' + snapshot['edition_key']
            old = self._row(table, f'{fk}=%s AND profile_context=%s AND recorded_to_gen IS NULL AND is_canonical', (actor, context))
            fields = dict(observed_at=NOW, display_name=name, country_code_source=country,
                          profile_context=context, variant_key='source:exact', **provenance)
            if old:
                self._replace(table, old, **fields)
            else:
                self._insert(table, **{fk: actor}, **fields)
        return self._insert(
            'football.' + category + '_ranking_entries', snapshot_id=snapshot['id'], **{fk: actor},
            **{'points' if category == 'team' else 'coefficient': points},
            rank=rank, previous_rank=previous, earned_points=earned, source_record_id=record['id'],
        )

    def _team(self, label):
        return self._insert('football.teams', slug='rankings-' + label.lower(), name='Stable ' + label,
                            team_type='national', gender='men')['id']

    def _association(self, code):
        return self._insert('football.associations', name='Stable ' + code, federation_code=code)['id']

    def prepare_rankings(self):
        self.ranking_sources, self.ranking_datasets = {}, {}
        self.ranking_docs, self.ranking_systems = [], {}
        with self._generation('ranking_observations') as generation:
            clubs = self._system('uefa-clubs', 'uefa')
            assoc = self._system('uefa-associations', 'uefa')
            fifa = self._system('fifa-men', 'fifa')
            sport = self._system('uefa-clubs', 'sportsapi', 'fixture-sportsapi-v1')
            sport_assoc = self._system('uefa-associations', 'sportsapi', 'fixture-sportsapi-v1')
            self.ranking_systems.update(clubs=clubs, assoc=assoc, fifa=fifa, sport=sport)
            t0, t1 = [row['id'] for row in self.ids['teams'][:2]]
            club_url = 'https://comp.uefa.com/v2/coefficients?coefficientRange=OVERALL&coefficientType=MEN_CLUB&language=EN&page=1&pagesize=50&seasonYear=2026'
            doc = self._document('uefa', 'uefa-clubs', 'clubs26', club_url)
            self.ranking_docs.append(doc)
            c26 = self._ranking(clubs, '2026.uefa', doc, period='2025/2026')
            self._entry(clubs, c26, doc, t1, '20', 0, 'Second Ranked Club', 'ESP', 2, None)
            self._entry(clubs, c26, doc, t0, UEFA_ID, 1, 'First Ranked Club', 'FRA', 2,
                        Decimal('123.450001'), earned=Decimal('0'), previous=5)
            doc = self._document('uefa', 'uefa-clubs', 'clubs27', club_url.replace('2026', '2027'))
            self.ranking_docs.append(doc)
            c27 = self._ranking(clubs, '2027.uefa', doc, period='2026/2027')
            self._entry(clubs, c27, doc, t1, '20', 0, 'Second Club Next Edition', 'ESP', 1, Decimal('21'))
            countries = [(self._association(c), c, name) for c, name in
                         [('FRA', 'France'), ('ESP', 'Spain'), ('ITA', 'Italy')]]
            for year in (2026, 2027):
                doc = self._document('uefa', 'uefa-associations', f'associations-{year}', UEFA_URL.replace('2026', str(year)))
                self.ranking_docs.append(doc)
                snapshot = self._ranking(assoc, f'{year}.uefa', doc, period=f'{year-1}/{year}',
                                         base_season_year=year, target_season_year=year + 1)
                for i, (actor, country, name) in enumerate(countries):
                    self._entry(assoc, snapshot, doc, actor, str(100 + i), i, name, country,
                                (1, 2, 2)[i], (Decimal('100.123456'), Decimal('80.100000'), Decimal('80.100000'))[i],
                                earned=Decimal('10') + i)
                    self._insert(
                        'football.association_ranking_components', snapshot_id=snapshot['id'], association_id=actor,
                        component_period=str(year), component_rank=i + 1,
                        value=(Decimal('70'), Decimal('8.125001'), Decimal('2'))[i],
                        national_association_points=(Decimal('0'), None, Decimal('7.25'))[i],
                        total_value=Decimal('50') + i, total_points_with_bonus=Decimal('1.25') + i,
                        factor_bonus_for_title_held=Decimal('0'), factor_total_bonus=Decimal('0.5'),
                        matches_count=10 + i, teams_count=3, teams_still_playing=(0, 2, 1)[i],
                    )
            self.national = [self._team(c) for c in ('BRA', 'FRA')]
            doc = self._document('fifa', 'fifa-men', 'fifa', FIFA_URL)
            page = self._document('fifa', 'fifa-men', 'fifa-page', FIFA_URL)
            self.ranking_docs.extend([doc, page])
            self._insert('ingest.document_lineage', derived_document_id=doc['id'], parent_document_id=page['id'],
                         transform_version='ranking-fixture-observed-v1')
            f26 = self._ranking(fifa, '2026-10-12.fifa', doc, period='Official observed date',
                                effective_on=date(2026,10,12),
                                published_at=datetime(2026,10,14,12,30,tzinfo=timezone.utc),
                                source_updated_at=datetime(2026,10,16,13,45,tzinfo=timezone.utc))
            self._entry(fifa, f26, doc, self.national[0], '0001', 0, 'Brasil', 'BRA', 1,
                        Decimal('9007199254.740993'), previous=3)
            self._entry(fifa, f26, page, self.national[1], '2', 0, 'France', 'FRA', 2, Decimal('18.123456'))
            doc = self._document('sportsapi', 'uefa-clubs', 'sports-club', 'https://api.sportsapi.app/v2/rankings/uefa-clubs')
            self.ranking_docs.append(doc)
            s26 = self._ranking(sport, '2026-11-04.sportsapi', doc, official=False)
            self._entry(sport, s26, doc, t0, 'soc-007', 0, 'SportsAPI Club', 'FRA', 1, Decimal('3.456789'))
            doc = self._document('sportsapi', 'uefa-associations', 'sports-unadmitted', 'https://api.sportsapi.app/v2/rankings/uefa-countries')
            self.ranking_docs.append(doc)
            self._ranking(sport_assoc, '2026-11-04.sportsapi', doc, complete=False, official=False)
            self._bind_rankings(self.ranking_docs)
        self.rankings_generation = generation
        return {'generation': generation, 'documents': [d['id'] for d in self.ranking_docs]}

    def correction(self, mode):
        with self._generation('ranking_' + mode) as generation:
            clubs = self.ranking_systems['clubs']
            t0, t1 = [row['id'] for row in self.ids['teams'][:2]]
            if mode in ('bound', 'unbound'):
                doc = self._document('uefa', 'uefa-clubs', mode, None)
                snapshot = self._ranking(clubs, '2026.uefa', doc, period='2025/2026',
                                         revision=2 if mode == 'bound' else 3)
                self._entry(clubs, snapshot, doc, t0, UEFA_ID, 0, 'Corrected Club' if mode == 'bound' else 'Unbound Club',
                            'FRA', 3, Decimal('71.876543') if mode == 'bound' else Decimal('1.2'))
                self._entry(clubs, snapshot, doc, t1, '20', 1, 'Second Ranked Club', 'ESP', 3, None)
            elif mode == 'link_ambiguous':
                doc = self._document('uefa', 'uefa-clubs', mode, None)
                r = self._source_record(doc, '0000012346', 0, 'ranking_identity_v1')
                self._insert('football.team_source_ids', team_id=t0, external_id=r['external_key'],
                             source_id=r['source_id'], source_record_id=r['id'])
            elif mode == 'incomplete':
                doc = self._document('uefa', 'uefa-clubs', mode, None)
                self._ranking(clubs, '2027.uefa', doc, period='2026/2027', revision=2, complete=False)
            elif mode == 'method_ambiguous':
                doc = self._document('uefa', 'uefa-clubs', mode, None)
                other = self._system('uefa-clubs', 'uefa', 'fixture-other-observed-method')
                self._ranking(other, '2026.uefa', doc, period='2025/2026', complete=False)
            elif mode == 'no_profile':
                doc = self._document('fifa', 'fifa-men', mode, None)
                fifa = self.ranking_systems['fifa']
                snapshot = self._ranking(fifa, '2026-11-02.fifa', doc)
                self._entry(fifa, snapshot, doc, self.national[0], '0001', 0, '', None, 1, Decimal('2'),
                            has_profile=False)
            else:
                raise AssertionError(mode)
            if mode != 'unbound':
                self.ranking_docs.append(doc)
            self._bind_rankings(self.ranking_docs)
        return {'generation': generation, 'document': doc['id']}

    def foreign_lineage(self):
        with self._generation('rankings_invalid_ancestor'):
            fifa = self.ranking_systems['fifa']
            doc = self._document('fifa', 'fifa-men', 'invalid-ancestor', FIFA_URL)
            snapshot = self._ranking(fifa, '2026-10-13.fifa', doc)
            old = self._row('ingest.source_records', 'source_id=%s AND external_key=%s',
                            (doc['source_id'], '0001'))
            self._entry(fifa, snapshot, doc, self.national[0], '0001', 0, 'Invalid', 'BRA',
                        1, Decimal('2'), captured=old, has_profile=False)


CompetitionFixture = RankingFixture
