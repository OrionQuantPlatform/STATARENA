"""Read-only final filesystem E2E against the reviewed deletion manifest."""
from pathlib import Path
import json,os,re
root=Path.cwd();folder=Path(__file__).resolve().parent
manifest=json.loads((folder/'delete-plan.json').read_text())
files=manifest['files'];remaining=[f['copy'] for f in files if (root/f['copy']).exists()]
extra=[]
for base,dirs,names in os.walk(root):
 dirs[:]=[d for d in dirs if d not in {'.git','node_modules','.next','.next-dev','.next-prod','output','outputs','.venv','__pycache__','.playwright-cli'}]
 for name in names:
  if re.search(r' \d+(?=\.|$)',name):extra.append(str((Path(base)/name).relative_to(root)))
prototypes={name:(root/'prototypes/accueil'/name).exists() for name in ['index.html','option-b.html','option-c.html']}
report={'setup':'Final worktree inventory; excludes Git internals, dependencies, caches and generated evidence.','command':'python3 output/playwright/page-seasons-layout-20261103/cleanup-final.py','inputs':'delete-plan.json (42 reviewed paths)','expected':'All 42 reviewed copies absent; only the unpaired WAL retained; canonical files and distinct prototypes B/C retained.','reviewed':len(files),'remainingReviewed':remaining,'otherNumbered':extra,'distinctPrototypes':prototypes,'gitRefsRecovery':'.git/codex-ref-quarantine-20261103/RESULTS.json','status':'passed' if not remaining and len(files)==42 and extra==['data/computed/pitchapi-world/queue 2.sqlite-wal'] and all(prototypes.values()) else 'failed'}
(folder/'cleanup-final.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':report['status'],'reviewed':len(files),'remaining':len(remaining),'otherNumbered':extra}));raise SystemExit(report['status']!='passed')
