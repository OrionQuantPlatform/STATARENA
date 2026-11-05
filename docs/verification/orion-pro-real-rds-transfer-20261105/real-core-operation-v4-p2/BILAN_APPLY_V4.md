# Real P2 core import: second failure and verified rollback

Suggested commit: `test: preserve failed RDS015 core import and verified rollback`.

One readonly preflight passed in75.011s with553562 retained source rows, no COPY and no allocation. One apply ran once and failed in802.929s, after copying553545 business rows (478547 native scalar rows) through731 COPY commands and verifying91 uncommitted native relations. The PostgreSQL8s statement deadline canceled seal with57014 while evaluating the full variant interval overlap for `football.player_match_metric_values` (`ingest.validate_generation`, line153). There was no completed phase. This context identifies the active predicate at cancellation; it does not measure standalone predicate duration or its actual plan. The earlier three membership guards were not the failing expression in this attempt.

An independent fresh TLS readonly connection used15 SELECTs in8.499s. It verified exact B0/schema/journal/roles/ACL, with no committed business facts and24 monotone sequence deltas fully explained:22 business nextvals plus generation/snapshot2→3. No reset, replay, publication, source purge or activation ran. The current native state fingerprint is ff1f3a336bfde1067b2b70e0fc6d3517f4d648631c2813374bca04cd4fddf189. Raw sporting bodies were not staged or archived. The ephemeral private auth was removed and both transport connections closed; readback connection/auth also closed.

| Actual observed measure | First failed import | Second failed import |
| --- | ---: | ---: |
| Outer elapsed, seconds |803.840|802.929|
| Business rows copied in transaction |553545|553545|
| COPY commands |731|731|
| Business nextvals |561145|22|
| Committed business rows |0|0|

The reduced nextval count reuses the earlier reservations, not a successful speed improvement. The native relation-size observation changed from388587520B to773259264B (+384671744B, ~367MiB), despite rollback. This is physical allocation at the observation times, not committed sporting data, reclaimed capacity or an AWS bill increase. No storage resize or vacuum was executed.

The typed source V4 was stopped cleanly after readback and retained unchanged, while the previous RAM capture remains available. Original authority bytes are retained; two stale descriptive summary fields were corrected by the separate addendum. The effective V4 marker/checkpoint and exact preflight pins were correct. A cold fresh-COPY owned PostgreSQL planner test precedes any potential new real action. No retry is authorized by this receipt.
