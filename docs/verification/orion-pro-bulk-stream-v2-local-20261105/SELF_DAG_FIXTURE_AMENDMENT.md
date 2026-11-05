# ROOT static review amendment — before the first PG campaign

ROOT identified that two stage rows could share one COPY statement: immediate self-FKs are checked at statement end, so PK inversion alone did not prove cross-batch transport. The original missing-implementation RED7e5b6680 and its E2E/input snapshots stay immutable and historical. The existing dense-copy evidence counter was subsequently wired to its actual observed core checkpoint; it was previously an unused zero placeholder. Neither change constitutes a PG execution.

The complete existing E2E is amended before the new writer trace contract: compact source now inserts1010native stages before the original first seal, parent revision2000, child revision2,1008flat roots. A raw PK first window cannot contain the child's parent. The stage supplement is included in the actual E2E producer SHA. Dense source remains478547scalars and only2stages; no extra dense construction or flag changes writer batching. Caps remain1000rows/1MiB per batch and4096self vertices/8MiB graph.

Acceptance requires source/target native94 parity, observed actual stage COPY commands in separate rank windows containing parent and child, parent command before child command and monotone progress. Generic bounded self-edge witnesses and window metadata expose that proof; they do not alter transport order or raise a bound. These added assertions are written before the product gains the witness/window contract. No PG campaign is authorized or started by this amendment.

Suggested commit: `perf: stream typed native phases within bounded memory`.
