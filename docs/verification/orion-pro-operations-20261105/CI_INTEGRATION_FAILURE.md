# Preserved CI failure42037789869

Suggested commit: `test: separate frozen entity evidence from current route integration`.

The batch/media step stopped before PG/HTTP:0pass/0fail/12unverified. Its previous guard compared every first-lot manifest entry against current workspace files, including aws-app.js and the global route matrix. New operational routes intentionally changed those two mutable integration artifacts. The first entity lot and all its original receipts remain valid.

Restore its original ALL_ROUTE_MATRIX.json byte-for-byte. The new current41remaining route matrix moves to operations/API_ROUTE_MATRIX.json; the guard now reads this current matrix. For the batch/media test, verify the old route source against its retained original input, and test the captured current router through the same12functional cases plus the independent20case original-baseline guard. The original frozen manifest digest is unchanged; no original artifact/hash or expected football/media response is rewritten. No production request or business acceptance occurred in the failed CI step.
