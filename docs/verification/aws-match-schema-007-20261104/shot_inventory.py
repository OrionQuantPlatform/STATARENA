"""Inspect archived shot keys/types on RDS in small indexed groups; transmit signatures only."""
import json,os,time
from collections import Counter
from pathlib import Path
from capture import connect
folder=Path(__file__).resolve().parent
with connect(12) as db:
    paths=[p for p, in db.execute("SELECT DISTINCT s.ref->'tables'->'shots'->>'path' FROM statarena.shards s WHERE s.ref->'tables'->'shots'->>'path' IS NOT NULL ORDER BY 1")]
    print(len(paths),"archived shot sources",flush=True)
    counts=Counter();processed=0;started=time.monotonic()
    for start in range(0,len(paths),16):
        part=paths[start:start+16]
        rows=db.execute("""with chosen as materialized(
            select document from statarena.current_file_documents where document_path=any(%s))
            select e.key,jsonb_typeof(e.value),count(*) from chosen
            cross join lateral jsonb_path_query(document,'$[*].response.data.periods[*].shots[*]') shot
            cross join lateral jsonb_each(shot) e(key,value) group by 1,2""",(part,)).fetchall()
        for k,t,n in rows:counts[k,t]+=n
        processed+=len(part)
        out={"sourcePaths":len(paths),"processedPaths":processed,"seconds":round(time.monotonic()-started,2),"fields":[[k,t,n]for(k,t),n in sorted(counts.items())]}
        (folder/"archived-shot-inventory.json").write_text(json.dumps(out,indent=2)+"\n")
        if start%256==0:print(processed,list(sorted(set(k for k,t in counts))),flush=True)
