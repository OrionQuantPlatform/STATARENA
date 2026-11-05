The five typed enrichment routes passed **24/24** cases on Node 24.22.2 and PostgreSQL 18.6 in the isolated HTTP adapter with existing application controls. This qualifies the module with synthetic typed data. The actual app wiring and production data/release are separate.

- Before implementation, Node 24 produced the expected missing-entrypoint error, with no PG or HTTP started: [RED receipt](runs/20261105T173524362138Z-node24-entrypoint-absent/result.json), SHA `f99308afc4bd5da351e42a81870c53b68a3ac81efda3d9688a5e32692f086a7d`. The initial runner is retained byte exact in `prepatch-attribution/`. The attribution correction used additional E2E assertions written before that correction; the first module candidate and amended prepatch input list remain inspectable there. The old incomplete manifests are historical and were never used to authorize PG.
- [V1](runs/20261105T174852390693Z-enrichment-product-v1/result.json) stopped at P03: an inherited fixture path shadowed the fixture helper. P00–P02 passed; 20 cases were not executed. It used 276 SQL and 19 HTTP in 3.214 s. All four cleanup checks passed. V2 changes only the fixture helper name and its ten call sites. The product and executable assertions are byte identical across both runs.
- [V2](runs/20261105T175249748741Z-enrichment-product-v2/result.json) used **964 SQL** reservations and 964 server statements, **104 HTTP**, and **6.093 s**. Owned disk peaked at 71,786,496 bytes, evidence at 7,769,057 bytes during the run. Four cleanup checks passed. All 63 input pins matched. No provider, Neon, cloud, source or RDS call; eight blocked calibration attempts, zero unplanned attempts. The HTTP client did not follow external redirects.

| Route | Successful GET SQL | HEAD / conditional SQL |
|---|---:|---:|
| `/api/club-wikidata` | 3 by exact name/country; 4 by exact UEFA ID | 4 for the tested UEFA request |
| `/api/coach-portrait` | 2 | 2 |
| `/api/stadium` | 2 | 2 |
| `/api/player-honours` | 4 | 3 |
| `/api/club-links` | 2 | 2 |

All five HEAD and conditional responses have zero body. Honours HEAD/304 runs its bounded winner metadata query and skips the body query. The actual existing AWS asset handler returned GET and HEAD 307 with one metadata statement each; the redirect target used the exact content key. An asset correction changed the old portrait's ETag and redirect target; a second row with the same alias was rejected. The fixture did not fetch image bytes.

The actual front-end consumers read the untouched wire. They recovered the club by leading-zero UEFA ID and by exact typed country/name; the Commons alias resolved to `/api/assets`. They displayed two honour groups and three labelled winning editions, while the typed DTO retained one unlabelled winning edition and the original Wikipedia revision URL. An unbound source document stayed unavailable and a malformed citation failed before conditional handling.

The real native catalogue trigger rejected a draft pointer with SQLSTATE `23514`. A new sealed catalogue changed capacity from 0 to 50,000, leaving the retained old token byte stable. Unknown and competing coach tenures stayed explicit. Readback hashes of **94 tables, 67 sequences and 339 rows** matched before and after the final read phase; runtime write returned `25006`. Four frozen V1 bodies and ETags matched exactly.

The fixture does not test production scale, AWS delivery, or the original source populations. Model103 cannot publish an official club-to-home-venue link, venue creation date, or the existing stadium plan registry through this adapter. Those remain explicitly unrecorded. See [real data handoff](REAL_DATA_HANDOFF.md) for the remaining typed admission work. No inference from match venues, missing tenure bounds, or title strings.

Suggested commit: `feat: serve typed club facts portraits stadiums honours and links`.
