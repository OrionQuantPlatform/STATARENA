# Proposed v2 E2E and resource gate — no execution

No test, code, PG or remote campaign is started here. ROOT must approve this design and the exact endpoint-policy pair before tests/code. Existing frozen v1/scaffold/P1 evidence stays unchanged; no old green is attributed to v2 transport. The actual source RAM SQL comparison is not presumed complete.

## Tests before implementation

Write the complete local E2E first and retain its real missing-streamer RED without PostgreSQL. Only after that RED write the streamer. Scope is M0/94 active relations, explicit IDs/open retained history and the exact accepted source P1-overlay→target P1-journal pair. Nothing applies014 as a side effect. Fixtures use native match/participant/metric/canonical grains, not many alternative variants on one entity.

| Workflow | Required observable outcome |
|---|---|
| Missing implementation, offline default | Actual pre-code RED; offline plan no env-secret/client/service/SQL access, no fixture start |
| Endpoint and three contracts | Owned local engine/role/identity, complete structure, owner/ACL/procprops, B0 and separate source-overlay/target-journal descriptors. A function hash or label alone never admits a pair |
| Unqualified P0/P1/LOCAL099/mixed source or target | Refuse before business COPY; do not rerun original dense0138s baseline |
| Policy drift or owner/ACL mismatch | Refuse; role-slot normalization only on reviewed security fields, never SQL/source strings |
| Source/model/producer/phase/document drift | Full94-table native acceptance and sealed phase receipt bindings refuse any mismatch before phase DML |
| Ownership source joins | Every transported relation has exactly one accepted owner;0bootstrap neutral, no future dependencies, no hidden full-row cache; explain plans/actual bounded work saved |
| FK component mapping | Generation/snapshot direct and transitive maps exact; H2H/coverage children map generation; standing_rows.snapshot_id stays business ID; ambiguous/missing/forward map refuses |
| Immediate FK order / self DAG | All inter-table relations ordered; sources upstream, stage parent and metric numerator/denominator parents copied first; missing/cycle/over4096nodes/8192edges/8MiB/1MiB rank-map refuse |
| PK/width preflight and raw COPY | Keyset windows≤1000, encoded COPY≤1MiB/row/batch, no OFFSET/per-row WAN lookup; exact source range/count, arbitrary protocol block boundaries, field escaping and tail complete; server/client memory bounded |
| Native types/states | Independent SQL-text oracle:29-digit+fraction numeric, precise technical JSONB, SQL NULL/JSON null/missing/array/string,0/false/empty/Unicode/escaped control text, all five metric states, unchanged fact timestamps |
| Bootstrap identities and explicit business IDs | Ten seeds/two contracts/B0 unchanged;65 business sequence reservation plans bounded and monotone; import_run IDs preserved; no blind business-ID remap or setval |
| Rollback sequence gaps | Compact mid-COPY and before-seal faults roll back actual phase, sequences not reset; restart recovers distinct generation and snapshot maps, not equal-number assumptions |
| Collision / corruption | Existing unrelated row, foreign source_record/provider, copied scalar changed, duplicate/missing child or cohort mismatch refuses with exact native error/oracle; no silent ON CONFLICT/dedup |
| Source RO lifecycle | Per-phase source RR+global accepted digest, expected source-coordinate prefix digest before target BEGIN, source transaction closed before target oracle/seal/commit. Source change at reopen refuses; idle deadline/refusal tested, no heartbeat/timeout raise |
| Control receipts | New writer/policy/source/target refs and actual mapped generations/snapshot IDs; bounded technical parameters/checkpoint regenerated; precise copied JSONB facts never decoded through float; no raw source body copied |
| Core prefix interruption | After dense core commit, stop actual worker; new process validates full prefix and source/policies/maps and copies families only. Core is not recopied merely to repeat the run |
| Family rollback and restart | Inject one compact family failure, preserve committed core, retry families under a new target generation/snapshot if consumed IDs left gaps; one source family generation still maps to one successful target generation |
| Lost COMMIT ack | Fresh RO inspection classifies committed prefix or rollback; mixed state refuses, no blind replay/duplicate |
| No-op | Full input twice, second process has0COPY/nextval/generation/receipt clock updates; stale receipt/control checksum refuses |
| Dense capacity | Exactly15437appearances×31=478547canonical scalars,612draft matches and one primary variant; source built once, core transported once; all94 relations/controls/sequence states accounted for |
| Native phase admission | Native full seal and deferred commit each<8s; COPY, preflight, source/target oracle and server plans separately measured. No new index/grant/policy/trigger bypass or phase split |
| Serving / no source body | Legacy/publication namespaces and pointers unchanged; runtime cannot import; no collector/source HTTP/object-body read, dump/staging/blob/file export or purge |
| Cleanup / budget | Exact rerun/setup/inputs, policy pair, SQL plans, counts/digests, sequence gaps, error/ack states, buffer/metadata/IO counters and cleanup saved. All clients/owned PG/temp paths stopped/removed |

