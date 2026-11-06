"""Check the production-free relational CI definition before and after wiring."""
from pathlib import Path
import json, sys
import yaml
from fnmatch import fnmatchcase
here=Path(__file__).resolve().parent; root=here.parents[2]; phase=sys.argv[1]
raw=(root/'.github/workflows/verify-ingestion.yml').read_text()
workflow=yaml.safe_load(raw); job=workflow.get('jobs',{}).get('relational',{}); steps=job.get('steps',[])
commands='\n'.join(step.get('run','') for step in steps); env=job.get('env',{})
events=workflow.get('on',workflow.get(True,{}))
required_paths=('dashboard/backend/aws-app.js','dashboard/frontend/src/services/football-client.js',
                'dashboard/frontend/src/season_data.js','tests/retire_models_postgres.py')
def covered(event, path):
    patterns=events.get(event,{}).get('paths',[])
    return any(not pattern.startswith('!') and fnmatchcase(path,pattern) for pattern in patterns) and not any(
        pattern.startswith('!') and fnmatchcase(path,pattern[1:]) for pattern in patterns)
checks={
  'disposable database installed in explicit tool directory':any(s.get('working-directory')=='/tmp/statarena-cache-test-tools' and 'embedded-postgres@18.6.0-beta.19' in s.get('run','') for s in steps),
  'Bun and Node pinned':any(s.get('with',{}).get('bun-version')=='1.4.4' for s in steps) and any(str(s.get('with',{}).get('node-version'))=='24' for s in steps),
  'frozen dashboard dependencies':'bun install --frozen-lockfile' in commands,
  'real publisher entry point':'aws-rematerialize-20261104/run.mjs ci' in commands,
  'core normalizer and API': 'verify_relational_core.mjs' in commands and str(env.get('STATARENA_CORE_API'))=='1',
  'captured API families':all(f'capture_ci.py {family}' in commands for family in ('match','support','catalog')),
  'fresh receipts uploaded on failure':any(s.get('if')=='always()' and 'upload-artifact' in s.get('uses','') for s in steps),
  'production authority absent':bool(job) and 'id-token' not in job.get('permissions',{}) and 'secrets.' not in str(job) and '/aws-database' not in ' '.join(s.get('uses','') for s in steps),
  'service/loader paths trigger both events':all(covered(event,path) for event in ('push','pull_request') for path in required_paths),
}
report={'rerun':f'python3 docs/verification/aws-actions-20261104/ci_contract.py {phase}','checks':checks,'passed':sum(checks.values()),'total':len(checks)}
(here/f'{phase}.json').write_text(json.dumps(report,indent=2)+'\n');print(report['passed'],'/',report['total'])
sys.exit(not all(checks.values()))
