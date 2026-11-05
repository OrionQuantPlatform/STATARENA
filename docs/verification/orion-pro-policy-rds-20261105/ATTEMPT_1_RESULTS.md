# First adapter campaign — stopped at setup

The genuine missing-adapter RED is preserved at `runs/20261105T022012136519Z-precode-missing-adapter-red/result.json`:0pass/1fail/19unverified,0PGstarts. The complete E2E existed before adapter.py; TEST_BEFORE_IMPLEMENTATION.json records the two harness corrections made while the adapter was still absent. No test was added after implementation.

The single authorized owned campaign stopped after1.257s with **1pass/1fail/18unverified**: [result.json](runs/20261105T023121117636Z-owned-rds-adapter-compact/result.json), SHA256 `520d42f7bccb0446e783e1d9bba40a6cde68d4055ae9ed6fd35a4e0bf966b7c3`. PostgreSQL returned25006/ReadOnlySqlTransaction during owned_tls_setup. The setup connection deliberately inherits default_transaction_read_only=on, but the harness then issues CREATE ROLE without an explicit writable setup session. PG correctly refuses it. This is a local setup defect; no adapter SQL, exact Q04 cardinality, P1 adoption, rollback or no-op acceptance is established.

Before/after: PG campaign starts0→1, maximum1; ledger state stop_for_ROOT, no resource limit hit. The server stopped and the owned PG directory was removed. All19 protected input hashes, including the original four static plan files, remain exact.0cloud/SSM/RDS/source/RAM calls and0remote writes. No new remote release/ledger was created; the source RAM server was untouched.

No code fix or retry followed this failure. The narrow proposed harness correction for ROOT review is to explicitly make only the already verified owned-superuser **setup** session writable before CREATE ROLE/CREATE DATABASE; CREATE DATABASE cannot run inside a transaction block. Keep every owner/ingest/runtime inspection/writer startup deadline8s/1s and default-readonly entry unchanged. A subsequent campaign needs a new explicit ROOT allocation/append-only continuation, not resetting this consumed ledger.

Current unqualified code: adapter SHA `332d963bbe008c741212801172b3a6a48d52344682768b3285ea8091b15e081c`; E2E SHA `87d61d5d6bc3ec3ba81f690283e0f92005a4db36ce329dfa1304cb8c9b054612`. Source snapshots, exact command, expected workflows, actual error code, public TLS setup and cleanup logs are archived in the two runs. Private TLS key existed only in the removed owned directory. The remote path and authentication are unexecuted. `fullAcceptance=false`, ProOFF/collectorsdisabled, user107 pending.

Suggested commit: `feat: prepare exact read-only RDS validator policy preflight` (local qualification incomplete).
