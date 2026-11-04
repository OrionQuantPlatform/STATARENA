"""Measure named typed columns against exactly the same 411,416 source metric rows."""
import collections,gzip,hashlib,itertools,json,os,re,sys,time
from pathlib import Path
import psycopg
folder=Path(__file__).parent
src=Path('/tmp/statarena-metric-values-20261104')
report={"setup":"local PostgreSQL 18/real metrics TSV/native values. Both directions EXCEPT ALL, measured relations with indexes","tables":{}}
def qi(n):return '"'+n.replace('"','""')+'"'
def colkey(k):return re.sub('[^a-z0-9_]+','_',re.sub('([a-z])([A-Z])',r'\1_\2',k)).lower()
def sem(key,label):
    if key=='':return "shotmap_flag" if label=="Shotmap" else None
    return key
def small(v):return v is None or (float(v).is_integer() and -32768<=v<=32767)
def copy_rows(db,table,cols,rows):
    with db.cursor() as c,c.copy("copy "+table+"("+",".join(map(qi,cols))+") from stdin") as st:
        for row in rows:st.write_row(row)
def size(db,schema):
    return dict(db.execute("select relname,pg_total_relation_size(oid) from pg_class where relnamespace=%s::regnamespace and relkind='r' order by relname",(schema,)).fetchall())
def flags(missing,nulls):
    keys=["key","stat","stat.type","stat.value","stat.total"]
    assert set(missing)<=set(keys) and set(nulls)<={'stat'}
    return sum((1<<i) for i,k in enumerate(keys) if k in missing)+(32 if "stat" in nulls else 0)
def flag_array():
    return "array_remove(array["+ ",".join("case when (d.flags & "+str(1<<i)+")<>0 then '"+k+"' end" for i,k in enumerate(["key","stat","stat.type","stat.value","stat.total"]))+"],null)"
def bench(db,old,view,ids):
    result={}
    responses={}
    for label,t in [('original',old),('wide',view)]:
        ticks=[];checks=[]
        for rid in [*ids,*ids]:
            now=time.monotonic();data=db.execute("select parent_no,jsonb_object_agg(metric_label,jsonb_build_object('key',key,'stat',jsonb_build_object('type',stat_type,'value',stat_value) || case when 'stat.total'=any(missing) then '{}'::jsonb else jsonb_build_object('total',stat_total) end) order by position) from "+t+" where resource_id=%s group by parent_no order by parent_no",(rid,)).fetchall()
            ticks.append(round((time.monotonic()-now)*1000,3));checks.append(hashlib.sha256(json.dumps(data,separators=(',',':')).encode()).hexdigest())
        result[label]={'milliseconds':ticks,'ids':ids}
        responses[label]=checks
    assert responses['original']==responses['wide'];return result
