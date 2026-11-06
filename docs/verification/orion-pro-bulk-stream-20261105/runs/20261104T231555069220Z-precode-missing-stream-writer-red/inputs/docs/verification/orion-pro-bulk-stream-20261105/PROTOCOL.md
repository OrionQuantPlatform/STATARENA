# Streaming typed bulk v2 — pre-code local E2E protocol

Status: ROOT approved local implementation following the [separate feasibility plan](../orion-pro-bulk-20261104/v2-feasibility/PLAN.md). This protocol and the complete E2E must precede the new importer. Preserve v1's code, E2E and 529 frozen artifacts, normalizer, model18da43…, sealed012/013 and every older lot. No source/API/cloud/RDS/Neon access, extra agent, migration, schema change, commit or deployment.

## Fixture and actors

Use two databases on one harness-owned loopback PostgreSQL18.6 cluster. Setup/cleanup owner is separate from ordinary source reader / destination ingest / runtime actors. Apply the existing sealed SQL and bootstrap without compiling or rewriting them. Reuse the existing grants and native begin/seal/commit guards. Keep all installed FK/CHECK/UQ/triggers active, with no admin membership, trigger disable, replication-role change or sequence reset.

The positive candidate contains exactly **15,437 player appearances ×31 metrics =478,547 canonical scalar rows**. Distribute appearances over612 draft matches, two actual match-team sides per match, distinct player/match/metric keys,31 registered metric definitions, one stable primary variant, and exact participant revision/source-record/provider/period bindings. Reuse player identities across matches without duplicating a player inside a match. Do not manufacture scalar density through noncanonical variants on one participant. Use native SQL fixtures only, no normalizer, source response, dump or opaque report.

The core remains one native source generation. A second source phase adds the six atomic-child families and append-only observations. Every source generation maps to exactly one newly allocated destination generation; bootstrap maps semantically, and snapshot IDs have their own mapping. Create legitimate sequence gaps using nextval and a writer begin/rollback in the target so destination generation and snapshot numbers differ. Never split a source generation to satisfy a deadline.

Exact technical JSONB includes a29-digit integer, long fraction, JSON null/missing/array/text, false,0,empty text, backslash/tab/newline/Unicode. Keep SQL NULL separate. COPY values come from SQL text, never JSON-decoded float. Source/destination native SQL row digests are independent of the source producer and streaming adapter. Retain v1's exact baseline tolerance allowlist: only journal applied_at and bootstrap created_at/sealed_at may differ as installation clocks; bootstrap IDs/generation map, but every seed definition and all fact timestamps/values stay exact. New snapshot priority/cutoff remain exact; only enumerated loader controls are regenerated.

## Resource and execution budget before the first large run

- No database starts for the first missing-implementation RED. Before the first478,547-row run, send ROOT this budget and save it in the evidence.
- At most **three full-scale local runs**,20minutes wall time per run and60minutes cumulative campaign. A genuine8-second seal/commit or unbounded source-plan failure stops the campaign for ROOT review; do not spend the remaining budget repeating it unchanged.
- Owned PostgreSQL directory: **8GiB maximum observed footprint**, with a7GiB soft stop, periodic monitoring and forced owned-process cleanup on exhaustion; no payload export. Require at least16GiB free before starting. Current readback has roughly602GiB free. Keep final metadata/log artifacts below64MiB for the campaign and record actual sizes.
- Statement timeout8s, lock timeout1s and connect timeout≤8s; no timeout increases. Native setup DML also uses8s, inserting in bounded statements inside the one core generation. Source/target COPY, source plans, oracle, seal and commit have separate timings.
- Preserve64 phases,2M total rows,500k per table,1,000-row/1MiB chunks,1MiB encoded row,16MiB payload buffers,32MiB ownership/self-graph metadata,1M nextval calls per business sequence/5M total. No silent limit increases.
- Keep server work_mem/hash settings at observed defaults. Start only this owned fixture with temp_file_limit512MiB per backend as a tighter workfile fence, not extra privileges for application roles. Record actual settings, temporary byte/file counters and query-plan buffer/workfile statistics. Server work memory is distinct from client metadata; neither is inferred from the other's bound.
- A bounded v1 plan-only attempt on the same candidate is permitted once (≤90s), writing its receipt only to this new folder. Expect refusal at32MiB metadata without target mutation. If the budget expires first, report that as unverified capacity, not the expected refusal. Do not rerun v1's complete E2E.

