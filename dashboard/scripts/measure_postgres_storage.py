#!/usr/bin/env python3
"""Import every tracked data file into disposable PostgreSQL and measure it.

Scalars become SQL columns; nested/mixed values remain JSONB. This measures an
explicit, reproducible hybrid schema, not a hypothetical optimal schema.
"""
import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import time
import traceback
import zipfile

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb

ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = {'raw': 'canonical', 'sources': 'originals', 'computed': 'derived'}
SQL_TYPES = {'bool': 'boolean', 'int': 'bigint', 'float': 'double precision',
             'text': 'text', 'json': 'jsonb'}


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode()


def named(value):
    stem = re.sub(r'[^a-z0-9_]', '_', value.lower()).strip('_') or 'value'
    return stem[:42] + '_' + hashlib.sha256(value.encode()).hexdigest()[:12]


def kind(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return 'bool'
    if isinstance(value, int) and -(2**63) <= value < 2**63:
        return 'int'
    if isinstance(value, float):
        return 'float'
    if isinstance(value, str):
        return 'text'
    return 'json'


def merged(left, right):
    if left is None:
        return right
    if right is None or left == right:
        return left
    # Mixed numeric types remain JSONB: no silent precision/type conversion.
    return 'json'


def family(path, member=''):
    parts = Path(path).parts
    if len(parts) == 2:
        return 'other_data', Path(parts[1]).name.split('.')[0]
    schema = SCHEMAS.get(parts[1], 'other_data')
    rest = list(parts[2:])
    if parts[1] == 'raw' and rest[:1] == ['seasons']:
        label = 'observations_' + rest[3] if len(rest) > 4 and rest[2] == 'observations' else 'seasons_' + rest[2]
    elif parts[1] == 'raw' and rest[:1] == ['profiles']:
        label = 'profiles_' + rest[1]
    elif parts[1] == 'raw' and rest[:1] == ['pitchapi-world']:
        label = 'world_' + (rest[1] if len(rest) > 2 else Path(rest[-1]).name.split('.')[0])
    elif parts[1] == 'sources' and rest[:1] == ['pitchapi'] and member:
        member_parts = Path(member).parts
        label = 'pitchapi_' + '_'.join(member_parts[:2] if member_parts[0] == 'profiles' else member_parts[:1])
    elif parts[1] == 'sources':
        label = rest[0] + ('_csv' if member.lower().endswith('.csv') or path.lower().endswith(('.csv', '.csv.gz')) else '_documents')
    elif len(rest) > 1:
        label = rest[0]
    else:
        label = Path(rest[0]).name.split('.')[0]
    return schema, label


def load_json(body):
    def invalid_constant(value):
        raise ValueError('Non-standard JSON number: ' + value)
    return json.loads(body, parse_constant=invalid_constant)


def objects(value):
    if isinstance(value, list):
        for row in value:
            if isinstance(row, dict):
                yield row
            elif isinstance(row, list):
                yield {'column_' + str(i): v for i, v in enumerate(row)}
            else:
                yield {'value': row}
    elif isinstance(value, dict):
        # Index maps use entity IDs as keys. Avoid thousands of SQL columns.
        dynamic = len(value) > 128 or (value and all(
            re.match(r'^(?:[0-9a-f]{20,}|[lmtps]_[A-Za-z0-9]+|(?:players|teams|leagues):)', k)
            for k in value))
        if dynamic:
            for key, row in value.items():
                yield {'map_key': key, 'value': row}
        else:
            yield value
    else:
        yield {'value': value}


def decoded_records(path, member, body):
    name = (member or path).lower()
    group = family(path, member)
    if name.endswith('.gz'):
        body = gzip.decompress(body)
        name = name[:-3]
    if name.endswith('.json'):
        obj = load_json(body)
        if isinstance(obj, dict) and obj.get('format') == 'orion-packed-tables-v1':
            # Restore packed views to typed record rows, not one file-sized row.
            yield (group[0], 'dashboard_metadata'), member, {k: v for k, v in obj.items() if k != 'tables'}
            for table, packed in obj['tables'].items():
                keys, dictionaries = packed['keys'], packed.get('dictionaries', {})
                missing = packed.get('missing', {})
                for i, row in enumerate(packed['rows']):
                    if len(row) != len(keys):
                        raise ValueError('Packed row width mismatch: ' + path)
                    absent = set(missing.get(str(i), []))
                    restored = {key: (dictionaries[str(j)][row[j]]
                                if str(j) in dictionaries and row[j] is not None else row[j])
                                for j, key in enumerate(keys) if j not in absent}
                    yield (group[0], 'dashboard_' + table), member, restored
        else:
            for row in objects(obj):
                yield group, member, row
    elif name.endswith('.csv'):
        text = body.decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(text, newline=''))
        if reader.fieldnames is None:
            return
        if len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError('Duplicate CSV column: ' + path + '!' + member)
        for row in reader:
            if None in row:
                raise ValueError('CSV row wider than header: ' + path + '!' + member)
            yield group, member, row
    elif name.endswith(('.md', '.txt', '.html', '.yml', '.yaml', '.gitignore', '.license')) or Path(name).name in {'license', 'copying', 'readme'}:
        yield group, member, {'content': body.decode('utf-8-sig')}
    else:
        # Extensionless metadata is accepted only if valid JSON or UTF-8 text.
        if '.' not in Path(name).name:
            try:
                obj = load_json(body)
            except (ValueError, UnicodeError):
                yield group, member, {'content': body.decode('utf-8-sig')}
            else:
                for row in objects(obj):
                    yield group, member, row
        else:
            raise ValueError('Unsupported tracked data format: ' + path + '!' + member)


