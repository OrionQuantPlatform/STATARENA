# Qualified publisher pre-code result — expected missing-helper RED

Suggested commit: `test: qualify typed publisher inputs and complete precode oracles`.

**The five real setup gates passed. The single actual publisher CLI call then failed because the product file is absent.** Overall FAIL is the intended pre-code RED: P01 pass,P00 fail(expectedPreCodeRed=true),P02–P29 unverified. No other error occurred and no publisher or substitute output was implemented. Stop for ROOT review; no fifth run is implied.

## Exact reproduction and evidence

```sh
PYTHONPATH=/tmp/statarena-publication-test-python python3 docs/verification/orion-pro-publisher-20261105/qualified-precode/publisher_workflow.py --label qualified-precode-red
```

Required existing local tools: PG18.6 binaries at `/tmp/statarena-cache-test-tools/node_modules/@embedded-postgres/darwin-arm64/native/bin`, Python psycopg dependencies at `/tmp/statarena-publication-test-python`, Bun and existing dashboard node_modules. Bun receives --no-env-file and a minimal child environment. No credential/DSN is put in argv or evidence. libpq's `/dev/null` password-file warning is retained; no credential file was supplied.

Run: `runs/20261105T024932945739Z-qualified-precode-red/`.
Receipt SHA256: `f91ee58434d94f391ac85d1eba9ca8bab538ae7923a6302ad85884769b757c82`.
Elapsed11.915s including cleanup. The immutable run contains38 exact code/model/SQL/protocol inputs,typed input readback/closure evidence,isolated real API export16 files,all SQL/HTTP traces,commands,deadline/privilege observations and CLI stdout/stderr. `PRECODE_SOURCES.json` pins the new test/oracle bytes before PG or product implementation; SHA256 `4624b52a26ff59879128507abc9ae7658965f504d3c941da5ee0fbee10f2ca7a`.

## Setup expected versus actual

| Gate | Expected | Actual |
|---|---|---|
| Independent typed inputs | Exact103-model/94active schema and012/013 bootstrap; actual selected A/B/C inputs,real keys/states/aliases/profiles/source contracts; zero outputs | PASS. PG180006,171typed rows,3 editions/5 match identities,dg3/cg2.62 independent input/closure SQL queries. B squad2/playing-only1; both B shots use the playing shared actor; changed content revisions2 |
| Real API identity/export/source fences | Real frozen aws-app/readers,explicit canonical modules only,runtime readonly8s/1s; calibrated source/network tripwires | PASS.16 canonical exported files,no dotenv/numbered copies,real runtime readonly on. Four API tripwires blocked their deliberate calibrations before file/provider/network work |
| Four unpublished HTTP paths |4GET +manifest HEAD,503/no-store,metadata-only,no source/body fallback | PASS. All5 returned503/no-store; HEAD body empty; exactly one orion:meta SQL query per request,zero heavy/legacy body queries |
| Main and two worker deadlines | Actual startup8s statement/1s lock/5s idle,real lock/statement cancellation,≤5 connections | PASS. Main8.002s→57014; worker locks1.004/1.005s→55P03 and statements7.999/8.009s→57014. Both actual workers identified as statarena_ingest; observed peak4 connections; PG physical cap5 |
| Actual writer/runtime privileges | Existing generated grants; writer cannot dirtyDELETE/direct validator/commit-sequence access; runtime cannot write even readonly off | PASS. Writer three42501 denials; runtime UPDATE42501; independent catalogue query found0 writable tables/columns across the94-table namespaces |

After all five, P01 was recorded. Then isolated Python -I invoked the actual absent `dashboard/scripts/orion_pro_publish.py --help` once,without DB environment. Expected usable CLI exit0; actual exit2/targetExists=false with No such file or directory. The full94-table counts/digests,build/pointer/dirty/sequence state remained unchanged across that call. The two earlier subprocesses were deadline **probes**,not publishers; no duplicate missing-helper invocations or hand-built publication occurred.

