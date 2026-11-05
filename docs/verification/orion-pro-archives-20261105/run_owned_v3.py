#!/usr/bin/env python3
"""Tighten the V3 campaign within ROOT's cumulative 90s local allocation."""
from pathlib import Path
import runpy
import signal
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
if len(sys.argv)!=2:
    raise SystemExit('Pass the exact ROOT_OWNED_ARCHIVES_V3.json SHA256')
digest=sys.argv[1]
test=ROOT/'tests/orion_pro_archives_local.py'
sys.argv=[str(test),'--run-owned','--release',str(HERE/'ROOT_OWNED_ARCHIVES_V3.json'),
          '--release-sha256',digest,'--label','archives-product-v3']
def expired(signum,frame):
    raise TimeoutError('Owned archive V3 work deadline; preserve receipt and clean resources')
signal.signal(signal.SIGALRM,expired)
# V2 used 4.365s; reserve the remaining time for bounded API/PG cleanup.
signal.setitimer(signal.ITIMER_REAL,55)
try:
    runpy.run_path(str(test),run_name='__main__')
finally:
    signal.setitimer(signal.ITIMER_REAL,0)
