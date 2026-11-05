#!/usr/bin/env python3
"""Static pre-campaign inventory only: no driver import, PG or product execution."""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
WRITER = ROOT / 'dashboard/scripts/orion_pro_bulk_stream_v2.py'
E2E = ROOT / 'tests/orion_pro_bulk_stream_v2_local.py'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read(path):
    return json.loads(path.read_text())

def main():
    result = {'kind': 'stream_v2_static_preparation_only', 'atUtc': datetime.now(timezone.utc).isoformat(),
              'command': 'python3 docs/verification/orion-pro-bulk-stream-v2-local-20261105/inspect_preparation.py',
              'cases': [], 'pgStarts': 0, 'connections': 0, 'runtimeTransportVerified': False, 'fullAcceptance': False}
    def check(name, predicate, actual):
        result['cases'].append({'case': name, 'status': 'pass' if predicate else 'fail', 'actual': actual})
    writer, e2e = ast.parse(WRITER.read_text()), ast.parse(E2E.read_text())
    cls = next(n for n in writer.body if isinstance(n, ast.ClassDef) and n.name == 'Stream')
    methods = {n.name: n for n in cls.body if isinstance(n, ast.FunctionDef)}
    check('ast_and_complete_class_scope', len(methods) == 28 and next(n.lineno for n in writer.body if isinstance(n, ast.FunctionDef) and n.name == 'main') > cls.end_lineno,
          {'methods': len(methods), 'writerLines': len(WRITER.read_text().splitlines()), 'e2eLines': len(E2E.read_text().splitlines())})
    binding = read(BASE / 'BINDINGS.json')
    pins = {path: sha(ROOT / path) == value for path, value in binding['inputs'].items()}
    check('frozen_dependencies', all(pins.values()), {'matched': sum(pins.values()), 'total': len(pins), 'paths': pins})
    model = read(ROOT / 'docs/architecture/orion-plan-20261104/target-schema.proposed.json')
    all_tables = [t for s in model['schemas'] for t in s['tables']]
    tables = {t['qualified_name']: t for t in all_tables if t['phase'] != 'models'}
    counts = lambda ts: [len(ts), sum(len(t['columns']) for t in ts), sum(len(t['foreign_keys']) for t in ts)]
    check('closed_model_counts', counts(all_tables) == [103,1791,450] and counts(list(tables.values())) == [94,1709,431],
          {'model': counts(all_tables), 'active': counts(list(tables.values()))})
    matrix = read(ROOT / 'docs/verification/orion-pro-bulk-stream-v2-20261105/OWNERSHIP_MATRIX.json')
    order = {name: i for i, name in enumerate(matrix['interTableDependencyOrder'])}
    check('physical_primary_keys_and_intertable_order', all(not t['columns'][c]['nullable'] for t in tables.values() for c in t['primary_key']['columns']) and
          all(fk['references']['table'] == name or order[fk['references']['table']] < order[name] for name, t in tables.items() for fk in t['foreign_keys']),
          {'relations': len(order), 'copy': len(matrix['copiedRelations']), 'controls': len(matrix['regeneratedControlRelations']), 'empty': len(matrix['mustBeEmptyRelations'])})
    components = {('ingest.dataset_snapshots','id'): 'snapshot', ('ingest.dataset_snapshots','generation'): 'generation'}
    changed = True
    while changed:
        changed = False
        for name, table in tables.items():
            for fk in table['foreign_keys']:
                for col, parent in zip(fk['columns'], fk['references']['columns']):
                    kind = components.get((fk['references']['table'], parent))
                    if kind and (name, col) not in components:
                        components[name, col] = kind
                        changed = True
    check('control_component_closure', len(components) == 106 and components.get(('football.match_h2h_entries','recorded_from_gen')) == 'generation' and ('football.standing_rows','snapshot_id') not in components,
          {'components': len(components), 'h2hGeneration': components.get(('football.match_h2h_entries','recorded_from_gen')), 'standingSnapshotBusinessIdUnmapped': ('football.standing_rows','snapshot_id') not in components})
    self_tables = [name for name,t in tables.items() if any(fk['references']['table'] == name for fk in t['foreign_keys'])]
    check('three_self_graphs', sorted(self_tables) == ['football.competition_stages','football.metric_definitions','ingest.sources'], self_tables)
    connection = next(n for n in writer.body if isinstance(n, ast.FunctionDef) and n.name == 'connect')
    calls = [n for n in ast.walk(connection) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr == 'connect']
    keywords = {k.arg: ast.literal_eval(k.value) for k in calls[0].keywords if isinstance(k.value,ast.Constant)}
    check('literal_owned_route_before_connect', keywords.get('host') == keywords.get('hostaddr') == '127.0.0.1' and keywords.get('connect_timeout') == 8,
          {'host': keywords.get('host'), 'hostaddr': keywords.get('hostaddr'), 'connectTimeout': keywords.get('connect_timeout')})
    strings = [n.value for n in ast.walk(writer) if isinstance(n,ast.Constant) and isinstance(n.value,str)]
    forbidden = [s for s in strings if re.search(r'(?i)\b(?:CREATE|ALTER|DROP|TRUNCATE|DELETE)\s+(?:TABLE|FUNCTION|SCHEMA|INDEX|ROLE|VIEW|FROM)\b|DISABLE\s+TRIGGER|session_replication_role|\bsetval\(', s)]
    calls_all = [n.func.attr for n in ast.walk(writer) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)]
    check('copy_native_no_schema_or_fact_adapter', not forbidden and 'write_row' not in calls_all and 'copy' in calls_all,
          {'forbiddenSqlLiterals': len(forbidden), 'writeRowCalls': calls_all.count('write_row'), 'copyCallSites': calls_all.count('copy')})
    manifests = [ROOT / p for p in binding['inputs'] if 'schema-policies' in p and 'membership-nonnull' in p]
    manifest = read(manifests[0])
    check('current_guard_pair_not_historical_compatibility', sha(manifests[0]) == binding['policyManifestSha256'] and manifest['qualifiedImportPairs'] == [] and manifest['scope'] == 'validator_policy_local_adoption_014',
          {'manifestSha256': sha(manifests[0]), 'oracleSha256': binding['policyOracleSha256'], 'oldQualifiedImportPairs': manifest['qualifiedImportPairs'], 'sourceDescriptor': binding['sourceDescriptor'], 'targetDescriptor': binding['targetDescriptor']})
    roots = sorted([str(i) for i in range(3,1011)] + ['2000'])
    check('compact_cross_batch_self_dag_shape', len(roots) + 1 == 1010 and roots.index('2000') < 1000 and 2000 not in list(range(2,1002)) and 'selfCopyWindows' in E2E.read_text() and "parent_window['copyCommand']<child_window['copyCommand']" in E2E.read_text(),
          {'compactStages': 1010, 'stageParentRevision': 2000, 'stageChildRevision': 2, 'parentTopologicalRank': roots.index('2000'), 'childTopologicalRank': 1009,
           'rawPkFirst1000ContainsParent': False, 'selfVerticesCompact': 1043, 'selfVerticesDense': 35, 'selfEdges': 4, 'minimumCompactStageCopyCommands': 2, 'actualCommandsUnverified': True})
    fixture = ROOT / 'tests/orion_pro_bulk_stream_local.py'
    shapes = []
    for appearances,matches,players in [(40,4,40),(15437,612,800)]:
        shape = {'APPEARANCES': appearances, 'SCALARS': appearances*31, 'MATCHES': matches, 'PLAYERS': players, 'VERSION': binding['fixtureVersion']}
        producer = {'frozenFixtureSha256': sha(fixture), 'e2eSha256': sha(E2E), 'version': binding['fixtureVersion'], 'shape': shape}
        shapes.append({'shape': shape, 'proposedSyntheticProducerSha256': hashlib.sha256(json.dumps(producer,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest(), 'actualSqlAcceptanceExists': False})
    check('synthetic_producer_not_real_source_acceptance', shapes[1]['shape']['SCALARS'] == 478547 and binding['productionOrRealSourceCompatibility'] is False, shapes)
    red = BASE / 'runs/20261105T023316177502Z-complete-e2e-missing-writer-red/result.json'
    red_body = read(red)
    check('historical_precode_red_preserved', sha(red) == '7e5b668066b0d10eccb35b1f001a9ae40e673aa0197f398e2e96e9267d19e32c' and red_body['counts'] == {'pass':0,'fail':1,'unverified':28} and red_body['cleanup']['pgStarted'] is False,
          {'receiptSha256': sha(red), 'counts': red_body['counts'], 'scope': 'Original complete E2E snapshot; later ROOT cross-batch fixture amendment explicit, not retroactive'})
    offline = read(BASE / 'offline-cli-final.json')
    check('actual_final_offline_cli_only', offline['writerSha256'] == sha(WRITER) and offline['status'] == 'offline_plan' and offline['connections'] == offline['copyCommands'] == offline['nextvalCalls'] == 0,
          {'writerSha256': offline['writerSha256'], 'connections': offline['connections'], 'copyCommands': offline['copyCommands'], 'nextvalCalls': offline['nextvalCalls']})
    check('no_campaign_release_or_pg_ledger', not (BASE / 'ROOT_CAMPAIGN_AUTHORIZATION.json').exists() and not (BASE / 'campaign.json').exists(),
          {'campaignAuthorized': False, 'pgStarts': 0, 'requested': 'One owned PG/two DB/20min, compact then one dense construction/core COPY; first unexpected failure stops'})
    result['counts'] = {s: sum(c['status'] == s for c in result['cases']) for s in ['pass','fail']}
    result['status'] = 'pass' if result['counts']['fail'] == 0 else 'fail'
    result['sourceSha256'] = {'writer': sha(WRITER), 'e2e': sha(E2E), 'bindings': sha(BASE / 'BINDINGS.json'), 'inspector': sha(Path(__file__))}
    (BASE / 'static-preparation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':result['status'], 'counts':result['counts'], 'sha256':sha(BASE / 'static-preparation.json'), 'pgStarts':0}))
    return 0 if result['status'] == 'pass' else 1

if __name__ == '__main__':
    raise SystemExit(main())