## Bounds, preservation and cleanup

| Resource/evidence | Actual / cap |
|---|---|
| SQL |135 reserved operational calls /1500;134 server-logged operational commands outside fixture setup. The one-call difference is SET application_name,logged under the previous setup application.194 fixed setup commands separately logged |
| HTTP |5 /200,all loopback |
| Data/output |171 /5000 rows;3 /3 editions;5 /12 retained match identities;3 /24 accepted generations;0 builds/summaries/publications |
| Processes/connections |1 owned PG,1 real API,2 simultaneous probes,peak4 /5 connections |
| Source transports |0 football source file/object/provider reads during actual requests;0 post-calibration access violations. Eight deliberate API/worker calibration attempts were blocked and stored separately; they are not concealed as zero attempts |
| Source bytes | sourceChangesDuringRun=[] |
| Earlier artifacts |148 predecessor SHA entries plus20 static-review entries unchanged before/after;both original manifest hashes verified. All three failed setup receipts remain unchanged |
| Cleanup | Owned PG stopped and directory removed,API and both worker processes stopped |

## S01–S14 status and limits

All amendments live only in this new directory. S01 real composite coverage identity,S02 coherent B playing/unused cohort,S03 increasing synthetic content revisions,S04/S05 actual selected input readbacks and flags,S09 complete P01 ordering,and S13 separate physical source_priority_version/upstream row contracts/transform SHA were exercised during setup. Exact independent initial closure digests were computed from real retained typed rows: A `f773b3f5f51e4a72c4109e0086eb95c943b74bf9bec96ea3d82124fdba6f63ce`,B `db39cb347441d12982c9d4a966f3fd7ff880ff28c71e1f1ee76e3fb8b84a1ffb`,C `176ba2699b0d0de0aab1c4d05e8bf7e009dc8b5d3ad5063f5df92de3f6174270`.

The complete future test/oracle code is written before the publisher exists: S06 explicit NULL score observations versus absent rows;S07 exact source/code/policy/closure/environment/snapshot output bindings;S08 an empty artifact reaching the real CLI through a separately valid envelope;S10 independent backend/pg_locks verification before global activation lock;S11 both absent/null successors and valid historical/stale-current real coverage keys;S12 NULL selected profile;S14 nullable C shot/native DTO fields. They remain **unverified**,together with publication,counter outputs,pins/cursors,HEAD/304 on ready builds,no-ops,crashes/concurrency/recovery and all helper-dependent cases. A computed source digest is not an executed publisher/build result or business source acceptance.

The dependency/environment contract is explicit in DEPENDENCY_CONTRACT.md. Environment expectation SHA256 is `d0fb32013747398b2c82e48f70e058bb368aecd0f3e382a36d8c24f475767770`;future publisher code SHA is deliberately null while the file is absent. No source-v2,real-data fidelity,014/107,full backend parity,hosted frontend,AWS/Neon or production activation result is inferred. ROOT reviews this pre-code evidence and contracts before implementing or running a product publisher.

Key test/oracle SHA256:

| File | SHA256 |
|---|---|
| publisher_workflow.py | `78872b83525d30a6e74f0d0312830c742546c18c5e92b04ab69b4c4b0f44eebe` |
| typed_inputs.py | `a5318274eb4329017b8f9e0f4a266a914974a5ed6fd5eff8300e0eacf5c99815` |
| typed_oracle.py | `12bc8c97bcb86e57e20152cd85eda7e25afdcd90a5fb683d9b726ac53516fe9f` |
| publisher_oracles.py | `fb788c5fe3052dc5a887b8fcd86616207caea79cf7f460caf1b842250c7e01a7` |

`FINAL_CHECKSUMS.json` pins every file in this new dossier/run,including complete useful source copies. The predecessor and static dossiers were not modified to hide any failure.
