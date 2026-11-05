# Owned 016 SQL workflow

Suggested commit: `test: qualify additive native match detail migration on PostgreSQL`.

Run the frozen D00–D22 case functions against one fresh owned PostgreSQL18.6 cluster. Install the exact012–015 chain as an ordinary database owner, populate the existing ReaderFixture through the ordinary ingest role, then exercise the upgrade. This is SQL migration and integrity evidence. Reader HTTP, real publisher, real RDS adoption, full source parity and production gains require separate proof.

- D00: querying the proposed field on the old schema must fail 42703.
- D01: apply016 and its journal row inside a forced rollback. Every projected old row, catalogue definition, view and sequence must remain exact.
- D02: upgrade on the populated old schema. A legacy coordinate with 16 significant digits must keep its historical PostgreSQL text in both the base row and the original double precision view. The view OID and ACL must remain exact. Check98tables/1823columns/447FKs and a checked journal-based no-op. New presence fields are unrecorded, never inferred.
- D03–D19 and D21: follow the frozen cases and independently read the inserted facts. The two omission cases use a fixture-only suppression of the named metadata/summary rows; no production guard is disabled. Force all deferred checks after seal. Negative cases must fail the specific native invariant, then roll back. Nontransactional sequence gaps remain monotone.
- D20: ordinary runtime reads the new immutable children. Ordinary ingest cannot update them, and the owner cannot bypass their immutable trigger. A new member cannot append to an already sealed native cohort.
- D22: an old physically observed profile is retained after correction and the native validator preserves all original015 predicate lines except the five enlarged no-op comparisons. This SQL proof does not replace old-token HTTP regression under016.

Bounded one-shot: one owned PG/DB, at most four open clients,600s,15000 external SQL calls,20000 synthetic physical rows,1GiB owned disk,96MiB evidence. Stop on the first unexpected result, retain exact inputs/commands/cases/logs, close clients and remove only the new owned cluster. No source, cloud or real DB calls.
