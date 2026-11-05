# Shot detail E2E attempts

Suggested commit: feat: serve typed match and player shot details.

[Unwired v1, fd92123b](runs/20261105T172506566866Z-shot-details-unwired-red-v1/result.json)
stopped before any HTTP. The inherited legacy fixture kept players_count=1
after the new known no-shot actor made two distinct players in edition A.
The existing READY guard rejected the false count with SQLSTATE 23514.
The new fixture computes the exact selected distinct count from SQL at
the build dataset generation. No guard or case assertion was weakened.
