# Non-applied metric membership fast path

Written before the candidate SQL. No migration, validator, grant, model, source fact or RDS fact has been changed. This is a concrete candidate for an independently reviewed append-only migration, not authorization to install it.

## Evidence and uncertainty

The V3 real writer copied 553,545 rows including 478,547 metric cells, verified its 91 native business relations and reached seal. The seal statement was cancelled at its unchanged 8-second limit (57014); ROOT independently proved rollback to B0 with the expected monotone sequence reservations. The writer did not retain the server's nested error context, so the individual cancelled validator predicate is unknown. The candidate below is a performance hypothesis to qualify, not a demonstrated cure for that real failure.

The separately allocated six-query source diagnostic retained 24,292 bytes of exact metadata/plans and closed its RO/RR/TLS connection in 2.476 seconds. The source's metric table has exact statistics from autoanalyze at 11:20:33 UTC, after the original core construction; it is not an uncommitted fresh-COPY target. Existing source ingest MAINTAIN is false and owner MAINTAIN true. The real ingest grant generator supplies SELECT/INSERT/limited UPDATE and sequence USAGE, with no MAINTAIN grant. No additional grant is proposed.

The metric-definition membership predicate (014 line 241) scans all 478,547 selected child rows and rejects 7,178,205 candidate parent comparisons, despite all 31 definitions being valid. Its source time is 1,104 ms. In contrast, the participant membership predicate (line 243) happens to validate 15,437 anchors first and never scans the metric child table; it takes 37 ms. Both overlap scans remain substantial (732/376 ms), so a three-predicate fast path may still leave a target-specific I/O bottleneck. The five measured plans show no JIT or temporary-block spill. Nothing here establishes the target's actual post-COPY statistics or plan.

## Exact change

Only the three metric child membership assertions at sealed014 lines 241–243 are wrapped. Each original SELECT, condition, NULL operator, selected-parent identity, interval, canonical/deleted predicate and exception message remains byte-for-byte inside the true branch:

```sql
IF (CASE WHEN EXISTS (
    SELECT 1 FROM parent anchor
    WHERE NOT EXISTS (exact_original_selected_parent_subquery)
) THEN EXISTS (exact_original_child_join_anchor_query)
ELSE false END) THEN
    RAISE EXCEPTION USING ERRCODE='23514', MESSAGE=exact_original_message;
END IF;
```

The guard validates parents even when the planner would otherwise start with the large child relation. If all retained anchors have an exact selected parent, no child can violate this membership assertion and the original child scan is not executed. When any bad anchor exists, including an old/unselected/deleted/structurally changed historical anchor, the complete original predicate executes. There is no global join-method setting and no reliance on an ANALYZE privilege or a rewritten equality operator.

Let `B(a)` be exactly the original `NOT EXISTS(selected_parent ...)`, and let `C(c,a)` contain the original FK join, active child and complete non-NULL FK requirements. The old error condition is `EXISTS c,a: C(c,a) AND B(a)`. It implies `EXISTS a: B(a)`. Thus the new condition `CASE WHEN EXISTS a:B(a) THEN old_condition ELSE false END` equals the old condition. Both EXISTS values are two-valued booleans; the original predicates retain SQL's three-valued NULL behavior. All conditions are pure SQL against the same statement snapshot. This proof covers false-positive guard matches from unrelated historical anchors: they cause the original query to run, never an admission change.

`candidate_metric_membership_guard.sql` will contain the full original function with exactly those three line replacements. The reconstruction test restores those three original lines and requires byte equality to sealed014. All other 261 exception messages and their surrounding statements remain unchanged. The old compiler and migrations 012/013/014 remain sealed.

## Required failure matrix before installation

| Workflow | Expected result |
| --- | --- |
| Candidate absent before authoring | Structural precode RED, retained. |
| Alter any non-target byte or original nested predicate | Structural refusal. |
| Empty source/target, bootstrap and unrelated parent rows | Same old/native outcome and unchanged B0. |
| Dense initial core, valid 31 definitions/6 periods/15,437 participants | Same 91 hashes and 3 controls; all three guarded child subplans unexecuted; seal and deferred commit each below 8 seconds under ordinary ingest. |
| Missing or unselected definition/period/participant | Same 23514 error as old validator when an active child references it. |
| Nullable participant position NULL/NULL, NULL/value, value/NULL and value/value | Exactly the old membership outcomes; preserve IS NOT DISTINCT FROM where required. |
| Active child with partially NULL optional FK, absent anchor or deleted/canonical variants | Exactly old outcomes; no new interpretation of missing identity. |
| Closed intervals and selected historical epochs, parent reopen forbidden, unrelated old invalid anchor | Full old predicate runs where necessary; exact old pass/refusal and native rows preserved. |
| Non-identical reimport / identical reimport / failed collection / participant / lineage / cycles | Existing complete integrity E2Es unchanged. |
| Failed 8-second seal, dropped acknowledgement and fresh prefix/no-op | Existing rollback, monotone sequence gaps, closed receipt keys and resume proofs unchanged. |
| Real target performance | Requires a separately released operation and target oracle; source/structural passes do not authorize retry. |

Only structural checks are available now. No PostgreSQL execution of the candidate, no equivalence E2E on adversarial rows, no dense candidate seal benchmark and no RDS retry has been performed. A new migration would change the native function body/catalogue hash and must receive explicit new policy/journal/descriptor attestations rather than aliasing the old P1 pair.

## Statistics alternative

Refreshing selected fact-table statistics inside the existing owner SECURITY DEFINER seal function would see that transaction's uncommitted COPY rows without granting MAINTAIN to ingest. It still requires a new reviewed migration, preserves the existing owner/ACL/search_path, and must include ANALYZE plus seal validation within the same 8-second statement deadline. Repeating ANALYZE from the deferred commit validator would add avoidable work. This alternative is not currently justified by target plan evidence and is not implemented. Admin business writes, new grants, higher timeouts, disabled guards and model changes are outside this proposal.

Suggested commit: `perf: propose an invariant-preserving metric membership fast path`
