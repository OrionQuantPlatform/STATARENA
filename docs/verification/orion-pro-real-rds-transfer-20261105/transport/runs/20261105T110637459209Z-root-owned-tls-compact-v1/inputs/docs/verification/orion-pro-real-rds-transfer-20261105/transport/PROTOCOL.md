# Native SQL transport qualification — written before implementation

This is a distinct versioned adapter, not an extension of the V2 fixture policy.
The approved model, 012/013/014, normalizer, candidate, old writers, guards and
qualifiedImportPairs remain byte exact. No source body is captured by this test.

The default CLI is offline and must open no connection. Active modes require an
exact hash-bound source/target pair, native94 source acceptance and separate
release. Fixture acceptance is valid only for owned local TLS. Real acceptance
requires the frozen real producer/manifest/candidate and an owned SQL checkpoint;
its target is exclusively statarena_prod/statarena_ingest on the existing RDS.
No AWS, SSM, provider, RAM socket or remote PostgreSQL call is part of this E2E.

| Case | Setup / failure mode | Expected observable outcome |
|---|---|---|
| implementation_available | New CLI absent | Genuine missing-file RED; all dependent cases unverified |
| offline_default | Poisoned PG and cloud environment; socket/process/psycopg tripwires | offline_plan, zero connections, no tripwire |
| explicit_metadata_required | Active mode lacks each metadata input | Refusal before driver/socket/process |
| origin_pair_policy_routes | Fixture passed to RDS, real passed to local, wrong policy/model/actor/producer/hash, arbitrary host/DSN flags | Refusal before driver/socket/process |
| campaign_release | Local E2E release absent, stale code/test/bindings, reused allocation | No PostgreSQL start |
| owned_tls_native_setup | One private PG18.6, distinct source/target databases, ordinary runtime/ingest roles | TLS verify-full,8s/1s, source RO RR, no elevated writer |
| independent_endpoint_policies | Source012013+P1 body, target012013014; clocks/OIDs/B0 differ legitimately | Both independently exact; no local/RDS policy alias |
| native94_sequence_metadata | Native catalogue including all constraints/views/ACL/roles/default grants;67sequence shapes |94tables/1709columns/431FK/46views/67seq; no sequence value SELECT by writer |
| endpoint_actor_route_refusals | Bad owned epoch/port/actor, runtime COPY attempt, inherited route overrides | Refuse before business DML; runtime42501 |
| source_and_policy_drift | Changed source value, catalogue view/ACL or producer | Refuse; native destination and sequences unchanged |
| foreign_target_bootstrap | Foreign row in target or altered bootstrap | TARGET_DRIFT; no business DML |
| exact_preflight | Valid compact native fixture |91business+3control contracts;106mapped technical components, business IDs preserved |
| mid_copy_rollback | Fault after second COPY | All94native rows rolled back; legal sequence gaps retained |
| deadline_rollback | Native8s timeout before seal | Native57014; full phase rollback, no deadline relaxation |
| committed_core_resume | Exit after core commit | Fresh process copies only remaining family; zero recopied scalar rows |
| exact_native_controls | Independent native oracle and inverse technical IDs |91business relations exact,3control contracts exact;12B0 rows preserved and excluded from copied_rows |
| technical_clocks | Inspect each committed phase | run.started_at=finished_at=snapshot.created_at=sealed_at=transaction_timestamp |
| closed_checkpoint_corruption | Unknown key, forged copied count/checksum/missing or unequal clocks | TARGET_DRIFT; restore exact bytes then no-op |
| lost_commit_ack | Fault after COMMIT returns | COMMIT_ACK_UNKNOWN; new readonly prefix inspection resumes/no-ops without duplicate COPY |
| noop_and_native_identity | Fresh process after completion |0COPY/0nextval;94tables+67sequence values unchanged; next native business ID greater than source max |
| sourcefree_scope_cleanup | Final source/legacy sentinel/inventory checks | No publish/provider/cloud/raw copy; all owned clients/PG/private TMP removed |

Tests are written before the new implementation. Source-free mode runs actual
CLI children with physical network/driver/process tripwires. PG mode requires a
separate ROOT allocation bound to the exact test, writer, protocol and bindings
hashes. One cluster, compact fixture built once,600s maximum,1GiB owned disk,
64MiB evidence. Every child shares the global deadline with TERM/KILL and bounded
drain via the already qualified tests/orion_e2e_process.py. Stop at first unexpected
failure; preserve its receipt and mark later cases unverified. Do not reuse an
allocation or rewrite an earlier attempt.

Every run archives exact nonsecret inputs, hashes, command, expectations, actual
case results, CLI reports/stdout/stderr, PG logs/resource samples and cleanup.
Admin connections only create the disposable local fixture and independently
read sequence values/oracles; all transported business DML uses ordinary ingest.

Pilot limits remain500k rows/table,2M rows total,64phases,1MiB row/payload,
16MiB live buffers,32MiB metadata,1000rows/batch,8s SQL/1s locks. Closed historical
intervals are explicitly refused by this pilot. These are qualification admission
bounds, not final production caps. Full production needs partition-aware closed
interval transport, global reconciliation and scalable sequence reservation;
never silently omit rows, lower fidelity, or relabel unavailable data as NULL.

UX: offline default and actionable refusal codes; DX: separately versioned
adapter and immutable old contracts; AX: closed JSON schemas, pinned origins,
exact rerun receipts and no ambient DSN discovery. The intentional tradeoff is
continued pilot admission limits: this lot does not claim full-data completion.

Suggested commit: `feat: add explicit native SQL transport for real RDS pilots`.
