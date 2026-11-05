# Real core into existing RDS, separately released

This operation transports the verified committed core from its owned typed SQL checkpoint into the existing statarena_prod as statarena_ingest. It does not call a provider, capture another source, create schema/grants, publish analytics, activate Pro or delete a source. Its input is the two-season AWS-derived core, not the failed spatial phase. Missing useful fields and detailed families remain explicit; matches stay draft until independently admitted by the later real publication boundary.

Preconditions: source checkpoint35dba5b9… READY, independent native31 source=SQL5f9175c… and94tables/67sequence values unchanged after a fresh core-only no-op; native94 hash220b5da1…/553562physical rows. The current RDS P1 was independently compared in full to e24d… at rds-pair-readbacks/20261105T113633129823Z,20SELECT/6.631s,bootstrap-only. Distinct source012013+P1overlay and real target012013014 policies are never aliased. The native transport9ec803… and its immutable dependencies are qualified21/21 plus9/9 independent local cases, including generation≠snapshot remapping.

Expected operational E2E:

1. Default CLI opens no client. Exact committed metadata/code/authority is required; inheritedPG refuses before SSM. The separate preflight allocation may run once and must return preflight,0COPY/0nextval,closed clients.
2. Apply requires the successful preflight and separately generated apply release. One ordinary-ingest phase copies all accepted core business rows without changing their native IDs/values. Only declared technical generation/snapshot references and three control contracts are regenerated. Actual native8sSQL/1slocks remain. A timeout/refusal rolls back the phase; consumed sequences are legal gaps and are never reset.
3. Each mode has its own once-only checkpoint, one private auth lifecycle,900s absolute owned child bound,8MiB captured output. Metadata/payload caps remain those of the qualified pilot (500k/table/2Mtotal/64phases); they do not define final production scale. No new resource or grant.
4. Never retry a failure or uncertain COMMIT blindly. Preserve original stdout/report/counters and inspect the actual target prefix independently first. Private authentication is removed and child reaped on every controlled outcome.
5. After acknowledged apply, ROOT independently compares91business tables with SQL-native inverse substitutions from the frozen106column contract and verifies3regenerated controls, journal/B0/clocks/copy totals. It must also verify a fresh-process no-op without extra allocations. This readback is separate from the writer's own oracle. No production cutover or source deletion follows from pilot success alone.

Exact invocation after ROOT metadata release: `PYTHONPATH=/tmp/statarena-publication-test-python PYTHONDONTWRITEBYTECODE=1 python3 docs/verification/orion-pro-real-rds-transfer-20261105/rds_core_operation.py --preflight`, then `--apply` only after reviewing that receipt. All nonsecret inputs/commands/hashes/observed outcomes are retained in real-core-operation/. Source controller remains idle/read-only until ROOT STOP. AWS authentication uses the existing CLI profile; any renewal must use Dia.

Suggested commit: `feat: prepare verified real core transport to RDS`.
