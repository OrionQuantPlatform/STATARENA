# Four shot-actor metadata readback

ROOT authorized at most4SELECT statements /32KiB decoded metadata on the existing
readonly core source, with no restart, RAM read, cloud/RDS/Neon call or mutation.
Publisher supplied four exact2025shot IDs, public match/player/team IDs, source
document SHA and locators. The core source joins both seasons.

Expected workflow:1identity/TLS/RO RR/8s/1s check;2global stable player aliases,
profile identity/provenance and performance counts grouped by source document;
3the exact requested match/player/team participant cohorts;4exact shot record
IDs, actor foreign keys and source document/locator metadata. All outputs are
IDs, locators, hashes and counts; no player names/scalar sports values or bodies.

Each SELECT uses a server JSON byte/row envelope, with at most8192decoded bytes
including framing; total at most32768bytes. Stop if an envelope refuses, identity
differs, query fails or timeout occurs. No extra SELECT retry is authorized.
Record exact setup, command, inputs, SQL/parameters, expected and actual results,
query counts/bytes and closed connection. An absent2025performance or exact
match cohort must not be inferred to mean a globally absent player/profile.
The supplied per-shot source row digests are recorded as supplied witnesses;
this metadata-only read does not recompute row digests from a raw source body.

The source checkpoint, native94evidence and serving controller remain immutable.
Suggested commit: `test: inspect global core identities for four shot actors`.
