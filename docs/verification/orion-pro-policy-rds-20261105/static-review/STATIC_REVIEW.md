# Static review before any continuation

This review reads local source/model/sealed SQL/historical metadata only. No adapter/test import, PG start, SQL, cloud/source/RAM operation or product/test/ledger patch occurred. Attempt1 stays1pass/1fail/18unverified, with successful cleanup and its consumed campaign unchanged. Suggested commit: `test: audit owned RDS policy fixtures before continuation`.

## Confirmed blockers

| ID | Source | Concrete issue | Proposed narrow correction, not applied |
|---|---|---|---|
|F01|e2e.py120–122; actual25006|Owned OS-superuser setup inherits defaultRO and immediately CREATE ROLE; CREATE DATABASE would also need an autocommit writable setup session.|Verify native owned OS-superuser identity/route/data directory/TLS/8s/1s, then SET default_transaction_read_only=off on **that setup connection only**. Keep all actual statarena actor connections startupRO/TLS/8s/1s.|
|F02|e2e.py158|CHECK(public_key…) targets nonexistent football.players.public_key.|Use CHECK(display_name IS DISTINCT FROM 'synthetic_reserved').|
|F03|e2e.py170|INSERT INTO football.players(public_key) targets the same nonexistent column.|Use INSERT(display_name) with the explicitly synthetic fixture label; it creates a stable identity, no public alias or source biography.|
|F04|adapter.py queries.constraints and check_historical; e2e.py141|Q04 includes p/f/u/c/n but omits t, while the assertion counts ALL table pg_constraint rows.|Add t to the Q04 capture; exclude n **and t only from the old structural1476 comparison**. Retain all types exactly in the native baseline/delta oracle and freeze the measured current count+1.|
|F05|adapter.py artifact_path164/owned_marker153|Both resolve the supplied path before checking symlink evidence. A symlink under runs to another regular runs file is accepted as a regular contract; a marker alias similarly resolves to the valid marker.|lstat the raw leaf and refuse nonregular/symlink before resolve, then retain the existing resolved containment/owned marker checks. New passfile guard must also inspect raw leaf and raw private parent first.|

F04 is independently supported by sealed013 and the frozen guard-v2 native oracle. The historical2475 entries classify as995NOTNULL,431FK,846CHECK,105UNIQUE,94PK and4constraint triggers. Current Q04 would capture2471; the all-constraint assertion would expect a2476 sentinel cap. The four omitted keys are analytics.aggregation_builds.pro_ready_build, ingest.dataset_snapshots.pro_generation_commit, ingest.document_lineage.pro_graph_commit and ingest.sources.pro_graph_commit. They are existing013 objects, not new DDL/model changes. The current owned count remains unmeasured. Do not replace measurement with these historical numbers.

The proposed setup check is stronger than the existing server-version-only assertion: the connection is already explicitly routed to the fresh owned loopback server/certificate, but its actual native superuser/OS actor and data-directory identity are not yet asserted. The setup-mode change must follow those checks; no blanket read-write default for owner/ingest/runtime connections.

## All fixture SQL and row fields

[SQL_INVENTORY.json](SQL_INVENTORY.json) inventories32execute sites in the harness,12in the adapter, all literal mutation fixtures and historical result shapes. Its static parse confirms94active model tables/1709columns match sealed012 exactly and all model PK fields used by the independent native oracle exist. An exploratory identifier regex initially omitted names containing digits; the corrected analysis includes h2h. No product source was changed.

| Fixture / projection | Static result |
|---|---|
|football.players|0121778 defines id GENERATED ALWAYS, nullable display_name and created_at DEFAULT CURRENT_TIMESTAMP NOTNULL. No public_key. Public handles belong to ingest.public_aliases/public_aliases_current. Proposed display_name INSERT needs no other supplied field; nullable FK pairs stay NULL.|
|schema_migrations|version/content_sha256/applied_at/code_commit exist with matching types. applied_at/code_commit are schema-nullable; the suite must establish clocks through native observations, not infer a NOTNULL DDL guarantee. Repeated0hash passes the hex CHECK, so the negative digest fixture reaches the adapter.|
|football.periods|label/code exist, full_match is an actual bootstrap seed.013 pro_typed_guard prevents ordinary value UPDATE; the explicitly owned corruption fixture disables USER triggers, mutates label, re-enables them before inspection and rolls the transaction back. Privilege/runtime success is still unexecuted.|
|public_aliases_current view|Exact view exists in0127861 and the attested207relation projection. security_barrier mutation targets reloptions, not a changed SELECT definition.|
|players_id_seq|Attested as one of67sequences and produced by the sealed players identity. last_value/is_called are technical sequence projections, not model columns. setval is explicitly local read-write and restored because transaction rollback alone cannot restore it. No nextval is used by the auditor.|
|dataset_snapshots / relation_contracts|All snapshot keys referenced by the adapter and all four contract fields exist; bootstrap source queries return full SQL-native technical rows. Only the period-label corruption is presently tested; snapshot/contract negative variants are not.|
|Index/trigger fixtures|Historical index projection contains method/name/relation, and the qualified name construction is valid. Trigger projection contains kind/name and schema.table.trigger spelling. The first btree fillfactor and user-trigger-enabled mutations target existing properties. Actual ALTER privileges remain unexecuted.|
|Roles/schema/function/default ACL DDL|Identifiers and function bigint signature match sealed012/013. Roles/DB names are fixed. Native actor flags are intentionally synthetic/local and do not rebaseline RDS. All operations remain within the disposable owned PG.|
|Bootstrap install|Harness reads exact012/013 bytes and calls the existing bootstrap/role-grant producer; it does not invoke compiled_migrations or rewrite sealed files. Fixture installation code_commit deliberately matches historical c66e036…, with distinct native local installation clocks.|
|Leases/faults/local014|Migration(20261104,2), generation(20261104,1), serving97813003 fences match the declared protocol. Acceptance is prepared before holding a competing lease. Fixed014 and explicit CURRENT_TIMESTAMP journal INSERT reference existing objects/columns; no arbitrary SQL source is admitted. Runtime semantics remain unqualified after setup failure.|

