# Fixture aliases integration boundary

Suggested commit: `feat: serve published fixture compatibility routes`.

The original 50-closed-form inventory remains historical and unchanged. The current actionable matrix records two additional qualified forms: date and league fixture lists. The current guard must export the new runtime module, exclude precisely these two forms from the 501 frontier and require 38 remaining forms to refuse before legacy/source access. Existing 11 ProOFF positive controls and four frozen V1 reader bodies/ETags remain required.

For both aliases, missing/bad v must return400 with zeroSQL and zero legacy/source work. A valid explicit edition token must return200 through the published fixture reader, HEAD must return an empty body, and matching conditionalGET must return304 with empty body and metadata SQL only. The positive 16-case suite separately verifies page traversal, cursor/filter/edition binding, score/date/status DTOs, corrections and3SQLGET/2SQLHEAD304. Global date traversal across editions is a frontend task, not implicit whole-dataset behavior.

All checks use owned syntheticPG18.6 and actual HTTP only; no cloud, source body, real data, production performance or complete backend acceptance follows from this guard.
