#!/usr/bin/env python3
"""AST/schema/name/import preflight only; never imports the E2E or starts PG."""
import ast
import hashlib
import json
from pathlib import Path
import re

BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[3]

def main():
    model_path=ROOT/'docs/architecture/orion-plan-20261104/target-schema.proposed.json'
    assert hashlib.sha256(model_path.read_bytes()).hexdigest()=='18da43f940870b7a3a3cb49323c847dd5e5174e5eea1f8ff0c8a159cf373cb08'
    model=json.loads(model_path.read_text());tables={t['qualified_name']:t for s in model['schemas'] for t in s['tables'] if t['phase']!='models'}
    assert len(tables)==94 and sum(len(t['columns']) for t in tables.values())==1709
    checked=[];unknown=[];invalid_enums=[]
    def literals(node):
        if isinstance(node,ast.Constant):return [node.value]
        if isinstance(node,ast.IfExp):return literals(node.body)+literals(node.orelse)
        return []
    for file in sorted(BASE.glob('*.py')):
        tree=ast.parse(file.read_text(),filename=str(file))
        for node in ast.walk(tree):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr in ['_insert','_replace','_row','rows'] and node.args and isinstance(node.args[0],ast.Constant):
                table=node.args[0].value
                if not isinstance(table,str) or table not in tables:continue
                columns=tables[table]['columns'];fields=[k.arg for k in node.keywords if k.arg]
                if node.func.attr in ['_insert','_replace']:
                    unknown.extend((file.name,node.lineno,table,k) for k in fields if k not in columns)
                    for kw in node.keywords:
                        allowed=columns.get(kw.arg,{}).get('allowed_values')
                        if allowed is not None:invalid_enums.extend((file.name,node.lineno,table,kw.arg,v) for v in literals(kw.value) if v is not None and v not in allowed)
                if node.func.attr=='rows' and len(node.args)>1 and isinstance(node.args[1],ast.Constant):
                    unknown.extend((file.name,node.lineno,table,c) for c in re.findall(r'\br\.([a-z_][a-z0-9_]*)',node.args[1].value) if c not in columns)
                checked.append({'file':file.name,'line':node.lineno,'method':node.func.attr,'table':table,'fields':fields})
    assert not unknown,unknown
    assert not invalid_enums,invalid_enums
    assert 'revision_id' not in tables['ingest.match_coverage']['columns']
    assert tables['ingest.match_coverage']['primary_key']['columns']==['match_id','source_id','feature_code','variant_key','recorded_from_gen']
    assert all(re.fullmatch(r'(ingest|football|analytics)\.[a-z_][a-z0-9_]*',q) for q in tables)
    preserved=[]
    for path,want in [(BASE.parent/'THIRD_PRECODE_CHECKSUMS.json','7f0be897e84b6bc244e037dffc9de7012ddbbbfeae36cdee13b8802eb0205f47'),
                      (BASE.parent/'static-schema-review/STATIC_CHECKSUMS.json','20fd48fc3da68e03a40ca3f1d210f1946979aa04724a35deb05eb0f18ffbaa63')]:
        assert hashlib.sha256(path.read_bytes()).hexdigest()==want
        entries=json.loads(path.read_text())['sha256']
        assert all(hashlib.sha256((path.parent/n).read_bytes()).hexdigest()==h for n,h in entries.items())
        preserved.append({'manifest':str(path.relative_to(ROOT)),'entries':len(entries),'sha256':want})
    result={'kind':'STATIC_AST_SCHEMA_GATE_NOT_E2E','activeTables':94,'columns':1709,'typedSitesChecked':checked,
      'unknownColumns':unknown,'invalidLiteralEnums':invalid_enums,'preserved':preserved,'databaseStarts':0,'httpRequests':0,
      'publisherExists':(ROOT/'dashboard/scripts/orion_pro_publish.py').exists(),
      'newSourceSha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(BASE.iterdir()) if p.is_file() and p.suffix in ['.py','.mjs','.md','.json'] and p.name!='static-gate.json'}}
    assert not result['publisherExists']
    (BASE/'static-gate.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'kind':result['kind'],'typedSites':len(checked),'unknownColumns':0,'invalidEnums':0,'preservedEntries':168,'databaseStarts':0,'httpRequests':0}))

if __name__=='__main__':main()
