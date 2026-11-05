#!/usr/bin/env python3
"""One readonly progress observation of the already-running real transport."""
import argparse,json,os,socket
from pathlib import Path
from datetime import datetime,timezone
BASE=Path(__file__).resolve().parent
SQL="""SELECT a.pid,a.application_name,a.state,a.wait_event_type,a.wait_event,
 extract(epoch FROM clock_timestamp()-a.xact_start)::text AS transaction_seconds,
 left(a.query,240),p.command,p.type,p.tuples_processed,p.bytes_processed
 FROM pg_stat_activity a LEFT JOIN pg_stat_progress_copy p USING(pid)
 WHERE a.usename=current_user AND a.application_name='orion_pro_native_transport_real_v2'
 ORDER BY a.pid LIMIT 5"""
def main():
 p=argparse.ArgumentParser();p.add_argument('--observe',action='store_true');args=p.parse_args()
 if not args.observe:print(json.dumps({'status':'offline_plan','connections':0}));return
 assert not any(k.startswith('PG') for k in os.environ)
 import ingest_actor,psycopg
 report={'command':['python3',str(Path(__file__)),'--observe'],'sql':SQL,'selects':0,'writes':[],'fullAcceptance':False};conn=None;private=None
 out=BASE/'real-core-operation-v3'/('progress-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json')
 try:
  with ingest_actor.private_authentication() as path:
   private=path;addr=sorted({i[4][0] for i in socket.getaddrinfo(ingest_actor.HOST,5432,type=socket.SOCK_STREAM)})[0]
   conn=psycopg.connect(host=ingest_actor.HOST,hostaddr=addr,port=5432,dbname=ingest_actor.DATABASE,user=ingest_actor.ACTOR,passfile=str(path),sslrootcert=str(ingest_actor.ROOT/'dashboard/backend/certs/rds-us-east-2.pem'),sslmode='verify-full',connect_timeout=7,autocommit=True,options='-c default_transaction_read_only=on -c statement_timeout=8000 -c lock_timeout=1000')
   report['selects']=1;report['observed']=conn.execute(SQL).fetchall();report['status']='observed'
 except Exception as e:report.update(status='fail',errorType=type(e).__name__,sqlstate=getattr(e,'sqlstate',None))
 finally:
  if conn:conn.close()
  report['connectionClosed']=conn is None or conn.closed;report['privateAuthenticationRemoved']=private is None or not private.exists();out.write_text(json.dumps(report,indent=2,default=str)+'\n');print(json.dumps({'evidence':str(out),'status':report['status'],'observed':report.get('observed'),'privateAuthenticationRemoved':report['privateAuthenticationRemoved']},default=str))
if __name__=='__main__':main()
