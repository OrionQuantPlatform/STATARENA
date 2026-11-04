# Exact preparation and proposed capture commands

Run from `/Users/lemonnierhugo/Desktop/Coding Project/Football_ranking` with the
existing Python dependencies in `/tmp/statarena-publication-test-python` and the
embedded PostgreSQL18.6 binaries. No command performs login or installs tools.

Preparation only (no source access):

```sh
PYTHONPATH=/tmp/statarena-publication-test-python python3 docs/verification/orion-pro-real-native-spatial-20261104/capture.py --check-only --expected-selects 0 --expected-decoded-bytes 0
PYTHONPATH=/tmp/statarena-publication-test-python python3 docs/verification/orion-pro-real-native-spatial-20261104/e2e.py --prepare-only --label frozen-preparation
```

The preparation suite uses an owned disposable PostgreSQL server and SELECT-only
synthetic guard metadata. It inserts no synthetic sports rows. Expected:7pass,
4real steps unverified, status`prepared_real_unverified`; both source ledgers
unchanged. The code and fixtures are snapshotted into the run inputs.

**Do not execute the following capture until ROOT separately approves this exact
manifest/protocol/code.** Its source-authorized flag records that later decision;
preparation and the earlier commit alone are insufficient authorization.

Use a fresh private directory and leave this process running while local E2E
uses the same socket. This proposed path has not been created by preparation.
If it already exists, stop and inspect; never delete/reuse it implicitly.

```sh
mkdir -m 700 /tmp/orion-real-native-spatial-20261104-v1
PYTHONPATH=/tmp/statarena-publication-test-python python3 docs/verification/orion-pro-real-native-spatial-20261104/capture.py --ledger docs/verification/orion-pro-real-native-spatial-20261104/budget.json --expected-selects 0 --expected-decoded-bytes 0 --approved-commit 4a6ae73222951c553dfa5fa89a2910a191b7416d --source-authorized --socket /tmp/orion-real-native-spatial-20261104-v1/source.sock --evidence docs/verification/orion-pro-real-native-spatial-20261104/capture-v1
```

The source connections are sequential: AWS closes before Neon opens. Effective
hard limits across both origins are11SELECT,33554432decoded bytes,3object HTTP
requests and1048576physical HTTP bytes. Nominal4SELECT/3HTTP. The AWS body SELECT
has server LIMIT3 and8MiB per document (24MiB total); profile metadata is admitted
server-side at most2048rows, capped text sizes and min2MiB/remaining global bytes.
Neon object3957B/decoded16259B is pinned by exact key/SHA and conditional ETag.
The three HTTP operations are HEAD,GET last4bytes,GET entire one object, no retry.
No source file is written or transferred to AWS/S3/RDS. Existing Neon auth is
validated privately before the first source connection; missing/changed config
or new auth requirement blocks without login. Secret values never enter logs.

After the ready receipt, in another process:

```sh
PYTHONPATH=/tmp/statarena-publication-test-python python3 docs/verification/orion-pro-real-native-spatial-20261104/e2e.py --source-socket /tmp/orion-real-native-spatial-20261104-v1/source.sock --label real-native-spatial-v1
```

This candidate starts empty and contains real source-derived core facts and the
selected spatial observation only. It never invokes the old real-pilot test,
its demo correction or its foreign fixtures. It performs no remote SQL writes.
The new test’s independent SQL oracles must compare the31native slots per source
performance and exact sparse source tuples. Historical expected478547slots and
1344triplets are reported against actual source counts; neither is fabricated.
If identity/cohort/precision differs, retain the failed/partial evidence and RAM
for analysis; do not adjust participants, source values or thresholds to pass.
Full acceptance remains false even when all scoped oracles pass.

The test launches a fresh exec process against the same RAM and compares all94
SQL table hashes/67sequences before/after. Further authorized local iterations
must reuse this socket; there is no source fallback or recapture flag. A lost
capture is consumed and requires a new explicit authorization.

When ROOT closes the RAM phase:

```sh
python3 - <<'PY'
import socket
with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as client:
    client.connect('/tmp/orion-real-native-spatial-20261104-v1/source.sock')
    client.sendall(b'STOP\n')
PY
```

STOP releases the snapshot and removes the socket. The metadata budget and every
failure/receipt remain. No command here resets either ledger.

Suggested commit: `test: qualify native metrics and sparse heatmaps from bounded real sources`.