## Q01–Q14 projection review

| Group | Reference and disposition |
|---|---|
|Q01identity|Technical settings/pg_stat_ssl/DB owner fields; fixed actor/session_actor and TLS/8s/1s/RR checks. Native owned start/DB callback, no current RDS owner-flag inference.|
|Q02relations/views|Retains attested207 relation identities/view definitions/options, adds owner/ACL/RLS/comments/view-column descriptors and m detection. Physical bytes alone are explicitly excluded from semantic equality.|
|Q03columns|Retains all historical keys: relation/name/type/nullable/identity/generated/default_sql; adds column ACL/collation.|
|Q04constraints|Historical16-field projection is retained. **F04 blocks completeness** until t is included and historical n/t filtering is explicit.|
|Q05indexes|Historical method/name/relation/definition/predicate/validity/uniqueness fields align. No projection-name blocker found.|
|Q06functions/triggers|Retains kind/name/identity/safe/settings/definition; adds exact owner/ACL/OID/stable native properties/language/args/result/comment. Body is separately represented by definition, while other properties remain bound. No whole local composite substitutes RDS ownership.|
|Q07journal|Historical version/hash/commit projection aligns; applied_at is added. Local exact native prefix comparisons preserve clocks; no global timestamp exception.|
|Q08bootstrap|Tagged relation plus SQL-native JSON text for snapshot,10seeds,2contracts. Expected old seed objects/contracts match existing keys; snapshot's previously unobserved fields are captured locally, not attributed to old RDS proof.|
|Q09nonbootstrap|89other active tables are inspected with EXISTS only. Returns names, never business rows; empty scope is required.|
|Q10sequences|67names derive from exact attested relation metadata, not a broad table scan. Captures native values/definitions; first RDS visibility is unverified and ingest USAGE does not prove SELECT access.|
|Q11security|Relevant named actors/object owners, memberships, schemas, default ACLs and effective grants; source columns match the frozen guard-v2 inspection contract. Old runtime297grants/3schema privileges are explicitly reconciled; new admin/native data still needs separate ROOT review.|
|Q12concurrency|Bounded technical transaction/advisory/write-lock rows, no SQL query bodies. Any nonempty set refuses. Native RDS stats visibility remains unverified.|
|Q13retained namespaces|Names only, not a source-content/version/transfer proof.|
|Q14validator|Existing bigint signature and native nonbody pg_proc properties/OID; matches the previously qualified property projection.|

All metadata SELECTs remain unexecuted in this adapter campaign. Their PostgreSQL technical fields are cross-referenced to frozen historical queries/current guard-v2 inspection source; static syntax/projection alignment is not execution or permission proof. The budget is unchanged4MiB/16SELECT/20instructions;4136960B is reserved. Exact Q04 row count and actual wire/metadata sizes require the future owned campaign. No hardcoded2475/2476 acceptance is proposed.

## Claims versus configured20cases

Only implementation_available ran successfully; owned_tls_setup failed and all remaining cases are unverified. The table distinguishes what the configured test actually asserts from broader untested variants.

