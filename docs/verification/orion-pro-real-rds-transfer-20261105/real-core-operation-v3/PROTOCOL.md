# Real core operation V3

Suggested commit: `feat: qualify real typed core transport with fresh source identity`.

This release retains the real adapter FA0E and its immutable receipt contract. The historical logical checkpoint35dba5… is the content approval used by that contract; it does not assert that the old postmaster remains alive. The current endpoint is the independently qualified service checkpoint8f4d77… with actual epoch2026-11-05T12:54:23.896939+00:00.

Before any authentication, the supervisor compares complete94table/67sequence dictionaries and all checkpoint content except the five explicit routing fields. It pins both checkpoints, both native readbacks, the continuation proofs, the current private marker hash and the actual endpoint descriptor. Only postmasterStartedAt changed in the complete descriptor/marker. The writer checks that actual epoch over TLS on every connection. No stale epoch alias, altered old result or producer receipt rewrite is used.

Preflight and apply have separate once-only releases, the unchanged900s child deadline and8sSQL/1slocks. Apply additionally requires a successful preflight bound to the exact same authority. No full source acceptance, publication or production activation follows from this transport. Existing RDS, ordinary ingest, no new schema/grant/resource/raw staging.

Expected source553562 native rows; copied domain553545 rows (three control relations regenerated,12B0 seed/contract rows retained),839players/20teams/612matches/15437performances/478547native metric states/9795shots. Matches remain draft; detailed families/spatial/full leaf fidelity remain open.

Commands from repository root:
`PYTHONPATH=/tmp/statarena-publication-test-python PYTHONDONTWRITEBYTECODE=1 python3 docs/verification/orion-pro-real-rds-transfer-20261105/rds_core_operation_v3.py --preflight`
then `--apply` only after ROOT reviews preflight. Never blindly retry or reset a consumed release; independently inspect RDS first after any failure or uncertain acknowledgment. Independent target inverse94/controls and a fresh no-op are required after acknowledged apply.