def records(path):
    file = ROOT / path
    if path.endswith(('.tar.gz', '.tgz', '.tar')):
        with tarfile.open(file, 'r:*') as archive:
            for member in archive:
                if member.isdir():
                    continue
                if not member.isfile():
                    raise ValueError('Non-regular archive member: ' + path + '!' + member.name)
                with archive.extractfile(member) as stream:
                    yield from decoded_records(path, member.name, stream.read())
    elif path.endswith('.zip'):
        with zipfile.ZipFile(file) as archive:
            for member in archive.infolist():
                if not member.is_dir():
                    yield from decoded_records(path, member.filename, archive.read(member))
    else:
        yield from decoded_records(path, '', file.read_bytes())


def check_disk():
    if shutil.disk_usage(ROOT).free < 2 * 1024**3:
        raise RuntimeError('Less than 2 GiB free: refusing an incomplete measurement')


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def inventory(out):
    paths = subprocess.check_output(['git', 'ls-files', '-z', '--', 'data'], cwd=ROOT).decode().split('\0')
    paths = sorted(p for p in paths if p)
    if not paths:
        raise ValueError('No tracked data files')
    tables = {}
    files = []
    for file_id, path in enumerate(paths, 1):
        file = ROOT / path
        with file.open('rb') as stream:
            source_sha = hashlib.file_digest(stream, 'sha256').hexdigest()
        entry = {'id': file_id, 'path': path, 'bytes': file.stat().st_size,
                 'sha256': source_sha,
                 'rows': 0, 'tables': {}}
        for group, member, row in records(path):
            if any(not isinstance(key, str) for key in row):
                raise ValueError('Non-string column key: ' + path)
            table = tables.setdefault(group, {'columns': {}, 'rows': 0, 'files': set()})
            table['rows'] += 1
            table['files'].add(file_id)
            entry['rows'] += 1
            label = '.'.join(group)
            entry['tables'][label] = entry['tables'].get(label, 0) + 1
            for key, value in row.items():
                table['columns'][key] = merged(table['columns'].get(key), kind(value))
            if len(table['columns']) > 1500:
                raise ValueError('More than 1500 columns: ' + label)
        files.append(entry)
        if file_id % 1000 == 0:
            print('Inventoried', file_id, '/', len(paths), path, flush=True)
            check_disk()
    for group, table in tables.items():
        table['columns'] = {k: (v or 'json') for k, v in sorted(table['columns'].items())}
        table['name'] = named(group[1])
        table['sql_columns'] = {key: named('field_' + key) for key in table['columns']}
        if len(set(table['sql_columns'].values())) != len(table['columns']):
            raise ValueError('SQL column collision: ' + str(group))
    if len({(g[0], t['name']) for g, t in tables.items()}) != len(tables):
        raise ValueError('SQL table collision')
    write_json(out / 'input-manifest.json', files)
    write_json(out / 'schema-map.json', {'.'.join(g): dict(t, files=sorted(t['files'])) for g, t in tables.items()})
    print('Inventory complete:', len(files), 'files;', len(tables), 'tables;', sum(t['rows'] for t in tables.values()), 'rows', flush=True)
    return files, tables


