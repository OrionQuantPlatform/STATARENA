#!/usr/bin/env python3
"""Prepare a PostgreSQL-normalized catalogue in an owned loopback PG18.6 only.

Importing this module performs no connection. The sole CLI action is local
preparation; there is no remote host, DSN, apply or configurable remote mode.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'dashboard/scripts'))
SCHEMAS = ['ingest','football','analytics']
SOURCE_PATHS = [ROOT/'docs/architecture/orion-plan-20261104/target-schema.proposed.json',
               HERE/'approval.json',HERE/'model-amendments.json',Path(__file__),HERE/'rds_readback.py',
               *[ROOT/'dashboard/scripts'/n for n in ('orion_pro_schema.py','orion_pro_integrity.py','orion_pro_migrate.py')],
               *[ROOT/'dashboard/backend/migrations'/n for n in ('012_orion_pro_domain.sql','013_orion_pro_integrity.sql')]]

# Five catalogue reads replace the five existing remote catalogue reads. View
# definitions share the relation query, preserving the 14-SELECT remote bound.
QUERIES = {
 'relations': """SELECT n.nspname||'.'||c.relname AS relation,c.relkind,
   CASE WHEN c.relkind IN ('r','p') THEN pg_total_relation_size(c.oid) ELSE 0 END AS bytes,
   CASE WHEN c.relkind='v' THEN pg_get_viewdef(c.oid,false) ELSE NULL END AS definition,
   c.reloptions AS options
   FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
   WHERE n.nspname=ANY(%s) AND c.relkind IN ('r','p','v','S') ORDER BY 1""",
 'columns': """SELECT n.nspname||'.'||c.relname AS relation,a.attname AS name,
   format_type(a.atttypid,a.atttypmod) AS type,NOT a.attnotnull AS nullable,
   a.attidentity AS identity,a.attgenerated AS generated,pg_get_expr(d.adbin,d.adrelid,false) AS default_sql
   FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid JOIN pg_namespace n ON n.oid=c.relnamespace
   LEFT JOIN pg_attrdef d ON d.adrelid=a.attrelid AND d.adnum=a.attnum
   WHERE n.nspname=ANY(%s) AND c.relkind IN ('r','p') AND a.attnum>0 AND NOT a.attisdropped
   ORDER BY 1,a.attnum""",
 'constraints': """SELECT n.nspname||'.'||c.relname AS relation,con.conname AS name,
   con.contype AS kind,con.convalidated AS validated,con.condeferrable AS deferrable,
   con.condeferred AS initially_deferred,con.connoinherit AS no_inherit,
   con.confmatchtype AS match_type,con.confupdtype AS on_update,con.confdeltype AS on_delete,
   pg_get_constraintdef(con.oid,false) AS definition,
   CASE WHEN con.contype='c' THEN pg_get_expr(con.conbin,con.conrelid,false) ELSE NULL END AS expression,
   CASE WHEN con.contype='u' THEN ix.indnullsnotdistinct ELSE NULL END AS nulls_not_distinct,
   ARRAY(SELECT a.attname FROM unnest(con.conkey) WITH ORDINALITY u(k,o)
     JOIN pg_attribute a ON a.attrelid=con.conrelid AND a.attnum=u.k ORDER BY u.o) AS columns,
   CASE WHEN con.confrelid<>0 THEN (SELECT ns.nspname||'.'||cl.relname FROM pg_class cl
     JOIN pg_namespace ns ON ns.oid=cl.relnamespace WHERE cl.oid=con.confrelid) END AS parent,
   ARRAY(SELECT a.attname FROM unnest(con.confkey) WITH ORDINALITY u(k,o)
     JOIN pg_attribute a ON a.attrelid=con.confrelid AND a.attnum=u.k ORDER BY u.o) AS parent_columns
   FROM pg_constraint con JOIN pg_class c ON c.oid=con.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace
   LEFT JOIN pg_index ix ON ix.indexrelid=con.conindid
   WHERE n.nspname=ANY(%s) AND con.contype IN ('p','f','u','c') ORDER BY 1,2""",
 'indexes': """SELECT n.nspname||'.'||c.relname AS relation,i.relname AS name,
   x.indisvalid AND x.indisready AND x.indislive AS valid,x.indisunique AS unique,
   x.indisprimary AS primary,x.indimmediate AS immediate,x.indnullsnotdistinct AS nulls_not_distinct,
   am.amname AS method,pg_get_indexdef(x.indexrelid) AS definition,
   pg_get_expr(x.indpred,x.indrelid,false) AS predicate
   FROM pg_index x JOIN pg_class c ON c.oid=x.indrelid JOIN pg_class i ON i.oid=x.indexrelid
   JOIN pg_namespace n ON n.oid=c.relnamespace JOIN pg_am am ON am.oid=i.relam
   WHERE n.nspname=ANY(%s) ORDER BY 1,2""",
 'guards': """SELECT 'function' AS kind,n.nspname||'.'||p.proname AS name,
   pg_get_function_identity_arguments(p.oid) AS identity,p.prosecdef AS safe,p.proconfig AS settings,
   pg_get_functiondef(p.oid) AS definition
   FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname=ANY(%s)
   UNION ALL SELECT 'trigger',n.nspname||'.'||c.relname||'.'||t.tgname,'' AS identity,
   t.tgenabled='O',NULL::text[],pg_get_triggerdef(t.oid,false)
   FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace
   WHERE n.nspname=ANY(%s) AND NOT t.tgisinternal ORDER BY 1,2,3"""
}
KEYS = {'relations':('relation',),'columns':('relation','name'),'constraints':('relation','name'),
        'indexes':('relation','name'),'guards':('kind','name','identity')}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hashed(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


def sources():
    return {str(p.relative_to(ROOT)):sha(p) for p in SOURCE_PATHS}


def normalized(group, rows):
    result=[{k:v for k,v in row.items() if not (group=='relations' and k=='bytes')} for row in rows]
    return sorted(result,key=lambda row:tuple(row[k] for k in KEYS[group]))


def compare(group, actual, expected):
    actual=normalized(group,actual);expected=normalized(group,expected)
    keys=KEYS[group]
    left={tuple(row[k] for k in keys):row for row in actual}
    right={tuple(row[k] for k in keys):row for row in expected}
    differences=[list(k) for k in sorted(left.keys()|right.keys()) if left.get(k)!=right.get(k)]
    return actual==expected and len(left)==len(actual) and len(right)==len(expected),{
        'actual':len(actual),'expected':len(expected),'differences':differences}


def load_expected(path, digest):
    path=path.resolve();path.relative_to(HERE)
    if not re.fullmatch('[0-9a-f]{64}',digest) or sha(path)!=digest:
        raise ValueError('Expected catalogue digest mismatch')
    data=json.loads(path.read_text())
    if data.get('kind')!='owned_pg18_expected_catalogue_v1' or data.get('sourceSha256')!=sources():
        raise ValueError('Expected catalogue source binding differs from current code/model/SQL')
    prep=data.get('preparation',{});cleanup=prep.get('cleanup',{})
    if prep.get('status')!='complete' or prep.get('serverVersion')!=180006 or cleanup.get('server_stopped') is not True or cleanup.get('owned_directory_removed') is not True:
        raise ValueError('Expected catalogue lacks completed owned PostgreSQL preparation/cleanup')
    if set(data.get('catalogue',{}))!=set(QUERIES) or hashed(data['catalogue'])!=data.get('catalogueSha256'):
        raise ValueError('Expected catalogue normalized content digest mismatch')
    return data


def prepare_local(args):
    from harness import LocalPostgres
    from orion_pro_schema import SPEC,approved_model,active_tables,schema_sql
    from orion_pro_integrity import integrity_sql
    from orion_pro_migrate import bootstrap
    import psycopg
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    run=HERE/'expected-catalogues'/(stamp+'-'+args.label);inputs=run/'inputs';inputs.mkdir(parents=True)
    source_hashes=sources()
    for source in SOURCE_PATHS:shutil.copy2(source,inputs/source.name)
    model=approved_model(SPEC)
    paths={v:ROOT/f'dashboard/backend/migrations/{v}_orion_pro_{name}.sql' for v,name in [('012','domain'),('013','integrity')]}
    artifacts=[('012',paths['012'],schema_sql(model)),('013',paths['013'],integrity_sql(model,active_tables(model)))]
    report={'kind':'owned_pg18_expected_catalogue_v1','sourceSha256':source_hashes,'modelSha256':sha(SPEC),
            'migratorSha256':sha(ROOT/'dashboard/scripts/orion_pro_migrate.py'),
            'migrationSha256':{v:sha(path) for v,path in paths.items()},'catalogue':{},
            'preparation':{'startedAt':datetime.now(timezone.utc).isoformat(),'status':'failed',
                           'command':['python3',str(Path(__file__).relative_to(ROOT)),*sys.argv[1:]],
                           'setup':'Owned loopback PostgreSQL18.6; exact checked 012/013 and shared bootstrap; no remote connection or CLI'}}
    pg=LocalPostgres(args.pg_bin,run);db=None
    try:
        if not all(path.read_text()==body for _,path,body in artifacts):
            raise ValueError('Checked migration bytes differ from pure current compiler')
        pg.start();db=psycopg.connect(pg.dsn,autocommit=True,options='-c search_path=pg_catalog')
        if db.info.server_version!=180006:raise ValueError('Owned preparation requires PostgreSQL18.6')
        report['preparation']['serverVersion']=db.info.server_version
        commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        with db.transaction():
            for version,path,sql in artifacts:
                db.execute(sql,prepare=False)
                db.execute('INSERT INTO ingest.schema_migrations(version,content_sha256,applied_at,code_commit) VALUES(%s,%s,CURRENT_TIMESTAMP,%s)',(version,sha(path),commit))
            report['preparation']['bootstrap']=bootstrap(db,model,artifacts)
        journal=dict(db.execute('SELECT version,content_sha256 FROM ingest.schema_migrations ORDER BY version').fetchall())
        if journal!=report['migrationSha256']:raise ValueError('Owned preparation journal differs from checked SQL')
        report['preparation']['journal']=journal
        report['preparation']['queries']=[]
        for name,sql in QUERIES.items():
            cur=db.execute(sql,(SCHEMAS,SCHEMAS) if name=='guards' else (SCHEMAS,))
            rows=[dict(zip((c.name for c in cur.description),row)) for row in cur.fetchall()]
            report['catalogue'][name]=normalized(name,rows)
            report['preparation']['queries'].append({'name':name,'sql':sql,'rows':len(rows)})
        tables={r['relation'] for r in report['catalogue']['relations'] if r['relkind'] in ('r','p')}
        if tables!=set(active_tables(model)):raise ValueError('Prepared table catalogue differs from approved active model')
        if sources()!=source_hashes:raise ValueError('Inputs changed during owned preparation')
        report['catalogueSha256']=hashed(report['catalogue'])
        report['preparation']['status']='complete'
    except Exception as exc:
        report['preparation']['error']={'type':type(exc).__name__,'sqlstate':getattr(exc,'sqlstate',None)}
        if isinstance(exc,ValueError):report['preparation']['error']['reason']=str(exc)
    finally:
        if db is not None:db.close()
        report['preparation']['cleanup']=pg.cleanup()
        report['preparation']['finishedAt']=datetime.now(timezone.utc).isoformat()
        out=run/'expected-catalogue.json';out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
        print(json.dumps({'status':report['preparation']['status'],'catalogue':str(out.relative_to(ROOT)),
                          'sha256':sha(out),'counts':{k:len(v) for k,v in report['catalogue'].items()}}))
    return 0 if report['preparation']['status']=='complete' else 1


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepare-local',action='store_true',required=True)
    p.add_argument('--label',default='expected-catalogue')
    p.add_argument('--pg-bin',type=Path,default=Path('/tmp/statarena-cache-test-tools/node_modules/@embedded-postgres/darwin-arm64/native/bin'))
    args=p.parse_args()
    if not re.fullmatch('[a-zA-Z0-9][a-zA-Z0-9-]{0,79}',args.label):p.error('Use a simple bounded label')
    return prepare_local(args)


if __name__=='__main__':
    raise SystemExit(main())
