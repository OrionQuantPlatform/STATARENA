# Retained failures

Suggested commit: `feat: serve Pro health settings and media from typed SQL`.

Precode20261105T132547635277Z:1pass/1fail/12unverified. Actual Node24 router queried nonexistent legacy statarena_app from Pro health (42P01). Owned PG and HTTP cleaned.

ProductV1 20261105T132716842170Z:7pass/1fail/6unverified. Settings projected id::text and ORDER BY id resolved the text output alias. Cursor compared bigint, so lexical ordering skipped rows (second page1row instead of11). Product fix qualifies r.id for numeric order; same pagination expectation retained. Test fixture API typo correct_edition_a was corrected to its existing correct method before this first product run; no business assertion changed.
