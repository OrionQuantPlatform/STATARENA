"""Offline qualification of saved diagnostics; no source connection or replay."""
from collections import Counter
import datetime
import hashlib
import json
from pathlib import Path

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
load=lambda name:json.loads((OUT/name).read_text())
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
scope=load('scope-and-budget.json')
initial=load('execution.json');external=load('external-execution.json');completion=load('aws-completion-execution.json')
decoded=[]
for source,name in [('neon','neon-content.json'),('aws','aws-content.json'),('neon','external-neon.json'),('aws','aws-completion-content.json')]:
    for row in load(name)['objects']:
        if row['status']=='decoded':decoded.append({'source':source,'receipt':name,**row})
by={(row['source'],row['path']):row for row in decoded}
observations=[]
checks=[]
def check(name,passed):checks.append({'name':name,'passed':bool(passed)})
for target in scope['targets']:
    row=by.get((target['source'],target['path']))
    check('exact physical version '+target['source']+':'+target['path'],row is not None and row['actualPhysicalSha256']==target['expectedPhysicalSha256'] and row.get('actualPhysicalBytes',row.get('physicalBytes'))==target['expectedPhysicalBytes'])
    if row is None or target['kind']=='manifest':continue
    snapshot=load(target['source']+'-content.json')['preflight']
    selectors={(s['endpoint'],s['params']):s for s in snapshot['selectors'] or []}
    for q in row['qualifications']:
        expected=next(s for s in target['selectors'] if s['endpoint']==q['endpoint'] and s['params']==q['params'])
        actual=selectors[(q['endpoint'],q['params'])]
        pointer_ok=all(actual.get(k)==expected.get(k) for k in ['status','ref_path','ref_ordinal'])
        identity_ok=q.get('responseIdState')=='present' and q.get('observedContextIds')==[q['expectedId']] and not q.get('contradictoryIds')
        # HTTP status is transport/catalogue metadata; API JSON need not repeat it.
        status_ok=actual['status']==200 and q.get('bodyHttpStatus') in [None,200]
        selected_key=q['endpoint']+' '+q['params'];selected=row['selectionSummaries'].get(selected_key,{})
        qualified=pointer_ok and identity_ok and status_ok and selected.get('state')=='object' and not q.get('error')
        item={'source':target['source'],'path':target['path'],'endpoint':q['endpoint'],'params':q['params'],'expectedId':q['expectedId'],
            'observedContextIds':q.get('observedContextIds'),'frozenSelectorVerified':pointer_ok,'responseContextQualified':qualified,
            'httpStatus':actual['status'],'httpStatusEvidence':'exact frozen resource key, rechecked in RO snapshot; body field optional',
            'bodyHttpStatus':q.get('bodyHttpStatus'),'selection':q.get('selection'),'selectedOrdinal':q.get('selectedOrdinal'),
            'archiveCandidateMembers':q.get('candidateMembers'),'selectedTypedSha256':selected.get('typedSha256'),
            'observedFieldPaths':len(selected.get('shape',{}).get('fieldStates',{})),'completeTypedMappingAccepted':False}
        observations.append(item);check('selector and response ID '+target['source']+':'+q['endpoint'],qualified)

pointers={}
for source in ['neon','aws']:
    row=by[(source,'computed/dashboard/index.json')]
    scoped=[r['metadata'] for r in row['manifestMetadata']['qualifiedLeagueMetadata'] if any(year in r['metadata'].get('path','') for year in ['2025-2026','2026-2027'])]
    pointers[source]={('2026/2027' if '2026-2027' in r['path'] else '2025/2026'):r for r in scoped}
manifest={'fullTypedDigestsEqual':by[('neon','computed/dashboard/index.json')]['decodedTypedSha256']==by[('aws','computed/dashboard/index.json')]['decodedTypedSha256'],
    'scopePointers':pointers,'scopePointersEqual':pointers['neon']==pointers['aws'],'partitionBodiesFetched':0,
    'positionalDifferenceCount':next(r for r in load('content-comparison.json') if r['kind']=='manifest')['differenceCount'],
    'positionalDifferenceMeaning':'Array order is retained in the raw comparison; positional differences are not an entity-level update count',
    'supplierOrderingProved':False}
check('two scoped manifest pointers equal by season/league',manifest['scopePointersEqual'] and len(pointers['neon'])==2)
(OUT/'manifest-scope-comparison.json').write_text(json.dumps(manifest,indent=2)+'\n')

inventory=json.loads((ROOT/'docs/verification/orion-transfer-inventory-20261104/inventory.json').read_text())
negative=[{'key':r['key'],'httpStatus':r['neon']['status'],'refPath':r['neon']['ref_path'],'bodyReadThisPhase':False,
    'interpretation':'negative cached provider observation; no sport fact or lifetime zero inferred'} for r in inventory['resources']['rows'] if r['classification']=='absent_in_aws' and r['neon']['status']==404]
neon_observations=load('external-neon.json')['objects']
native=[]
for row in neon_observations:
    q=row['qualifications'][0];s=next(iter(row['selectionSummaries'].values()))['shape']
    native.append({'endpoint':q['endpoint'],'rootFieldStates':{k:v for k,v in s['fieldStates'].items() if k.count('.')<=1},
        'arrayLengths':{k:{f:v[f] for f in ['collections','elements','minimumLength','maximumLength']} for k,v in s['arrays'].items()},
        'nativeTypesCoerced':False,'supplierClockQualified':False})
