# Third capture, distinct from the two historical ledgers

The earlier RAM process no longer exists. This operation refreshes only the already pinned three AWS indexed documents and one existing Neon spatial object. It never calls Pitch, creates an object, writes a source body, imports a business row, or changes schema/security. The old ledgers and evidence remain immutable. The frozen capture owns its own four declared SELECTs and three object HTTP calls, bounded by the unchanged manifest limits (11 SELECT,32MiB decoded,3 HTTP,1MiB physical); no retry/reset is allowed.

Before implementation, expected operational outcomes/failure modes:

| Trigger | Expected observable outcome |
| --- | --- |
| Default/check-only CLI | Validate pins, fresh ledger and installed dependency versions; no AWS authentication, source connection or source call. |
| Any inherited `PG*`, changed code/dependency/old ledger, consumed new ledger, wrong branch or unpublished launcher | Refuse before authentication or launching capture. |
| Live capture | Use exact account/ingest SSM credential in private0700/0600 passfile; fixed host/prod/actor; frozen TLS/RO/timeouts. Code must already be on main. |
| Version/object mismatch or capture error | Stop first failure, preserve consumed ledger and metadata, no fallback/refetch. |
| No READY within180s or output over64KiB | Terminate/reap only owned child process group; remove private authentication; preserve failure receipt. |
| READY | Frozen clients are already closed. Remove passfile immediately, retain owned RAM child until ROOT sends STOP. No credentials are kept on disk while serving RAM. |
| STOP or owned launcher interruption | Record exit/cleanup; remove owned socket directory after child death. No kill of unrelated process. |

Preparation E2E uses the actual CLI with source forbidden: default path must pass; inheritedPG path must refuse, each with0source calls. The live E2E receipt records exact commands, release/ledger hashes, actual child readiness and final cleanup. No isolated test is introduced. Expected unchanged corpus:4documents,4SELECT,9682314decodedB,3HTTP,3961physicalB; identity metadata timestamps can change byte counts and are reported as observed. Pinned versions and physical hashes must match exactly.

Rerun preparation: `PYTHONPATH=/tmp/statarena-publication-test-python PYTHONDONTWRITEBYTECODE=1 STATARENA_SOURCE_FORBIDDEN=1 python3 docs/verification/orion-pro-real-rds-transfer-20261105/recapture.py --check-only`.

Live command (single consumption): same Python path, without source-forbidden, `python3 docs/verification/orion-pro-real-rds-transfer-20261105/recapture.py --capture`. The committed release pins the wrapper/actor, frozen source and old ledgers; the new initial ledger is checked before SSM. The capture's own historical `--approved-commit` binds only its unchanged normalizer; the current launcher/main publication is checked separately. Do not substitute fixture data for this origin.

Dependencies: Python3.14.6, psycopg/psycopg-binary3.3.7, boto3/botocore1.43.124, s3transfer0.19.3, jmespath1.1.0, urllib32.8.0, python-dateutil2.9.0.post0,six1.17.0. Restore with `python3 -m pip install --target /tmp/statarena-publication-test-python psycopg[binary]==3.3.7 boto3==1.43.124 botocore==1.43.124 s3transfer==0.19.3 jmespath==1.1.0 urllib3==2.8.0 python-dateutil==2.9.0.post0 six==1.17.0` (quote the psycopg argument in zsh).

This is source recovery for the approved pilot, not global data acceptance or a performance benchmark. Current RDS has native014 and no football facts; production Pro remains OFF and collectors disabled. Suggested commit: `feat: prepare real typed RDS pilot source and actor checks`.
