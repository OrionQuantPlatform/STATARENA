import gzip,json,os,subprocess,sys,tempfile
from pathlib import Path
import psycopg
folder=Path(__file__).resolve().parent;root=folder.parents[2];phase=sys.argv[1]
sys.path.insert(0,str(root/'dashboard/scripts'))
from relational_match import publish_match_details,publish_match_resource
def get(db,mid,fam,subject=""):
 return db.execute("select statarena_app.detail_response(f) from statarena_app.match_families f where match_id=%s and family=%s and subject_id=%s and params='{}'",(mid,fam,subject)).fetchone()[0]
def payload(mid,shots):
 return {"status":200,"data":{"match_id":mid,"periods":[{"period":"first","shots":shots}]},"error":None}
actual=json.loads(gzip.decompress((folder/'own-goal-source.json.gz').read_bytes()))
both=json.loads(gzip.decompress((folder/'scope-counterexamples.json.gz').read_bytes()))
report={"passed":False,"checks":[]}
with psycopg.connect(os.environ['LOCAL_FIXTURE_DB'],autocommit=True) as db:
 with tempfile.TemporaryDirectory() as tmp:
  for mod in ('relational_match','relational_match_ddl','relational_match_model'):
   (Path(tmp)/(mod+'.py')).write_bytes(subprocess.check_output(["git","-C",root,"show","57f65bbc:dashboard/scripts/"+mod+".py"]))
  subprocess.run([sys.executable,"-c","import os,psycopg;from relational_match import publish_match_details; db=psycopg.connect(os.environ['LOCAL_FIXTURE_DB']);publish_match_details(db,'m_OLD001',{'shots':{'status':200,'data':{'match_id':'m_OLD001','periods':[{'period':'first','shots':[{'id':'s_OLD001'}]}]},'error':None}});db.commit()"],cwd=tmp,env=dict(os.environ,PYTHONPATH=tmp+os.pathsep+os.environ.get("PYTHONPATH","")),check=True)
 if phase=="after":db.execute((root/"dashboard/backend/migrations/007_match_source_fields.sql").read_text())
 assert get(db,"m_OLD001","shots")==payload("m_OLD001",[{"id":"s_OLD001"}]);report["checks"].append("previous 004 shot retains absence")
 try:
  for sample in both.values():
   publish_match_details(db,sample['match'],{'shots':sample['value']})
   assert get(db,sample['match'],'shots')==sample['value'];report['checks'].append("actual "+sample['match'])
  for key in ('is_own_goal','is_saved_off_line'):
   shots=[{'id':'s_00000'+str(i),**({key:v} if i<3 else {})} for i,v in enumerate([True,False,None,None])]
   mid='m_NEW001';value=payload(mid,shots)
   publish_match_details(db,mid,{'shots':value})
   assert get(db,mid,'shots')==value
   for shot in shots:
    wrapper={'status':200,'data':shot,'error':None}
    assert publish_match_resource(db,"/matches/"+mid+"/shots/"+shot['id'],{},wrapper)
    assert get(db,mid,'single_shot',shot['id'])==wrapper
   player={'status':200,'data':{'player':{'id':'p_NEW001'},'shots':shots},'error':None}
   publish_match_resource(db,'/matches/'+mid+'/players/p_NEW001/shots',{},player)
   assert get(db,mid,'player_shots','p_NEW001')==player
   if phase=='after':db.execute((root/'dashboard/backend/migrations/007_match_source_fields.sql').read_text())
   assert get(db,mid,'shots')==value and get(db,mid,'player_shots','p_NEW001')==player
   report['checks'].append(key+" true false null absent across three routes and repeated migration")
  report['passed']=True
 except (ValueError,TypeError) as e:
  report['error']=str(e)
print(json.dumps(report))
