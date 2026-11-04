#!/usr/bin/env python3
"""Exact live credential-value check; never emits values, hashes or lengths."""
import datetime, gzip, json, pathlib, subprocess, urllib.parse
ROOT = pathlib.Path(__file__).resolve().parents[3]
PARAMS = ['/statarena/app/' + x for x in ('rds-runtime','rds-ingest','rds-admin','s3-runtime','s3-ingest')]
raw = subprocess.run(['aws','--profile','statarena','--region','us-east-2','ssm','get-parameters','--with-decryption','--names',*PARAMS,'--output','json'],check=True,capture_output=True,text=True)
params = json.loads(raw.stdout)
assert not params.get('InvalidParameters') and len(params['Parameters']) == len(PARAMS)
values = set()
def collect(value):
    if isinstance(value,dict):
        for key,item in value.items():
            normalized = ''.join(c for c in key.lower() if c.isalnum())
            if normalized in {'password','secretaccesskey','accesskeyid','sessiontoken','databaseurl','token'} and isinstance(item,str) and item:
                values.add(item)
            else: collect(item)
    elif isinstance(value,list):
        for item in value: collect(item)
for param in params['Parameters']: collect(json.loads(param['Value']))
assert len(values) >= 5, 'Expected credential fields not found; check key names privately'
needles = set()
for value in values:
    for variant in (value,urllib.parse.quote(value,safe=''),urllib.parse.quote_plus(value),json.dumps(value)[1:-1]):
        needles.add(variant.encode())
tracked = subprocess.run(['git','ls-files','-z','--cached','--others','--exclude-standard'],cwd=ROOT,check=True,capture_output=True).stdout.split(b'\0')
files = sorted(set(pathlib.Path(x.decode()) for x in tracked if x))
found = []; checked = 0; expanded = 0
for relative in files:
    path = ROOT / relative
    if not path.is_file(): continue
    body = path.read_bytes(); checked += 1
    contents = [body]
    if body[:2] == b'\x1f\x8b':
        contents.append(gzip.decompress(body)); expanded += 1
    if any(needle in content for content in contents for needle in needles):
        found.append(str(relative))
receipt = {'atUtc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'rerun':'python3 docs/verification/aws-release-20261104/scan_credentials.py',
           'setup':'Current SSM credentials held privately in process memory; exact raw, JSON-escaped and URL-encoded value matching across all tracked and new nonignored working-tree files, including gzip contents.',
           'expected':'No live credential value in repository content',
           'filesChecked':checked,'gzipFilesExpanded':expanded,'matchedPaths':found,'passed':not found,
           'limits':'Exact known credential scan, not a general secret scanner or a history scan. Does not print values or credential-derived hashes.'}
out = pathlib.Path(__file__).with_name('credential-scan-final.json');out.write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
raise SystemExit(bool(found))
