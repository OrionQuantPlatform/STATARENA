"""Server-side field/type inventory across indexed archive response documents.
Read every root response in selected shards; inspect the first array member (all
event rows, all object properties), normalizing dynamic player-stat metric names.
No response bodies cross the connection.
"""
import json,itertools,sys,time
from collections import defaultdict
from pathlib import Path
from capture import connect
folder=Path(__file__).resolve().parent;sys.path.insert(0,str(folder.parents[2]/"dashboard/scripts"))
from relational_match_model import Children,families
def mapping(family):
    result={}
    def walk(model,p):
        result[p]={"object"}
        for k,v in model.items():
            key=(*p,k)
            if isinstance(v,dict):walk(v,key)
            elif isinstance(v,Children):
                result[key]={"object" if v.keyed else "array"}
                walk(v.fields,(*key,"*" if v.keyed else "[]"))
            elif v=="integer[][]":
                result[key]={"array"};result[(*key,"[]")]={"array"};result[(*key,"[]","[]")]={"integer"}
            else:result[key]={"text":{"string"},"integer":{"integer"},"boolean":{"boolean"},"double precision":{"integer","decimal"}}[v]
    if family=="players":result[()]={"array"};walk(families["players"].fields["players"].fields,("[]",))
    else:walk(families[family].fields,())
    return result
sql="""WITH RECURSIVE docs AS MATERIALIZED (SELECT document FROM statarena.current_file_documents WHERE document_path=ANY(%s)),
walk(p,v) AS (
 SELECT ARRAY[]::text[], row->'response'->'data' FROM docs CROSS JOIN LATERAL jsonb_array_elements(document) row
 UNION ALL SELECT w.p||ARRAY[ch.k],ch.v FROM walk w CROSS JOIN LATERAL (
  SELECT CASE WHEN w.p[greatest(1,cardinality(w.p)-2):cardinality(w.p)]=ARRAY['stats','[]','stats'] THEN '*' ELSE kv.key END k,kv.value v
   FROM jsonb_each(CASE WHEN jsonb_typeof(w.v)='object' THEN w.v ELSE '{}'::jsonb END) kv
  UNION ALL SELECT '[]',ar.v FROM jsonb_array_elements(CASE WHEN jsonb_typeof(w.v)='array' AND w.p=ARRAY['events'] THEN w.v ELSE '[]'::jsonb END) ar(v)
  UNION ALL SELECT '[]',w.v->0 WHERE jsonb_typeof(w.v)='array' AND w.p<>ARRAY['events'] AND w.v->0 IS NOT NULL
 ) ch WHERE cardinality(w.p)<14)
SELECT p,CASE WHEN jsonb_typeof(v)='number' THEN CASE WHEN v::text ~ '^-?[0-9]+$' THEN 'integer' ELSE 'decimal' END ELSE jsonb_typeof(v) END t
FROM walk GROUP BY 1,2"""
if __name__=="__main__":
 full='--all' in sys.argv;dest=folder/("archive-shapes-all.json" if full else "archive-shapes-broad.json")
 receipt={"boundedArrays":"First entry of each nested array, every event, every dynamic player metric in visited group, every root response in each inspected source. Full shot rows separately audited.","families":{}}
 with connect(30) as db:
    for family in ("events","match","lineups","stats","players","player_halves","h2h","momentum","advanced_teams","advanced_players","pass_networks","heatmaps","shots"):
        allpaths=[p for p, in db.execute("SELECT DISTINCT s.ref->'tables'->%s->>'path' FROM statarena.shards s WHERE s.ref->'tables'->%s->>'path' IS NOT NULL ORDER BY 1",(family,family))]
        paths=allpaths if full else allpaths[::max(1,len(allpaths)//36)]
        expected=mapping(family);seen=defaultdict(set);processed=0;tm=time.monotonic()
        for i in range(0,len(paths),12):
            selected=paths[i:i+12]
            for p,t in db.execute(sql,(selected,)):
                if t is not None:seen[tuple(p)].add(t)
            processed+=len(selected)
            issues={".".join(p):sorted(ts) for p,ts in seen.items() if p not in expected or (ts-{'null'})-expected[p]}
            receipt["families"][family]={"available":len(allpaths),"scanned":processed,"seconds":round(time.monotonic()-tm,2),"distinctPaths":len(seen),"issues":issues}
            dest.write_text(json.dumps(receipt,indent=2)+"\n")
        print(family,processed,issues,flush=True)
