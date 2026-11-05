# Preserved setup failures

Suggested commit: `feat: add typed edition-bound entity profile readers`.

1. `runs/20261105T114105985608Z-actual-router-first`: runtime read-only case
   passed, unpublished route503 verified, then the synthetic missing-profile
   participant used undeclared squad status `bench`. The sealed schema rejected
   it. One case passed, one failed,28 unverified. Approved `unused_substitute`
   with played=false expresses the intended case. No expectation or product
   change was made.
2. `runs/20261105T114409550282Z-actual-router-fixture-enum-v2`: the enum was
   accepted, then the inherited ReaderFixture builder's fixed players_count=1
   was rejected by sealed validate_aggregation_build. The new corpus has two
   selected A participants and zero in D. One case passed, one failed,28
   unverified. The new entity fixture now calculates its summary team/player
   counters from its selected generation instead of inheriting fixed counts.
   The original shared reader fixture, product, router, tests and expected
   outcomes remain unchanged.

Each run stopped at the first unexpected failure. Both ledgers preserve inputs,
SQL/logs and exact commands, and prove Bun/PG/admin closure and owned-directory
removal. Neither run exercised positive entity content nor proves API success.
These failures are fixture errors and must not be reported as product passes.
