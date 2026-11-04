# Parent review — bounded schema/bootstrap scope

Suggested commit: `docs: record parent acceptance boundaries for the Orion pilot`.

The parent reviewed the pure schema compiler/local migrator, complete integrity generator, guarded RDS wrapper, final real-source normalizer and its last two fixes, independent readback/catalogue helper and the local TLS drift workflow. Sub-agent conclusions were checked against the actual code and result artifacts; delegation is not treated as acceptance by itself.

Accepted component evidence before a remote schema decision:

- Current-model PostgreSQL workflow: 23/23, 57 invalid operations rejected; actual applied 012/013 and immutable original model retained.
- Native metric states: 25/25; four targeted CHECK changes and four descriptions replay exactly from the original approval.
- Real local sources: 15/15, with `fullAcceptance=false`; source IDs, hashes, common native state/projection equality and missing/wrong profiles are explicit. No new raw-body storage or remote data write exists in this entry point.
- RDS CLI: seven offline workflows; default preflight remains read-only. Apply requires committed exact main source, explicit parent receipt and fresh capacity/identity/lease checks.
- Readback: eight owned PostgreSQL/TLS workflows. A healthy catalogue passes eleven cases; column UPDATE privilege, changed CHECK, index, removed view, FK action and UQ null semantics are actually rejected. Source-bound normalized definitions cover 94 tables, 46 views, 67 sequences, 1709 columns, 1476 constraints, 352 indexes, 90 functions and 84 triggers. The parent independently revalidated the expected-catalogue hash/source binding.

The readback review found three real blind spots in the initial script and a SQL privilege evaluation error. Their original REDs remain under `rds-readback-local-runs/`; later passing results do not overwrite them. The normalizer review likewise found context-rounded decimal hashes and absent collections mislabelled empty; genuine pre-code counterexamples were retained before the fixes.

The next RDS acceptance is **only** additive schema/bootstrap/grants in `ingest`, `football`, `analytics`, on the existing PG18.6/64GiB instance. It does not accept real-data migration, a production collector/publisher, complete native source fidelity, a web reader, cleanup, a new AWS resource or public cutover. The wrapper exposes no remote reset/rollback. Source document metadata guards permit only audited forward retention transitions; source body purge is outside this step.

UX remains on the previously accepted production bridge while data is incomplete. DX gains a deterministic approved-model compiler, checksummed migrations and reproducible local workflows. AX gains explicit CLI modes, bounded reads and inspectable receipts. The tradeoff is additional temporary schema/storage and unfinished compatibility work; no production speed or cost gain is inferred from this pilot.

Known importer limits remain blocking for full acceptance: fresh-process resume, full useful-field/variant reconciliation, common metrics beyond the four registered slots, source coordinate semantics, complete profile/media/enrichment coverage and real production aggregation/publication/cache flows. No missing or unverified field is accepted as observed zero, null or empty solely to make a test pass.