The oracle is native and independent of the COPY adapter. All94 relation states are covered; the three regenerated control tables have exact declared projection contracts, not a generic hash exception. Security/canonical/cohort failures must hit their intended rules rather than an earlier malformed fixture. Validate every direct fixture INSERT against M0 before the single large start.

## One concrete proposed local campaign

| Item | Proposed ceiling / discipline |
|---|---|
| Current static lot |0PG/SQL/source/remote;≤1MiB document artifacts |
| Pre-code | One missing-implementation RED,0PG |
| Local compact checks | Run before density within the same explicitly owned campaign; test-only schemas may be reset on the same two DBs before the one dense construction, with exact bootstrap reinstall through frozen SQL. No external reset mode |
| Dense start | **One** campaign/owned PG, two DBs; source construction once and core transfer once; no routine original013 baseline or full repeated dense replay |
| Time |≤20min whole campaign, including source setup/transport/oracle/restart; individual SQL8s, lock1s; respect actual idle deadlines without increasing them |
| Data/profile |≤2M rows overall,≤500k/table,≤64knowledge phases;478547scalars/15437appearances/31metrics/612matches in the one dense fixture |
| Client metadata |32MiB total: target16MiB model/policy/SQL metadata,8MiB self graphs,4MiB maps/receipts/counters,4MiB headroom. Actual combined/transient object accounting remains the authority; these are quotas, not permission to exceed32 |
| Client transport |16MiB total; native payload≤1MiB,≤1000rows/batch; include both protocol buffers, SQL/PK width window, live frame and encoding copies |
| Source/target server | Owned PG8GiB, soft stop7GiB; temp_file_limit512MiB/backend; unchanged work_mem/parallel settings, no new index or TEMP table |
| Sequences |≤1M nextval calls/sequence,≤5M total, blocks≤10000; reserve monotone; rollback gaps not reset |
| Evidence |≤64MiB, no full copied fact dump/JSON/CSV or raw provider body; source/target typed digests/metadata only |
| Stop | First unexpected fixture/guard/ownership/plan/deadline/size failure: preserve RED and cleanup, brief ROOT before another PG. No second dense start is implicitly allocated |

Compact crashes happen before the dense construction. The dense continuation may deliberately interrupt after the core has committed and retry only the small families phase; repeated native reads for independent source/target or prefix oracles are measurements, not an extra source build/core copy. A failure requiring a new full dense source/core attempt exhausts this one-start proposal and needs a new ROOT allocation. Do not describe a policy-binding refusal from v1 as a measured memory-capacity refusal: the v1>32MiB conclusion here is the explicit160bytes×478547 static accounting bound.

No file with streamer code, test implementation, executable SQL, role/grant change or deployment is created by this design. Proposed future files are new v2-only names (`dashboard/scripts/orion_pro_bulk_stream_v2.py`, `tests/orion_pro_bulk_stream_v2_local.py`); old v1 and scaffold never become mutable implementation targets.

## RDS gates later, separately authorized

1. ROOT accepts the actual typed source SQL/native comparison and its limitations; provider completeness/purge remain separate. Qualify the exact source-overlay/producer/native SHA and destination deployment policy pair in a new acceptance, without editing P1 or source receipts.
2. New remote adapter/E2E first proves readonly defaults, TLS verify-full/identity, indirect credential safety, nonowner ingest/runtime refusal, hard endpoint binding, current schema/policy/B0/readback, bootstrap/exact-prefix collision rules and no legacy/serving writes. The current local014 runner is not converted silently into an RDS client.
3. A fresh RO RDS preflight has its own explicit query/byte/time budget. It proves metadata/security/capacity state, not dense COPY/seal performance. Missing rights/indexes/resources are a stop, not a grant/resize request embedded in import.
4. Only a later explicit bounded data-apply acceptance can authorize the actual candidate transfer. It must specify phase/row/bytes/nextval/elapsed/WAL/storage ceilings and one eligible target; local success grants none of those writes. Every data operation remains inside native phase admission and exact prefix oracles. RDS8s failure stops, without higher deadlines or splitting a source generation.
5. Independent post-commit readback and source/target native parity establish that imported partial candidate only. Ready builds/readers/publication/cutover/full source fidelity/purge need their own acceptance. AWS legacy and original source copies remain intact.

Suggested commit: `docs: define bounded typed streaming phases and RDS qualification gates`.
