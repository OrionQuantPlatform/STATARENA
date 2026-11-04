# Exact-key content qualification — 4 November 2026

**14/14exact physical versions examined and SHA-verified;12/12observation response IDs/selectors qualified. Typed import remains blocked on the incomplete mapping; no remote mutation or purge occurred.** This new pass leaves the metadata inventory at `eab371a87c`, its budgets and receipts unchanged. Model `18da43f9…`,012/013, application code and WORKLOG were not modified.

[result.json](result.json) records the qualification and limits; [IMPORT_PLAN.md](IMPORT_PLAN.md) names concrete existing typed destinations and unresolved mappings. All persisted content evidence consists of metadata/digests/types/counts/qualifying IDs and bounded useful differences. No raw/decoded source body, gzip, opaque sports report or replay snapshot was saved to disk/RDS/S3.

## Actual budget and transport

| Measure | Actual | Cap |
|---|---:|---:|
| SQL instructions including implicit BEGIN/ROLLBACK | **8** |18|
| Object HTTP requests, counted at actual SDK send | **36** |36|
| Decoded bytes, including the whole two old archive objects | **663756** |33554432|
| Full physical object bytes fetched | **347557** |2MiB/object|
| Additional four-byte Range payloads | **48** |12×4|
| Physical payload including ranges | **347605** |Bounded by exact advertised sizes|

Decoded breakdown: two SQL-hot manifests **321993bytes**, nine Neon external objects **173613bytes**, three AWS external objects **168150bytes**. Both source DBs used RR/RO, client TLS verify-full, statement8s/lock1s deadlines and ROLLBACK. SQL/selectors and budget were recorded before reads. Source objects were resolved at existing `data/<exact path>` keys in the configured Neon branch bucket and the inventoried AWS bucket; no bucket listing, provider query, partition follow-up or512archive scan occurred. HEAD length, conditional Range4/GET, frozen SHA, real bounded gzip output, UTF8/JSON and duplicate-key guards were enforced.

The RAM holders exited and released source references: [initial cleanup](ram-cleanup.json), [external cleanup](external-ram-cleanup.json), [AWS completion cleanup](aws-completion-ram-cleanup.json). Request logs and source-code hashes are in [execution.json](execution.json), [external-execution.json](external-execution.json) and [aws-completion-execution.json](aws-completion-execution.json). Credential scans record only outcomes, never credential values.

## Concrete delta, with its meaning

- **Five nonempty HTTP200bodies:** a306match league response, one detailed match, H2H, lineups and heatmaps. The league versions share all306match-ID sets, with **81finished/scored versus80**, and225versus226not-started/null-score rows. The exact changed fixture ID/full scalar pairing is not retained by this summary and remains an import gate.
- **Three explicit empty HTTP200collections** for `m_2vsKSO`: events, momentum points and team-stat periods. They support empty observed-family coverage, not invented numeric zeros or a permanent claim about a future match.
- **One explicit null collection:** `shots.periods=null`. Preserve `collection_state='null'`, unknown row count; never convert it to empty/zero.
- **H2H `m_0xOQtL`:33entries versus old AWSempty**,32finished/1not-finished, one null-score entry. Keep observed order, identities, time text and both versions. Totals and native finished-boolean mapping remain incomplete.
- **Lineups `m_0xOQtL`:40versus39listed players**, both Neon teams confirmed versus both AWSunconfirmed; source category `standard` versus `predicted`. Three side/role ID groups differ, listed in the import plan and [qualified-resource-pairs.json](qualified-resource-pairs.json). These are source observations, not proven identity mistakes or automatically new global players.
- **Heatmaps:30player +2team collections**,1344rows each containing3integers,4032numeric elements; frame `home_ltr`. Exact coordinate/count positions and missing-cell semantics remain unqualified. The current dense-grid importer must not be used on this representation without a source-driven oracle.
- **Six HTTP404resource keys remain metadata-only** from the frozen inventory; their bodies were not read. They are negative cached observations, not missing sport facts, empty success or authority to fabricate fetch attempts.

The three changed pointers have different exact selected typed digests. Source field/state/ID and confirmation/category differences are recorded. No supplier revision order is proved: storage LastModified, cache/import/index clocks, additional rows and body HTTP status are not a monotone provider version. Preserve both AWS/Neon variants and leave canonical promotion to an accepted policy. The isolated AWS-only object from the inventory remains untouched.

