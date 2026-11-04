from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import urlopen,Request
from urllib.error import HTTPError
import json,hashlib,time,threading
here=Path(__file__).parent;c=here/'api-cache';c.mkdir(exist_ok=True);lock=threading.Lock()
base='https://d317dq37z1tacb.cloudfront.net';budget=[0,0]
class H(BaseHTTPRequestHandler):
 def do_GET(self):
  path=urlsplit(self.path).path
  if not path.startswith('/api/') or len(self.path)>900:self.send_error(400);return
  k=hashlib.sha256(self.path.encode()).hexdigest();bfile=c/(k+'.bin');hfile=c/(k+'.json')
  if path.startswith('/api/seasons/partition'):time.sleep(.22)
  if not hfile.exists():
   with lock:
    if not hfile.exists():
     if path=='/api/assets' or budget[0]>=10 or budget[1]>2_000_000:self.send_error(503);return
     try:r=urlopen(Request(base+self.path,headers={'Accept':'application/json'}),timeout=15)
     except HTTPError as e:r=e
     with r:
      b=r.read(4_500_000);meta=dict(status=r.status,path=self.path,type=r.headers.get('content-type'));bfile.write_bytes(b);hfile.write_text(json.dumps(meta));budget[0]+=1;budget[1]+=len(b)
  b=bfile.read_bytes();m=json.loads(hfile.read_text()); self.send_response(m['status']);self.send_header('Content-Type',m['type'] or 'application/json');self.send_header('Access-Control-Allow-Origin','*');self.send_header('Content-Length',str(len(b)));self.end_headers()
  try:self.wfile.write(b)
  except BrokenPipeError: pass
 def log_message(self,*args):pass
ThreadingHTTPServer(('127.0.0.1',18947),H).serve_forever()
