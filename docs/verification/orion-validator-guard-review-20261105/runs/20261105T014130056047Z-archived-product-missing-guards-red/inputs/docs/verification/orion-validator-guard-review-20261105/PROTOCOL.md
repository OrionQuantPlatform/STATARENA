# P1 guard review — contract and E2E before correction

ROOT has placed a HOLD on all existing policy/helper/runner/manifests/tests and the253-artifact manifest until the functional14/14 checkpoint is committed and its archive SHA is supplied. This new namespace alone may be written now. No PostgreSQL, product change, source/cloud/RDS/SSM access or dense run occurs during that HOLD. The frozen streaming design is unchanged.

Two narrowly scoped defects are to be closed after the archive checkpoint:

1. `host='127.0.0.1'` alone does not pin a libpq route if PGHOSTADDR is inherited. The runner must additionally supply literal `hostaddr='127.0.0.1'` before opening the connection. The E2E invokes the actual CLI with PGHOSTADDR=203.0.113.77 and a driver tripwire; the tripwire records safe explicit host/hostaddr/port and **prevents any real nonlocal connection**. Offline default must still call no connector. Positive local owner/epoch/ordinary-role/read-only checks remain exact.
2. The current catalogue omits46 views, three schemas' owner/ACLs, relevant default ACLs and fixture-role flags/memberships. The new bounded inspection must include native view definition/columns/options/owner/ACL, schema owner/ACL, global and schema default ACLs relevant to actual owners/three roles, all safe native flags/configs of policy_owner/ingest/runtime and memberships involving them in both directions. Resolve referenced OIDs to role/schema/type names; do not hash nonportable catalogue OIDs or password fields. No schema/view/grant/default privilege/role is changed by the upgrade; inspection only.

The actual RED runs against the archived unchanged product before the correction. It may collect all **known expected missing-guard assertions** in one owned compact workflow; any other setup/native guard/bound failure stops immediately and requires ROOT briefing. Then write the two product corrections and one compact green. No post-implementation unit tests are introduced.

## Exact new E2E matrix

| Workflow | Expected outcome |
|---|---|
| Archive checkpoint absent | Stop before PG or product mutation; distinguish this archival gate from a functional RED |
| Archive bound | Original final-hashes253 file bytes exact; every archived entry verified at ROOT's commit. Live helper/runner may change later; do not claim their HEAD hashes stayed old |
| Setup | One owned local PG18.6, two DBs, ordinary policy_owner/ingest/runtime; exact sealed012/013/B0;8s/1s/512MiB temp; no credential/DSN output |
| Read-only positive | Original local marker with aware epoch/role/flags passes; exact1709 table declarations remain. Current local-only endpoint constraints unchanged |
| Offline poisoned PGHOSTADDR | Actual CLI returns an offline plan and makes zero driver connection calls |
| CLI poisoned PGHOSTADDR with tripwire | Old runner produces a prevented nonlocal-route attempt and the test is RED; corrected runner explicitly supplies127.0.0.1 for both host and hostaddr and reaches only the owned PG |
| Full native catalogue |46 native views, three schemas, three role rows plus relevant default ACL and membership categories; all within32MiB metadata/16MiB buffers. Missing categories are an expected old-product RED, not a passing completeness claim |
| View definition drift | Commit a changed definition in owned fixture, actual preflight refusesCATALOGUE, then restore exact native definition/security state; no repair by runner |
| Schema CREATE drift | Grant runtime CREATE on football in fixture, preflight refuses, restore exact ACL; no new upgrade grant |
| Schema default ACL drift | Owner's future-table INSERT grant to runtime in football refuses; restore exact pg_default_acl state |
| Global relevant default ACL drift | Owner's future-function EXECUTE grant to runtime refuses; restore exact global defaults |
| Runtime flag drift | Test-admin toggles runtime BYPASSRLS in owned fixture, preflight refuses before application, restore ordinary flags |
| Role membership drift | Test-admin grants ingest to runtime, preflight refuses; revoke and restore exact native membership/security state |
| Unrelated fields / routine properties | No relaxation of function SQL139/46, OID/owner/ACL/procprops, originalB0, role privilege checks or model hashes |
| Positive014 apply/no-op | Corrected endpoint and inspection accept exact target; one function+one timestamped journal entry only, same views/schema/default ACLs/role flags/memberships, old012/013 exact, no-op clocks/sequences unchanged |
| LOCAL099 | Separate local acceptance and append-only099; same security/view state and timestamped journal; no production099/015 or RDS compensation permission |
| Freeze | Model/012/013/default producers/oldv1/oldtests and13 protected inputs unchanged; original receipts/253 manifest unchanged; old external source paths verified at archive SHA and stored snapshots, not current HEAD |
| Cleanup | All clients stopped/closed, owned PG removed, safe driver tripwire trace, actual CLI commands/results, native category/security snapshots, archive hashes, new source hashes/oracle/manifests and resource logs saved |

Fixture tampering is deliberate and reversible in the owned DB, under its setup owner/test-admin only. Application actors stay ordinary. Each drift is restored before the next; a native audit of views/schemas/default ACLs/role flags/memberships is independently compared before/after. A rejection caused by a malformed fixture or unexpected privilege failure does not satisfy an intended missing-guard assertion.

## Policy revision and preserved history

After ROOT supplies the archive SHA, new product sources may be fixed while old source snapshots/commit and the253 manifest remain immutable. New policy revision/oracle files must use a new fixed directory such as `dashboard/backend/schema-policies/orion-pro/guard-review-v2/`; old P0/P1/oracle/local099 files are not overwritten. New local099 artifacts belong in this namespace. No arbitrary SQL/path/latest input and no compatibility pair is added.014 stays SHA e0810f8670b2cb627ade2c76e3c8eb527ab31fd595d5cf939fd63bfc5cf649d6.

The new review manifest binds the new helper/runner hashes, the archive commit and historical14/14/clock receipt as history, expanded inspection contract and new actual oracle. It must not hash itself/its containing commit or a receipt taking it as input. It does not reattribute old14/14 as expanded-guard proof. Existing source-overlay/RDS qualification remains closed/localOnly.

## Conditional budget

Only after archive SHA: at most **two new compact PG starts**, one planned RED and one green,≤10min each,1ownedPG/2DB per start. No dense/source/remote activity. Same32MiB metadata/16MiB buffers,8s statements/1s locks,8GiB owned PG soft stop7GiB,temp512MiB/backend,64MiB evidence in this namespace. No old ledger reset. At first unanticipated failure preserve results/cleanup and brief ROOT before another PG. Planned guard RED is recorded honestly; it is not success.

Suggested commit: `fix: pin local policy routes and inspect complete security catalogue`.
