# Native route activation and the entity boundary check

The original Linux run 42073282469 is retained. Its unchanged entity fixture passed 29 of 30 cases; E30 expected the old unimplemented status 501 on the now-owned lineup route. The actual request returned 400 NATIVE_MATCH_VERSION_INVALID with zero SQL and no caching. The failure is in the test's route inventory assumption.

The live E30 retains a zero-SQL 501 witness on an unregistered match path, asserts the new zero-SQL 400 for the old unversioned lineup request, and asserts a 503 after metadata only when an old READY publication is explicitly requested as native. It still checks every trace for legacy queries and external calls. The original frozen receipt and runner are unchanged in their original bundle.

Rerun the original on commit `7eb01f0aff3d937736769299d8f2d8911c85bd29` with the command and inputs from result.json. Source: GitHub Actions artifact 13436698578. Artifact result SHA-256: d201050f3bbd82089a372b3b805d1ddb4d82456bce86d6046fb1dfa385cefbab .

Suggested commit: `test: keep entity boundary checks current with native match routes`.
