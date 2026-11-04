# RDS publication capacity after the first two partitions

**Hold the 100-minute backfill.** The first successful publication left 4.412 GB of admissible growth under the configured database ceiling and reserve. For the complete source population the two player metric tables alone project to **20.63 GB**, and the independently measured detail tables outside them project to **11.91 GB**. A shared metric dictionary is valuable, but cannot make the full workload fit by itself.

At 03:20 UTC the database occupied 11.332 GB, including 0.193 GB of normalized application tables. The imported document table occupied 10.432 GB including its indexes. The RDS volume is 20 GiB, and the SQL budget is 16.000 GB with 0.256 GB reserved. The first hosted run normalized 189 matches, published two partitions, 1,880 supporting projections and 37,867 image references. Those fixed records and differences in historical family coverage make simple extrapolation from two partitions misleading.

| Full-population component | Estimated size | Basis |
|---|---:|---|
| Player metric rows | 10.75 GB | About 48.41 million rows; sample-based 95% interval 47.66–49.16 million |
| Half metric rows | 9.88 GB | About 45.51 million rows; sample-based 95% interval 41.38–49.64 million |
| Other measured match-detail tables | 11.91 GB | Sample interval 11.33–12.49 GB at current bytes/row |
| Match-family headers | 0.24 GB | 950,370 eligible family keys times the first publication's physical bytes per header |
| Core appearances, membership and shots | 1.81 GB | Parent player/shot rows at their currently observed core bytes/row |
| Catalog | 0.815 GB | Previous PostgreSQL roundtrip for all 537 matched source versions |
| Existing source and non-application database | 11.14 GB | Measured database size minus normalized table allocations |

The **partial current-layout scenario totals 46.54 GB**. Detail tables alone account for 32.54 GB with a sampling interval of 31.31–33.77 GB. The 46.54 GB scenario excludes some core relations, marginal unsupported densities, future ingestion, temporary/WAL working space and capacity reserve. Physical bytes/row come from the first two partitions. They can change with value lengths, deduplication, index fill, page bloat, and future source revisions. As a sensitivity check, reducing every projected detail-table cost by 25% still leaves 24.40 GB of those detail tables alone. A larger instance would affect CPU and memory; the reported disk calculation concerns volume and database budget.

The survey reconstructed saved-over-archive selection, independent nested resources and parameter variants from the prior complete metadata capture. The population includes 950,370 eligible family keys across 39 strata, including 71,445 saved error headers. A fixed-seed sample of 1,300 responses used 100 keys in each player/half/single-player stratum where available and 28 in other non-error strata. Of these, 856 were passed through the actual typed writer's row decoder. The body-transfer checkpoint stopped after its last eight-key batch at 35.50 MB of selected response JSON. Server-side SQL counted rows for the remainder and independently matched the actual writer on 69 overlapping inputs. The additional count results used about 40 KB. All 1,300 sampled identities resolved. The approximate 95% intervals use stratified sample variance with finite-population corrections. They describe sampling variability, not uncertainty in storage density or future compression.

The largest nonmetric projections are pass edges (1.53 GB), half-stat groups (1.32 GB), advanced player totals (1.24 GB), player heatmaps (1.01 GB), player stat groups (0.99 GB), team stat items (0.93 GB), match shots (0.76 GB) and full-roster player entries (0.72 GB). Even eliminating the two largest metric tables entirely would leave 11.91 GB of other detail tables before core, catalog or source. The admission decision does not depend on the ultimate metric design.

## Private relational storage experiment

Two sequential read-only copies retrieved the complete 411,416 **published typed metric rows** (29.35 MB PostgreSQL text COPY) into a disposable PostgreSQL 18 replica. The recreated physical baseline including its two unique indexes exactly matched the summed production size, 90,243,072 bytes. The full metric identity included separate dynamic label, key, type, value, total, null-group and missing-field indicators. Both alternatives kept typed fact values and relational links. Arrays were used only by temporary construction queries to compare ordered sequences.

| On-disk layout for the same published metrics | Size | Reduction |
|---|---:|---:|
| Original two metric tables | 90.24 MB | — |
| 3,970 distinct exact metric-value records plus 411,416 resource/group/ordinal links | 35.81 MB | 60.3% |
| Same value dictionary plus 30,519 unique ordered groups, 236,611 member links and 62,577 source/group links | 26.61 MB | 70.5% |

The shared-group reconstruction returned **zero symmetric differences across all original columns and all rows**, including record order, numeric values, nullable fields and dynamic labels. The private trial measures isolated physical storage and exact reconstruction of this metric corpus. It does not implement transactional dictionary publication, changes to the API reader, or a migration. At the observed trial ratios alone the partial full-database scenarios remain 34.10 GB and 32.00 GB, respectively. Dictionary reuse could improve with more matches or worsen as new source values arrive.

The independently run named-column and relational-template trial on the same 411,416 rows used 4,415,488 bytes for half metrics and 3,301,376 for player metrics, with zero differences in both directions. Applying those measured per-row costs to the estimated population gives **1.749 GB for metrics and 27.66 GB for the partial full database**. This makes named numeric columns the strongest trial here on size. A production design still needs explicit behavior for unseen metric names and novel layouts.

A capacity-compatible design must address multiple families together. The next concrete candidates are resource/version sharing for identical saved singles and parent groups, shared player/team identities in pass edges, and removing redundant child record/ordinal indexes only where exact reconstruction and deletion performance hold. Measure them against the same effective population with a bounded staging plan. Retaining the full raw staging store and the complete serving model on the current volume is a material constraint and any change to the source retention or deployment budget needs an explicit owner decision.

Inspect the [working protocol](PROTOCOL.md), [forecast](forecast.json), [all samples and strata](effective-sample.json), [complete typed input hashes](published-metrics.json), and [physical layouts and full equality comparison](metric-layout/results.json). From the repo root, use the existing read-only AWS profile and the local gzip metadata/files specified in the capture script. Refresh the metadata through the preceding discovery verification if unavailable.

```sh
PYTHONPATH=/tmp/statarena-publication-test-python python3 docs/verification/aws-capacity-20261104/survey.py
PYTHONPATH=/tmp/statarena-publication-test-python python3 docs/verification/aws-capacity-20261104/count_remaining.py
PYTHONPATH=/tmp/statarena-publication-test-python python3 docs/verification/aws-capacity-20261104/metrics_capture.py
node docs/verification/aws-capacity-20261104/run.mjs metric-layout
python3 docs/verification/aws-capacity-20261104/forecast.py
```

Suggested commit `docs: measure RDS publication capacity and relational metric compaction`.