def sql_row(file_id, ordinal, member, row, table):
    missing = [key for key in table['columns'] if key not in row]
    plain = [file_id, ordinal, member, missing]
    adapted = plain.copy()
    for key, typ in table['columns'].items():
        value = row.get(key)
        plain.append(value)
        adapted.append(Jsonb(value) if typ == 'json' and value is not None else value)
    return plain, adapted


def import_table(conn, out, group, table, files):
    schema, _ = group
    target = sql.Identifier(schema, table['name'])
    columns = ['_file_id', '_ordinal', '_member', '_missing'] + list(table['sql_columns'].values())
    definitions = [sql.SQL('_file_id bigint NOT NULL'), sql.SQL('_ordinal bigint NOT NULL'),
                   sql.SQL('_member text NOT NULL'), sql.SQL('_missing text[] NOT NULL')]
    definitions += [sql.SQL('{} {}').format(sql.Identifier(table['sql_columns'][key]), sql.SQL(SQL_TYPES[typ]))
                    for key, typ in table['columns'].items()]
    create = sql.SQL('CREATE TABLE {} ({})').format(target, sql.SQL(', ').join(definitions))
    conn.execute(create)
    with (out / 'schema.sql').open('a') as ddl:
        ddl.write(create.as_string(conn) + ';\n')
    expected = hashlib.sha256()
    count = 0
    copy = sql.SQL('COPY {} ({}) FROM STDIN').format(target, sql.SQL(', ').join(map(sql.Identifier, columns)))
    with conn.cursor().copy(copy) as writer:
        for file_id in sorted(table['files']):
            path = files[file_id - 1]['path']
            for ordinal, (row_group, member, row) in enumerate(records(path)):
                if row_group != group:
                    continue
                plain, adapted = sql_row(file_id, ordinal, member, row, table)
                expected.update(encoded(plain) + b'\n')
                writer.write_row(adapted)
                count += 1
                if count % 100000 == 0:
                    print('COPY', '.'.join(group), count, '/', table['rows'], flush=True)
                    check_disk()
    if count != table['rows']:
        raise AssertionError(('COPY count mismatch', group, count, table['rows']))
    indexes = [sql.SQL('ALTER TABLE {} ADD PRIMARY KEY (_file_id, _ordinal)').format(target)]
    # Foreign keys cannot be asserted across versioned/duplicated snapshots.
    # These B-tree indexes give practical joins without inventing uniqueness.
    for key, typ in table['columns'].items():
        if key in {'id', 'matchId', 'playerId', 'playerRef', 'teamId', 'leagueId', 'documentId', 'match_id', 'player_id', 'team_id'} and typ in {'text', 'int'}:
            indexes.append(sql.SQL('CREATE INDEX ON {} ({})').format(target, sql.Identifier(table['sql_columns'][key])))
    for statement in indexes:
        conn.execute(statement)
        with (out / 'schema.sql').open('a') as ddl:
            ddl.write(statement.as_string(conn) + ';\n')
    conn.execute(sql.SQL('ANALYZE {}').format(target))
    actual = hashlib.sha256()
    actual_count = 0
    with conn.cursor(name='verify', withhold=True) as cursor:
        cursor.itersize = 2000
        cursor.execute(sql.SQL('SELECT {} FROM {} ORDER BY _file_id, _ordinal').format(
            sql.SQL(', ').join(map(sql.Identifier, columns)), target))
        for row in cursor:
            actual.update(encoded(row) + b'\n')
            actual_count += 1
    if actual_count != count or actual.hexdigest() != expected.hexdigest():
        raise AssertionError(('Full readback mismatch', group, count, actual_count, expected.hexdigest(), actual.hexdigest()))
    print('Verified', '.'.join(group), count, 'rows', flush=True)
    return {'schema': schema, 'family': group[1], 'table': table['name'], 'rows': count,
            'expected_sha256': expected.hexdigest(), 'actual_sha256': actual.hexdigest(), 'verified': True}


