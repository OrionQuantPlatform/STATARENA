# Typed Pro pilot E2E protocol — 4 November 2026

This protocol and the executable E2E are written before the implementation they cover. The original approved input is `target-schema.proposed.json`, SHA-256 `028c221d4cd45ad809a2340e62f34ab9df191c593b23c0c45d5f44587eb35a8c`. The previous history prototype and its results are not acceptance evidence for this model.

The bounded native metric-state correction is tested first in `METRIC_STATES_PROTOCOL.md` and recorded in `model-amendments.json`. Candidate `18da43f940870b7a3a3cb49323c847dd5e5174e5eea1f8ff0c8a159cf373cb08` changes exactly four CHECK expressions and four descriptions. The E2E retains the original approval digest and independently reconstructs this eight-path correction before accepting the candidate. It does not describe that candidate as a separately approved model or change the 23 workflow assertions/counts.

## Scope, setup and exact rerun

Only an owned, disposable PostgreSQL 18.6 process listening on loopback is mutated. No AWS, Neon, provider request, cloud write, source transfer, branch, commit or deployment is performed. The runner receives a local connection through `ORION_PILOT_DATABASE_URL` and requires `STATARENA_TEST_DATABASE=1`; no password is placed in command arguments. Temporary PostgreSQL data is removed only after its owned process is stopped. SQL and process logs, fixture/test/model digests and quantitative readbacks remain in each evidence run.

```sh
PYTHONPATH=/tmp/statarena-publication-test-python python3 tests/orion_pro_pilot_postgres.py --run-label acceptance
```

The binary directory defaults to `/tmp/statarena-cache-test-tools/node_modules/@embedded-postgres/darwin-arm64/native/bin`; `--pg-bin` and `--python-path` allow an equivalent explicit local runtime. The E2E checks server version, bootstraps an empty database via `dashboard/scripts/orion_pro_migrate.py --local --target 013`, restarts PostgreSQL, rolls back 013 to 012 locally, then reapplies 013. Each process command and its exit code are recorded. The run's `result.json` distinguishes pass, fail and unverified; an initial missing runner is an expected RED baseline, never a passed acceptance run.

## Failure matrix written before implementation

| Case | Inputs / action | Expected observable outcome |
|---|---|---|
| runner_available | Execute the approved local CLI on an empty owned server | Missing runner gives an inspectable RED; implemented runner exits zero and records migrations |
| active_catalogue | Independently compare `pg_catalog` with the approved model | Exactly 94 active tables and all their column types, nullability, PKs and FKs; nine `models` tables absent; no active FK targets a deferred table; no history or four universal registries |
| bootstrap_bindings | Empty bootstrap periods and positions | Six periods and four positions reference a real sealed generation and immutable `bootstrap_v1` relation contracts; exact digest binding; no guessed generation/hash |
| migration_idempotence_restart_rollback | Apply twice, stop/start owned server, rollback 013→012, reapply | Same catalogue and seed contents, immutable migration checksums, no duplicate seed generation; rollback/reapply is atomic and inspectable |
| typed_shared_editions | A/B share a player and team; C is independent; public aliases, physical match/side/player anchors | Complete FK-valid typed fixture commits; old public route resolves from the retained alias, not current identity cache |
| retained_xg_and_cohort | Correct exact `NUMERIC` xG 0.82→0.67; change a common profile/mapping; retain all cohort rows, minutes, coverage and metric/position/period definitions | Current view reads 0.67; old snapshot/build reads 0.82 and its entire exact dependency set; deterministic cohort computation reproduces the old result; dependent A/B identified and independent C preserved |
| no_op_reimport | Reimport equal typed values and dependencies, including a changed HTTP body with equal normalization | No new typed revision, generation or publication; attempts remain recorded. This exercises the local pilot normalization protocol, not an unadapted production collector |
| http_dedup | Same request/hash twice; distinct request with same hash; failed attempt | Two content receipts for two requests, every attempt retained; missing HTTP fingerprint rejected; no source body persisted |
| source_receipt_retention_guards | Mutate valid HTTP digest/request/origin; legacy retention transition with and without accepted reconciliation/verified cleanup | Receipt values immutable; unaudited transitions rejected; one-way staged→reconciled→deleted allowed only with the synthetic SQL audit inputs; no actual source purge is performed |
| typed_states_and_profiles | Absent/null/zero/empty/numeric-string values and profile string/number variants | Representable profile states preserved exactly; invalid state/value pairs rejected. Any xG state representation missing from the approved model remains explicitly unverified rather than silently claimed |
| contract_and_seed_versions | Wrong contract version; missing/mismatched period or position definition; mutate existing contract | FK/CHECK or immutability rejection; correct version remains readable |
| wrong_parent_provider_h2h | Existing but wrong match/player/team revision; wrong provider record; H2H provider differs from collection | Composite FK or sealing rejection; no accepted cross-family/provider attachment |
| parent_selection_consistency | Correct a selected match-side membership while retaining children anchored to previous physical version | Seal rejects incompatible logical membership; old anchor is allowed when selected membership still agrees |
| shot_profiles | Profile supplied with null shooter/keeper or another player's identity | CHECK/composite FK rejection, without requiring a profile when only an identity is known |
| atomic_heatmaps_networks | Duplicate coordinates; same coordinates in distinct parent versions; out of bounds; edge to another network | Duplicate/out-of-bounds/cross-network writes rejected; independent parent versions accepted; sealed children immutable |
| atomic_collections | Empty vs absent/null/unavailable; child in wrong family/generation; accepted then failed fetch | Explicit states preserved; mixed collection rejected; failed request does not erase accepted children |
| append_only_parser_correction | Same source record renormalized for standing/ranking/match details, old then new generation | Two retained typed observations; at old g old content, at new g correction; no-op does not allocate; previous revision in later g and two states in one g rejected; children immutable |
| generation_guards | Backdated overlap, canonical double selection, sealed-generation insertion, past-value mutation/deletion, reopening closure | SQL rejection or seal rejection; original snapshot unchanged; closure only once in a new draft generation |
| concurrent_generation_order | Two real database connections allocating and committing generations | Second writer waits for the first global transaction lock; committed receipt order increases, rollback leaks no typed partial rows |
| publication_guards | Publish building build, draft snapshot, wrong edition/catalogue/representation; mutate ready aggregate/build | All rejected; valid sealed ready build publishes; frozen publication keeps exact build/catalogue/representation |
| ready_engagement_guards | Retain physical FK-valid match sides but remove edition team selection by noncanonical/closed/tombstone; shared team is still engaged in B; nullable summary teams_count is omitted | Ready build for A is rejected with an engagement-specific error, independently of FK existence, B's engagement and summary-counter checks |
| readonly_role | SET ROLE to a dedicated NOLOGIN web role | SELECT allowed; INSERT/UPDATE/DELETE and generation helper access rejected |
| queue_lease | Two workers acquire, nonowner completes, expired lease reacquired, stale attempt completes under reused owner | At most one active lease; nonowner and stale attempt rejected; attempts nonnegative and transitions valid |

