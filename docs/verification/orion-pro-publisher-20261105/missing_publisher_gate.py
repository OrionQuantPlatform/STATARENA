#!/usr/bin/env python3
"""Pre-code real CLI RED only; no DB/HTTP/source or publisher execution exists."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[2]
TARGET=ROOT/'dashboard/scripts/orion_pro_publish.py'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--label',default='publisher-absent-red')
    args=parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]{0,70}',args.label):parser.error('Use a simple label')
    # This phase is deliberately scoped to an absent helper. A later existing
    # publisher is not launched without ROOT's next-stage authorization.
    if TARGET.exists():raise SystemExit('Publisher now exists; this absent-helper phase must be reviewed before execution')
    run=BASE/'runs'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-'+args.label)
    run.mkdir(parents=True)
    pinned=[ROOT/'docs/architecture/orion-plan-20261104/target-schema.proposed.json',
      ROOT/'dashboard/backend/migrations/012_orion_pro_domain.sql',ROOT/'dashboard/backend/migrations/013_orion_pro_integrity.sql',
      ROOT/'dashboard/scripts/orion_pro_normalize.py',ROOT/'dashboard/scripts/orion_pro_integrity.py',
      ROOT/'dashboard/backend/aws-app.js',ROOT/'dashboard/backend/services/orion-pro.js',
      ROOT/'docs/verification/orion-pro-readers-20261104/fixture.py',
      ROOT/'docs/verification/orion-pro-api-coverage-20261105/FINAL_CHECKSUMS.json',
      BASE/'PROTOCOL.md',BASE/'FAILURE_MATRIX.json',BASE/'LOCAL_BUDGET.md',Path(__file__)]
    before={str(p.relative_to(ROOT)):sha(p) for p in pinned}
    command=[sys.executable,'-I',str(TARGET),'--help']
    env={k:os.environ[k] for k in ['PATH','HOME','TMPDIR','USER','LANG','LC_ALL'] if k in os.environ}
    started=datetime.now(timezone.utc).isoformat()
    child=subprocess.run(command,cwd=BASE,env=env,capture_output=True,text=True,timeout=10)
    (run/'stdout.log').write_text(child.stdout);(run/'stderr.log').write_text(child.stderr)
    unchanged=all(sha(p)==before[str(p.relative_to(ROOT))] for p in pinned)
    missing=not TARGET.exists() and child.returncode==2 and 'No such file or directory' in child.stderr
    acceptance=child.returncode==0
    report={'kind':'REAL_PRECODE_CLI_GATE_NOT_PG_HTTP_E2E','case':'P00','startedAt':started,
      'command':['python3',str(Path(__file__).relative_to(ROOT)),*sys.argv[1:]],'childCommand':command,
      'workingDirectory':str(BASE),'setup':'Python isolated mode, absent target, minimal environment; no DB/HTTP/source inputs',
      'expected':{'exitCode':0,'meaning':'A publisher CLI exists and can expose help before any DB access'},
      'actual':{'exitCode':child.returncode,'targetExists':TARGET.exists(),'stdoutFile':'stdout.log','stderrFile':'stderr.log'},
      'status':'pass' if acceptance else 'fail','expectedPreCodeRedObserved':missing,
      'unexecutedWorkflowCases':[f'P{i:02d}' for i in range(1,30)],
      'sourceSha256':before,'sourceBytesUnchanged':unchanged,'no014Exists':not any((ROOT/'dashboard/backend/migrations').glob('014*')),
      'sqlExecuted':False,'postgresStarted':False,'httpStarted':False,'publisherImplemented':False,
      'sourceBodiesRead':False,'remoteActions':[],'model107Used':False,
      'cleanup':{'childExited':True,'ownedServicesStarted':0,'temporaryDatabaseCreated':False},
      'limits':['Only absent-CLI availability is exercised; no publisher/data/admission/concurrency/PG/HTTP behavior is verified.',
                'Nonzero is retained as RED, not converted into a passing publisher test.'],
      'finishedAt':datetime.now(timezone.utc).isoformat()}
    (run/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'status':report['status'],'expectedPreCodeRedObserved':missing,'receipt':str((run/'result.json').relative_to(ROOT))}))
    return 0 if acceptance and unchanged else 1


if __name__=='__main__':raise SystemExit(main())
