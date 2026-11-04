# Published season and fixture page timings

On commit e1771cc437, visit the two /api/seasons/partition pages at limits 100 and 50 (format=columns, season=2026/2027, league=l_0ALvwF), then /api/fixtures first and second pages at limit 50 with the same league and season. Reuse the returned cursor. Use the current runtime role, TLS, one connection with read-only startup options, and one EXPLAIN (ANALYZE,BUFFERS,TIMING OFF,FORMAT JSON) with actual bound values for each of the four exact handler SQL statements. Do not write to RDS or change AWS configuration. Stop if the known dense-100 SHA (0d6bbe72588aa8df43b6d7933093a9d9cd8f028a1b53d61fc8c68bdc37f7d403) changes. Validate pages have stable publication versions and distinct fixture IDs.

Measure PostgreSQL server time, read and hit blocks, actual plan/rows, database field bytes, JSON parse time, JS response shaping/packing and serialization. Log only digests, byte counts, instrumentation and SQL, not football payloads or credentials. Separate local runtime/WAN timing from production Lambda reports. Find production sampled events already available via CloudWatch. If absent or not attributable, report the stage gap; don't increase the sample rate or extrapolate production per-stage timings. Prior 12 matched memory-comparison Lambda invocations and their 512MiB warm median are in the adjacent aws-lambda-memory-20261104 receipt. This is a bounded diagnostic, not a throughput benchmark.

Rerun from the repository root using a local Node with module.registerHooks, installed dashboard dependencies, and authorized read access to the statarena AWS profile.

    node docs/verification/aws-pagination-plans-20261104/measure.mjs
    python3 docs/verification/aws-pagination-plans-20261104/origin.py

After the four page reads, the dense SQL result showed 11.74 MB of fields including 8.79 MB of appearance JSON. For the private candidate comparison, execute the dense SELECT once to seed an in-memory replay of the genuine PG result. A/B test only the existing camelRow helper (per-property regex/map/fromEntries) versus a map of transformed field names and a simple loop. Twelve matched warm rounds, AB/BA order, compare complete public SHA on every run before recommending. Time the helper itself plus whole handler response. Local V8 case cannot measure live Lambda savings. Also measure the same query with the unchanged relational appearance rows sent as ordered arrays of typed fields instead of repeated JSON field names. Use an explicit descriptor from migration 003, reconstruct the internal JS rows with the identical ordered names, require deep equality on the complete SQL response and HTTP SHA. At most that one candidate SELECT and one matching plan. No product or cloud schema edits.

    node docs/verification/aws-pagination-plans-20261104/replay.mjs
    python3 docs/verification/aws-pagination-plans-20261104/describe.py

The replay reads the explicit column order from the returned fields. The offline describe step independently requires it to match sealed migration 003 plus the three selected join fields. Both must pass. Eleven representative reads or plans and one read-only identity query across both Node scripts.
