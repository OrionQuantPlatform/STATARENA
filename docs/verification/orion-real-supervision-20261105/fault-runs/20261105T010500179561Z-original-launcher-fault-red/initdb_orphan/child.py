import json,os,pathlib,subprocess,sys,tempfile,time
META=pathlib.Path('/Users/lemonnierhugo/Desktop/Coding Project/Football_ranking/docs/verification/orion-real-supervision-20261105/fault-runs/20261105T010500179561Z-original-launcher-fault-red/initdb_orphan/fixture-owned.json')
owned=pathlib.Path(tempfile.mkdtemp(prefix='orion-pro-e2e-'))
proc=subprocess.Popen(['/tmp/statarena-cache-test-tools/node_modules/@embedded-postgres/darwin-arm64/native/bin/initdb','-D',str(owned/'data'),'--auth=trust','--no-locale','--encoding=UTF8'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
META.write_text(json.dumps({'ownedRoot':str(owned),'uid':os.getuid(),'initdbPid':proc.pid,'group':os.getpgrp()}))
time.sleep(20)
