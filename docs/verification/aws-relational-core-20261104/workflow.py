"""Actual SQL publication workflows; fixtures never leave a temporary database."""
import argparse, copy, hashlib, json, os, sys
from pathlib import Path
from urllib.parse import urlparse
import psycopg

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT/'dashboard/scripts'), str(ROOT/'tests')]
from test_dashboard_data import synthetic, metric
from build_dashboard_data import build_snapshot

parser = argparse.ArgumentParser(); parser.add_argument('--report', required=True); args = parser.parse_args()
target = urlparse(os.environ['TEST_DATABASE_URL'])
assert target.hostname == '127.0.0.1' and target.path == '/relational_core_e2e'
report = {'setup': 'Real isolated PostgreSQL18, existing provider normalizer and backend-owned typed application schema. No production writes.', 'command': os.environ['STATARENA_E2E_COMMAND'], 'expected': 'All five publication workflows preserve the stated relational invariants.', 'cases': [], 'status': 'failed'}

def run(name, fn):
    case = {'name': name, 'checks': [], 'status': 'failed'}; report['cases'].append(case)
    def check(label, passed, actual):
        case['checks'].append({'name': label, 'passed': bool(passed), 'actual': actual})
        if not passed: raise AssertionError(label)
    try: fn(check); case['status'] = 'passed'
    except Exception as e: case['error'] = type(e).__name__ + ': ' + str(e)

