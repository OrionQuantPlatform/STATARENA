"""Local artifact/credential checks only; no connection, SQL or source-body replay."""
import ast
import datetime
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
now=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
failures=[];counts={'json':0,'python':0,'localLinks':0}
known=[]
for line in (ROOT/'dashboard/.env').read_text().splitlines():
    if '=' not in line or line.lstrip().startswith('#'):continue
    key,value=line.split('=',1);key=key.strip();value=value.strip().strip('"').strip("'")
    if key in {'NEON_STORAGE_ACCESS_KEY_ID','NEON_STORAGE_SECRET_ACCESS_KEY'} and len(value)>=8:known.append(value)
    if key=='NEON_DATABASE_URL':
        known.append(value)
        password=urlsplit(value).password
        if password:known.append(unquote(password))
hits=[]
patterns=[r'postgres(?:ql)?://[^\s\"\']+',r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b',r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----']
for path in sorted(OUT.rglob('*')):
    if not path.is_file():continue
    if path.suffix not in {'.json','.md','.py','.log'}:
        failures.append({'unexpectedArtifactType':str(path.relative_to(OUT))});continue
    text=path.read_text()
    if any(secret in text for secret in known) or any(re.search(pattern,text) for pattern in patterns):hits.append(str(path.relative_to(OUT)))
    if path.suffix=='.py':ast.parse(text);counts['python']+=1
    if path.suffix=='.json':json.loads(text);counts['json']+=1
    if path.suffix=='.md':
        for href in re.findall(r'\]\(([^\s)]+)\)',text):
            if not urlsplit(href).scheme:
                counts['localLinks']+=1
                if not (path.parent/href).exists():failures.append({'missingLink':str(path.relative_to(OUT))+':'+href})
scan={'atUtc':now(),'knownNeonCredentialValuesChecked':len(known),'matchingPaths':hits,'valuesPersisted':False,
    'awsExportedCredentialScan':'aws-credential-output-scan.json, known3AWS values checked while held in RAM; no values persisted',
    'passed':not hits and json.loads((OUT/'aws-credential-output-scan.json').read_text())['passed']}
(OUT/'credential-scan.json').write_text(json.dumps(scan,indent=2)+'\n')
result=json.loads((OUT/'result.json').read_text())
if not result['qualificationChecksPassed'] or not scan['passed']:failures.append({'qualificationOrCredentialCheckFailed':True})
sources=[('execution.json','read_content.py','sourceCodeSha256'),('external-execution.json','read_external.py','sourceCodeSha256'),('aws-completion-execution.json','complete_aws.py','sourceCodeSha256')]
for receipt,script,field in sources:
    if json.loads((OUT/receipt).read_text())[field]!=sha(OUT/script):failures.append({'executedSourceBytesChanged':script})
protected=json.loads((OUT/'protected-before.json').read_text())
changed=[path for path,digest in protected.items() if not (ROOT/path).is_file() or sha(ROOT/path)!=digest]
if changed:failures.append({'previousFrozenInventoryChanged':changed})
for name in ['ram-cleanup.json','external-ram-cleanup.json','aws-completion-ram-cleanup.json']:
    if json.loads((OUT/name).read_text())['bodyFilesWritten']:failures.append({'bodyFileRecorded':name})
receipt={'atUtc':now(),'scope':'Offline syntax, exact executed-source bytes, local links, frozen prior inventory, cleanup and credentials; no unit test, remote query or payload replay',
    'counts':counts,'priorInventoryProtectedFiles':len(protected),'priorInventoryChangedPaths':changed,'failures':failures,
    'credentialScanPassed':scan['passed'],'passed':not failures}
(OUT/'artifact-validation.json').write_text(json.dumps(receipt,indent=2)+'\n')
hashes={str(p.relative_to(OUT)):sha(p) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='final-hashes.json'}
(OUT/'final-hashes.json').write_text(json.dumps({'atUtc':now(),'scope':'Content phase evidence frozen; exact code/metadata only, no body files', 'files':hashes},indent=2)+'\n')
print(json.dumps({'passed':receipt['passed'],'counts':counts,'protectedPriorFiles':len(protected),'changedPriorFiles':len(changed),'credentialScanPassed':scan['passed'],'failures':failures,
    'resultSha256':hashes['result.json'],'resultsSha256':hashes['RESULTS.md'],'importPlanSha256':hashes['IMPORT_PLAN.md'],'files':len(hashes)}))
raise SystemExit(0 if receipt['passed'] else 1)
