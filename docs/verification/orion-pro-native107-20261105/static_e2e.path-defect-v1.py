#!/usr/bin/env python3
"""Pre-code, source-free model/migration workflow; no driver or network imports."""
from __future__ import annotations
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import traceback

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PROPOSAL = ROOT / 'docs/verification/orion-pro-match-details-20261104'
MODEL = ROOT / 'docs/architecture/orion-native-details-107-20261105/target-schema.approved-107.json'
PRODUCT = ROOT / 'dashboard/scripts/orion_pro_native107_schema.py'
MIGRATION = ROOT / 'dashboard/backend/migrations/016_orion_pro_native_match_details.sql'
PINS = {
    'docs/architecture/orion-plan-20261104/target-schema.proposed.json': '18da43f940870b7a3a3cb49323c847dd5e5174e5eea1f8ff0c8a159cf373cb08',
    'docs/verification/orion-pro-match-details-20261104/PROPOSED_MODEL.patch.json': 'd8626f25dff07e6f1562273bdac88fc849623065389da9c88df2e6583f62575b',
    'docs/verification/orion-pro-match-details-20261104/AMENDMENT_SPEC.json': 'd21938839a5c20853cf2f916b3230b3e06245db7da94ca1c6d6e2a4223dfa7a6',
    'docs/verification/orion-pro-match-details-20261104/target-schema.native-details.CANDIDATE.json': 'be2251bfdbf8e3253503cd2b4172f26b580994a0e3c100553f50532399da34aa',
    'dashboard/backend/migrations/012_orion_pro_domain.sql': 'f255868599c72d69f40f575a919045325ea1093a00fe4f5a6b96eae9f2c49f65',
    'dashboard/backend/migrations/013_orion_pro_integrity.sql': '85525221cad51b32aff79a777098211b4112f9f00ea7161ac93945654eeb6968',
    'dashboard/backend/migrations/014_orion_pro_membership_nonnull.sql': 'e0810f8670b2cb627ade2c76e3c8eb527ab31fd595d5cf939fd63bfc5cf649d6',
    'dashboard/backend/migrations/015_orion_pro_metric_membership_guard.sql': '3b85fcb4fe9380cc5f96238620ff3f4bedee7485ed52c98fef0bddfac1092bd7',
    'dashboard/scripts/orion_pro_schema.py': '6f4578b10c2344885bbf79ab0853fe0f0fd7fffa0663ee74600f5c6ebbe544c3',
    'dashboard/scripts/orion_pro_integrity.py': '32aa1c84cbf3900b28fe2c1e186e4ba56695f83aeea17d5d1336882fec9aae85',
    'dashboard/scripts/orion_pro_publish.py': '222c4647a850eb3fe51dcc8c9ba71e35dafbfe28f69443c558675ebcca8faf59',
    'dashboard/scripts/orion_pro_admit_real.py': '0030eae7d08464ef3b9ebfdfe6485ab8db8aa1b1c732bf1d4629ce301b404fd0',
    'dashboard/scripts/orion_pro_publish_real.py': '6b6cd2ffd380d298429744a94cb0f587c653a990579518af2af4f2b90c80e38c',
    'dashboard/backend/services/orionPro.js': '4815cdfb184fbae31fa501b50695b235c2ca14b85660db6e6aee8f5fef979616',
}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def patch_independent(base, operations):
    result = copy.deepcopy(base)
    counts = {}
    for item in operations:
        op = item['op']; counts[op] = counts.get(op, 0) + 1
        parts = [p.replace('~1', '/').replace('~0', '~') for p in item['path'].split('/')[1:]]
        parent = result
        for key in parts[:-1]:
            parent = parent[int(key)] if isinstance(parent, list) else parent[key]
        key = parts[-1]
        if isinstance(parent, list):
            if key == '-':
                assert op == 'add'; parent.append(copy.deepcopy(item['value'])); continue
            key = int(key)
        if op == 'test':
            assert parent[key] == item['value'], item['path']
        elif op == 'replace':
            assert key in parent if isinstance(parent, dict) else 0 <= key < len(parent)
            parent[key] = copy.deepcopy(item['value'])
        elif op == 'add':
            if isinstance(parent, list): parent.insert(key, copy.deepcopy(item['value']))
            else:
                assert key not in parent, item['path']; parent[key] = copy.deepcopy(item['value'])
        else: raise AssertionError('Unapproved patch operation')
    assert counts == {'test': 15, 'replace': 6, 'add': 183}, counts
    return result

