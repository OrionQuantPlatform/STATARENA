#!/usr/bin/env python3
"""Independent read-only catalogue/bootstrap acceptance on the existing RDS."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'dashboard/scripts'))
from orion_pro_schema import approved_model, SPEC

HOST = 'statarena-postgres.clcy2iqyajbl.us-east-2.rds.amazonaws.com'
DB, ROLE, WEB = 'statarena_prod', 'statarena_ingest', 'statarena_runtime'
SCHEMAS = ['ingest', 'football', 'analytics']
CA = ROOT / 'dashboard/backend/certs/rds-us-east-2.pem'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hashed(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--apply-receipt', type=Path, required=True)
    p.add_argument('--apply-sha256', required=True)
    p.add_argument('--label', default='schema-bootstrap')
    args = p.parse_args()
    if not re.fullmatch('[a-zA-Z0-9][a-zA-Z0-9-]{0,79}', args.label):
        p.error('Use a simple bounded label')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    run = HERE / 'rds-readbacks' / (stamp + '-' + args.label)
    inputs = run / 'inputs'; inputs.mkdir(parents=True)
    import shutil
    for source in [Path(__file__), HERE / 'RDS_READBACK_PROTOCOL.md', SPEC]:
        shutil.copy2(source, inputs / source.name)
    report = {'kind': 'independent_rds_schema_bootstrap_readback', 'startedAt': datetime.now(timezone.utc).isoformat(),
              'setup': 'Existing instance; one read-only repeatable-read TLS session; indirect libpq password file; no secret retrieval',
              'command': ['python3', str(Path(__file__).relative_to(ROOT)), *sys.argv[1:]],
              'expected': str((HERE / 'RDS_READBACK_PROTOCOL.md').relative_to(ROOT)),
              'queries': [], 'cases': [], 'remoteWrites': [], 'modelSha256': sha(SPEC),
              'scriptSha256': sha(Path(__file__)), 'limitations': ['Schema/bootstrap only; no real-source or public cutover acceptance',
              'Source metadata estimates do not establish complete data fidelity or unchanged source bytes']}
    conn = None

    def case(name, ok, actual):
        report['cases'].append({'case': name, 'status': 'pass' if ok else 'fail', 'actual': actual})

    def query(name, sql, params=()):
        if len(report['queries']) >= 14 or not sql.lstrip().upper().startswith('SELECT'):
            raise ValueError('Read-only statement budget exceeded')
        start = time.monotonic(); cur = conn.execute(sql, params)
        rows = [dict(zip((c.name for c in cur.description), row)) for row in cur.fetchall()]
        report['queries'].append({'name': name, 'sql': sql, 'params': list(params), 'rows': rows,
                                  'elapsedMs': round((time.monotonic()-start)*1000, 3)})
        return rows

    try:
        receipt_path = args.apply_receipt.resolve(); receipt_path.relative_to(HERE)
        if not re.fullmatch('[0-9a-f]{64}', args.apply_sha256) or sha(receipt_path) != args.apply_sha256:
            raise ValueError('Apply receipt digest mismatch')
        receipt = json.loads(receipt_path.read_text()); model = approved_model(SPEC)
        tables = {t['qualified_name']: t for s in model['schemas'] for t in s['tables'] if t['phase'] != 'models'}
        migrations = {v: sha(ROOT / f'dashboard/backend/migrations/{v}_orion_pro_{name}.sql') for v, name in [('012', 'domain'), ('013', 'integrity')]}
        if receipt.get('status') != 'applied' or receipt.get('mode') != 'apply' or receipt['apply']['transaction'] != 'atomic_committed' or receipt['apply']['scope'] != 'schema_and_bootstrap_only':
            raise ValueError('Receipt does not establish a committed schema/bootstrap apply')
        if receipt['plan']['modelSha256'] != sha(SPEC) or receipt['plan']['migrationSha256'] != migrations:
            raise ValueError('Current model/migration bytes differ from the apply receipt')
        report['applyReceipt'] = {'path': str(receipt_path.relative_to(ROOT)), 'sha256': args.apply_sha256}
        case('receipt_model_sql_binding', True, {'commit': receipt['plan']['git']['commit'], 'migrations': migrations})
        import psycopg
        conn = psycopg.connect(host=HOST, port=5432, dbname=DB, user=ROLE, sslmode='verify-full', sslrootcert=str(CA),
            connect_timeout=7, autocommit=True, application_name='orion-pro-independent-readback',
            options='-c default_transaction_read_only=on -c statement_timeout=8000 -c lock_timeout=1000 -c idle_in_transaction_session_timeout=15000')
        with conn.transaction():
            conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
            identity = query('identity', "SELECT current_database() AS database,current_user AS role,current_setting('transaction_read_only') AS read_only,current_setting('transaction_isolation') AS isolation,(SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()) AS ssl")[0]
            case('readonly_tls_engine_identity', identity == {'database': DB, 'role': ROLE, 'read_only': 'on', 'isolation': 'repeatable read', 'ssl': True} and conn.info.server_version == 180006, {**identity, 'serverVersion': conn.info.server_version})
            relations = query('relations', "SELECT n.nspname||'.'||c.relname AS relation,c.relkind,CASE WHEN c.relkind IN ('r','p') THEN pg_total_relation_size(c.oid) ELSE 0 END AS bytes FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname=ANY(%s) AND c.relkind IN ('r','p','v','S') ORDER BY 1", (SCHEMAS,))
            actual_tables = {r['relation'] for r in relations if r['relkind'] in {'r','p'}}
            columns = query('columns', "SELECT n.nspname||'.'||c.relname AS relation,a.attname AS name,format_type(a.atttypid,a.atttypmod) AS type,NOT a.attnotnull AS nullable FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname=ANY(%s) AND c.relkind IN ('r','p') AND a.attnum>0 AND NOT a.attisdropped ORDER BY 1,a.attnum", (SCHEMAS,))
            expected_columns = {(name, c): ({'timestamptz':'timestamp with time zone'}.get(v['type'], v['type']).replace(', ', ','), v['nullable']) for name,t in tables.items() for c,v in t['columns'].items()}
            got_columns = {(r['relation'],r['name']): (r['type'].replace(', ', ','),r['nullable']) for r in columns}
            case('exact_tables_columns_types_nullability', actual_tables == set(tables) and got_columns == expected_columns,
                 {'tables':len(actual_tables), 'columns':len(columns), 'missingTables':sorted(set(tables)-actual_tables), 'extraTables':sorted(actual_tables-set(tables)), 'columnDifferences':sorted(str(k) for k in set(got_columns)|set(expected_columns) if got_columns.get(k) != expected_columns.get(k))})
            constraints = query('constraints', "SELECT n.nspname||'.'||c.relname AS relation,con.conname AS name,con.contype AS kind,con.convalidated AS validated,ARRAY(SELECT a.attname FROM unnest(con.conkey) WITH ORDINALITY u(k,o) JOIN pg_attribute a ON a.attrelid=con.conrelid AND a.attnum=u.k ORDER BY u.o) AS columns,CASE WHEN con.confrelid<>0 THEN (SELECT ns.nspname||'.'||cl.relname FROM pg_class cl JOIN pg_namespace ns ON ns.oid=cl.relnamespace WHERE cl.oid=con.confrelid) END AS parent,ARRAY(SELECT a.attname FROM unnest(con.confkey) WITH ORDINALITY u(k,o) JOIN pg_attribute a ON a.attrelid=con.confrelid AND a.attnum=u.k ORDER BY u.o) AS parent_columns FROM pg_constraint con JOIN pg_class c ON c.oid=con.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname=ANY(%s) AND con.contype IN ('p','f','u','c') ORDER BY 1,2", (SCHEMAS,))
            expected_constraints = {}
            for name,t in tables.items():
                expected_constraints[(name,t['primary_key']['name'])] = ('p',tuple(t['primary_key']['columns']),None,())
                for kind,key in [('u','unique_constraints'),('f','foreign_keys'),('c','checks')]:
                    for item in t[key]:
                        ref = item.get('references', {})
                        expected_constraints[(name,item['name'])] = (kind,tuple(item.get('columns',[])) if kind!='c' else (),ref.get('table'),tuple(ref.get('columns',[])))
            got_constraints = {(r['relation'],r['name']): (r['kind'],tuple(r['columns']) if r['kind']!='c' else (),r['parent'],tuple(r['parent_columns'])) for r in constraints}
            case('exact_primary_foreign_unique_checks', got_constraints == expected_constraints and all(r['validated'] for r in constraints),
                 {'counts':{k:sum(r['kind']==k for r in constraints) for k in ('p','f','u','c')}, 'differences':sorted(str(k) for k in set(got_constraints)|set(expected_constraints) if got_constraints.get(k)!=expected_constraints.get(k)), 'unvalidated':sum(not r['validated'] for r in constraints)})
            indexes = query('indexes', "SELECT n.nspname||'.'||c.relname AS relation,i.relname AS name,x.indisvalid AND x.indisready AS valid FROM pg_index x JOIN pg_class c ON c.oid=x.indrelid JOIN pg_class i ON i.oid=x.indexrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname=ANY(%s) ORDER BY 1,2", (SCHEMAS,))
            expected_indexes = {(name,i['name']) for name,t in tables.items() for i in t['indexes']}
            got_indexes = {(r['relation'],r['name']) for r in indexes if r['valid']}
            case('declared_indexes_valid', expected_indexes <= got_indexes and all(r['valid'] for r in indexes), {'declared':len(expected_indexes),'actualIncludingConstraintIndexes':len(indexes),'missing':sorted(expected_indexes-got_indexes)})
            guards = query('functions_triggers', "SELECT 'function' AS kind,n.nspname||'.'||p.proname AS name,p.prosecdef AS safe,p.proconfig AS settings FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname=ANY(%s) UNION ALL SELECT 'trigger',n.nspname||'.'||c.relname||'.'||t.tgname,t.tgenabled='O',NULL::text[] FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname=ANY(%s) AND NOT t.tgisinternal ORDER BY 1,2", (SCHEMAS,SCHEMAS))
            sql = (ROOT/'dashboard/backend/migrations/013_orion_pro_integrity.sql').read_text()
            expected_guards = {('function',s+'.'+n) for s,n in re.findall(r'CREATE OR REPLACE FUNCTION "([^"]+)"\."([^"]+)"',sql)}
            expected_guards |= {('trigger',s+'.'+t+'.'+n) for n,s,t in re.findall(r'CREATE(?: CONSTRAINT)? TRIGGER "([^"]+)" [^\n]* ON "([^"]+)"\."([^"]+)"',sql)}
            case('integrity_guards_enabled_and_fixed_path', {(g['kind'],g['name']) for g in guards} == expected_guards and all(g['safe'] and (g['kind']=='trigger' or g['settings']==['search_path=pg_catalog']) for g in guards), {'functions':sum(g['kind']=='function' for g in guards),'triggers':sum(g['kind']=='trigger' for g in guards),'expected':len(expected_guards)})
            journal = query('journal','SELECT version,content_sha256,code_commit FROM ingest.schema_migrations ORDER BY version')
            snapshots = query('bootstrap_snapshot','SELECT snapshot_key,generation,status,manifest_sha256 FROM ingest.dataset_snapshots ORDER BY generation')
            bootstrap = receipt['apply']['bootstrap']; bundle = {'model':sha(SPEC),'migrator':sha(ROOT/'dashboard/scripts/orion_pro_migrate.py'),'migrations':migrations}
            code_hash = hashed(bundle); manifest_hash = hashed({'bootstrap':model['seed_data'],'artifact':code_hash})
            seeds = query('seeds', 'SELECT relation,row FROM ('+' UNION ALL '.join(f"SELECT '{name}'::text AS relation,to_jsonb(t) AS row FROM {name} t" for name in model['seed_data'])+') s ORDER BY relation,row->>\'code\'')
            seed_ok = len(seeds)==sum(map(len,model['seed_data'].values()))
            if len(snapshots)!=1:
                seed_ok=False
            else:
                for name, templates in model['seed_data'].items():
                    rows={r['row']['code']:r['row'] for r in seeds if r['relation']==name}
                    for seed in templates:
                        row=rows.get(seed['code'],{})
                        seed_ok = seed_ok and all(row.get(k)==v for k,v in seed.items()) and row.get('recorded_from_gen')==snapshots[0]['generation'] and row.get('transform_code_sha256')==code_hash
            contracts = query('contracts','SELECT relation_code,relation_name,contract_version,grain_definition FROM ingest.relation_contracts ORDER BY relation_name,contract_version')
            expected_snapshot = {'snapshot_key':'bootstrap-v1-'+sha(SPEC)[:16], 'generation':bootstrap['generation'], 'status':'sealed', 'manifest_sha256':manifest_hash}
            case('journal_seed_generation_and_code_binding', {r['version']:r['content_sha256'] for r in journal}==migrations and len(journal)==2 and all(r['code_commit']==receipt['plan']['git']['commit'] for r in journal) and snapshots==[expected_snapshot] and seed_ok and contracts==sorted(model['bootstrap']['relation_contracts'],key=lambda r:(r['relation_name'],r['contract_version'])), {'journal':journal,'snapshots':snapshots,'seedRows':len(seeds),'artifactSha256':code_hash,'manifestSha256':manifest_hash,'contracts':len(contracts)})
            allowed = {'ingest.schema_migrations','ingest.dataset_snapshots','ingest.relation_contracts',*model['seed_data']}
            populated = query('nonbootstrap_scope','SELECT * FROM ('+' UNION ALL '.join(f"SELECT '{name}'::text AS relation WHERE EXISTS(SELECT 1 FROM {name} LIMIT 1)" for name in sorted(set(tables)-allowed))+') x')
            case('bootstrap_only_no_business_data', not populated, populated)
            privileges = query('runtime_effective_privileges', "SELECT 'table' AS kind,n.nspname||'.'||c.relname AS name,has_table_privilege(%s,c.oid,'SELECT') AS readable,has_table_privilege(%s,c.oid,'INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER') AS writable FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname=ANY(%s) AND c.relkind IN ('r','p','v') UNION ALL SELECT 'function',n.nspname||'.'||p.proname,has_function_privilege(%s,p.oid,'EXECUTE'),false FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname=ANY(%s) UNION ALL SELECT 'sequence',n.nspname||'.'||c.relname,false,CASE WHEN c.relkind='S' THEN has_sequence_privilege(%s,c.oid,'USAGE,SELECT,UPDATE') ELSE false END FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname=ANY(%s) AND c.relkind='S' ORDER BY 1,2", (WEB,WEB,SCHEMAS,WEB,SCHEMAS,WEB,SCHEMAS))
            bad_privileges=[r for r in privileges if r['writable'] or (r['kind']=='table' and not r['readable']) or (r['kind']=='function' and r['readable'] != (r['name']=='ingest.selected_at'))]
            case('runtime_readonly_effective_grants', not bad_privileges, {'relationsAndHelpers':len(privileges),'violations':bad_privileges})
            schema_access = query('runtime_schema_access', "SELECT nspname AS schema,has_schema_privilege(%s,oid,'USAGE') AS usable,has_schema_privilege(%s,oid,'CREATE') AS creatable FROM pg_namespace WHERE nspname=ANY(%s) ORDER BY 1", (WEB,WEB,SCHEMAS))
            case('runtime_schema_usage_without_create', len(schema_access)==3 and all(r['usable'] and not r['creatable'] for r in schema_access), schema_access)
            source_meta = query('retained_source_schema_metadata', "SELECT n.nspname AS schema,count(*) FILTER(WHERE c.relkind IN ('r','p')) AS tables,coalesce(sum(s.n_live_tup),0) AS estimated_rows FROM pg_namespace n LEFT JOIN pg_class c ON c.relnamespace=n.oid LEFT JOIN pg_stat_user_tables s ON s.relid=c.oid WHERE n.nspname IN ('statarena','statarena_app') GROUP BY 1 ORDER BY 1")
            case('legacy_source_namespaces_retained', {r['schema'] for r in source_meta}=={'statarena','statarena_app'} and all(r['tables']>0 for r in source_meta), {'metadataOnly':source_meta,'estimatesOnly':True})
            report['newRelationBytes'] = sum(r['bytes'] for r in relations)
            report['newRelationStorageMeaning'] = 'Additive schema/bootstrap overhead, including indexes; not a storage saving'
    except Exception as exc:
        report['error']={'type':type(exc).__name__,'sqlstate':getattr(exc,'sqlstate',None)}
        if isinstance(exc,ValueError):report['error']['reason']=str(exc)
    finally:
        if conn is not None:conn.close()
        report['cleanup']={'connectionClosed':conn is None or conn.closed}
        report['finishedAt']=datetime.now(timezone.utc).isoformat()
        report['status']='pass' if len(report['cases'])==11 and all(c['status']=='pass' for c in report['cases']) and 'error' not in report else 'fail'
        (run/'result.json').write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps({'status':report['status'],'cases':{s:sum(c['status']==s for c in report['cases']) for s in ('pass','fail')},'receipt':str((run/'result.json').relative_to(ROOT)),'receiptSha256':sha(run/'result.json')}))
    return 0 if report['status']=='pass' else 1


if __name__=='__main__':
    raise SystemExit(main())
