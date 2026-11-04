"""Locate a deterministic saved type mismatch. Return only its first real response."""
import gzip,json,string
from pathlib import Path
from capture import connect
from saved_inventory import head
folder=Path(__file__).resolve().parent
query=head.replace(" f,ref FROM ("," f,ref,endpoint FROM (").replace("AS suffix,ref FROM","AS suffix,ref,endpoint FROM").replace("SELECT f,ref,CASE","SELECT f,ref,endpoint,CASE").replace("SELECT f, CASE","SELECT f,ref,endpoint, CASE").split(",\nwalk(f,p,v)")[0]
query+=""" SELECT endpoint,ref,coalesce(elem->'observation',elem->'response',elem)->'data' FROM items
WHERE f='single_player' AND (coalesce(elem->'observation',elem->'response',elem)->'data') ? 'position_id' ORDER BY endpoint LIMIT 1"""
with connect(20) as db:
 for c in string.digits+string.ascii_uppercase+string.ascii_lowercase:
    prefix='/matches/m_'+c
    row=db.execute(query,(prefix,prefix+'~',43)).fetchone()
    if row:
        endpoint,ref,data=row
        sha=db.execute("select encode(sha256,'hex') from statarena.objects where path=%s",(ref['path'],)).fetchone()[0]
        out={"endpoint":endpoint,"ref":ref,"sourceSha256":sha,"status":200,"data":data}
        (folder/"single-player-position-source.json.gz").write_bytes(gzip.compress(json.dumps(out,separators=(",",":")).encode(),mtime=0))
        print(endpoint,data.get("position_id"));break
