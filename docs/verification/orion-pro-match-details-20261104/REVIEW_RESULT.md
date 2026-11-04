# Native-detail proposal — frozen review export

Suggested commit: `docs: propose typed native match detail amendments with cohort proofs`.

Open [NATIVE_MODEL_REVIEW.html](NATIVE_MODEL_REVIEW.html) locally. It contains the four-child SVG, complete114-column dictionary, searchable107-table candidate and proposed FK/CHECK/replacement/rule definitions. The approved103-table model is linked separately and remains unchanged.

| Model definitions | Before | Proposed | Delta |
|---|---:|---:|---:|
| All tables |103|107|+4|
| Active tables |94|98|+4|
| Columns |1791|1905|+114|
| FK |450|466|+16|
| JSONB columns |51|51|0|
| CHECK |889|1017|+128|

There are65 additions on7 existing tables and49 columns on4 new children;4 column replacements and2 existing finite CHECK replacements;4 PKs,1 UQ constraint and1 explicit index added. The9 deferred model tables and96 untouched definitions remain unchanged. Counts are calculated from the actual JSONPatch materialization in MODEL_DELTA.json, not inferred from a database.

The strict document export first rejected duplicate raw_pitch_x/y finite CHECK names; STATIC_REVIEW_FAILURE.json preserves that refusal. The corrected patch replaces the exact two existing expressions under test preconditions. Cardinality CHECKs also explicitly reject NULL count for empty/present. This is static proposal correction, not executed SQL behavior.

## Executed document checks

- In-memory RFC6902 application/reference/enum/cardinality-expression checks pass. The approved model and012/013 hashes match their original pinned values.
- Real cached Chromium149.0.7827.55, Playwright CLI0.1.23:11/11 local-document cases pass. Dictionary114, catalogue107, filters4new/7modified/96retained, retained-column search, four column/two CHECK replacements,16FK,128newCHECK,7unimplemented rules and8unaccepted shapes are visible.
- At390px, page scrollWidth=390, each tab target46px high, mobile search works. The wide diagram/dictionary use their own labelled horizontal scroll regions; all nodes/columns are not simultaneously visible.
- Observed requests:1 file:// GET,0 external attempts,0 browser/console errors. CSP disallows external connections. No source/football response was fetched or simulated.
- Named browser closed. No service, database, SQL compiler, migration, cloud, provider or source-body operation ran.

Exact setup, commands, expected/actual cases, source/artifact hashes and cleanup: [browser receipt](output/playwright/native-review/result.json), [raw browser log](output/playwright/native-review/browser.log), [DOM snapshot](output/playwright/native-review/snapshot.log), [export receipt](REVIEW_EXPORT.json). Regenerate the document with `python3 docs/verification/orion-pro-match-details-20261104/build_review.py`. Browser commands and cached executable path are in the receipt; preserve the existing evidence directory before any same-workspace rerun. The final HTML/candidate/harness bytes remain identical to the bytes exercised by the browser.

Screenshots: [desktop amendment](output/playwright/native-review/01-amendment-desktop.png), [desktop catalogue](output/playwright/native-review/02-catalogue-desktop.png), [mobile amendment](output/playwright/native-review/03-amendment-mobile.png), [mobile catalogue](output/playwright/native-review/04-catalogue-mobile.png).

## Still unverified and not authorized by this export

No new model approval, SQL compilation/execution, migration014, DB constraint E2E, producer/reader implementation, source reconciliation, purge, flag activation or publication.96 qualified leaf paths have proposed targets; this two-match diagnostic universe does not establish exhaustive native coverage. Unresolvable actor objects, nonstring IDs, unregistered stat bindings, unseen fields and historical losses remain explicit in UNCOVERED_AND_GATES.json.

HEATMAP_CONTEXT_PROOF.md references the preserved repeated-team insertion collision and proposes distinct exact actor-record contexts. No PG insertion/reader test of that context policy has run; a single successful old join does not accept the general mapper. Old summary-v1-shots-v1 representations require their original adapter and future compatibility evidence.