def totals(model, active=False):
    tables = [t for s in model['schemas'] for t in s['tables'] if not active or t['phase'] != 'models']
    return {'tables':len(tables),'columns':sum(len(t['columns']) for t in tables),
            'foreignKeys':sum(len(t['foreign_keys']) for t in tables),
            'checks':sum(len(t['checks']) for t in tables),
            'jsonb':sum(c['type']=='jsonb' for t in tables for c in t['columns'].values())}

def input_workflow():
    observed = {p:sha(ROOT/p) for p in PINS}
    assert observed == PINS, {p:observed[p] for p in PINS if observed[p] != PINS[p]}
    approval = json.loads((PROPOSAL/'USER_APPROVAL_20261105.json').read_text())
    assert approval['approvedBy'] == 'user'
    assert approval['jsonPatchSha256'] == PINS[str((PROPOSAL/'PROPOSED_MODEL.patch.json').relative_to(ROOT))]
    base = json.loads((ROOT/next(iter(PINS))).read_text())
    structural = patch_independent(base, json.loads((PROPOSAL/'PROPOSED_MODEL.patch.json').read_text()))
    assert structural == json.loads((PROPOSAL/'target-schema.native-details.CANDIDATE.json').read_text())
    assert totals(structural) == {'tables':107,'columns':1905,'foreignKeys':466,'checks':1017,'jsonb':51}
    assert totals(structural, True) == {'tables':98,'columns':1823,'foreignKeys':447,'checks':974,'jsonb':35}
    return {'inputHashes':observed,'approvalSha256':sha(PROPOSAL/'USER_APPROVAL_20261105.json'), 'all':totals(structural),'active':totals(structural,True)}

def model_workflow():
    assert MODEL.is_file(), 'APPROVED_107_MODEL_ABSENT'
    model=json.loads(MODEL.read_text()); candidate=json.loads((PROPOSAL/'target-schema.native-details.CANDIDATE.json').read_text())
    structural=copy.deepcopy(model)
    for key in ('format_version','status','planning','selective_versioning'):structural[key]=candidate[key]
    del structural['native107_adoption']
    assert structural == candidate, 'Unrecorded model changes'
    assert model['planning']['tables']==107 and model['planning']['columns']==1905 and model['planning']['foreign_keys']==466
    assert model['planning']['version_classes']=={'selected_relations':46,'parent_version_children':10,'existing_append_only':9,'stable_identities':3}
    assert len(model['selective_versioning']['parent_version_children'])==10
    assert model['native107_adoption']['approval_sha256']==sha(PROPOSAL/'USER_APPROVAL_20261105.json')
    assert model['status']=='user_approved_native_match_details_not_deployed'
    return {'modelSha256':sha(MODEL),'all':totals(model),'active':totals(model,True)}

def generator_workflow():
    assert PRODUCT.is_file(), 'NATIVE107_GENERATOR_ABSENT'
    result=subprocess.run([sys.executable,'-I',str(PRODUCT),'--check'],cwd=ROOT,text=True,capture_output=True,timeout=10)
    assert result.returncode==0, result.stderr
    data=json.loads(result.stdout);assert data['modelSha256']==sha(MODEL)
    assert MIGRATION.is_file(), 'MIGRATION_016_ABSENT'
    assert data['migrationSha256']==sha(MIGRATION)
    return data

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run-static',action='store_true');args=parser.parse_args()
    if not args.run_static:parser.error('Explicit --run-static required; never starts PG')
    run=HERE/'static-runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');run.mkdir(parents=True)
    receipt={'kind':'native107_static_e2e_v1','command':[sys.executable,'-I',str(Path(__file__).resolve()),'--run-static'],
             'expected':'Exact immutable inputs, approved model107 materialization, deterministic016; missing product is pre-code RED',
             'cases':[],'pgConnections':0,'networkCalls':0,'sourceReads':0,'status':'running'}
    try:
        for name, action in [('N00a_inputs',input_workflow),('N00b_materialization',model_workflow),('N01_generator',generator_workflow)]:
            try:actual=action()
            except Exception as exc:
                receipt['cases'].append({'id':name,'status':'failed','error':str(exc),'traceback':traceback.format_exc()});raise
            receipt['cases'].append({'id':name,'status':'passed','actual':actual})
        receipt['status']='passed'
    except Exception:receipt['status']='failed'
    finally:
        receipt['unverified']=[n for n in ('N00a_inputs','N00b_materialization','N01_generator') if n not in {c['id'] for c in receipt['cases']}]
        receipt['cleanup']={'noOwnedServicesStarted':True};(run/'result.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':receipt['status'],'receipt':str(run/'result.json'),'sha256':sha(run/'result.json')}))
    return 0 if receipt['status']=='passed' else 1

if __name__=='__main__':raise SystemExit(main())
