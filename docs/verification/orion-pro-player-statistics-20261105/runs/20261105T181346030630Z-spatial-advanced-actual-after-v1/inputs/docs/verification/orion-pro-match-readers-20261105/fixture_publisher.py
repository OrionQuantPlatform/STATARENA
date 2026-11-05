"""Synthetic guarded READY workflow for the reader E2E, authored before code.

The components are independently captured SQL tuples from the owned fixture.
Their exact joint encoding uses the approved publication binding. This is not
the production publisher or its canonical closure oracle.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
BASE_MODEL = ROOT / 'docs/architecture/orion-plan-20261104/target-schema.proposed.json'
CODE_SHA = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
NATIVE_FAMILIES = ['events', 'lineups', 'stats', 'h2h', 'momentum', 'match']
PARENT = ('match_id', 'source_id', 'feature_code', 'variant_key', 'recorded_from_gen')
VOLATILE = {'recorded_to_gen', 'updated_at', 'computed_at'}


def canon(value):
    def typed(x):
        if isinstance(x, Decimal):
            return {'numeric': str(x)}
        if isinstance(x, (date, datetime)):
            return {'dateOrTime': x.isoformat()}
        raise TypeError(type(x))
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False, default=typed).encode('utf-8')


def digest(value):
    return hashlib.sha256(canon(value)).hexdigest()


def public_tokens(row, binding):
    fields = ['build_id', 'edition_id', 'dataset_snapshot_id', 'dataset_generation',
              'catalog_snapshot_id', 'catalog_generation', 'representation_version',
              'code_content_sha256', 'dependencies_sha256', 'environment_sha256',
              'metrics_contract_version', 'transform_version']
    pro1 = 'pro1.' + row['build_id'] + '.' + digest([row[k] for k in fields])
    values = {
        '$exactPro1Token': pro1, '$buildIdDecimalString': row['build_id'],
        '$effectiveDatasetGenerationDecimalString': row['dataset_generation'],
        '$effectiveCatalogGenerationDecimalString': row['catalog_generation'],
        '$jointDependenciesSha256': row['dependencies_sha256'],
        '$buildEnvironmentSha256': row['environment_sha256'],
        '$buildCodeContentSha256': row['code_content_sha256'],
    }
    array = [values.get(value, value) for value in binding['nativeToken']['digestInputArray']]
    assert len(array) == 12 and all(type(value) is str and value.isascii() for value in array)
    return {'v': pro1, 'nv': 'native1.' + row['build_id'] + '.' + digest(array),
            'nativeDigestInput': array, 'row': row}


def build_metadata(conn, build_id):
    cur = conn.execute('''SELECT b.id::text build_id,b.competition_season_id::text edition_id,
        b.dataset_snapshot_id::text dataset_snapshot_id,d.generation::text dataset_generation,
        b.catalog_snapshot_id::text catalog_snapshot_id,c.generation::text catalog_generation,
        b.representation_version,b.code_content_sha256,b.dependencies_sha256,b.environment_sha256,
        b.metrics_contract_version,b.transform_version
        FROM analytics.aggregation_builds b JOIN ingest.dataset_snapshots d ON d.id=b.dataset_snapshot_id
        JOIN ingest.dataset_snapshots c ON c.id=b.catalog_snapshot_id
        WHERE b.id=%s AND b.status='ready' AND d.status='sealed' AND c.status='sealed' ''', (build_id,))
    row = cur.fetchone()
    assert row is not None
    return dict(zip((c.name for c in cur.description), row))


class FixturePublisher:
    def __init__(self, fixture, writer, binding):
        self.fixture, self.writer, self.binding = fixture, writer, binding
        model103 = json.loads(BASE_MODEL.read_text())
        self.old_tables = {t['qualified_name']: t for s in model103['schemas'] for t in s['tables']}
        self.environment = digest(['owned synthetic fixture', 'PG18.6', binding['modelSha256']])

    def rows(self, table, where, params, *, old=False):
        spec = (self.old_tables if old else self.fixture.tables)[table]
        names = [c for c in spec['columns'] if c not in VOLATILE]
        fields = ','.join('"' + c + '"' for c in names)
        order = ','.join('"' + c + '"' for c in spec['primary_key']['columns'])
        rows = self.writer.execute(f'SELECT {fields} FROM {table} WHERE {where} ORDER BY {order}', params).fetchall()
        return [dict(zip(names, row)) for row in rows]

    def closures(self, edition, dg, cg):
        f = self.fixture
        mids = [m['id'] for key, m in f.match_rows.items() if f.match_keys[key] == edition]
        ed, competition = f.editions[edition]['id'], f.competition['id']
        window = 'recorded_from_gen<=%s AND (recorded_to_gen IS NULL OR %s<recorded_to_gen)'
        selected = window + ' AND is_canonical AND NOT is_deleted'
        v1 = {}
        for table in ('football.matches', 'football.match_teams', 'football.match_scores', 'football.shots', 'football.match_players'):
            id_column = 'id' if table == 'football.matches' else 'match_id'
            v1[table] = self.rows(table, id_column + '=ANY(%s) AND ' + selected, (mids, dg, dg), old=True)
        v1['football.competition_seasons'] = self.rows('football.competition_seasons', 'id=%s AND ' + selected, (ed, dg, dg), old=True)
        v1['football.competitions'] = self.rows('football.competitions', 'id=%s AND ' + selected, (competition, cg, cg), old=True)
        v1['ingest.match_coverage'] = self.rows('ingest.match_coverage', "match_id=ANY(%s) AND feature_code='shots' AND is_canonical AND " + window,
                                               (mids, dg, dg), old=True)
        teams = sorted({row['team_id'] for row in v1['football.match_teams'] if row['team_id'] is not None})
        players = sorted({row['player_id'] for row in v1['football.match_players']} |
                         {row[field] for row in v1['football.shots'] for field in ('player_id', 'keeper_id') if row[field] is not None})
        for kind, ids in (('team', teams), ('player', players)):
            v1['football.' + kind + '_profile_versions'] = self.rows('football.' + kind + '_profile_versions',
                f"{kind}_id=ANY(%s) AND profile_context IN ('provider_global','legacy_normalized_global','global') AND " + selected,
                (ids, cg, cg), old=True)
        v1['ingest.public_aliases'] = self.rows('ingest.public_aliases', '''(match_id=ANY(%s) OR team_id=ANY(%s)
            OR player_id=ANY(%s) OR competition_id=%s) AND NOT is_deleted AND ''' + window,
            (mids, teams, players, competition, cg, cg), old=True)

        native = {'ingest.match_coverage': self.rows('ingest.match_coverage',
            'match_id=ANY(%s) AND feature_code=ANY(%s) AND is_canonical AND ' + window,
            (mids, NATIVE_FAMILIES, dg, dg))}
        team_profiles, player_profiles, scalars, record_ids, document_ids = set(), set(), set(), set(), set()
        children = {
            'events': ['football.match_events'], 'h2h': ['football.match_h2h_summaries', 'football.match_h2h_entries'],
            'stats': ['football.match_team_stat_periods', 'football.match_team_stat_groups', 'football.match_team_stat_items'],
            'momentum': ['football.match_momentum'],
        }
        def append(table, rows):
            native.setdefault(table, []).extend(rows)
            for row in rows:
                if row.get('source_record_id') is not None:
                    record_ids.add(row['source_record_id'])
        for c in native['ingest.match_coverage']:
            record_ids.add(c['source_record_id']); document_ids.add(c['document_id'])
            team_profiles.update(c[k] for k in ('source_home_team_profile_version_id', 'source_away_team_profile_version_id') if c[k] is not None)
            key = tuple(c[k] for k in PARENT)
            for table in children.get(c['feature_code'], []):
                rows = self.rows(table, ' AND '.join(k + '=%s' for k in PARENT), key)
                append(table, rows)
                if table == 'football.match_events':
                    player_profiles.update(row[k] for row in rows for k in ('player_profile_version_id', 'sub_in_player_profile_version_id') if row[k] is not None)
                if table == 'football.match_team_stat_items':
                    scalars.update(row[k] for row in rows for k in ('home_metric_revision_id', 'away_metric_revision_id'))
            if c['feature_code'] == 'lineups':
                headers = self.rows('football.match_lineups', '''match_id=%s AND source_id=%s AND source_feature_code=%s
                    AND variant_key=%s AND source_collection_from_gen=%s''', key)
                append('football.match_lineups', headers)
                members = self.rows('football.match_players', 'lineup_revision_id=ANY(%s) AND NOT is_deleted AND ' + window,
                                    ([r['revision_id'] for r in headers], dg, dg))
                append('football.match_players', members)
                player_profiles.update(r['profile_version_id'] for r in members if r['profile_version_id'] is not None)
            if c['feature_code'] == 'match':
                append('football.matches', self.rows('football.matches', 'revision_id=%s', (c['match_revision_id'],)))
                append('football.match_observation_details', self.rows('football.match_observation_details', 'source_record_id=%s', (c['source_record_id'],)))
                append('football.match_scores', self.rows('football.match_scores', 'match_id=%s AND source_id=%s AND source_record_id=%s AND ' + window,
                    (c['match_id'], c['source_id'], c['source_record_id'], dg, dg)))
        append('football.team_profile_versions', self.rows('football.team_profile_versions', 'id=ANY(%s)', (sorted(team_profiles),)))
        append('football.player_profile_versions', self.rows('football.player_profile_versions', 'id=ANY(%s)', (sorted(player_profiles),)))
        append('football.team_match_metric_values', self.rows('football.team_match_metric_values', 'revision_id=ANY(%s)', (sorted(scalars),)))
        append('ingest.source_records', self.rows('ingest.source_records', 'id=ANY(%s) OR document_id=ANY(%s)',
               (sorted(record_ids - {None}), sorted(document_ids - {None}))))
        source_documents = sorted({r['document_id'] for r in native['ingest.source_records']})
        append('ingest.source_documents', self.rows('ingest.source_documents', 'id=ANY(%s)', (source_documents,)))
        assert native['ingest.match_coverage'], 'No typed native fixture observation in edition'
        v1sha, nativesha = digest(v1), digest(native)
        joint = {'model107Sha256': self.binding['modelSha256'], 'nativeClosureSha256': nativesha,
                 'scheme': self.binding['jointDependencyScheme'], 'v1ClosureSha256': v1sha}
        return {'joint': joint, 'dependenciesSha256': digest(joint),
                'v1Rows': {k: len(v) for k, v in v1.items()}, 'nativeRows': {k: len(v) for k, v in native.items()}}

    def publish(self, generation, editions, label):
        f = self.fixture
        old_conn = f.conn
        current, created, closures = {}, {}, {}
        f.conn = self.writer
        try:
            role = self.writer.execute('SELECT current_user, rolsuper FROM pg_roles WHERE rolname=current_user').fetchone()
            assert role == ('statarena_ingest', False), role
            snap = self.writer.execute('SELECT id FROM ingest.dataset_snapshots WHERE generation=%s AND status=\'sealed\'', (generation,)).fetchone()
            assert snap is not None
            for key in editions:
                ed = f.editions[key]
                closure = closures[key] = self.closures(key, generation, generation)
                existing = self.writer.execute('''SELECT b.id,b.dependencies_sha256,b.transform_version,b.metrics_contract_version
                    FROM analytics.publication_versions p JOIN analytics.aggregation_builds b ON b.id=p.build_id
                    WHERE p.competition_season_id=%s AND p.published_to_gen IS NULL''', (ed['id'],)).fetchone()
                if existing and existing[1:] == (closure['dependenciesSha256'], self.binding['transformVersion'], self.binding['metricsContractVersion']):
                    current[key] = existing[0]
                    continue
                with self.writer.transaction():
                    b = f._insert('analytics.aggregation_builds', competition_season_id=ed['id'],
                                  competition_season_revision_id=ed['revision_id'], dataset_snapshot_id=snap[0], catalog_snapshot_id=snap[0],
                                  representation_version=self.binding['buildRepresentation'], code_commit=CODE_SHA,
                                  code_content_sha256=CODE_SHA, dependencies_sha256=closure['dependenciesSha256'],
                                  environment_sha256=self.environment, metrics_contract_version=self.binding['metricsContractVersion'],
                                  transform_version=self.binding['transformVersion'], status='building')
                    # Only native observations change in this fixture. The typed
                    # V1 summary projection stays identical to its original build.
                    for table in ('analytics.match_summary', 'analytics.competition_summary'):
                        for row in self.rows(table, 'build_id=%s', (f.initial_builds[key],)):
                            f._insert(table, **{**row, 'build_id': b['id']})
                    self.writer.execute("UPDATE analytics.aggregation_builds SET status='ready',finished_at=CURRENT_TIMESTAMP WHERE id=%s", (b['id'],))
                current[key] = created[key] = b['id']
            if created:
                f.publish(created, label)
        finally:
            f.conn = old_conn
        tokens = {key: public_tokens(build_metadata(self.writer, b), self.binding) for key, b in current.items()}
        return {'kind': 'synthetic-ordinary-writer-ready-not-production-publisher',
                'role': role[0], 'created': created, 'builds': current, 'tokens': tokens,
                'componentProof': closures, 'codeContentSha256': CODE_SHA}
