# Independent target oracle supplement — separate from the21/21 receipt

No existing writer, original E2E or receipt may change. This supplement closes two
precise evidence gaps: the first campaign called the writer's own target oracle,
and its generated IDs did not deliberately distinguish generation from snapshot.
It does not replace or retrospectively expand that campaign's conclusions.

The frozen CONTROL_COMPONENTS.json enumerates106technical columns from the
approved model. It is derived independently by walking every column's outgoing
foreign-key ancestry to either dataset_snapshots.generation or its id. The
supplement never obtains column kinds from a writer report or invokes the
writer's NativeTransport/projection/native/business/prefix methods as an oracle.

Before implementation of the supplementary E2E, these outcomes are fixed:

1. Offline check verifies the approved model, explicit106contract, original
   writer/test/bindings hashes and unchanged21/21 receipt; no PG or network.
2. Missing or stale separate ROOT allocation refuses before driver import or PG.
3. A new separately allocated private PG18.6 contains one compact source fixture
   and one target, distinct ordinary roles and actual TLS. Writer DML uses ingest.
4. The local target ingest legally consumes dataset_snapshots_id_seq once, then
   calls begin_generation inside a rolled-back transaction. No setval. The first
   transported target generation and snapshot IDs must differ, and each must
   differ from the corresponding source technical ID.
5. Run the unchanged CLI once. Read the destination control rows independently;
   derive maps from checkpoint source coordinates + native snapshot coordinates,
   requiring unique source phases, identities, positive/monotone destination IDs.
6. Build explicit CASE substitutions solely from frozen106contract and those
   independently read maps. Use tests/orion_pro_bulk_local.py oracle for source
   and target. All91business native hashes/counts must agree, with unmodified
   business IDs, SQL types, absent/null/zero/empty states and12B0 rows preserved.
7. Independently verify3control contracts: original target journal/clocks and B0
   native text unchanged; exactly one generated run/snapshot per accepted phase;
   closed checkpoint fields/digests/source run hashes, exact parameters/counters,
   source phase manifests, and all4transaction clocks equal. Total copied rows
   equals source copied-relations rows minus12B0, without using a writer counter
   as the expected source count.
8. Fresh CLI process is no-op:0COPY/0nextval; all94physical native tables and67
   independently observed sequence values unchanged. Source remains byte exact.
9. Close every connection; stop/remove only the owned PG/private TMP; retain exact
   rerun command, nonsecret inputs, hashes, SQL substitutions, native91comparison,
   control3comparison, outputs/logs/resources/cleanup. No cloud/RAM/provider/body.

ROOT must allocate the future run separately. Proposed maximums:1cluster,
1compact construction,300s,1GiB disk,64MiB proof; global child deadlines use the
qualified run_bounded helper. Cleanup has its own bounded10s allowance so an
expired campaign cannot prevent stopping its owned server. First unexpected
failure stops the campaign; no allocation reset. A missing-release refusal is an
allocation guard observation, not a missing-product RED or a passing PG result.

Real IDs: begin_generation takes nextval on commit_generation_seq, then INSERT
evaluates the separate snapshot identity sequence. The nominal fresh source uses
one of each and may currently yield equal numbers. Equality is not contractual:
legal sequence reservations or an interruption between allocations can create
gaps independently. No real-source value has been read by this supplementary
preparation; ROOT must inspect the actual IDs rather than infer equality.

Suggested commit: `test: independently verify native transport control remapping`.
