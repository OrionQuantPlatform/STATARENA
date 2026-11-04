# Retained runs

Suggested commit: `test: verify paginated Pro React workflows in a real browser`.

`runs/20261104T210600396577Z-pre-react-red/result.json` is retained unchanged. Its generic initial assertion says the first 30 rows did not render, but its Next log and browser document500 show a **preparation failure**, not a React Pro integration RED: declared `flag-icons@7.6.0` was absent from the shared dependency install. PG18.6, 61/1/1 published fixture, Bun runtime readonly and cleanup passed; ten dependent UI cases were unverified. No claim of a genuine application RED is based on that run.

The next run supplies the exact declared package from the existing Bun cache only inside the owned temporary frontend. Shared source/dependencies remain unchanged.
