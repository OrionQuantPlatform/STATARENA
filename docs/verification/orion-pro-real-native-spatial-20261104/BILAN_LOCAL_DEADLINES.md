# Local writer deadlines enforced

**9local preparation workflows pass;4real workflows remain unverified.**
The actual main writer and a fresh exec worker both report orion_pro_ingest,
statement_timeout8s and lock_timeout1s. No source request, new capture/RAM,
real import or synthetic sports fact was produced. `fullAcceptance=false`.

The failure matrix and complete local E2E preceded the correction. Genuine RED:
`runs/20261104T233800429837Z-local-deadlines-precode-red/result.json` (1pass/1fail/11unverified). Direct SQL readback
showed main0/0; six nonconforming connections reached the source-binding guard,
proving the deadline gate was missing; the fresh worker deadline mode was absent.
The positive8s/1s and wrong-role checks already behaved as recorded. All94table/
67sequence fingerprints remained unchanged during that RED.

The implementation sets libpq startup statement_timeout8000 and lock_timeout1000
for the main writer and the real fresh-worker branch. It adds candidate
validate_local_writer(), called first by import_candidate(), which checks actual
role and current timeout GUCs before snapshot binding or normalizer/fact writes.
The localhost whitelist and exact ingest role restriction remain unchanged.
The worker's source-free deadlines-only mode uses the same connection path and
same guard, returning before socket/source access. It does not create a fake
RAM source or bypass the real import gate.

Final receipt: `runs/20261104T233911598302Z-local-deadlines-final-source-free/result.json` (9pass/0fail/4unverified).
Detailed settings/API results: `runs/20261104T233911598302Z-local-deadlines-final-source-free/local-deadlines-result.json`.
All10deadline outcomes pass: main; six deliberately invalid timeout pairs;
positive8s/1s reaching the existing source-binding refusal; wrong role refused;
and actual fresh worker settings. The invalid7s/9s/unlimited values are negative
fixtures that are rejected before import, not changed production deadlines.
Fingerprints of all94tables/67sequences are exactly unchanged:
`bf508d05ffab2afa16d21cffcc9dda8d5c2ab3ce68991fe15409c1a89f68fd08`. No sports row, source correction or foreign identity
was inserted. Both owned local servers were stopped and removed.

The prior14case JSON-null E2E also passes unchanged. Capture1498,normalizer4b98,
model,failed v1budget4SELECT/9666054B/0HTTP,old89-query ledger and ROOT's one-shot
metadata result remain byte-identical. No capture-v2 ledger or authorization is
inferred from this local pass. All earlier null-fix/source-failure/preparation
inputs and receipts are retained.

This pass proves configuration and refusal behavior, not large-dataset sealing
performance. No0.5M-row seal was run here and no timeout was relaxed for success.
ROOT's separate semantic-equivalent validator optimization/qualification remains
necessary before a real import if old013cannot seal within8s. Real native478547
slots and1344triplets remain unverified. Another source capture/import requires
ROOT's separate review,commit and second release.

Hashes:

- Candidate: `218f378b599cd166f747fbacf6f79148220150fbc2bede4f81bef535eca553bc`
- E2E: `10d25d137810983c53f8ded21a1015dfc9b01821e386b67b85d9d57247ee2240`
- Local deadline protocol: `835c5e23e519a4a09fbadae901cc0c2be5ac16549e7fd18a6ef04fea778c2782`
- Final result: `aa40deca6b8743a18b230f5b4f0b766cf415002e7684dcf6656e678ff4fbd3eb`
- Local deadline proof: `606d95441a6d540087478b90a133bb08a39ef70c7bb2720650d57bbe234fc817`
- Frozen capture: `1498d36da2f83ea548db8a3433dd4d78f08add0e0bd6a5c90ef68b60851f7fe9`
- Failed v1ledger: `58266b444de46a8c957e2f5b480f5dfcb2f9bddba83402615723c16d5cca7281`

Exact source-free rerun:

```sh
PYTHONPATH=/tmp/statarena-publication-test-python /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 docs/verification/orion-pro-real-native-spatial-20261104/e2e.py --prepare-only --label local-deadlines-final-source-free
```

Suggested commit: `test: enforce local candidate database deadlines`.