## Representation to prove

Compute ownership/cohort by per-relation set joins and source-phase aggregates; retain no row-sized client owner/FK index. Keep only static model/query metadata,≤64 maps/receipts, small sequence plans and bounded graphs for sources/stages/metric definitions. Fetch a self graph only after count/key-byte checks; account dependency/edge/order workspaces too. Closed history, unknown/forward ownership and oversized graphs refuse before target writes.

Transport uses client COPY streams. Source pages use native PK keysets and bounded set queries, with no OFFSET or per-row WAN lookup. Whole-table COPY held open while waiting for many destination writes could itself exceed8s, so source pages must complete within the same deadline. Keep declared generation/snapshot transformations transitive over FK components. Use separate topological rank pages for the three self-reference relations; the native oracle still hashes real PK order.

The native row digest domain remains v1's length-prefixed SQL ROW(...)::text bytes, with declared control substitutions only. If COPY text escaping/framing is decoded to recover that text, prove exact agreement against an independent named-cursor SQL oracle; decode only framing, never JSON/scalar semantics. Every page/frame/chunk is bounded, including partial UTF-8, tabs/newlines/backslashes and NULL markers. No file/PROGRAM COPY, staging table, generic row registry, giant array/string aggregate or pipeline COPY.

## Complete workflow matrix written before importer

| Case | Expected observable outcome |
|---|---|
| Absent implementation | Genuine failure on missing new writer; no PG/source connection; later cases unverified |
| Owned setup/shape | Exact94-table catalogue and sealed bootstrap;478,547 canonical scalars at15437×31 distinct real grains,0 artificial density variants |
| V1 bounded comparison | One RO v1 preflight refuses metadata capacity or explicitly times out as unverified; no target row/sequence change |
| Default RO plan | Streaming source/native acceptance matches independent oracle; target rows/sequences untouched |
| Endpoints/roles/bindings | Remote/same DB/unowned marker/admin/runtime/old code/source drift refuse before mutation; native runtime write/functions/sequence access denied |
| Source SQL plans | Representative scalar ownership/forward-cohort/paged COPY plans have bounded cardinality and no cartesian amplification; record actual rows/loops/buffers/workfiles under8s |
| Ownership failures | Unknown run, future parent phase, unsupported closed interval, self-cycle or graph/metadata exhaustion refuses, without materializing a universal registry |
| Wrong typed content | Deliberately valid but wrong transported scalar fails native phase oracle and rolls back before seal |
| Partial COPY interruption | Current phase rows/run/snapshot roll back; sequence gaps survive; serving/legacy sentinel unchanged |
| Prefix interruption | Full core generation seals/commits once; deliberate stop preserves exact prefix, no analytics/publication |
| New process resume | Verified prefix reused; families applied once; actual gen/snapshot maps and all inherited FK components remain correct |
| Full native oracle | All91 fact/support relations agree through independent native SQL; three controls verified explicitly;94 total covered, empty tables labelled |
| Exact types/framing | Exact numeric/fraction/native scalar states and technical JSONB; NULL/null/missing/array/text/zero/false/empty/Unicode/control characters preserved |
| Full no-op | New process reuses accepted completed candidate, with0 COPY/nextval/new generation and no row or sequence difference |
| Collision/corruption | Foreign row/ID/receipt/source binding refuses without upsert/repair; native FK/CHECK/value-update guards still reject |
| Sequence follow-up | Legal monotone catch-up preserves explicit IDs; a subsequent native default insert cannot collide, even after rollback gaps |
| Deadlines/workfiles | Every SQL/COPY/seal/commit respects8s/1s; a genuine seal/commit timeout or unbounded plan is retained RED and stops review; no ad-hoc generation split |
| Cleanup/no live/publish | No raw body, source/API call, remote action, new table, build/publication/queue or legacy mutation; connections/PG/data directory removed even on failure |

Save setup/inputs and exact rerun command, source/test/writer/v1/protocol/model/SQL hashes, phase/control maps, source/destination native oracles, role errors, SQL counts and timings, query plans, buffer/metadata accounting, disk/workfile counters, expected/actual failures, logs and cleanup at every completed E2E run. Persist metadata/digests only. No runtime/real-data acceptance is claimed until executed; local green cannot establish RDS/WAN capacity, real-source completeness, cutover or purge.

Suggested commit: `feat: stream typed bulk phases with bounded ownership joins`.
