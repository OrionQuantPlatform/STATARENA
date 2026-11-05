import json,os,pathlib,subprocess,sys,tempfile,time
META=pathlib.Path('/Users/lemonnierhugo/Desktop/Coding Project/Football_ranking/docs/verification/orion-real-supervision-20261105/fault-runs/20261105T010838592206Z-final-owned-scope-faults/exited_parent_pipe_holder/fixture-owned.json')
proc=subprocess.Popen([sys.executable,'-c','import time;time.sleep(10)'],close_fds=False)
META.write_text(json.dumps({'holderPid':proc.pid,'group':os.getpgrp(),'uid':os.getuid()}))
