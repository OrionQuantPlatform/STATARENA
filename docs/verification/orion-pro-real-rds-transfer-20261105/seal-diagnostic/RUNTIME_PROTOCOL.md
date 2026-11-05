# One owned local runtime campaign

ROOT authorized one new source-free campaign after the executable cases are reviewable: one TLS PG18.6 cluster, at most two fixture databases and five simultaneous clients, 600 seconds, 3 GiB owned disk and 96 MiB evidence. All SQL keeps statement_timeout=8000 and lock_timeout=1000. No real source/RAM/cloud/RDS access, restart of the retained corpus, extra grant, production policy or installed migration is permitted. The release pins this harness, this protocol, the candidate, sealed014 and the qualified fixture.

The compact database runs the exact sealed014 validator, not sealed013. The dense database starts from the same 012/013/014 journal and receives only the candidate function overlay in this disposable owned database. Function OID, ordinary owner, ACL, SECURITY DEFINER and search_path must remain exact. Both use the existing source-free native fixture function (`tests/orion_pro_bulk_stream_local.py`), without invoking its runner or touching its historical ledger. The only compact substitutions are 40 appearances, 1,240 cells, four matches and 40 players. Dense remains 15,437 appearances, 31 definitions and 478,547 cells. No new opaque document or body is constructed.

The ordinary ingest role creates and seals actual current draft generations. The unmodified ownership/xmin requirement is exercised at seal and deferred commit; no full-validator call on a retained sealed generation is used as a benchmark. Before the first dense seal, exact candidate predicates are EXPLAIN ANALYZE'd in that same owned draft transaction. All three parent guards must return false and all original metric-child subplans must have zero actual loops. No ANALYZE or join-method setting is issued.

## Executable workflows

For each compact014/dense-candidate database, run the same ordinary-ingest workflows:

- Three missing exact FK targets (definition, period, participant) fail 23503 at INSERT, with full rollback.
- Closing a retained referenced metric definition makes old and candidate metric-definition predicates true at the new generation and false at the original core generation. Seal must fail 23514 with that exact rule.
- Closing an otherwise unused bootstrap period, then inserting a typed metric row that references its retained version, exercises the period predicate. Exact old/new predicates agree and seal fails its exact 23514 rule. The negative transaction rolls back the bootstrap change.
- Closing a participant, replacing it with the wrong team, a noncanonical participant, a deleted participant or a changed nullable position makes the exact participant predicates agree and seal fail 23514. Native physical FK and existing mapping guards remain enabled.
- NULL/NULL positive replacement changes explicit participation evidence while retaining the structural membership. Seal and deferred commit succeed below eight seconds.
- A positive NULL-to-position transition closes/replaces the active participant and all its 31 metric children together. Both exact predicates remain false, original core remains historically valid, and seal plus deferred commit succeed below eight seconds.
- From that non-NULL state, value/NULL and value/different-value replacements fail 23514; value/same-value replacement with changed evidence succeeds. Existing explicit typed position mappings are used, with no invented source default.
- Closed historical anchors whose old children are inactive trigger the conservative parent guard while the complete old predicate remains false; they must not create a new rejection. Reopening a closed interval fails 55000.

Every negative transaction compares native94 before/after hashes, with sequence67 values required to be monotone (rolled-back reservations are legitimate). Predicates are compared as exact SQL against the same transaction, at both the draft generation and original core generation. Only expected 23503/23514/55000 errors are caught; any other failure stops the whole campaign, preserving the first failure, inputs and logs. No corrective rerun is allowed under the consumed allocation.

Required final observations: compact baseline014 has successful native seals and deferred commits; dense candidate has successful core/family seals and deferred commits; candidate CASE branches do not touch the metric child on the initial all-valid parent sets; no data transformation, schema/index/ACL/function-identity drift or new privilege; runtime still cannot allocate/seal/validate/write or read sequence values. All other 261 exception statements and all guards outside the three candidate wrappers remain structurally exact.

The owned cluster is stopped in every outcome. Success removes only that newly owned temporary root. Failure retains that bounded stopped fixture root for ROOT inspection. The preexisting real corpus is never touched. Child commands use the qualified global-deadline/TERM/KILL/drain helper; the Python/SQL phase has the same absolute wall deadline and disk/proof monitoring. The cleanup has a separate bounded grace interval. Report exact commands, setup, input hashes, expected/actual SQL outcomes, plans, native hashes, timings, resource samples and cleanup. Local success is not real RDS performance acceptance.

Suggested commit: `test: qualify the metric membership guard against sealed014`
