# Bounded Neon/AWS metadata inventory — 4 November 2026

Status: **partial metadata inventory, no transfer and no full acceptance**. ROOT owns the missing/stale-data work under Hugo's transfer correction. This pass retrieved metadata only, wrote only this folder, and performed no SQL mutation, payload/body download, decoding, collector run, deployment or paid configuration change.

The configured source is **Orion Tech Sport**, project `sweet-queen-11955006`, branch `production` / `br-mute-bonus-be23014e`, database `neondb`, endpoint `ep-steep-boat-bekuqo4w`. The connector endpoint matches the hostname in the existing local configuration; no DSN was printed or stored. Project `morning-thunder-68538387` (`neon-red-chair`) has archived branch `main` / `br-hidden-math-awrw1xep`, which was not activated or queried. Organization `org-late-credit-34206597` returned HTTP401; the exact sanitized errors are retained in [connector-errors.json](connector-errors.json). Discovery of every possible source remains incomplete.

Successful metadata snapshots: Neon **20:22:37 UTC / 21:22:37 Paris**, AWS final exact-key probe **20:24:23 UTC / 21:24:23 Paris**, both repeatable-read/read-only with 8-second statement and 1-second lock deadlines. They were sequential, not simultaneous. Client TLS uses `verify-full`; [client readback](client-tls-readback-final.json) records SSL in use. No active configuration was changed.

| Metadata scope | Observed result | Meaning and limit |
|---|---|---|
| Ligue1 fixtures, two seasons | **612 identical ID/date/status tuples** | Bodies and every business field remain unverified |
| Previously catalogued archives | **512/512 present with identical stored SHA/size**; all512 AWS indexes reference that SHA | Catalogue agreement, not recomputed bytes, typed import or exhaustive leaf acceptance |
| Seven representative match-resource prefixes plus league keys | **17 identical keys, 15 absent in AWS, 3 different pointers** | Exact endpoint/params comparison within the selected prefixes; no global resource completeness claim |
| Missing AWS resource keys | **9 HTTP200, 6 HTTP404** | Negative provider results are not missing business facts and do not authorize collection |
| Object versions in the collected scope | **537 identical, 9 absent in AWS, 1 different version, 1 present in AWS with Neon absence unverified** | The AWS-only collected key was not explicitly probed on Neon; preserve it |
| Targeted profiles | **62 exact `/players/{id}`, `{}` keys absent in both sources**; one identical pointer for `p_1JuxKR` | Other paths/params/projects may contain profiles; no global absence claim |
| Known identity conflict | Same path, ordinal25 and stored SHA as the prior rejected member | The metadata fingerprint remains ambiguous; no member was decoded or declared repaired |

Exact keys and both versions are retained in [inventory.json](inventory.json). Counts summarize its rows and are not acceptance gates.

The fifteen missing AWS resource keys comprise fourteen for `m_2vsKSO`, plus `/matches/m_0xOQtL/heatmaps` with `{"frame":"home_ltr"}`. The three differing pointers are `/leagues/l_3FJFUl/matches` with season2026/2027/statusall, `/matches/m_0xOQtL/h2h`, and `/matches/m_0xOQtL/lineups`. The manifest object `computed/dashboard/index.json` also differs: Neon stored SHA `b122429dc63106ff9e071f3db215adfecf4acd019a42370101ae4e97e2ef425c` (161009bytes), AWS `4295ab0eedcaf225cb2c04ac8e4cc56e1531a31221e76fcd161b4890621c3ff2` (160984bytes). No manifest body or current selected partition pointer was read. **No supplier version order, and hence no confirmed stale replacement, is established.** Import/index clocks do not prove supplier freshness.

## Failures retained

The first connector transaction expired: `NeonDbError: canceling statement due to statement timeout`. [neon-run.json](neon-run.json) preserves it with no usable partial result. The full planned10statements are conservatively charged.

The bounded direct Neon snapshot was initially marked fail because its guard required server-side `pg_stat_ssl.ssl=true`. The actual receipt has `ssl=false` at the server and RR/RO as required; connection construction enforced client `sslmode=verify-full`. A first client-TLS capture then failed on an unsupported driver attribute; both failed receipts are retained. The final no-SQL [client TLS readback](client-tls-readback-final.json) confirms TLS in use and verify-full at the evidenced endpoint. The provider documents the [Neon proxy and verify-full client validation](https://neon.com/docs/security/security-overview); using the server flag as the client transport gate was an instrumentation error. The original receipts/runners are preserved as historical executions; the final inventory records this correction and does not rewrite their statuses.

The first AWS snapshot is retained separately from the later exact-key completion. Thirteen repeated result rows came from overlapping UNION paths in the completion query; comparison deduplicates endpoint/params and excludes query counters. They are not duplicate source facts. Raw `has_error` represents SQL non-nullability of JSONB and is not interpreted as a provider failure, because JSON null may also satisfy that predicate.

## Budget, reproduction and next boundary

[Final budget](final-execution-budget.json): **19/20 conservative SQL statements including controls, 1161222/16777216 serialized SQL-result bytes**. There was one client operation at a time, and all data snapshots rolled back before closing. The final inventory's11offline receipt-coherence checks pass; its status remains partial. No more SQL is authorized by this receipt.

Original commands/tool arguments and exact SQL are in [PROTOCOL.md](PROTOCOL.md), [query-plan.json](query-plan.json), [fallback-query-plan.json](fallback-query-plan.json) and [aws-complete-query.json](aws-complete-query.json). The live commands were:

```sh
python3 -B docs/verification/orion-transfer-inventory-20261104/prepare_inventory.py
python3 -B docs/verification/orion-transfer-inventory-20261104/metadata_inventory.py --prepare-only
PYTHONPATH=/tmp/statarena-publication-test-python python3 -B docs/verification/orion-transfer-inventory-20261104/metadata_inventory.py
PYTHONPATH=/tmp/statarena-publication-test-python python3 -B docs/verification/orion-transfer-inventory-20261104/verify_tls_and_complete_aws.py
PYTHONPATH=/tmp/statarena-publication-test-python python3 -B docs/verification/orion-transfer-inventory-20261104/read_client_tls.py
```

The first SQL attempt used Neon connector `run_sql_transaction` with the recorded project/branch/compute/database and `neonSetup + queries[*].sql` from `query-plan.json`. Existing receipts prevent implicit re-execution or a budget reset. A fresh live pass requires a new separately authorized budget and preserved prior receipts; use the client TLS gate, rather than repeating the initial server-flag guard. Auth/quota failures must remain exact and sanitized, without a paid upgrade or substituted source.

Reproduce the comparison **offline, with no database access**:

```sh
python3 -B docs/verification/orion-transfer-inventory-20261104/compare_metadata.py
```

Next work is content-aware, exact-selector validation and approved typed ingestion for positive observations, with both versions preserved, explicit native-state/identity/unit contracts and all existing acceptance gates. HTTP404 observations, the wrong-identity profile, unknown manifest selection, archived/inaccessible sources and the62lookup gaps need separate dispositions. This evidence authorizes no transfer, overwrite, purge, public cutover or schema change.

Suggested commit: `docs: inventory bounded Neon and AWS source metadata`.
