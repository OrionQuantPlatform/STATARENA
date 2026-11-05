#!/usr/bin/env python3
"""Independent read-only readback of the committed real core in RDS017.

Separate RO/RR TLS ingest connection. Does not use the writer's inverse
projection: every business relation of the 94 model is hashed natively on RDS
(same framing as tests/orion_pro_bulk_local.native_rows) after mapping only the
generation/snapshot control components back to their source values (FK closure)
and casting the two widened coordinates back to float8. The result must equal
the frozen source native digests in the accepted source tables.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time

sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[3]
sys.path[:0] = [str(ROOT / 'dashboard/scripts'), str(ROOT / 'tests')]
import orion_pro_native_transport_real_v4 as writer  # noqa: E402
import orion_pro_target_overlay as overlay  # noqa: E402
from orion_pro_schema import active_tables, ident  # noqa: E402

old = writer.old
CONTROL = {'ingest.dataset_snapshots', 'ingest.schema_migrations', 'ingest.import_runs'}
OPTIONS = ('-c default_transaction_read_only=on -c statement_timeout=120000 -c lock_timeout=1000 '
           '-c timezone=UTC -c datestyle=ISO,YMD -c extra_float_digits=3 -c idle_in_transaction_session_timeout=60000')


def rel(name):
    return '.'.join('"' + part + '"' for part in name.split('.'))


def native_rows(conn, table, definitions, substitutions):
    columns = list(definitions[table]['columns'])
    projection = [substitutions.get(c, '"' + c + '"') for c in columns]
    order = ','.join('"' + c + '"' for c in definitions[table]['primary_key']['columns'])
    sql = f"SELECT ROW({','.join(projection)})::text FROM {rel(table)} ORDER BY {order}"
    h = hashlib.sha256()
    count = 0
    with conn.cursor(name='readback_' + str(time.monotonic_ns())) as cursor:
        cursor.itersize = 20000
        cursor.execute(sql)
        for (value,) in cursor:
            body = value.encode()
            h.update(str(len(body)).encode() + b':' + body + b'\n')
            count += 1
    return {'rows': count, 'sha256': h.hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    args = parser.parse_args()
    run = args.run.resolve()
    accepted = json.loads((run / 'acceptance.json').read_text())
    applied = json.loads((run / 'apply.result.json').read_text())
    out = run / 'independent-readback'
    out.mkdir(exist_ok=False)
    model = active_tables(json.loads(old.MODEL.read_text()))
    report = {'kind': 'real_rds017_core_independent_readback_v1', 'startedAt': datetime.now(timezone.utc).isoformat(),
              'writes': [], 'connections': 0, 'status': 'running'}
    started = time.monotonic()
    conn = None
    try:
        with writer.ingest_auth() as passfile:
            conn = writer.rds_connection(passfile, OPTIONS)
        report['connections'] = 1
        conn.execute('BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY')
        controls = conn.execute('SELECT generation,id,status,transform_version,snapshot_key,sealed_at IS NOT NULL '
                                'FROM ingest.dataset_snapshots ORDER BY generation').fetchall()
        runs = conn.execute("SELECT id,mode,status,transform_version,checkpoint->>'copied_rows' FROM ingest.import_runs ORDER BY id").fetchall()
        report['controls'] = [list(r) for r in controls]
        report['importRuns'] = [list(r) for r in runs]
        phase = accepted['sourcePhases'][0]
        g = int(applied['generationMap'][str(phase['generation'])])
        sid = int(applied['snapshotMap'][str(phase['snapshotId'])])
        assert [tuple(r[:4]) for r in controls] == [(1, 1, 'sealed', 'bootstrap_v1'), (g, sid, 'sealed', writer.VERSION)], \
            'Exactly B0 plus one sealed V4 snapshot required'
        assert len(runs) == 1 and runs[0][0] == phase['runId'] and runs[0][3] == writer.VERSION and int(runs[0][4]) == 553545
        # FK closure of the generation/snapshot control components (106 expected).
        components = {('ingest.dataset_snapshots', 'generation'): 0, ('ingest.dataset_snapshots', 'id'): 1}
        before = {}
        while before != components:
            before = components.copy()
            for name, table in model.items():
                for fk in table['foreign_keys']:
                    for child, parent in zip(fk['columns'], fk['references']['columns']):
                        marker = components.get((fk['references']['table'], parent))
                        if marker is not None:
                            components[name, child] = marker
        report['controlComponents'] = len(components)
        source_controls = [(1, 1), (phase['generation'], phase['snapshotId'])]
        target_controls = [(1, 1), (g, sid)]
        substitutions = {}
        for (name, column), i in components.items():
            col = ident(column)
            clauses = ' '.join(f'WHEN {t[i]} THEN {s[i]}' for s, t in zip(source_controls, target_controls))
            substitutions.setdefault(name, {})[column] = f'CASE {col} {clauses} ELSE {col} END'
        substitutions.setdefault('football.match_players', {}).update(
            raw_pitch_x='raw_pitch_x::float8', raw_pitch_y='raw_pitch_y::float8')
        business = sorted(k for k in model if k not in CONTROL)
        got, mismatches = {}, []
        for name in business:
            got[name] = native_rows(conn, name, model, substitutions.get(name, {}))
            if got[name] != accepted['sourceTables'][name]:
                mismatches.append({'table': name, 'target': got[name], 'source': accepted['sourceTables'][name]})
        report['businessRelations'] = len(business)
        report['businessRows'] = sum(v['rows'] for v in got.values())
        report['businessNativeSha256'] = old.hashed(got)
        report['mismatches'] = mismatches
        report['targetDefaults'] = overlay.verify_core_defaults(conn)
        conn.rollback()
        report['status'] = 'verified_exact_source_native91' if not mismatches else 'mismatch'
        (out / 'business-native.json').write_text(json.dumps(got, indent=1, sort_keys=True) + '\n')
    except BaseException as error:
        report.update(status='fail', errorType=type(error).__name__, error=str(error)[:4000],
                      sqlstate=getattr(error, 'sqlstate', None))
    finally:
        if conn is not None:
            conn.close()
        report['connectionClosed'] = conn is None or conn.closed
        report['elapsedSeconds'] = round(time.monotonic() - started, 3)
        (out / 'result.json').write_text(json.dumps(report, indent=2, default=str) + '\n')
        print(json.dumps({k: report.get(k) for k in ('status', 'businessRelations', 'businessRows', 'controlComponents',
                                                       'mismatches', 'error', 'elapsedSeconds')}, default=str)[:3000])
    return 0 if report['status'] == 'verified_exact_source_native91' else 1


if __name__ == '__main__':
    raise SystemExit(main())