| Case | Actual configured assertions | Coverage limits |
|---|---|---|
|implementation_available|Import adapter/fixed input hashes|No metadata/transition execution.|
|owned_tls_setup|Fresh TLS PG/roles/2DB/bootstrap,8s/1s/log settings|Stopped at first CREATE ROLE; subsequent setup assertions did not run.|
|prepare_composed_contract|Two native contracts, rolled-back014 overlay, all pg_constraint count+1|Blocked by F04 even after setup fix. No RDS oracle prepared.|
|offline_and_remote_boundary|Offline with poison env/tripwire; unknown CLI flags; missing checkpoint|remote-no-release/missing-checkpoint both hit CHECKPOINT first. No actual bad release/hash/target/consumed remote-ledger path is reached.|
|owned_cli_and_route_pins|Actual owned CLI plus PGHOSTADDR refusal/tripwire|Only one poison key; wrong TLS CA/start time/GUC/engine/role variants not individually exercised.|
|catalogue_and_equivalence|94/1709/431/46/67 counts and139/46/81 equivalence|Full baseline comparison exists, but no negative case for every schema property.|
|nonzero_roles_exact|Admin CREATEDB/CREATEROLE true, superfalse; expected roles='[]' refuses|This removes ALL expected roles, not a one-flag flip. No role-membership mutation.|
|native_catalogue_drift|View reloption, added CHECK, fillfactor, enabled trigger, function volatility|CHECK currently F02; no same-count CHECK replacement, view SELECT change, function owner/SECDEF/search_path/signature/type/body negative variant.|
|native_acl_drift|Schema CREATE, PUBLIC EXECUTE, default table SELECT|No owner transfer, column/sequence ACL or membership counterexample.|
|journal_and_clocks|+1µs existing012clock; wrong013hash; native timestamps aware/nonNULL|No unknown/099 chain, extra014/P0-body mismatch, NULL/naive/malformed clock or timezone-display counterexample.|
|bootstrap_and_populated|One period label corruption; one uncommitted foreign player; exact state before/after refusal/restoration|INSERT currently F03. No snapshot/contract/seed-count variants. This is a transient synthetic identity, not public alias/profile coverage.|
|sequence_state|One setval drift and restoration; all67independently observed|No missing/invisible sequence privilege counterexample.|
|leases_and_concurrency|Three fences independently plus active writer|No RDS service/stat-visibility test.|
|atomic_failures|After function and after journal faults; independent rollback state|No arbitrary network/driver/cleanup fault matrix.|
|adoption_clock_and_preservation|Single function delta; old journal exact; new transaction clock; full native preservation|Auditor hashes93nonjournal tables plus exact native journal separately =94tables. It does not emit94row-digest entries.|
|lost_acknowledgement|Actual local commit then injected lost ack; new-connection P1 readback/no-op|Readback is a new connection in same process; remote uncertain commit is not tested.|
|fresh_process_noop|New CLI process; independent93native+exact journal and67sequence equality|Local fixture only, no real source/import pair.|
|old_guards_stay_closed|Old local parser refuses unknown DB; old bulk baseline rejects014|No weakening of old helpers; broader public reader/streamer compatibility unqualified.|
|bounded_queries_and_checkpoints|Native Q04 server row/byte overflow plus in-memory budget counters|No actual remote ledger one-shot/mismatch/retry path. Watchdog budget/cleanup-failure branches are not fault-injected.|
|protected_inputs_and_cleanup|19input hashes; finally checks stop/remove/complete statuses|Normal cleanup passed attempt1; error branch is not qualified. Current finally can remove private parent even if pg.cleanup raised; see below.|

Coverage labels must be narrowed to these actual assertions unless ROOT explicitly authorizes additional E2E counterexamples before the next implementation changes. Broad names alone cannot qualify the omitted variants. All final remote claims stay blocked; fullAcceptance=false even if the future local20cases pass.

## Additional review items, not silently fixed

- `no_pg_environment` rejects PGPASSFILE. Remote currently relies on default libpq password-file lookup, so ROOT's preferred temporary-passfile path is not implemented/qualified. [PASSFILE_GUARD_MATRIX.md](PASSFILE_GUARD_MATRIX.md) specifies the new guard before code; it leaves all PG* routing/options rejected.
- Current finally unconditionally removes private after a pg.cleanup exception. A stop failure could therefore delete a still-live owned data tree. Recommend retaining that tree for ROOT cleanup when server stop/removal is unproved, with failed status; no new fault test or fix ran here. Attempt1 normal cleanup was successful.
- The one-function/journal transition should be extracted unchanged into a private connection-independent core before its final qualification, with owned API unchanged, so an eventual separately reviewed ROOT RDS wrapper reuses it. [CONTINUATION_DESIGN.md](CONTINUATION_DESIGN.md) keeps target/auth/release/contract guards in distinct wrappers. No remote apply CLI or shared local/RDS acceptance alias is proposed.

F05 counterexamples belong in the complete E2E **before the guard correction**: after the real owned PG/contracts are prepared, create a contract symlink under the run pointing to the real contract, supply its real SHA and valid marker/DB to the actual owned-preflight CLI, and require INPUT/exit2 with no driver attempt. The old code would erase the alias and accept the positive target. Also alias the actual owned marker and require LOCAL/exit2 before driver access. Keep an ordinary regular-file positive CLI control. These are real owned-CLI workflows with physical symlinks, not SQL mocks; none ran in this static review. No broader filesystem policy is proposed.

The [proposed diff](PROPOSED_FIXTURE_DIFF.patch) is text only, not applied. It includes F01–F05 and native setup verification; release/ledger/auth/core items remain an explicit reviewed design, not implemented code. Original adapter332d963…/test87d61d5…/campaign3d65c2… and all attempt1 bytes remain unchanged.
