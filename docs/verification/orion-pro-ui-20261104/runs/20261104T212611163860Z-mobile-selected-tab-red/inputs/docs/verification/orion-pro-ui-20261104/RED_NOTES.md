# Retained runs

Suggested commit: `test: verify paginated Pro React workflows in a real browser`.

`runs/20261104T210600396577Z-pre-react-red/result.json` is retained unchanged. Its generic initial assertion says the first 30 rows did not render, but its Next log and browser document500 show a **preparation failure**, not a React Pro integration RED: declared `flag-icons@7.6.0` was absent from the shared dependency install. PG18.6, 61/1/1 published fixture, Bun runtime readonly and cleanup passed; ten dependent UI cases were unverified. No claim of a genuine application RED is based on that run.

The next run supplies the exact declared package from the existing Bun cache only inside the owned temporary frontend. Shared source/dependencies remain unchanged.

`runs/20261104T210742109610Z-pre-react-application-red/result.json` is the genuine application RED, SHA256 `5babf4e174a84c079e8b8d17b2015a53ea969666c3d6845b992b933cea84e6e0`. Next document and Pro manifest return200. The old React data path requests `/api/seasons/partition?season=2024%2F2025&league=l_000001&format=columns&limit=100`, which returns503. The settled DOM/screenshot shows `Données indisponibles (HTTP 503).` and no match rows. Two cases pass (owned published setup and cleanup), one fails (render first30), and ten dependent cases remain unverified. The shared source hashes remained unchanged. ROOT was informed only after receipt, screenshot, settled DOM, browser trace and cleanup were saved; this is the pre-integration baseline.

The next fixture extension is specified before its corresponding React correction: B's private club profile has SQL `display_name=NULL` while A/C keep their selected names. This tests the existing Media `name.split` path using real SQL/API values, without rewriting the DTO.

`runs/20261104T211636636384Z-react-first-integration/result.json` retains the first post-integration run:12 pass,1 fail,1 unverified. The failed expectation belongs to the **harness oracle**. It opened C's unknown shots, received the correct404 `NOT_COLLECTED`/`no-store`, then incorrectly required that failed response to behave like a retained successful cache entry. Its retry on remount is correct under the sealed client contract. No frontend fix was requested for this result. The corrected browser workflow tests C's available summary only (1GET before/after correction,0 shotsGET); A continues to test successful summary and shots retention. The network-boundary case is rerun in full rather than excluding C404/console errors from a pass.
