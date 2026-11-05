# Four FIFA and UEFA ranking routes in the actual AWS router

The standalone owned module proof exercised all 24 ranking scenarios with the existing consumers. This integration wires `orionProRankingsRoute` into `aws-app.js` after the enrichment routes and reruns the same 24 scenarios against the actual app. The four ranking forms close the API route matrix: 57 of 57 forms are typed, and no catalogued form remains on the `501_before_legacy_dispatch` fallback.

The shared guard therefore replaces the three `unsupported_*_remaining4` cases with `unsupported_*_uncatalogued`. They still prove the Pro fallback (501, `no-store`, no ETag, no SQL, no legacy or source access, empty HEAD body) for an unregistered ranking subpath, an extended ranking path and an unknown capability, so the ranking module cannot swallow paths outside its four exact forms. The new `typed_rankings_frontier` case checks that unexpected, malformed or wrong-method requests on all four forms fail before SQL, legacy reads or source access.

Synthetic typed observations only. Real FIFA/UEFA source reconciliation, the publisher completeness attestation, SportsAPI legacy occurrences, the aggregate teams-still-playing field and hosted data remain unqualified. See [REAL_DATA_HANDOFF.md](REAL_DATA_HANDOFF.md).

Suggested commit: `feat: serve published FIFA and UEFA rankings from typed SQL`.
