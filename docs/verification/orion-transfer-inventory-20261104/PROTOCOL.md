# Bounded Neon/AWS transfer metadata inventory

Owner: ROOT, following Hugo's transfer-scope correction of 4 November 2026. The former third-party ownership is superseded. This pass writes only this evidence folder and performs no transfer, body download, service mutation, migration, collector activation, deployment or commit.

Read the installed `neon` and `neon-postgres` skills before discovery. Prefer the Neon connector. Existing authenticated CLI/direct access is a fallback only if the connector is unavailable or cannot meet the explicit read-only snapshot contract; no new credential, paid resource, branch or endpoint is created or reconfigured. Connection strings/passwords remain in memory and are never printed or persisted.

Scope: Ligue 1 `l_3FJFUl`, seasons `2025/2026` and `2026/2027`; the 62 profile lookup gaps from the prior source inventory plus the known `p_1JuxKR` conflict; currently referenced and previously catalogued source/archive metadata, computed manifest/partition object metadata. No sport/document body is selected, decoded, hashed or staged. Existing stored SHA values identify catalogued versions and are not a fresh recomputation of payload bytes.

Plan sent to ROOT before SQL execution:

1. Discover projects, branches, computes and databases through read-only Neon administration metadata. Match endpoint IDs to the existing local configuration without exposing its DSN. Record inaccessible organizations and archived branches as unverified; do not activate them.
2. One Neon connector transaction on the evidenced source branch: repeatable-read, read-only, statement timeout 8 seconds and lock timeout 1 second. Five metadata SELECTs: identity/catalogue, scoped fixtures, resource pointers, object versions, observation/projection pointers. Explicit field/row caps and a conservative 512 KiB server-side JSON budget per SELECT report truncation.
3. After the Neon transaction closes, one sequential AWS PostgreSQL client/snapshot with the same controls and projections; include exact newly discovered Neon keys in the AWS lookup. Use the existing libpq credential path without printing or reading its secret contents.
4. Compare exact keys, pointer tuples, statuses, stored SHA and sizes. Retain timestamps as observations; an AWS import/index timestamp is not supplier freshness. No count-only completeness claim and no replacement decision from timestamps alone.

Hard budget for this pass: at most **20 SQL statements including transaction controls**, **16 MiB of serialized SQL results**, one client operation at a time, no concurrent snapshots. Planned execution is at most 19 statements (Neon 3 setup + 5 SELECT + implicit BEGIN/COMMIT; AWS BEGIN + 2 SET LOCAL + 5 SELECT + ROLLBACK). Failed submitted statements conservatively consume budget. Read-only administration API calls are recorded separately. Stop before crossing a cap.

SQL inputs and exact statements are saved in `query-plan.json` before execution. Results retain exact sanitized errors, commands/tool arguments, UTC snapshot times, statement/byte counters, input hashes, row caps and scope. If quota/authentication blocks access, keep the error and continue with available metadata/local inventories; do not upgrade a plan, substitute a source or invent results.

Expected classifications:

- `identical_metadata`: same key, pointer/status and stored SHA/size where those fields exist; never a claim of complete source or typed fact fidelity.
- `absent_in_aws` / `absent_in_neon`: exact queried key absent from that snapshot, with source lookup and truncation limits stated.
- `different_version`: pointers or stored SHA differ; retain both versions. `stale` requires a meaningful supplier version order; import timestamps alone leave ordering ambiguous.
- `ambiguous`: conflicting identity, pointer, status or unorderable version evidence.
- `unverified`: inaccessible project/branch, truncation, unqueried body/member identity, missing hash or unresolved current manifest selection.

Any failure and unresolved item remains explicit. Purge, full transfer acceptance and public cutover remain outside this pass. Resume only with the same metadata contract and a fresh separately authorized query budget; this inventory does not authorize a data transfer.

Suggested commit: `docs: inventory bounded Neon and AWS source metadata`.

## Recorded timeout and bounded fallback

The first Neon connector transaction returned exactly `NeonDbError: canceling statement due to statement timeout`, with no usable partial rows. Preserve `neon-run.json`; conservatively charge its entire planned maximum of 10 statements. No successful snapshot is inferred from it.

Fallback announced to ROOT before execution: reuse the configured Neon DSN in memory, with its evidenced direct host, then the existing AWS libpq credentials; one Python process, one connection at a time. Startup options enforce repeatable-read/read-only, 8-second statement and 1-second lock deadlines before the first statement. Each database gets one consolidated metadata SELECT, followed by ROLLBACK and close. Total maximum is now 16 statements including the failed first attempt and both new BEGIN/ROLLBACK pairs. Queries are generated and saved before connection in `fallback-query-plan.json`; no default settings or credentials are changed remotely or on disk.

The fallback reads all scoped fixture metadata, exact `{}` lookup pointers for 63 profiles, already catalogued archive/object versions and a limited set of representative match-resource endpoint prefixes from the existing source inventory/report. It does not retry the broad all-match/observation query that expired. The limited resource-key coverage is explicit in the final receipt. Existing imported/indexed SHA and clocks cannot establish provider-body freshness or repair the known wrong member identity.

The direct Neon snapshot exposed an incorrect server-TLS guard; its fail status is retained. Two subsequent client TLS handshakes executed zero SQL: the first capture failed on an unsupported driver attribute, the final capture recorded SSL in use with verify-full. One additional AWS RR/RO SELECT completed the exact newly discovered Neon keys, with BEGIN/ROLLBACK: final conservative SQL total19/20. Its exact query was saved before connection in `aws-complete-query.json`. No further SQL is executed in this pass. See `RESULTS.md` and `inventory.json` for the complete failure chain and limits.
