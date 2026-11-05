import os
from pathlib import Path
import psycopg
def no_network_connect(*args,**kwargs):
    Path(os.environ['ORION_CONNECT_TRIPWIRE']).write_text('driver_connect_attempted\n')
    raise RuntimeError('local_worker_connect_tripwire_no_network')
psycopg.connect=no_network_connect
