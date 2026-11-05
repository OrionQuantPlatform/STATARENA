# Preserve the V1 coordinate wire type after migration016

Suggested commit: `fix: retain numeric V1 appearance coordinates after widening`.

Run the eight existing actual Node24 workflows first. In the same owned populated database, capture the pinned appearance GET and its exact JSON coordinate types/body/ETag. Then install exact015 and016 in one local transaction and request the same pinned representation again. At least one nonnull stored coordinate must be exercised.

The unchanged contract is a JSON number or null. A string from the PostgreSQL numeric driver is a breaking type change, even if it contains the same digits. Preserve the exact historical response bytes and ETag, and prove cold HEAD/304 remains body-free and metadata-only. The corrective scope is the V1 SQL projection; do not change global numeric parsing or the exact-decimal native match reader.

No production migration or data, source call, provider or cloud service is exercised. Save exact installed migrations, inputs, before/after requests, fixture, cleanup and status. The first RED must run before the serving fix.