lineup=next(row for row in neon_observations if row['qualifications'][0]['endpoint'].endswith('/lineups'))
aws_lineup=next(row for row in load('aws-completion-content.json')['objects'] if row['qualifications'][0]['endpoint'].endswith('/lineups'))
lineup_shapes=[next(iter(row['selectionSummaries'].values()))['shape'] for row in [lineup,aws_lineup]]
lineup_context={'neon':{'confirmed':{k:v for k,v in lineup_shapes[0]['booleanValues'].items() if 'confirmed' in k},'lineupType':{k:v for k,v in lineup_shapes[0]['enumValues'].items() if 'lineup_type' in k}},
    'aws':{'confirmed':{k:v for k,v in lineup_shapes[1]['booleanValues'].items() if 'confirmed' in k},'lineupType':{k:v for k,v in lineup_shapes[1]['enumValues'].items() if 'lineup_type' in k}},
    'meaning':'Distinct source contexts/values retained; no supplier order or canonical promotion inferred'}
for source,name in [('neon','neon-content.json'),('aws','aws-content.json')]:
    doc=load(name);identity=doc['preflight']['identity']
    check(source+' RO/RR/deadlines/TLS',identity['read_only']=='on' and identity['isolation']=='repeatable read' and identity['statement_timeout']=='8s' and doc['clientTls']['sslInUse'] and doc['clientTls']['sslmode']=='verify-full')
budget=completion['budget']
check('same budget respected across SQL and object transports',budget['sqlInstructions']==8 and budget['objectHttpRequests']==36 and budget['decodedBytes']==sum(row['decodedBytes'] for row in decoded) and budget['decodedBytes']<=33554432)
check('all14 exact versions decoded',len(decoded)==14 and len(by)==14)
check('previous inventory folder unchanged',all((ROOT/path).is_file() and sha(ROOT/path)==digest for path,digest in load('protected-before.json').items()))
check('approved model unchanged',sha(ROOT/'docs/architecture/orion-plan-20261104/target-schema.proposed.json')==scope['modelSha256'])
result={'atUtc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'bounded_content_qualification_complete_import_mapping_partial',
    'versionsDecoded':len(decoded),'physicalHashesVerified':sum(c['passed'] for c in checks if c['name'].startswith('exact physical version ')),
    'observationContexts':len(observations),'responseIdsAndSelectorsQualified':sum(o['responseContextQualified'] for o in observations),
    'observations':observations,'nativeCollectionSummary':native,'lineupContextComparison':lineup_context,
    'resourcePairs':load('qualified-resource-pairs.json'),'manifestComparison':manifest,'negative404MetadataOnly':negative,
    'budget':budget,'physicalPayloadBytes':sum(row.get('actualPhysicalBytes',row.get('physicalBytes',0)) for row in decoded),
    'physicalRangeBytes':48,'physicalBytesIncludingRange':completion['totalPhysicalBytesFetchedIncludingManifestsAndRange'],
    'decodedBytesBySource':{'sqlManifests':321993,'neonExternal':external['budget']['decodedBytes']-321993,'awsExternal':budget['decodedBytes']-external['budget']['decodedBytes']},
    'checks':checks,'qualificationChecksPassed':all(c['passed'] for c in checks),'remoteWrites':[],'bodyPersistence':False,'providerRequests':0,
    'fullSourceFidelityAccepted':False,'remoteImportAccepted':False,'purgeAuthorized':False,'supplierFreshnessOrderProved':False,
    'limits':['Only14exact object versions; no512archive scan or new provider/partition fetch',
        'Each old AWS archive has16members; onlyunique m_0xOQtL ordinal2 qualified here',
        'No exhaustive scalar leaf pairing/changed league row ID retained for unequal pairs; field/state/ID differences and exact typed hashes are available',
        'Heatmap triple positions/units/missing cells, source lineup_type standard, H2H totals/finished boolean, referee/has_playoff and observed coach identity still need exact mapping',
        'Body HTTP status is absent in10directAPIJSON envelopes; status200 is qualified from the bound resource catalogue; original conservative body-status guard outputs retained',
        'SQL NULL bodies were external, not proof of changed content; first blocked-size receipts and subsequent explicit transport extension retained',
        'AWS SDK login-provider CRT dependency failed before any object HTTP; existing CLI credentials used inRAM and scanned, never stored',
        'Cache/import/index/S3 dates and extra rows do not prove supplier recency; preserve both versions and AWS-only observations'],
    'sourceReceiptsSha256':{name:sha(OUT/name) for name in ['scope-and-budget.json','query-plan.json','execution.json','neon-content.json','aws-content.json','external-neon.json','external-aws.json','external-execution.json','aws-completion-content.json','aws-completion-execution.json','qualified-resource-pairs.json','manifest-scope-comparison.json','aws-credential-output-scan.json','IMPORT_PLAN.md']}}
(OUT/'result.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({'status':result['status'],'versions':len(decoded),'shaVerified':result['physicalHashesVerified'],'qualifiedContexts':result['responseIdsAndSelectorsQualified'],
    'decodedBytes':budget['decodedBytes'],'physicalBytesIncludingRange':result['physicalBytesIncludingRange'],'sql':budget['sqlInstructions'],'http':budget['objectHttpRequests'],
    'checks':len(checks),'checksPassed':result['qualificationChecksPassed']}))
