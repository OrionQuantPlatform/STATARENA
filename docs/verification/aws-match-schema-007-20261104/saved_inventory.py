"""Read-only SQL inventory of direct saved match resource families and nested routes."""
import json,string,sys,time
from collections import defaultdict
from pathlib import Path
from array_inventory import mapping,sql
from capture import connect
folder=Path(__file__).resolve().parent
def expected(f):
    subset={"single_player":("players",("[]",)), "single_shot":("shots",("periods","[]","shots","[]")),
            "single_halves":("player_halves",("players","[]")), "single_advanced":("advanced_players",("players","[]"))}
    if f not in subset:return mapping(f)
    fam,prefix=subset[f];src=mapping(fam);out={k[len(prefix):]:v for k,v in src.items() if k[:len(prefix)]==prefix}
    if f=="single_halves":out[("match_id",)]={"string"}
    return out
head="""WITH RECURSIVE refs AS MATERIALIZED (
 SELECT CASE WHEN suffix='' THEN 'match' WHEN suffix='players/halves' THEN 'player_halves'
 WHEN suffix='advanced' THEN 'advanced_teams' WHEN suffix='advanced/players' THEN 'advanced_players'
 WHEN suffix='advanced/network' THEN 'pass_networks'
 WHEN suffix LIKE 'shots/s_%%' THEN 'single_shot'
 WHEN suffix LIKE 'players/p_%%/halves' THEN 'single_halves'
 WHEN suffix LIKE 'players/p_%%/shots' THEN 'player_shots'
 WHEN suffix LIKE 'players/p_%%' THEN 'single_player'
 WHEN suffix LIKE 'advanced/players/p_%%' THEN 'single_advanced'
 ELSE suffix END f,ref FROM (
 SELECT substring(endpoint FROM 19) AS suffix,ref FROM statarena.resources
 WHERE endpoint >= %s AND endpoint < %s AND ref IS NOT NULL AND status=200 AND mod(hashtextextended(endpoint||params,0),%s)=0) r),
docs AS MATERIALIZED(SELECT f,ref,CASE WHEN ref?'ordinal' THEN d.document->(ref->>'ordinal')::int ELSE d.document END v
 FROM refs JOIN statarena.current_file_documents d ON d.document_path=ref->>'path'),
items AS MATERIALIZED(SELECT f, CASE WHEN ref?'documentId' THEN jsonb_path_query_first(v,'$[*] ? (@.documentId == $id)',jsonb_build_object('id',ref->>'documentId')) ELSE v END elem FROM docs),
walk(f,p,v) AS(
 SELECT f,ARRAY[]::text[],coalesce(elem->'observation',elem->'response',elem)->'data' FROM items"""
tail=sql.split(" UNION ALL SELECT w.p||ARRAY[ch.k]",1)[1]
query=(head+" UNION ALL SELECT w.f,w.p||ARRAY[ch.k]"+tail).replace("SELECT p,CASE","SELECT f,p,CASE").replace("FROM walk GROUP BY 1,2","FROM walk GROUP BY 1,2,3")
if __name__=="__main__":
    allsrc="--all" in sys.argv;mod=1 if allsrc else 43
    target=folder/("saved-shapes-all.json" if allsrc else "saved-shapes-broad.json")
    seen=defaultdict(lambda:defaultdict(set));start=time.monotonic()
    with connect(40) as db:
        for i,c in enumerate(string.digits+string.ascii_uppercase+string.ascii_lowercase):
            prefix='/matches/m_'+c
            for f,p,t in db.execute(query,(prefix,prefix+'~',mod)):
                if t is not None:seen[f][tuple(p)].add(t)
            out={"completedIdPrefixes":i+1,"idPrefixes":62,"deterministicHashDivisor":mod,"seconds":round(time.monotonic()-start,2),"families":{}}
            for f,paths in seen.items():
                try:allowed=expected(f)
                except KeyError:allowed={}
                issues={".".join(p):sorted(ts) for p,ts in paths.items() if p not in allowed or (ts-{'null'})-allowed[p]}
                out["families"][f]={"distinctPaths":len(paths),"issues":issues}
            target.write_text(json.dumps(out,indent=2)+"\n")
            if i%10==0:print(i+1,{f:x['issues'] for f,x in out["families"].items() if x['issues']},flush=True)
