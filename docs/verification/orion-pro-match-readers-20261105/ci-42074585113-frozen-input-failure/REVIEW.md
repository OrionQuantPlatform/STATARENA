# Separate frozen entity inputs from the live regression

GitHub Actions run 42074585113 passed the live entity checks, then stopped the catalogue/media runner before any database or HTTP activity. The runner incorrectly checked the *current* E30 test file against an older frozen test manifest. All 12 scenarios were unverified in that run.

Verify the byte-exact historical test through its retained snapshot, like the historical router. The live catalogue/media tests still exercise the current router, the complete frozen manifest, the original four-query RED and the same 12 scenarios. Original result: artifact 13438720124, SHA-256 1717e669db15fd2160bf3dc8af18b16c20bc3b604c343974151503f258c1a343.

Suggested commit: `test: verify retained entity test input against its frozen manifest`.
