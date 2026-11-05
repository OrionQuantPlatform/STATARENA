# Readonly native RDS pair preparation

Before business transport, independently compare the actual existing RDS P1 with the committed014 final readback. A descriptor carrying the string e24d… alone is not an attestation. The entire stable native state (94relations,1709columns,2475nativeconstraints,views/indexes/guards/roles/ACL/defaults,original journal/bootstrap and67sequence values) must hash to the independently accepted e24d2f4864f2a24c639d5556b4012d276b8958f5df3d02e2a80e52a601ae9a32. Refuse drift or any nonbootstrap fact before publishing a transport target descriptor.

Operator default is offline. `--observe` uses one existing admin credential in a private0700/0600 passfile, fixed verified RDS hostname/address/prod/CA, actual admin identity/TLS/PostgreSQL18.6, readonly repeatable-read,8sSQL/1slocks. No schema, grants, facts, sequence allocation, collector or publication change. InheritedPG settings refuse before AWS. Bound one observation to24SELECT/90s/32MiB retained metadata, using the previously qualified native envelope/bounds. The native observation itself keeps its14SELECT/4MiB envelope. The separate transport catalogue descriptor is prepared in the same snapshot and later rechecked by the ordinary ingest worker. Admin sequence reads here never grant SELECT to ingest.

Expected E2E outcome: actual native hash exactly equals the prior P1; separately serialized target descriptor identifies current epoch, exact catalogue/security/function properties, actual012013014 clocks and bootstrap. Close the connection and remove private authentication on success/failure; preserve a new timestamped receipt and exact inputs. This does not authorize business writes or prove data/backend completeness. Any mismatch is a failure, never a new baseline inferred from itself.

Rerun preparation: `PYTHONPATH=/tmp/statarena-publication-test-python PYTHONDONTWRITEBYTECODE=1 python3 docs/verification/orion-pro-real-rds-transfer-20261105/rds_pair_readonly.py`. Live readonly command adds `--observe`. Requires already authenticated AWS CLI profile statarena; if authentication is needed, Dia only.

Suggested commit: `test: attest real RDS policy before typed transport`.
