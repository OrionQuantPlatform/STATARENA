# Full-objective readiness audit

**The full migration is not achieved.** The bounded live metadata capture succeeded with TLS verification and a read-only RDS identity. The serving namespace contains159 base tables and5views, with zerojson/jsonb/bytea columns. It still contains only2 published partitions,189matches and8,304appearances, with484partition jobs waiting. The last publisher receipt reports36,709remaining units. That last-run value is not a newly executed source discovery. [Actual metadata and command](metadata.json).

[Requirement-by-requirement audit](requirements.json) distinguishes the deployed/current-scope evidence from full publication, whole-site validation, live writer verification, production cutover and retirement. No narrow browser run or green CI is treated as full completion.

GitHub lists14workflow records, but only6current definitions exist in main and the backend branch, with identical path sets. One extra record is GitHub-generated dependency graph work; seven other records have no current file in either tree. Their old branch/manual histories were preserved. The existing availability monitor is disabled_manually. All six current workflow definitions are accounted for in the migration code; main has not been cut over. [Authoritative inventory and commands](actions-inventory.json).

The remaining legacy cleanup was rebased and tested as an isolated63-path patch. It preserves175sensitive current paths, migrations003–009, final data transport and browser behavior. The parent separately verified five actual PostgreSQL publisher flows and ten HTTP cases through its candidate app entry. Ingestion-role environment separation and an obsolete frontend fixture were corrected in that private preparation. Its checksum-pinned artifact is retained for future review. [Prepared patch and all tests](../aws-retirement-prepared-20261104/RESULTS.md).

Current RDS remains20GiB/micro with no pending modification; the post-compaction full footprint is estimated~27.8GB before reserve, retaining original sources. The exact20→64GiB proposal and+$5.06USD/month storage calculation remain [awaiting explicit owner approval](../aws-capacity-20261104/storage-change-plan.json). No full backfill or cleanup activation was performed in this audit.

After an approved/verified capacity change, align the admission guard, resume existing jobs without --all, prove complete source coverage and API/UI integrity, validate the active AWS writers, then perform production cutover and activate the reviewed retirement patch. Source data stays retained. Disabled workflows stay disabled unless separately authorized.

Suggested commit: `docs: audit full AWS readiness and prepare gated legacy retirement`.
