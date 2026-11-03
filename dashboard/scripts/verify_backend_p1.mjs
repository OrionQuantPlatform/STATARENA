process.env.STATARENA_TEST_EXTENSION = new URL(
  "./verify_backend_p1_cases.mjs",
  import.meta.url,
).href;
process.env.STATARENA_TEST_EVIDENCE ||=
  "docs/verification/backend-p1-20261103/after";
await import("./verify_backend_cache.mjs");
