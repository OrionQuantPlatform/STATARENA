# Real core transport V4 into the adopted RDS017 schema

Two real RDS015 imports (V3 and V4-P2) copied all 553,545 business rows in ~800 s,
then the client cancelled `ingest.seal_generation` at the writer's own 8 s statement
limit (57014). Both were rolled back and independently verified at B0. The RDS
t4g.micro runs `work_mem=4MB`; the seal's interval-overlap checks over 478,547 metric
rows sort on disk. After the rollbacks autovacuum truncated the heaps (reltuples 0,
relpages 0) and left ~711 MB of index on `football.player_match_metric_values`.
Locally the same seal takes ~2 s on a fresh COPY, so the budget, not the validator
logic, is the blocker. Since then 016/017 were adopted (98 relations), so the v3
writer, pinned to the RDS015 descriptor, can no longer admit the target.

`dashboard/scripts/orion_pro_native_transport_real_v4.py` changes only this:

* Target: a fresh read-only ingest readback of the adopted 017 schema
  (`overlay.catalogue(conn,'017')`: journal = exact 012–017 chain, 98/1829/447,
  defaults intact, 4 new detail tables empty), plus the frozen catalogue,
  validator properties, journal and B0 text. Adoption receipt be6ca7bd….
* Overlay: the qualified `TransportOverlay` (coordinate round-trip guard, inverse
  float8 projection, default new core fields, empty new tables) wraps the frozen v3
  source/COPY/prefix methods. Owned proof: target-overlay 9/9.
* Budget: inside the import transaction only, `SET LOCAL statement_timeout=300000`
  and `SET LOCAL work_mem='64MB'` immediately before `seal_generation`; they also
  bound the deferred COMMIT and revert at transaction end. All other statements keep
  8 s / 1 s. No migration, validator, grant, model, index or AWS resource change.
* Source: unchanged v3 validation (frozen descriptor, live epoch, logical checkpoint,
  producer, native94/31 oracles) via a fresh `core-recovery-v6` read-only restart.
  The source acceptance fields are byte-equal to the reviewed V4-P2 acceptance.

Evidence so far:

| Step | Result |
| --- | --- |
| RDS017 target readback `target-readbacks/20261105T192039Z` | verified; 0 import runs, B0 only, 4 empty detail tables, 5.9 s, 1 RO connection |
| Source `core-recovery-v5` | READY 7/7, then stopped cleanly: its recorded controller path was relative, so `operations/core-v1` preflight refused before any connection (`SOURCE_SERVICE`) |
| Source `core-recovery-v6` | READY 7/7 (`runs-v2/20261105T192211685980Z`) |
| `operations/core-v2` preflight | passed in 74.9 s: real source and RDS017 accepted, 553,545-row phase ownership, no COPY |
| `operations/core-v2` apply (user-approved) | **committed**: 731 COPY, 553,545 rows (478,547 metric values), 22 nextvals; COPY 594.3 s, seal 70.1 s, deferred commit 73.6 s under 5min/64MB/1s; 985.2 s total; generation/snapshot 2→4 |
| Independent readback (`operations/core-v2/independent-readback`) | **exact**: B0 + one sealed V4 snapshot, one run with 553,545 copied rows; all 91 business relations equal the frozen source native digests (553,557 rows incl. 12 B0 seeds, 106 control components remapped, coordinates cast to float8), 0 mismatches; new core defaults intact, 4 detail tables empty; 102.8 s, 1 RO connection |
| Source `core-recovery-v6` | stopped cleanly after readback; typed root retained |

Seal took 70 s on RDS versus ~2 s locally, which confirms the 8 s budget, not the
validator, caused the earlier failures. The data is committed but not yet published
to the site: READY publication, frontend cohorts and the remaining families come next.
