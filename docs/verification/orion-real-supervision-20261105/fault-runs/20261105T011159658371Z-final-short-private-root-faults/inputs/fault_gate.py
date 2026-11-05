"""Real OS process faults around the supervisor; no source, SQL or HTTP calls."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import selectors
import shlex
import shutil
import signal
import subprocess
import sys
import time

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
TARGET = BASE / 'supervise_real.py'
PG = Path('/tmp/statarena-cache-test-tools/node_modules/@embedded-postgres/darwin-arm64/native/bin/initdb')


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--label', required=True); args = parser.parse_args()
    run = BASE / 'fault-runs' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-' + args.label)
    run.mkdir(parents=True); (run / 'inputs').mkdir()
    for p in [TARGET, Path(__file__), BASE / 'PROTOCOL.md']:
        shutil.copy2(p, run / 'inputs' / p.name)
    report = {'command': [sys.executable, str(Path(__file__)), *sys.argv[1:]], 'cases': [],
              'supervisorSha256': hashlib.sha256(TARGET.read_bytes()).hexdigest(), 'sourceBodiesRead': 0,
              'sqlConnections': 0, 'remoteActions': [], 'fullAcceptance': False}
    for kind in ['initdb_orphan', 'exited_parent_pipe_holder']:
        folder = run / kind; folder.mkdir(); meta = folder / 'fixture-owned.json'
        child = folder / 'child.py'; wrapper = folder / 'wrapper.py'
        common = f"import json,os,pathlib,subprocess,sys,tempfile,time\nMETA=pathlib.Path({str(meta)!r})\n"
        if kind == 'initdb_orphan':
            code = common + f"owned=pathlib.Path(tempfile.mkdtemp(prefix='orion-pro-e2e-'))\nproc=subprocess.Popen([{str(PG)!r},'-D',str(owned/'data'),'--auth=trust','--no-locale','--encoding=UTF8'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)\nMETA.write_text(json.dumps({{'ownedRoot':str(owned),'uid':os.getuid(),'initdbPid':proc.pid,'group':os.getpgrp()}}))\ntime.sleep(20)\n"
        else:
            code = common + "proc=subprocess.Popen([sys.executable,'-c','import time;time.sleep(10)'],close_fds=False)\nMETA.write_text(json.dumps({'holderPid':proc.pid,'group':os.getpgrp(),'uid':os.getuid()}))\n"
        child.write_text(code)
        wrapper.write_text(f"import importlib.util,pathlib,sys\ns=importlib.util.spec_from_file_location('owned_supervisor',{str(TARGET)!r});m=importlib.util.module_from_spec(s);s.loader.exec_module(m)\nm.HELPER=pathlib.Path({str(child)!r})\nsys.argv=[{str(TARGET)!r},'--run','--mode','smoke']\nraise SystemExit(m.main())\n")
        env = {k: os.environ[k] for k in ['PATH', 'HOME', 'TMPDIR', 'USER', 'LANG', 'LC_ALL'] if k in os.environ}
        env['PYTHONPATH'] = '/tmp/statarena-publication-test-python'; env['PYTHONDONTWRITEBYTECODE'] = '1'
        started = time.monotonic(); killed = False; proc = subprocess.Popen([sys.executable, str(wrapper)], cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            if kind == 'initdb_orphan':
                until = time.monotonic() + 5
                while not meta.exists() and proc.poll() is None and time.monotonic() < until:time.sleep(.01)
                data = json.loads(meta.read_text()); owned = Path(data['ownedRoot'])
                assert data['uid'] == os.getuid() and owned.name.startswith('orion-pro-e2e-') and owned.is_dir() and not owned.is_symlink()
                assert not (owned / 'data/postmaster.pid').exists(), 'No postmaster is authorized in this fixture'
                os.killpg(data['group'], signal.SIGKILL); killed = True
            stdout, stderr = proc.communicate(timeout=15)
            elapsed = time.monotonic() - started
            (folder / 'stdout.log').write_bytes(stdout); (folder / 'stderr.log').write_bytes(stderr)
            final = json.loads(stdout.decode().strip().splitlines()[-1]); actual = json.loads((Path(final['evidence']) / 'result.json').read_text())
            data = json.loads(meta.read_text())
            if kind == 'initdb_orphan':
                cleaned = not Path(data['ownedRoot']).exists()
                passed = actual['status'] == 'fail' and final['cleanupVerified'] and cleaned and killed
                observation = {'ownedRoot': data['ownedRoot'], 'actualRootRemoved': cleaned, 'reportedCleanupVerified': final['cleanupVerified'], 'killedBeforePostmaster': True}
            else:
                state = subprocess.run(['ps', '-p', str(data['holderPid']), '-o', 'stat='], capture_output=True, text=True, timeout=2)
                holder_active = state.returncode == 0 and state.stdout.strip() and not state.stdout.lstrip().startswith('Z')
                passed = actual['status'] == 'fail' and elapsed < 4 and not holder_active
                observation = {'elapsedSeconds': round(elapsed, 3), 'holderStillActive': bool(holder_active), 'expectedMaximumSeconds': 4}
            report['cases'].append({'case': kind, 'status': 'pass' if passed else 'fail', 'supervisorExitCode': proc.returncode, 'actual': observation, 'outerReceipt': str(Path(final['evidence']) / 'result.json')})
        except Exception as error:
            report['cases'].append({'case': kind, 'status': 'fail', 'errorType': type(error).__name__})
        finally:
            if proc.poll() is None:proc.kill();proc.wait(timeout=3)
            if meta.exists():
                data = json.loads(meta.read_text())
                if 'ownedRoot' in data:
                    owned = Path(data['ownedRoot'])
                    if owned.exists():
                        assert owned.name.startswith('orion-pro-e2e-') and not owned.is_symlink() and owned.stat().st_uid == os.getuid() and not (owned / 'data/postmaster.pid').exists()
                        shutil.rmtree(owned)
                else:
                    try:os.killpg(data['group'], signal.SIGKILL)
                    except ProcessLookupError:pass
            report['cases'][-1]['fixtureCleanupComplete'] = True
    report['counts'] = {s: sum(c['status'] == s for c in report['cases']) for s in ['pass', 'fail']}
    report['status'] = 'pass' if report['counts'] == {'pass': 2, 'fail': 0} else 'fail'
    (run / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'status': report['status'], 'counts': report['counts'], 'evidence': str(run)}))
    return report['status'] != 'pass'


if __name__ == '__main__':raise SystemExit(main())
