# Local adoption of M0/P1 — pre-code contract

ROOT authorizes this new namespace, new policy/upgrade modules,014 and immutable manifests/oracle **locally only**. The static policy design remains frozen. Model18da43,012/013, their default producers/bootstrap, prior receipts and bulk v1 remain unchanged. No RDS/AWS/Neon/source/API connection, CI/git/WORKLOG change,107 application, streamer or deployment is permitted.

Allocation: `014_orion_pro_membership_nonnull.sql` is the only new production migration. Its bytes are the already-qualified candidate function plus final newline, SHA256 e0810f8670b2cb627ade2c76e3c8eb527ab31fd595d5cf939fd63bfc5cf649d6. It has no journal INSERT, grants, trigger/table/index, bootstrap or other statement. ROOT allocates099 only for an explicit LOCAL compensating artifact inside this proof namespace; there is no production099/015 file. Compensation needs a distinct manifest and acceptance; no arbitrary path/SQL/latest is admitted.

## Complete workflow expected before implementation

`tests/orion_pro_validator_policy_local.py` is written before the modules and retains the actual missing-implementation RED. Then a single green campaign may start one owned PG18.6 with two databases: an exact bootstrap target and a compact native facts database (40 appearances ×31 canonical metrics; no live source). The native fixture and negative workflows are imported read-only from frozen earlier tests with only in-memory fixture constants changed. The second database remains P0; it demonstrates the first-upgrade populated-target refusal and a transactionally rolled-back exact P1 overlay, without rewriting a migration receipt.

| Workflow | Observable expected outcome |
|---|---|
| Implementation absent | Real RED,0 PostgreSQL starts; later cases unverified |
| Owned setup | One cluster, two DBs; schema owner/ingest/runtime ordinary roles; exact012/013/bootstrap and role grants;8s statements/1s locks/512MiB temp |
| Oracle preparation | Read native P0 catalogue, transactionally replace only exact P1, capture P1 catalogue/procprops and roll back; source hashes fixed before manifest generation |
| Closed manifests, no hash cycles | Freeze oracle bound to code/SQL/B0 before manifest; P0→P1 parent hashes exact;099 local only; acceptance exterior binds manifest+code+actual before-state and release identifier |
| Offline default | Actual CLI exits with a plan and zero DB/service access despite poison cloud/DSN environment; unknown policy/path/latest/hash refused before connection |
| Function equivalence | Reverse139 target equalities to exactly P0;46 nullable comparisons retained,81 clauses; actual1709 declarations match M0 |
| Start-time timezone identity | Marker Europe/Paris and runner UTC must identify the exact same aware instant, preserving microseconds. A marker moved by one microsecond, a naive timestamp or nonparsable value must refuse. No timestamps of copied facts are normalized |
| Wrong/nullability/catalogue/function/journal/properties | Refuse; do not repair drift. Manual mutations are confined to owned test DB transactions and restored |
| Runtime/ingest application | Runner refuses ordinary nonowner actors; native function replacement/journal INSERT attempts return42501 |
| Lease held | Migration and generation leases separately refuse, no waiting beyond1s and no mutation |
| Failure after function / after journal | Actual transaction rollback restores P0, journal, bootstrap, all native facts and sequence state |
| Lost commit acknowledgement | Inject exception after actual commit; do not claim rollback. Fresh RO inspection proves exact P1 and014; retry is a no-op |
| Adoption | Only one function body and one014 journal entry change; OID/owner/ACL/all procprops, every other catalogue row, B0/seeds/contracts/generations/sequences unchanged |
| No-op and independent readback | New process reads exact policy state; repeated apply allocates nothing and appends no duplicate |
| Bulk v1 compatibility | Actual frozen v1 baseline guard refuses a target with014; no relaxation or old-receipt modification |
| Populated target | First P1 adoption refuses the compact facts DB. Transactional local overlay preserves independent SQL-native digests of all94 relations and precise JSONB/numeric/state distinctions. The frozen9/9 remains the evidence for the identical139/46 function's membership/FK counterexamples; do not reattribute it as a new semantic run |
| Wrong acceptance, old before-state, unknown journal/body | Refuse; facts/control rows remain exact. Target must be one exact known chain, not merely have a recognizable function |
|099 compensation | Different LOCAL acceptance; restore exact P0 body with new099 journal row, keep014; no production099/015. Retry no-op; later attempt to reapply014 refuses the compensated chain |
| Protection/cleanup | Old input hashes and frozen manifests unchanged; no raw bodies/DSNs/credentials persisted; actual commands/inputs/errors/native digests/catalogue/procprops/limits/timings saved; all connections closed and owned cluster removed |

The actual runner remains LOCAL ONLY. A marker must be owned by this OS user, inside a named owned temp PG root, with matching on-disk postmaster directory/port/start time and loopback connection identity. It never accepts a DSN/host/password/cloud option. The connection defaults read-only; apply switches one transaction to read-write only after identity checks, then fences migration/generation and rechecks state. Existing function owner only, no new privileges. The scope stays bootstrap-only for adoption and local compensation; a real populated-target upgrade would require another reviewed contract.

The oracle fingerprints all typed catalogue objects and SQL-native row text with bounded framing; journal additions are inspected separately. Technical JSONB is not decoded through floating-point. All facts and existing bootstrap clocks remain exact within one DB. Across installations, only explicitly recorded installation clocks/txid/OID and generation/snapshot mappings can differ; no broad timestamp exemption. Function properties include the complete native pg_proc projection in addition to normalized definition, owner, ACL and effective role access. OID is compared within a DB, never across independent DBs.

The new manifest does not hash itself, its containing commit or receipts taking it as input. It hashes the already-created oracle, code, old inputs and exact014. Acceptance is a separate artifact. Current policy is determined by **both exact journal chain and actual catalogue**, not either alone. Future streamer compatibility must additionally bind the exact typed-source policy/local-overlay identity and acceptance; the abstract P0/P1 names alone are insufficient. No compatibility pair is granted by this local adoption lot.

## Budget and stop

ROOT grants **one pre-code run and one green campaign,≤10min each**, at most2DB/1ownedPG. This is not a new dense budget.8GiB owned PG, soft stop7GiB;512MiB temp/backend;32MiB retained metadata;16MiB native buffers;64MiB evidence. Statement8s/lock1s; existing row/phase/sequence ceilings unchanged. At the first unexpected setup/guard/limit failure, preserve receipt+cleanup and brief ROOT before any new PG. No third campaign or implicit retry. Native9/9 already covers478547scalars; the next independent source E2E will carry that density, not this compact campaign.

ROOT continuation after the concrete first stop: the4pass/1fail/9unverified receipt9b63… remains unchanged, with all five prepared artifacts archived beside it. Initdb confirms Europe/Paris while the runner selects UTC; text start-time equality was an incorrect guard. After static review ROOT grants exactly one additional compact campaign≤10min with the same bounds, using native timestamptz versus a strictly parsed aware datetime and preserving microseconds. Naive/unparsable values refuse. The second-start authorization binds final code/test hashes and the original failure; no third PG start is authorized.

Exact rerun command: `python3 tests/orion_pro_validator_policy_local.py --label <new-label>`. The ledger deliberately refuses another campaign after its one allowed PG start; any reproduction requires a new explicit ROOT allocation and preserves this ledger. Setup/oracle/adoption/commit timings are separate. Local compact success establishes neither real source acceptance nor RDS/global-universe capacity; global validation remains around5.6s per seal/commit in the previous local0.5M proof, not a WAN/HTTP or micro-instance promise.

Suggested commit: `feat: adopt versioned non-null membership validation locally`.