with psycopg.connect(os.environ['TEST_DATABASE_URL'], autocommit=True) as db:
    raw, catalog = synthetic()
    # Identical printed IDs with different source types must survive SQL and HTTP.
    raw['samples'][1]['lineups']['data']['home']['starters'][0]['position_id'] = '11'
    raw['samples'][0]['players']['data'][0]['stats'][0]['stats']['Future'] = metric('new_observed_metric', 0)
    raw['samples'][0]['shots']['data']['periods'][0]['shots'][0].update({'goal_crossed_y': 32.2, 'goal_crossed_z': 1.4, 'blocked_x': 91.2, 'blocked_y': 33.1})
    snapshot = build_snapshot(raw, catalog)
    def setup(check):
        from relational_core import install_schema, publish_snapshot
        install_schema(db)
        with db.transaction(): publish_snapshot(db, '2026/2027', 'l_000001', snapshot)
        check('detail completeness persisted', db.execute("select count(*) from information_schema.columns where table_schema='statarena_app' and table_name='matches' and column_name='detail_collected'").fetchone()[0] == 1, 'nullable detail_collected')
        check('numeric position identifiers retain native type', db.execute("select count(*) from information_schema.columns where table_schema='statarena_app' and table_name='appearances' and column_name='position_id_type'").fetchone()[0] == 1, 'native identifier type metadata')
        check('source shot ordinals persisted', db.execute("select count(*) from information_schema.columns where table_schema='statarena_app' and table_name='shots' and column_name='ordinal'").fetchone()[0] == 1, 'typed shot ordinal')
        document_columns = set(db.execute("select table_name,column_name from information_schema.columns where table_schema='statarena_app' and (data_type in ('json','jsonb') or column_name in ('body','payload','document'))").fetchall())
        derived_columns = {('player_season_rollups', column) for column in ('identity','latest','teams','leagues','roles','metrics')}
        check('canonical facts contain no JSON or document columns', not document_columns-derived_columns, sorted(document_columns-derived_columns))
        check('derived player projection has only declared document fields', document_columns == derived_columns, sorted(document_columns))
        rollup = db.execute("select p.player_rollup_digest=p.source_digest, count(r.player_id) from statarena_app.partitions p join statarena_app.player_season_rollups r using(season,league_id) where p.season=%s and p.league_id=%s group by p.source_digest,p.player_rollup_digest", ('2026/2027','l_000001')).fetchone()
        check('derived projection shares the canonical publication digest', rollup is not None and rollup[0] and rollup[1]>0, list(rollup) if rollup else None)
        counts = db.execute("select (select count(*) from statarena_app.matches),(select count(*) from statarena_app.appearances),(select count(*) from statarena_app.shots)").fetchone()
        check('match, appearance and shot counts', counts == (2,2,1), list(counts))
        row = db.execute("select goals,minutes,passes_accurate,passes_attempted from statarena_app.appearances where match_id='m_000001'").fetchone()
        check('exact reliable statistics and attempts', row == (1,90,4,5), list(row))
        row = db.execute("select goals,passes_accurate from statarena_app.appearances where match_id='m_000002'").fetchone()
        check('suspicious null remains distinct from zero', row == (1,None), list(row))
        row = db.execute("select goal_crossed_y,goal_crossed_z,blocked_x,blocked_y,is_own_goal,is_goal from statarena_app.shots").fetchone()
        check('shot geometry and own-goal semantics', row == (32.2,1.4,91.2,33.1,True,False), list(row))
        row = db.execute("select value from statarena_app.appearance_metrics where metric_key='newObservedMetric' and appearance_id='m_000001:p_000001'").fetchone()
        check('unmapped observed metric retained including zero', row == (0,), row[0] if row else None)
    run('typed publication', setup)
    def repeat(check):
        from relational_core import publish_snapshot
        before = db.execute('select generation from statarena_app.publications').fetchone()[0]
        with db.transaction(): changed = publish_snapshot(db,'2026/2027','l_000001',snapshot)
        after = db.execute('select generation from statarena_app.publications').fetchone()[0]
        check('identical publication is a no-write', changed == 0 and before == after, {'changed':changed,'before':before,'after':after})
    run('idempotent rerun',repeat)
    def rollback(check):
        from relational_core import publish_snapshot
        prior = db.execute('select generation from statarena_app.publications').fetchone()[0]
        updated = copy.deepcopy(snapshot); updated['appearances'][0]['goals'] = 2
        class Abort(Exception): pass
        try:
            with db.transaction(): publish_snapshot(db,'2026/2027','l_000001',updated); raise Abort()
        except Abort: pass
        actual = db.execute("select goals from statarena_app.appearances where match_id='m_000001'").fetchone()[0]
        check('failed transaction leaves prior value', actual == 1, actual)
        after = db.execute('select generation from statarena_app.publications').fetchone()[0]
        check('failed transaction leaves generation', prior == after, {'before':prior,'after':after})
    run('atomic rollback',rollback)
    def change(check):
        from relational_core import publish_snapshot
        updated = copy.deepcopy(snapshot); updated['appearances'][0]['goals'] = 2
        with db.transaction(): changed = publish_snapshot(db,'2026/2027','l_000001',updated)
        actual = db.execute("select goals from statarena_app.appearances where match_id='m_000001'").fetchone()[0]
        check('changed publication updates value exactly once', changed == 1 and actual == 2, {'changed':changed,'goals':actual})
        duplicates = db.execute('select count(*)-count(distinct id) from statarena_app.appearances').fetchone()[0]
        check('no duplicate identities', duplicates == 0, duplicates)
    run('changed source',change)
    def isolation(check):
        from relational_core import publish_snapshot
        other = copy.deepcopy(snapshot)
        for row in other['matches']: row['id'] = row['id'].replace('m_00000','m_10000'); row['leagueId']='l_100001'
        for row in other['appearances']: row['matchId'] = row['matchId'].replace('m_00000','m_10000'); row['id']=row['id'].replace('m_00000','m_10000'); row['leagueId']='l_100001'
        with db.transaction(): publish_snapshot(db,'2026/2027','l_100001',other)
        with db.transaction(): publish_snapshot(db,'2026/2027','l_000001',snapshot)
        total = db.execute('select count(*) from statarena_app.matches').fetchone()[0]
        check('publishing one partition retains another', total == 4, total)
        missing = db.execute('select count(*) from statarena_app.appearances p left join statarena_app.matches m on m.id=p.match_id where m.id is null').fetchone()[0]
        check('appearance references remain intact', missing == 0, missing)
    run('partition isolation',isolation)

    def old_publication_upgrade(check):
        from relational_core import publish_snapshot
        from relational_snapshot import read_partition
        legacy = copy.deepcopy(snapshot)
        legacy['appearances'][0]['shirtNumber'] = '07'
        encoded = json.dumps(legacy,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
        old_digest = hashlib.sha256(encoded.encode()).hexdigest()
        db.execute('drop table statarena_app.appearance_shirt_numbers')
        db.execute('update statarena_app.partitions set source_digest=%s where season=%s and league_id=%s', (old_digest,'2026/2027','l_000001'))
        db.execute('update statarena_app.appearances set shirt_number=7 where id=%s', (legacy['appearances'][0]['id'],))
        db.execute((ROOT/'dashboard/backend/migrations/011_appearance_shirt_numbers.sql').read_text())
        queued = db.execute('select count(*) from statarena_app.publication_jobs where season=%s and league_id=%s', ('2026/2027','l_000001')).fetchone()[0]
        try:
            check('existing publication is queued for lossless upgrade', queued == 1, queued)
            with db.transaction(): changed = publish_snapshot(db,'2026/2027','l_000001',legacy)
            new_digest = db.execute('select source_digest from statarena_app.partitions where season=%s and league_id=%s', ('2026/2027','l_000001')).fetchone()[0]
            value = read_partition(db,'2026/2027','l_000001')['tables']['performances'][0]['shirtNumber']
            check('legacy digest cannot suppress scalar upgrade', changed == 1 and value == '07' and isinstance(value,str), {'changed':changed,'value':value})
            check('changed public representation has a new validator', old_digest != new_digest, {'old':old_digest,'new':new_digest})
        finally:
            with db.transaction(): publish_snapshot(db,'2026/2027','l_000001',snapshot)
    run('upgrade already published numeric coercions', old_publication_upgrade)

    def legacy_shirts(check):
        from relational_snapshot import read_partition
        key = snapshot['appearances'][0]['id']
        db.execute('delete from statarena_app.appearance_shirt_numbers where appearance_id=%s', (key,))
        rows = read_partition(db, '2026/2027', 'l_000001')['tables']['performances']
        actual = next(p['shirtNumber'] for p in rows if p['id'] == key)
        check('legacy numeric shirt fallback', actual == snapshot['appearances'][0]['shirtNumber'], actual)
    run('existing numeric appearance without scalar receipt', legacy_shirts)

    def native_shirts(check):
        from relational_core import publish_snapshot
        from relational_snapshot import read_partition
        observed = []
        for values in [('', '07'), (0, 12), (None, False), (True, 1.5)]:
            updated = copy.deepcopy(snapshot)
            for row, value in zip(updated['appearances'], values, strict=True): row['shirtNumber'] = value
            with db.transaction(): publish_snapshot(db, '2026/2027', 'l_000001', updated)
            actual = [p['shirtNumber'] for p in read_partition(db, '2026/2027', 'l_000001')['tables']['performances']]
            check('native shirt values and types '+repr(values), actual == list(values) and [type(x) for x in actual] == [type(x) for x in values], actual)
            before = db.execute('select generation from statarena_app.publications').fetchone()[0]
            with db.transaction(): changed = publish_snapshot(db, '2026/2027', 'l_000001', updated)
            check('unchanged scalar publication '+repr(values), changed == 0 and before == db.execute('select generation from statarena_app.publications').fetchone()[0], changed)
            observed.extend(actual)
        # The HTTP phase inspects both an empty and a leading-zero number.
        for row, value in zip(updated['appearances'], ('', '07'), strict=True): row['shirtNumber'] = value
        with db.transaction(): publish_snapshot(db, '2026/2027', 'l_000001', updated)
        check('all scalar forms covered', len(observed) == 8, observed)
    run('native shirt numbers survive SQL and repeat publication', native_shirts)

    def invalid_shirt(check):
        from relational_core import publish_snapshot
        before = db.execute('select generation from statarena_app.publications').fetchone()[0]
        bad = copy.deepcopy(snapshot);bad['appearances'][0]['shirtNumber'] = {'unexpected': 'structure'}
        try:
            with db.transaction(): publish_snapshot(db, '2026/2027', 'l_000001', bad)
        except (ValueError, TypeError): pass
        else: raise AssertionError('structural shirt number was accepted')
        check('bad scalar transaction preserves generation', before == db.execute('select generation from statarena_app.publications').fetchone()[0], before)
    run('structural shirt number fails atomically', invalid_shirt)

report['status'] = 'passed' if all(c['status']=='passed' for c in report['cases']) else 'failed'
Path(args.report).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'status':report['status'],'cases':len(report['cases']),'failed':[c['name'] for c in report['cases'] if c['status']!='passed']}))
raise SystemExit(report['status']!='passed')
