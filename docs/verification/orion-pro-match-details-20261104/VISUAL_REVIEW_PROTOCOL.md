# Static model review export

Suggested commit: `docs: propose typed native match detail amendments with cohort proofs`.

This protocol precedes the local document generator and its browser check. The output is a review of a **proposal**, not a new approved model, migration, SQL compiler result, database E2E, data acceptance or reader implementation. Only this directory may be written. No service is started; the browser opens the standalone HTML through a local file URL. No AWS, Neon, provider, raw source, database or application API is used.

## Inputs and reproducible command

From the repository root:

```sh
python3 docs/verification/orion-pro-match-details-20261104/build_review.py
```

The generator pins the approved model to SHA256 `18da43f940870b7a3a3cb49323c847dd5e5174e5eea1f8ff0c8a159cf373cb08`, reads AMENDMENT_SPEC.json and FIELD_MATRIX.json, builds the RFC6902 patch, applies it to an in-memory copy, then writes a candidate **only in this directory**. It never imports or invokes a migrator, compiler, normalizer, DB client or cloud SDK. The base model and012/013 are hashed again after generation and must match their input hashes. All links and embedded catalogue content are local. There is no network dependency or sporting source body.

Outputs: PROPOSED_MODEL.patch.json, target-schema.native-details.CANDIDATE.json, STATIC_PATCH_CHECK.json, MODEL_DELTA.json, COLUMN_DICTIONARY.json/.md and NATIVE_MODEL_REVIEW.html. The candidate is a base+patch review materialization; original planning/status metadata is retained, not a declaration of approval. Counts must be computed from actual before/after documents, including active/deferred subsets, not copied from narrative text. Two existing finite CHECK definitions must be replaced, alongside the four column replacements, rather than duplicated; STATIC_REVIEW_FAILURE.json preserves the first strict static refusal. This is a document check, not PostgreSQL execution.

## Failure matrix and expected outcomes

| Failure mode | Expected result |
|---|---|
| Different base model, missing table/column or replacement precondition | Stop without writing generated output |
| A changed table or added column outside the explicit specification; removed/reordered base table | Static check fails; the103 existing definitions must remain present with only the declared deltas |
| Missing FK target/column, target not PK/UQ, duplicate identifier, identifier over63 bytes or invalid proposed column reference | Static check fails; no SQL validation is inferred from passing |
| State enum has no explicit SQL CHECK | Static check fails; allowed_values alone is not enforcement |
| A collection CHECK permits present/empty with NULL count through CHECK UNKNOWN | Reject the proposed expression; require count IS NOT NULL and the explicit cardinality relation |
| Inaccurate table/column/FK/JSONB delta or incomplete dictionary | Stop; expected4 new typed children,114 added columns and4 replacements, with exactly114 unique dictionary entries |
| Child gains an independent knowledge interval, generic JSON value/body field or unknown new parent | Stop; inherit the existing coverage version and preserve typed values |
| HTML omits candidate tables/columns/relations or confuses proposed with approved | Browser/static check fails; all107 tables searchable, including9 deferred, with new/modified/retained status |
| Dictionary filtering or table search uses only the currently selected table | Browser check fails; search spans all114 additions or all107 full table definitions respectively |
| Browser script error, missing content, unlabelled controls or page-wide mobile overflow | Browser check fails and screenshot/logs retained |
| HTTP/HTTPS/WebSocket or other external request | Browser check fails; CSP blocks network and the document must need none |
| Claim of approved/applied/SQL-validated model or complete real-source fidelity | Fail review; unresolved fields/gates and unimplemented seven cross-row rules remain explicit |

## Browser workflow

Use the Playwright CLI skill with a named isolated cached Chromium session, opening the local `NATIVE_MODEL_REVIEW.html`. Record exact tool/browser paths and commands in the receipt. Install no browser/package or external asset as part of this check.

Before navigation, attach request/pageerror/console-error capture. Check the default amendment panel, exact counters, four-child parent diagram, dictionary114 and a filter for source_finished, catalogue107 and a search for a column in a retained table, explicit filters for4new/7modified/96retained, the four column/two CHECK replacement definitions,128addedCHECKs,16addedFKs and seven unimplemented rules. The FK/CHECK expectations are verified from the generated delta, not independent SQL assertions. At390px verify controls/content usable without page-wide overflow and capture a screenshot. The wide relationship diagram/table has its own labelled horizontal scroll region; all nodes/columns are not promised simultaneously visible on mobile. Screenshots/DOM/logs and actual outcomes belong in a new output/playwright receipt; failures are retained.

This checks the local review document end to end. It does not test proposed constraints in PostgreSQL or make a new reader, mapper or schema usable. Any later approved implementation needs its own pre-code owned-PG18.6 E2E with preserved RED, frozen A/B/C, read-only role and old representation compatibility.