## Manifest and selector qualifications

The manifest physical/typed digests differ globally, but the exact Ligue1partition path/SHA/sourceDigest is **identical for both requested seasons**: [manifest-scope-comparison.json](manifest-scope-comparison.json).2026/2027points to `l_3FJFUl-3403d71ab77e5287be09e9c2.json.gz`;2025/2026to `l_3FJFUl-1f2cbed49d570024ea3a0ee7.json.gz`. No partition body was fetched. The raw manifest comparison retains array order and reports791positional differences; these are not791business changes or authority to republish the catalogue.

The old AWS H2H/lineup objects each contain16members. Both exact `m_0xOQtL` selectors resolved uniquely to **ordinal2**, with matching response IDs. No first-member guess or new object/version was substituted. Full identity/source mapping outside these twelve contexts is unverified.

## Instrumentation failures preserved and reconciled

The first SQL attempt decoded only the two manifests. Its guard treated NULL SQL bodies as an unavailable physical size; the subsequent resolver inspection established external storage, not changed stored SHA. Those blocked-before-fetch receipts remain intact; the transport extension was explicitly authorized and documented before object requests.

The external AWS SDK first failed before any HTTP call because the installed botocore login provider lacked its CRT dependency. [external-aws.json](external-aws.json) retains the exact error. Existing AWS CLI credentials were then exported directly into process RAM; output was never printed/saved, no login or paid configuration change was performed. The remaining three objects consumed the reserved nine HTTP requests.

Ten direct API JSON envelopes carry `data` without duplicating HTTP status inside JSON. Their first conservative body-status guard is preserved. The final offline qualification uses the bound resource catalogue's200status, verified snapshot selector and actual matching response ID; an optional contradictory body status would block it. The two archive wrappers also contain status200. This correction does not claim that arbitrary HTTP200means a complete/valid sport family.

The33receipt qualification checks pass. They cover exact versions, selectors/IDs, source snapshot/TLS controls, counters, scoped manifest pointers and protected inputs. **They do not establish exhaustive scalar-leaf fidelity, an accepted importer, remote data completeness or public parity.**

## Reproduction and remaining boundary

Protocol, preconditions and exact SQL are in [PROTOCOL.md](PROTOCOL.md), [scope-and-budget.json](scope-and-budget.json) and [query-plan.json](query-plan.json). Actual commands used:

```sh
python3 -B docs/verification/orion-transfer-content-20261104/prepare_content.py
python3 -B docs/verification/orion-transfer-content-20261104/read_content.py --prepare-only
PYTHONPATH=/tmp/statarena-publication-test-python python3 -B docs/verification/orion-transfer-content-20261104/read_content.py --hold
PYTHONPATH=/tmp/statarena-publication-test-python python3 -B docs/verification/orion-transfer-content-20261104/read_external.py
PYTHONPATH=/tmp/statarena-publication-test-python python3 -B docs/verification/orion-transfer-content-20261104/complete_aws.py
python3 -B docs/verification/orion-transfer-content-20261104/qualify_content.py
```

The held reader received `stop` after its diagnostics were saved; no command reconnects. Live receipts prevent implicit replay/budget reset. Offline qualification can be reproduced from the saved diagnostics with the final command, without source access. A new live replay requires a fresh authorized budget and retained exact versions; no raw-disk replay exists.

Before typed import: accept every field/type/native state/unit/identity destination, source-version policy and collection contract, then execute an independent complete source→typed oracle retaining both variants and no-op behavior. Required destination decisions include H2H aggregates/native boolean, source lineup category, observed coach/referee/has_playoff and the heatmap format; no schema014 was created or proposed by default.

No old body is currently eligible for deletion. The old AWS league blob needs all306records reconciled; each old AWS archive needs **all16members**, retained versions and consumers reconciled; both manifests need catalogue-wide non-dependency proof. Matching metadata/pointers or typing one selected member is insufficient. The [import plan](IMPORT_PLAN.md) spells out these conditional future boundaries; full backend/data acceptance, cutover and purge remain open.

Suggested commit: `docs: qualify exact Neon AWS content differences for typed import`.
