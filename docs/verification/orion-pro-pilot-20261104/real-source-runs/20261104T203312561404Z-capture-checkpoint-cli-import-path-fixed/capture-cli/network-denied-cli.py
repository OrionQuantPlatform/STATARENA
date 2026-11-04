import sys,runpy
from pathlib import Path
import psycopg
module,attempt=sys.argv[1:3]
sys.path.insert(0,str(Path(module).parent))
sys.argv=[module,*sys.argv[3:]]
def denied(*args,**kwargs):
 Path(attempt).write_text('source connection attempted\n')
 raise AssertionError('Source connection forbidden in offline CLI E2E')
psycopg.connect=denied
runpy.run_path(module,run_name='__main__')