def measure(conn):
    return [dict(zip(['schema', 'table', 'heap_bytes', 'table_toast_bytes', 'index_bytes', 'total_bytes'], row))
            for row in conn.execute('''
              SELECT n.nspname, c.relname,
                     pg_relation_size(c.oid), pg_table_size(c.oid),
                     pg_indexes_size(c.oid), pg_total_relation_size(c.oid)
              FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
              WHERE c.relkind = 'r' AND n.nspname = ANY(%s)
              ORDER BY n.nspname, c.relname
            ''', (list(SCHEMAS.values()) + ['other_data', 'measurement'],))]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--dsn', default=os.environ.get('DATABASE_URL'))
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    started = time.time()
    report = {'status': 'running', 'started_at': datetime.now(timezone.utc).isoformat(),
              'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip(),
              'workflow_run': os.environ.get('GITHUB_SERVER_URL', 'https://github.com') + '/' + os.environ.get('GITHUB_REPOSITORY', 'OrionQuantPlatform/STATARENA') + '/actions/runs/' + os.environ.get('GITHUB_RUN_ID', 'local'),
              'python_version': sys.version, 'psycopg_version': psycopg.__version__,
              'layout': 'Typed scalar columns, nested/mixed JSONB, logged tables, source-row primary keys, entity B-tree indexes; all duplicate source/derived records retained.',
              'excluded_from_database_bytes': ['WAL', 'backups', 'replicas', 'Git history', 'PostgreSQL cluster files outside this database'],
              'rerun_command': 'DATABASE_URL=postgresql://postgres:postgres@localhost:5432/statarena_measure python3 -u dashboard/scripts/measure_postgres_storage.py --output /tmp/statarena-storage-evidence',
              'verification': []}
    write_json(out / 'measurement.json', report)
    try:
        if not args.dsn:
            raise ValueError('DATABASE_URL or --dsn required')
        files, tables = inventory(out)
        report.update(input_files=len(files), input_bytes=sum(f['bytes'] for f in files),
                      expected_rows=sum(t['rows'] for t in tables.values()))
        with psycopg.connect(args.dsn, autocommit=True) as conn:
            report['postgres_version'] = conn.execute('SELECT version()').fetchone()[0]
            # Refuse reuse; only a fresh, disposable database is supported.
            if conn.execute("SELECT count(*) FROM pg_tables WHERE schemaname NOT IN ('pg_catalog', 'information_schema')").fetchone()[0]:
                raise ValueError('Database is not empty; use a fresh disposable database')
            report['empty_database_bytes'] = conn.execute('SELECT pg_database_size(current_database())').fetchone()[0]
            schemas = sorted(set(g[0] for g in tables) | {'measurement'})
            (out / 'schema.sql').write_text('')
            for schema in schemas:
                statement = sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema))
                conn.execute(statement)
                with (out / 'schema.sql').open('a') as ddl:
                    ddl.write(statement.as_string(conn) + ';\n')
            metadata_ddl = 'CREATE TABLE measurement.files (id bigint PRIMARY KEY, path text NOT NULL UNIQUE, source_bytes bigint NOT NULL, sha256 text NOT NULL, expected_rows bigint NOT NULL)'
            conn.execute(metadata_ddl)
            with (out / 'schema.sql').open('a') as ddl:
                ddl.write(metadata_ddl + ';\n')
            with conn.cursor().copy('COPY measurement.files FROM STDIN') as writer:
                for f in files:
                    writer.write_row((f['id'], f['path'], f['bytes'], f['sha256'], f['rows']))
            # Lower temporary sort memory makes behavior predictable on hosted runners.
            conn.execute("SET maintenance_work_mem = '128MB'")
            for group, table in sorted(tables.items()):
                report['verification'].append(import_table(conn, out, group, table, files))
                write_json(out / 'measurement.json', report)
                check_disk()
            conn.execute('ANALYZE measurement.files')
            conn.execute('CHECKPOINT')
            sizes = measure(conn)
            grouped = defaultdict(lambda: Counter())
            for size in sizes:
                for key in ['heap_bytes', 'table_toast_bytes', 'index_bytes', 'total_bytes']:
                    grouped[size['schema']][key] += size[key]
            report.update(tables=sizes, schemas=dict(grouped),
                          application_relation_bytes=sum(s['total_bytes'] for s in sizes),
                          database_bytes=conn.execute('SELECT pg_database_size(current_database())').fetchone()[0],
                          actual_rows=sum(v['rows'] for v in report['verification']),
                          database_settings=dict(conn.execute("SELECT name, setting FROM pg_settings WHERE name = ANY(%s)",
                              (['block_size', 'default_toast_compression', 'server_version', 'wal_level', 'full_page_writes', 'data_checksums'],)).fetchall()))
            if report['actual_rows'] != report['expected_rows']:
                raise AssertionError('Whole import row count mismatch')
            report['status'] = 'complete'
            report['database_gb'] = report['database_bytes'] / 10**9
            report['database_gib'] = report['database_bytes'] / 2**30
    except Exception:
        report['status'] = 'failed'
        report['error'] = traceback.format_exc()
        raise
    finally:
        report['elapsed_seconds'] = round(time.time() - started, 2)
        write_json(out / 'measurement.json', report)
        lines = ['# Actual PostgreSQL storage measurement', '',
                 '- Status: **' + report['status'] + '**',
                 '- Source commit: `' + report['source_commit'] + '`',
                 '- Layout: ' + report['layout'], '']
        if report['status'] == 'complete':
            lines += [f"**Whole database: {report['database_bytes']:,} bytes = {report['database_gb']:.6f} GB = {report['database_gib']:.6f} GiB.**", '',
                      '| Schema | Tables + TOAST | Indexes | Total bytes | GB |',
                      '|---|---:|---:|---:|---:|']
            for schema, values in sorted(report['schemas'].items()):
                lines.append(f"| {schema} | {values['table_toast_bytes']:,} | {values['index_bytes']:,} | {values['total_bytes']:,} | {values['total_bytes'] / 1e9:.6f} |")
            lines += ['', f"Imported and fully readback-verified {report['actual_rows']:,} rows from {report['input_files']:,} tracked files ({report['input_bytes']:,} source bytes).",
                      'Canonical = raw; originals = duplicate source archive records; derived = generated views.',
                      'Database bytes include database catalog overhead. WAL, backups, replicas and Git history are excluded.']
        else:
            lines += ['No complete storage figure is available. See measurement.json and import.log for the failure.']
        lines += ['', '## Reproduce', '', 'Use PostgreSQL 17 and psycopg[binary]==3.2.3; start with a fresh database.',
                  'Check out source commit `' + report['source_commit'] + '`.', '',
                  '```sh', report['rerun_command'], '```', '',
                  'Evidence: input-manifest.json, schema-map.json, schema.sql, measurement.json and import.log.']
        summary = '\n'.join(lines) + '\n'
        (out / 'SUMMARY.md').write_text(summary)
        if os.environ.get('GITHUB_STEP_SUMMARY'):
            with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as stream:
                stream.write(summary)
        print(summary, flush=True)


if __name__ == '__main__':
    main()
