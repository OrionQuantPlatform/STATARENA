# Conditional HTTP reads against PostgreSQL 18

The preregistered [local SQL/HTTP workflow](PROTOCOL.md) passed 5/11 on the unmodified baseline and 11/11 after the change. Inspect [before](before.json) and [after](after.json) for actual statements by phase, complete HTTP status/body/validator/cache headers and independent writer interleavings. All requests used the AWS route on a real HTTP listener; the proxy cases used a second listener. This is not a CloudFront, production timing or cost measurement.

| Request | SQL before → after | Contract |
|---|---:|---|
| Cold stale conditional match or catalog edition | 3 → 2 | Current 200+ETag; one metadata lookup and one version-pinned body query |
| Warm stale conditional catalog | 2 → 1 | Body from the existing version-keyed local cache; match also measured 1 after |
| HEAD / matching weak/list validator | 1 → 1 | Zero body bytes |
| Unconditional through the local Next transport | 3 → 2 | No fabricated header; caller validators forwarded verbatim |
| Writer commits a replacement between SELECTs | 3 → 4 | Pinned read misses, single metadata refresh returns replacement body and ETag |
| Writer deletes the edition between SELECTs | 2 → 3 | 404 without an ETag |
| Writer changes the version on both attempts | 5 → 4 | 503/no-store instead of a mislabelled body |
| Wildcard on stored non-200 match | 1 → 2 | 404 with original structured error rather than JSON null |
| Absent match with wildcard | 1 → 1 | 404 |

A metadata-only result may hand the calling route a request-local body loader. It captures the committed version, uses the same version-checked body query and never crosses requests. An unchanged HEAD, a matching successful conditional and unversioned supporting readers leave their existing paths intact. Default APIs do not expose the private loader. No schema, stored data, status freshness, CDN policy or deployment changed.

Suggested commit: `perf: reuse verified publication metadata for conditional AWS reads`.
