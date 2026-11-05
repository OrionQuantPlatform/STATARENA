# Explicit local validator overlay prepared

**11source-free workflows pass;4real workflows remain unexecuted.** RAM PID54737,
session70680/private v2socket stay alive without refetch. No cloud/source request,
new body,real import or STOP occurred. `fullAcceptance=false`.

The option accepts only the exact reviewed path and explicit file SHAe0810f...
(applied strip-text SHA30f86f...). Model18da,sealed013file and actual migration
receipt are checked. Arbitrary copy/symlink/hash/missing path/SHA refuse before
PG setup. Default sealed013 is verified against its actual baseline body hash.
Exact candidate SQL bytes are in run inputs. It is policy
local_candidate_membership_e0810f,not a migration or production default.

Fresh ownedPG18.6 bootstraps012/013,then an8s/1s local admin replaces ONLY
validate_generation(bigint) before business writes. OID,owner/OID,ACL,SECURITY
DEFINER,search_path,signature/result/language are preserved. pg_proc row SHA:
`c46d9aeb0a0e6fbba71942b465a56e0bd8456c281718f973f3488e689c54ff27` → `910e5dfb226bd92610f30725327c889fb2eaef985c23cee2cb02a2b054d4a9c8`.
Other functions and94tables/67sequences stay unchanged. The genuine fresh CLI
worker reads this same installed receipt under orion_pro_ingest at8s/1s before
RAM access; no admin replacement or source read occurs in that worker check.

The worker now parses conninfo before connect.13CLI driver-tripwire negatives
cover external/missing/empty/multiple hosts,external/multiple/incoherent/empty
hostaddr,external PGHOSTADDR,socket and malformed URI. All refuse before driver
connect,with0actual external network attempts and no DSN secret in output.
Effective addresses are pinned to coherent exact loopback,not inherited routing.
The real positive local worker still succeeds under8s/1s and the explicit policy.

Owned logging is effective before start:own code calls initdb,writes only
terse/panic/parameters0 to auto.conf,then uses unchanged harness.start(). All3
actual pg_settings readbacks are from configuration file before facts. Main,
child probes and metadata fixture use this setup. The shared harness is intact.
ROOT's separate supervisor will additionally strip PG* environment defaults.

Final receipt: `runs/20261105T004734658907Z-local-overlay-logging-final-source-free/result.json` (11pass/0fail/4unverified).
It includes7option CLI cases,13DSN negatives,10deadline outcomes and14JSON-null
cases. Four owned PG roots(main,default probe,allowed probe,metadata fixture)
are stopped/removed. No synthetic sporting fact entered the candidate. Only
code/config/metadata/digests/identifier diagnostics are artifacts; no source
body,pg_dump,pickle or native SQL row was persisted.

All pre-code REDs and first10/4/prior11/4 remain immutable:missing option,
fresh-worker coverage,13driver trips before local validation,and stock logging
(default/error/default-source) before pre-start config. The current code/spec
bytes equal the final run input copies. Frozen capture1498,candidate218,
normalizer4b98,model18da,sealed012/013,harness,MANIFEST,failed v1/old89/v2ledgers,
v2metadata-manifest/inspection-inputs are unchanged.

FUTURE_REAL_OVERLAY_RUN.md contains the exact proposed command and ROOT-owned
supervision contract:1800s workload hardstop,4GiB disk,15s progress,owned cleanup.
Success requires exit0 AND all15cases(11+4) present once/pass,478547native and
1344cell comparisons,and fresh94table/67sequence no-op. Interrupt/hardstop/
cleanup failure is global failed/interrupted with remaining cases unverified;
a partial child statuspass is never accepted. ROOT owns the separate supervisor,
smoke and release. No real E2E or supervisor was run by this agent in this lot.
Source-only478547/1344 have NOT been compared with SQL yet.

- E2E SHA-256: `7ab6cd06852bf56186c29d26e7654cbd3a2d26546cefa12cc6065b1fbcf40ddd`
- Final result: `27a5621c31e3cab2ad5e93d287473c39bf4f3f6177088af934ecd174fcd49976`
- Overlay receipt: `2bb97d7ddca78de3ae704d4b3daa99715a435edbf88e1b7d9ad82f5d44740fe6`
- DSN proof: `821d9b167d73f26a23e6a4480aed1f32132910a5c9c1422b4cfcd6abaab8f8a9`
- Logging proof: `cdc6ce9e2bdcb30af09ffec5062cda29c24f8d36f68e583c44783758f1e1ddf1`
- Frozen v2budget: `30cd865d10da6d2dc28e53f0f741756549c576bfa35a90e050062a462dc078ac`

Exact source-free rerun:

```sh
PYTHONPATH=/tmp/statarena-publication-test-python /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 docs/verification/orion-pro-real-native-spatial-20261104/e2e.py --prepare-only --local-validator-overlay docs/verification/orion-validator-membership-20261105/candidate.sql --local-validator-overlay-sha256 e0810f8670b2cb627ade2c76e3c8eb527ab31fd595d5cf939fd63bfc5cf649d6 --label local-overlay-logging-final-source-free
```

Suggested commit: `test: add explicit local validator candidate policy`.
