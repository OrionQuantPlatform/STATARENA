# Local candidate deadlines: E2E specified before correction

ROOT authorized only a source-free local writer correction after null-fix commit
250020e62227e9269fa0c10110f4635a0901d5b8. Normalizer4b98,model,capture1498,
failed4-query capture,old89-query ledger and all prior receipts stay unchanged.
No new capture/RAM/source access,remote SQL or real typed import is authorized.

The harness starts PostgreSQL but supplies no writer statement/lock timeout.
The existing main and fresh worker connections use psycopg(pg.dsn) plus SET ROLE,
so a real runtime check must expose unlimited0/0 before the implementation fix.
Source capture OPTIONS are already correct and are not changed by this lot.

| Actual local connection/call | Expected observable result |
|---|---|
| Main E2E writer | actual role orion_pro_ingest,statement_timeout8s,lock_timeout1s before any candidate import |
| Fresh exec worker connection | same startup settings and actual role,reported by its genuine worker branch without RAM/source access |
| Candidate import with0/1s,7s/1s,9s/1s,8s/0,8s/999ms,8s/2s | CandidateError for nonconforming deadlines BEFORE source binding/normalizer/fact writes |
| Candidate import with8s/1s and deliberately absent source snapshot | deadline gate passes,then existing source binding guard refuses; no body/fact created |
| Local connection under wrong role | existing role restriction still refuses |
| Localhost connection policy | unchanged whitelist; no remote host is contacted |
| Every probe | all94table/67sequence fingerprints unchanged; no synthetic sports data |

Write the complete new E2E before changing writer options or the candidate API.
The E2E records the actual main settings,exercises import_candidate on real owned
PG connections with nonconforming settings,and launches the real --worker branch
in a source-free --deadlines-only mode. Its initial run must retain genuine RED
main0/0 and missing deadline guard/worker behavior. The expected8s/1s are fixed;
never raise,lower or bypass them to make a slow seal pass.

After RED,set statement_timeout=8000 and lock_timeout=1000 in libpq startup
options for both main and fresh worker. Add a candidate entry gate that reads
actual current_user and timeout GUC values before source binding or any write.
Keep the existing localhost and actual ingest-role restrictions. The source-free
worker mode must call this same gate and exit before socket/source loading.

The local deadline test and prior8preparatory cases must pass together. The14
JSON error cases remain part of that run. Four real native/spatial/import/replay
stages remain unverified. Save exact rerun,source/spec snapshots,settings/errors,
fingerprints and owned PG cleanup. Check both source ledgers and ROOT metadata
receipt bytes before/after. This test does not prove a0.5M-row real seal fits8s;
ROOT's validator performance work and its evidence are separate.

```sh
PYTHONPATH=/tmp/statarena-publication-test-python python3 docs/verification/orion-pro-real-native-spatial-20261104/e2e.py --prepare-only --label local-deadlines-precode-red
```

A later real capture requires ROOT review/commit and a distinct second release.
Do not create a new ledger or start RAM while implementing this local gate.

Suggested commit: `test: enforce local candidate database deadlines`.
