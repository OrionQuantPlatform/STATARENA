"""Reproduce the detached patch tree and audit paths sensitive to the rebase."""
import ast,hashlib,json,os,subprocess,tempfile
from pathlib import Path
d=Path(__file__).resolve().parent
work=Path('/tmp/statarena-aws-retirement-prepared-20261104')
base='887b560bf767993c989ab0631018b16490a70cb1';old='2c4ac0c06afe9d5001c21f70bbd6bcd4a34329fb'
patch=Path('/tmp/statarena-aws-retirement-prepared-20261104.patch');origin=Path('/tmp/statarena-aws-legacy-retirement-20261104.patch')
def git(*a,env=None):return subprocess.run(['git',*a],cwd=work,check=True,capture_output=True,env=env).stdout
def sha(b):return hashlib.sha256(b).hexdigest()
def methods(content):
 return {n.name:ast.dump(n,include_attributes=False)for n in ast.parse(content).body if isinstance(n,(ast.ClassDef,ast.FunctionDef))}
rel='dashboard/scripts/relational_materialize.py'
a=methods(git('show',base+':'+rel));b=methods(git('show',':'+rel))
changed=[n for n in a if a[n]!=b.get(n)]
assert changed==['run','main'];assert set(b)-set(a)=={'collector_plan'}
paths=git('diff','--cached','--name-only',base).decode().splitlines()
protected=[p for p in git('ls-tree','-r','--name-only',base).decode().splitlines() if p.startswith(('dashboard/backend/migrations/','dashboard/backend/services/relational-','dashboard/frontend/src/','.github/workflows/')) or p in ['dashboard/scripts/relational_core.py','dashboard/backend/services/partition-wire.js','dashboard/backend/aws-app.js']]
assert not set(protected).intersection(paths)
with tempfile.TemporaryDirectory() as temp:
 env={**os.environ,'GIT_INDEX_FILE':temp+'/index'}
 git('read-tree',base,env=env)
 git('apply','--cached','--check',str(patch),env=env)
 git('apply','--cached',str(patch),env=env)
 tree=git('write-tree',env=env).decode().strip()
assert tree==git('write-tree').decode().strip()
report=dict(base=base,originalBase=old,originalPatch=str(origin),originalSha256=sha(origin.read_bytes()),reviewPatch=str(patch),reviewSha256=sha(patch.read_bytes()),bytes=patch.stat().st_size,changedPaths=len(paths),tree=tree,verifiedByApplyingToFreshIndex=True,unchangedSensitivePaths=len(protected),protectedCategories=['all SQL migrations including 007,008,009','typed runtime core, match, supporting and catalogs','wire encoding and frontend including deferred comparison','all deployed workflows','core normalizer and SQL publisher except collector-related entry point and queue runner additions'],relationalMaterializeUnchangedDefinitions=[n for n in a if n not in changed],modifiedDefinitions=changed,addedDefinition='collector_plan',sourceDDLAndDataChanges=any(p.startswith(('data/','dashboard/backend/migrations/'))for p in paths),postBaseOverlaps=sorted(set(git('diff','--name-only',old,base).decode().splitlines()).intersection(paths)))
(d/'review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k]for k in ['reviewSha256','bytes','changedPaths','tree','verifiedByApplyingToFreshIndex','postBaseOverlaps']}))
