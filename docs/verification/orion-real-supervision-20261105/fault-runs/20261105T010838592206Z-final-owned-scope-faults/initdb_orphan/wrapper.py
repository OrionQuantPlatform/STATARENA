import importlib.util,pathlib,sys
s=importlib.util.spec_from_file_location('owned_supervisor','/Users/lemonnierhugo/Desktop/Coding Project/Football_ranking/docs/verification/orion-real-supervision-20261105/supervise_real.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
m.HELPER=pathlib.Path('/Users/lemonnierhugo/Desktop/Coding Project/Football_ranking/docs/verification/orion-real-supervision-20261105/fault-runs/20261105T010838592206Z-final-owned-scope-faults/initdb_orphan/child.py')
sys.argv=['/Users/lemonnierhugo/Desktop/Coding Project/Football_ranking/docs/verification/orion-real-supervision-20261105/supervise_real.py','--run','--mode','smoke']
raise SystemExit(m.main())
