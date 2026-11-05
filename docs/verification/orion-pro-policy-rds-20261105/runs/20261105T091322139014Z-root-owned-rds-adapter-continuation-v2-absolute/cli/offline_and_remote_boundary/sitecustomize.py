import os,socket
from pathlib import Path
import psycopg
def blocked(*a,**k):
 Path(os.environ['CONNECT_TRIPWIRE']).write_text('attempted')
 raise RuntimeError('network_forbidden')
psycopg.connect=blocked
socket.getaddrinfo=blocked
