"""Run the prewritten catalogue E2E against migration012 on an owned real PG18."""
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import sys
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = ['/tmp/statarena-publication-test-python', str(HERE)]
import psycopg
from harness import LocalPostgres
spec = importlib.util.spec_from_file_location('prewritten_pilot_e2e', ROOT / 'tests/orion_pro_pilot_postgres.py')
test = importlib.util.module_from_spec(spec)
spec.loader.exec_module(test)
evidence = HERE / 'runs' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-schema012')
evidence.mkdir(parents=True)
r = {'command': 'python3 docs/verification/orion-pro-pilot-20261104/schema_phase.py',
     'setup': 'Owned disposable PostgreSQL18.6; existing preimplementation active_catalogue E2E; migration012 only, no remote actions.',
     'expected': 'Actual94tables/1709columns/431FK and exact PK/types/nullability match the approved active model; no deferred models/history/registries.',
     'passed': False, 'limits': 'Only the prewritten schema catalogue phase is executed; bootstrap/semantic/fullpilot remain unverified.'}
pg = LocalPostgres(Path('/tmp/statarena-cache-test-tools/node_modules/@embedded-postgres/darwin-arm64/native/bin'), evidence)
conn = None
try:
    pg.start()
    pg.migration(ROOT, target='012')
    conn = psycopg.connect(pg.dsn, autocommit=True)
    r['actual'] = test.active_catalogue(conn, json.loads(test.MODEL.read_text()), evidence)
    r['passed'] = True
except Exception:
    r['error'] = traceback.format_exc()
finally:
    if conn is not None: conn.close()
    r['cleanup'] = pg.cleanup()
    r['passed'] = r['passed'] and r['cleanup']['server_stopped']
    (evidence / 'result.json').write_text(json.dumps(r, indent=2) + '\n')
    print(json.dumps({'evidence': str(evidence), **r}))
raise SystemExit(not r['passed'])
