# Selected match tab in the mobile scrollport — before correction

Suggested commit: `test: verify paginated Pro React workflows in a real browser`.

The parent review of the retained mobile screenshot found that the Tirs panel is displayed while its selected tab remains outside the horizontal tablist viewport. The original mobile assertion covered page overflow and working pager clicks; it did **not** certify visibility of the selected analysis tab. Preserve the earlier run as that narrower result.

Use the same complete local PG18.6 → read-only Bun Pro API → actual isolated Next frontend → real Chromium setup. Open A's summary from an actual match row, activate `Tirs & xG` at desktop width, wait for the genuine typed shot/point, set the document scroll to its initial top position, then resize the existing browser page to390×844. No application data, cache, response, stylesheet or tab attribute is injected.

Before any frontend correction, extend the E2E with this failure matrix:

| Case | Required outcome |
|---|---|
| Desktop-selected Tirs followed by mobile resize | Selected tab's complete horizontal bounding rectangle lies within the visible tablist scrollport and viewport, allowing1px rounding |
| Tablist wider than mobile viewport | Geometric check uses actual tablist bounding rect, clientLeft/clientWidth, scrollLeft and selected tab rect; Playwright isVisible alone is insufficient |
| Horizontal correction runs | Document scrollX/scrollY remains0 from the controlled top-position setup; selected tab correction does not move the whole page vertically |
| Failure | Actual geometry/scroll offsets, screenshot, settled DOM, network responses, SQL traces and cleanup retained as RED; no product fix by this harness owner |

The bounded counterexample rerun is `python3 tests/orion_pro_ui_local.py --label mobile-selected-tab-red --mobile-tab-only`. The complete workflow includes the same geometric case after correction. This verifies one real responsive Chromium viewport, not physical device/touch behavior.
