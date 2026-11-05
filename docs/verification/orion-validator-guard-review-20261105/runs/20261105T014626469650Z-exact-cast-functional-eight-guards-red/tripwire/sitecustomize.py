"""E2E-only sitecustomize body: never permits a nonlocal libpq route."""
import json
import os
from pathlib import Path
import psycopg

_original_connect = psycopg.connect

def _guarded_connect(*args, **kwargs):
    explicit = kwargs.get('hostaddr')
    effective = explicit if explicit is not None else os.environ.get('PGHOSTADDR')
    result = {'kind': 'e2e_libpq_route_tripwire', 'host': kwargs.get('host'),
              'explicitHostaddr': explicit, 'effectiveHostaddr': effective,
              'port': kwargs.get('port'), 'nonlocalPrevented': effective != '127.0.0.1',
              'actualNonlocalConnections': 0}
    Path(os.environ['ORION_ROUTE_TRIPWIRE_RESULT']).write_text(json.dumps(result) + '\n')
    if effective != '127.0.0.1':
        raise RuntimeError('E2E_NONLOCAL_ROUTE_PREVENTED_BEFORE_LIBPQ')
    return _original_connect(*args, **kwargs)

psycopg.connect = _guarded_connect
