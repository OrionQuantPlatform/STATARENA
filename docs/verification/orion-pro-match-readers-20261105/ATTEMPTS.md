# Owned native match detail attempts

Suggested commit: feat: serve six versioned typed match detail routes.

The complete inputs, exact command, HTTP and SQL traces, first failure and
cleanup are in each dated result below. No source services or hosted database
were used. The prefix of an evidence SHA is included for quick comparison.

| Attempt | Observable result | Evidence |
|---|---|---|
| 016 unwired v1 | Python could not resolve the historical fixture module. No PostgreSQL or HTTP started. | [3618dbf1](runs/20261105T165713310229Z-native016-actual-unwired-red-v1/result.json) |
| 016 unwired v2 | Frozen V1 baseline read, 415 typed rows, SQL CHECK stopped synthetic READY because its fixed finish preceded the real start. No native HTTP request. | [229fcb12](runs/20261105T165744310961Z-native016-actual-unwired-red-v2/result.json) |
| 016 unwired v3 | R01 passed; R02 actual application returned 501, no-store, zero SQL for that request. R03–32 unverified. Changed the synthetic build clock only; the runner's explicit deadline was shortened to 60 seconds for this allocation. | [60ead1a4](runs/20261105T170149678930Z-native016-actual-unwired-red-v3/result.json) |
| 016 wired v1 | R01–13 passed. The R14 fixture hit the existing physical lineup variant uniqueness constraint (23505) before the intended scalar mismatch. R15–32 unverified. | [e460e9d4](runs/20261105T170451475590Z-native016-actual-after-v1/result.json) |
| 016 wired v2 | R01–21 passed including the corrected R14. R22 leading-zero failed with the intended 016 locator guard; the invalid count failed with the earlier 013 whole-parent count guard, not the assumed 016 diagnostic. R23–32 unverified. | [0471d17f](runs/20261105T170941541528Z-native016-actual-after-v2/result.json) |

The R14 fixture correction closes the old native lineup member and header
intervals by their exact previous coverage key within the rollback-only
negative transaction. It preserves the intended 23514 guard assertion and the
old published bytes, rather than accepting the unrelated 23505.


The corrected R22 oracle distinguishes the exact diagnostics: 016 rejects a
leading-zero locator and 013 rejects a wrong total. Both require SQLSTATE
23514. The invalid drafts must roll back and the old HTTP representation must
remain byte-identical.

Both final owned runs passed:

- [6863b1d6](runs/20261105T171053104195Z-native016-actual-after-v3/result.json):
  R01–R32, including both exact R22 diagnostics. Runtime app and match reader
  were unchanged; the separately qualified V1 appearance coordinate fix was
  pinned as bff9b8d0 in the current actual import graph.
- [d91cec33](runs/20261105T171116890811Z-native017-actual-after-v1/result.json):
  13 coexistence regressions plus C01–C10 in the same cluster before and after
  append 017. Migration, model, binding and runtime pins are recorded separately.
