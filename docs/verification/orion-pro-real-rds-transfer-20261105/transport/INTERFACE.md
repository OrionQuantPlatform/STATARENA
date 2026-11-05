# Explicit checkpoint transport interface

The implementation is offline by default. No argument discovers a DSN, host,
policy alias or AWS credential. Active modes require separate `--pair` and
`--acceptance` JSON files plus their exact SHA256 arguments, `--source-marker`,
and `--release` plus its SHA256. RDS additionally requires `--target-passfile`.
All inherited PG environment variables are rejected before driver import.

The local source marker kind is owned_native_transport_pg18_v1, with private0600
file inside its owned0700orion-pro-e2e-*root: ownedRoot, port,
postmasterStartedAt, sourceDatabase, targetDatabase, certificatePath and
certificateSha256. The server/data path/PID/PG18/version/port/epoch and actual
TLS connection are checked. Real sourceDatabase is postgres; fixture databases
may differ. Source roles are orion_pro_owner/orion_pro_ingest/orion_pro_runtime;
source connection uses runtime. Target roles are statarena_admin/ingest/runtime;
target connection uses ingest. Target real database/host are fixed in the code.

ROOT can prepare each descriptor in its own read-only Repeatable Read transaction:
`describe_endpoint(conn, source=True, origin='real_native_sql_checkpoint')`
and `describe_endpoint(conn, source=False, origin='existing_rds_p1')`.
These are readonly preparation helpers, not an authority to connect or write.
They record the actual endpoint's native/security catalogue hash and counts,
validator properties/OID, full journal including installation clocks, journal
native digest, B0native text, role names and identity/epoch/TLS. The helper does
not substitute a local catalogue for RDS. Real target also binds the independently
adopted P1statee24d2f4864f2a24c639d5556b4012d276b8958f5df3d02e2a80e52a601ae9a32.

Pair fields are closed: kind=explicit_native_sql_transport_pair_v1,
environment=rds (or owned_local_tls), writerSha256, bindingSha256, source, target.
Source policy kind is typed_native_p1_overlay_v1,012013journal/P1body; target
typed_native_p1_journal_v1,012013014journal. Their hashes need not equal.

Acceptance kind native_sql_transport_acceptance_v1 has closed fields:
dataOrigin,writerSha256,bindingsSha256,pairSha256,modelSha256,producerSha256,
producerVersion,sourceNativeSha256,sourceTables,sourceRows,sourcePhases,
sourceCheckpointSha256,fullAcceptance=false and realSource (or fixture).
sourceTables is exactly the94relation-native rows/sha256 dictionary. sourcePhases
is the exact ordered phase/generation/snapshotId/runId/manifest set. A first real
runId=1 is valid. sourceCheckpointSha256 binds the separate ROOT source checkpoint.
realSource must equal:

```
{
  "normalizerSha256": "4b98a829bc7e32e11a7e66381ffecae6248ce536d17771aa080502374fe844bc",
  "manifestSha256": "654993cac446a9aa81cc2079a6b9fafd6ddef3a3188ff54ea5297b1677f5aaa9",
  "candidateSha256": "218f378b599cd166f747fbacf6f79148220150fbc2bede4f81bef535eca553bc",
  "checkpointKind": "owned_real_typed_sql_checkpoint_v1"
}
```

The separate operation release kind native_transport_operation_release_v1 has
scope=typed_real_business_pilot (or owned_source_free_fixture), mode=preflight-rds
or apply-rds (or corresponding local mode), writerSha256,bindingSha256,pairSha256,
acceptanceSha256,expiresAt and fullAcceptance=false. A preflight release cannot
authorize apply. Fault flags are accepted only for owned local apply. This
interface specification is not an operation release or business-write approval.

The source is reopened under RO RR and native94 rechecked at each phase. Source
reads close before target native oracle/seal/commit. Only generation/snapshot
components are remapped; source run IDs and all business IDs are preserved. The
new3control contracts have closed keys, source run/phase/checkpoint fingerprints,
source-derived counts and four exact native transaction clocks. A commit I/O
failure without a deterministic SQLSTATE reports COMMIT_ACK_UNKNOWN; fresh
readonly exact-prefix inspection is required. A completed phase is reused;
fresh no-op performs no COPY or sequence reservation.

Suggested commit: `docs: describe explicit real checkpoint transport contracts`.