def run(db,kind):
    schema='w_'+kind;old='o_'+kind;db.execute("create schema "+schema);db.execute("create schema "+old)
    base=old+'.metrics';wide=schema+'.stats';decl='resource_id bigint, record_no int, missing text[],null_groups text[],parent_no int,position int,metric_label text,key text,stat_type text,stat_value float8,stat_total float8'
    db.execute('create table '+base+' ('+decl+',primary key(resource_id,record_no),unique(resource_id,parent_no,position))')
    fh=src/(kind+'_stat_metrics.tsv.gz');raw=hashlib.sha256()
    with gzip.open(fh,'rb') as inp,db.cursor() as cur,cur.copy("copy "+base+" from stdin") as st:
        while b:=inp.read(1048576):raw.update(b);st.write(b)
    # Use observed semantic fields as the *reviewed model* rather than derive columns at runtime.
    # Future keys always go through overflow until a migration explicitly names a new column.
    ids={};fields={};totals={};names={};types={}
    for key,label,n,small_v,has_t,small_t in db.execute("""select key,metric_label,count(*),
      bool_and(stat_value is null or (stat_value=trunc(stat_value) and stat_value between -32768 and 32767)),
      bool_or(stat_total is not null),bool_and(stat_total is null or (stat_total=trunc(stat_total) and stat_total between -32768 and 32767))
      from """+base+" group by key,metric_label order by key,metric_label"):
        k=sem(key,label)
        if k is None:continue
        fields[k]=fields.get(k,True) and small_v;totals[k]=totals.get(k,False) or has_t;types[k]=types.get(k,True) and small_t
    db.execute(f"create table {schema}.definitions (id int primary key,semantic smallint,label text,source_key text,value_type text,flags smallint not null, unique nulls not distinct(semantic,label,source_key,value_type,flags))")
    db.execute(f"create table {schema}.templates (id int primary key,digest bytea not null unique)")
    db.execute(f"create table {schema}.members (template int references {schema}.templates,position int,definition int references {schema}.definitions,record_delta int not null,in_wide boolean not null,primary key(template,position))")
    for i,k in enumerate(fields):
        ids[k]=i+1;names[k]=colkey(k)
    assert len(set(names.values()))==len(names),names
    columns=[]
    for k,n in names.items():
        columns.append((n,'smallint' if fields[k] else 'double precision'))
        if totals[k]:columns.append((n+'_total','smallint' if types[k] else 'double precision'))
    db.execute(f"create table {wide}(resource_id bigint,parent_no int,template int not null references {schema}.templates,base_no int not null,"+",".join(qi(n)+' '+t for n,t in columns)+",primary key(resource_id,parent_no))")
    db.execute(f"create table {schema}.extra(resource_id bigint,parent_no int,position int,stat_value float8,stat_total float8,primary key(resource_id,parent_no,position),foreign key(resource_id,parent_no) references {wide})")
    defids={};layoutids={};defs=[];layouts=[];members=[];out=[];extras=[];sample_ids=[]
    def emit(rowset):
        occupied=set();layout=[];packed={};rid,_,_,_,parent,*_=rowset[0];anchor=min(r[1]for r in rowset)
        for _,record,missing,nulls,_,pos,label,key,typ,val,tot in rowset:
            k=sem(key,label);slot=ids.get(k,-1);address=(slot,label,key,typ,flags(missing,nulls))
            new=address not in defids
            did=defids.setdefault(address,len(defids)+1)
            if new:defs.append((did,*address))
            native=slot>0 and k not in occupied
            layout.append((pos,did,record-anchor,native))
            overflow=not native or (fields[k] and not small(val)) or (tot is not None and (not totals[k] or (types[k] and not small(tot))))
            if native:occupied.add(k)
            if overflow:
                extras.append((rid,parent,pos,val,tot))
            else:
                packed[names[k]]=int(val) if fields[k] and val is not None else val
                if totals[k]:packed[names[k]+'_total']=int(tot) if types[k] and tot is not None else tot
        sig=tuple(layout);new=sig not in layoutids
        tid=layoutids.setdefault(sig,len(layoutids)+1)
        if new:
            digest=hashlib.sha256(json.dumps(sig,separators=(',',':')).encode()).digest();layouts.append((tid,digest))
            members.extend((tid,*m)for m in sig)
        out.append((rid,parent,tid,anchor,*[packed.get(n)for n,_ in columns]))
    with db.cursor(name='scan_'+kind) as cursor:
        cursor.execute("select * from "+base+" order by resource_id,parent_no,position")
        for k,g in itertools.groupby(cursor,key=lambda r:(r[0],r[4])):emit(list(g))
    def flush():
        copy_rows(db,schema+'.definitions',['id','semantic','label','source_key','value_type','flags'],defs);defs.clear()
        copy_rows(db,schema+'.templates',['id','digest'],layouts);layouts.clear()
        copy_rows(db,schema+'.members',['template','position','definition','record_delta','in_wide'],members);members.clear()
        copy_rows(db,wide,['resource_id','parent_no','template','base_no',*[n for n,_ in columns]],out);out.clear()
        copy_rows(db,schema+'.extra',['resource_id','parent_no','position','stat_value','stat_total'],extras);extras.clear()
    groups=len(out);overflow=len(extras);flush()
    def getter(field):
        choices=["when "+str(ids[k])+" then w."+qi(names[k]+('_total' if field=='stat_total' else ''))+"::float8" for k in names if field!='stat_total' or totals[k]]
        return f"case when x.position is not null then x.{field} else case d.semantic "+" ".join(choices)+" end end"
    view=schema+'.decoded'
    db.execute("create view "+view+" as select w.resource_id,w.base_no+m.record_delta as record_no,"+flag_array()+" as missing,case when (d.flags & 32)<>0 then array['stat'] else '{}'::text[] end null_groups,w.parent_no,m.position,d.label as metric_label,d.source_key as key,d.value_type as stat_type,"+getter('stat_value')+' as stat_value,'+getter('stat_total')+f' as stat_total from {wide} w join {schema}.members m on m.template=w.template join {schema}.definitions d on d.id=m.definition left join {schema}.extra x on x.resource_id=w.resource_id and x.parent_no=w.parent_no and x.position=m.position')
    db.execute("analyze")
    def parity():
        diff=db.execute("select count(*) from ((select * from "+base+" except all select * from "+view+") union all (select * from "+view+" except all select * from "+base+")) diff").fetchone()[0];assert diff==0,diff;return diff
    compared=parity()
    count=db.execute('select count(*) from '+base).fetchone()[0]
    r={'nativeCopySha256':raw.hexdigest(),'sourceRows':count,'groups':groups,'semanticFields':len(names),'physicalMetricColumns':len(columns),'definitions':len(defids),'templates':len(layoutids),'overflowRows':overflow,'originalBytesByRelation':size(db,old),'wideBytesByRelation':size(db,schema),'sqlRowDifferences':compared}
    r['bytesPerMetric']=sum(r['wideBytesByRelation'].values())/count
    top=[row[0]for row in db.execute("select resource_id from "+base+" group by 1 order by count(*) desc,1 limit 5")]
    r['pointRead']=bench(db,base,view,top)
    edge=[(987654,8,[],[],4,0,'a','goals','integer',0,None),(987654,11,['stat.total'],[],4,1,'b','goals','integer',99999,None),(987654,18,['key','stat.type','stat.value'],[],4,2,'c',None,None,None,0),(987654,19,['key'],['stat'],4,3,'d',None,None,None,None),(987654,24,['key','stat'],[],4,4,'e',None,None,None,None),(987654,25,[],[],4,5,'f','never_seen','double',1.25,0),(987654,27,[],[],5,0,'g','goals','double',2.75,90000)]
    for grp in (edge[:6],edge[6:]):emit(grp)
    flush();copy_rows(db,base,[x.split()[0] for x in decl.split(',')],edge)
    r['adversarialDifferences']=parity()
    return r
with psycopg.connect(os.environ['TEST_DATABASE_URL']) as db:
    for kind in ['half','player']:
        start=time.monotonic();report['tables'][kind]=run(db,kind);db.commit()
        print(kind,report['tables'][kind]['bytesPerMetric'],time.monotonic()-start,flush=True)
        (folder/'results.json').write_text(json.dumps(report,indent=2)+'\n')