## Evidence and limits

Each run records setup, exact commands, inputs and their digests, expected outcomes, actual assertions, SQLSTATEs, PostgreSQL log, stdout/stderr, catalogue differences and cleanup ownership. A failed prerequisite leaves dependent cases unverified. New checks are not added after the implementation they cover; corrections to the harness preserve the original RED/failure artifacts and are identified in the next report.

The local fixture is an intentionally small typed workflow, not exhaustive reconciliation of legacy variants. It does not demonstrate production collector adaptation, public HTTP/cache/browser parity, remote RDS capacity, WAL, storage savings, latency gains, full source inventory, purge safety or reproducibility of an unspecified Orion scoring formula. Those remain separate acceptance gates. No new formula is introduced.

## Recorded local outcomes

- `runs/20261104T175834735172Z-initial-red-missing-runner`: initial RED, one failed prerequisite and 20 unverified workflows. PostgreSQL 18.6 ran and the absent runner was recorded. The matching source snapshot was added after the run and is explicitly marked as such in `snapshot-note.json`.
- `runs/20261104T181119553842Z-integration-1`: 14 passed and seven failed. The fixture's retained-row clone passed decoded JSONB as an unadapted Python dictionary; dependent correction checks failed as a consequence. The positive shot setup omitted its selected family coverage. The web role was not yet bound by the runner. This original evidence is retained.
- `runs/20261104T181231918635Z-integration-2-jsonb-and-shot-setup`: **21/21 local workflows passed**, including **48 rejected invalid workflows**. Independent catalogue readback: **94 tables, 1,709 columns, 94 primary keys and 431 foreign keys**. Six period and four position seeds are bound to the bootstrap. The 0.82→0.67 correction preserves the old exact cohort sum 1.00 and produces 0.85; shared A/B dependencies change and independent C keeps its build. Owned PostgreSQL was stopped and its temporary directory removed.
- Independent review then identified unimplemented receipt immutability and edition engagement requirements. Their additional executable tests were saved before the corresponding guards. `runs/20261104T181738367644Z-new-guard-gaps-red` failed receipt immutability; its engagement test was rejected only by the existing summary counter and therefore did not establish the intended guard. The corrected isolated test uses nullable `teams_count` and checks the error meaning. `runs/20261104T181829854021Z-receipt-and-engagement-red` then records the genuine **21 passed / two failed** baseline for both gaps.
- After those guards were implemented, `runs/20261104T182008595719Z-receipt-and-engagement-fixed` passed **23/23 local workflows with 57 invalid workflows rejected**. All earlier coverage remains passing. Receipt content/request/provenance mutations and unaudited retention transitions fail; the explicitly synthetic audited transition succeeds without any remote deletion. Missing/noncanonical/closed/tombstone A engagement is rejected specifically for engagement, although shared B engagement and physical match-side anchors remain valid. The catalogue remains **94 / 1,709 / 94 / 431**, and owned PostgreSQL cleanup succeeded.

For that 23-case run, runtime source snapshots were taken before the CLI regenerated the checked 013 SQL. `applied-sql-note.json` explicitly records a later SQL capture whose hashes match the original database migration journal; `applied-sql/` contains the executed SQL. The original result is unchanged. Subsequent harness runs label the startup phase and capture/compare applied SQL immediately after the CLI.

The green receipt separately records a **model fidelity gap**: `player_match_stats.xg` has no `xg_state` or source-text columns in the approved model, so absent/null/empty/numeric-string xG preservation is not established. Profile scalar states and exact numeric xG are exercised. A green bounded local run does not close this gap or the out-of-scope gates above.

Suggested commit: `test: define the selective inline Pro pilot E2E contract`.
