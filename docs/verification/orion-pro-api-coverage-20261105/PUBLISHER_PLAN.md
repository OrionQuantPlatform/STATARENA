# Production Pro publisher on the approved103-table model

Suggested commit: `docs: map Pro API coverage and define publication rollout`.

**Design proposal only.** No orion_pro_publish.py exists in the inspected scripts. No publisher code, publisher test/SQL, new table/resource, source read, remote mutation or activation is performed here. The local fallback guard is a separate completed change. Native-detail107 approval is still pending and is not needed to design this first existing-model publisher.

## Existing implementation versus missing work

The real reader derives a pro1 token from a ready edition build plus dataset/catalogue snapshot IDs/generations, representation_version, code_content_sha256, dependencies_sha256, environment_sha256, metrics_contract_version and transform_version. It additionally requires an actual publication_versions row. A ready but never published build is not readable. Unpinned requests resolve current edition pointers; an explicit old token can resolve a retained historical publication. No *_current view supplies a frozen response.

ReaderFixture.build/publish creates small synthetic outputs by hand. It writes match_summary and competition_summary, marks a build ready and publishes pointer versions; its dependency hash is only a fixture tuple containing edition/data/catalogue generations. Its correction method explicitly chooses A/B. It is **not** a production dependency resolver, aggregate publisher, dirty-queue consumer or proof of complete live normalization. Its identical-republication case exercises013's rejection/rollback; a production publisher must detect the no-op first. The currently inspected normalizer still writes matches with publication_state=draft and does not create ready builds or pointers. A draft dataset cannot become a complete publication by building an apparently empty edition.

## Grain, inputs and outputs

One build is **one competition_season_id × one immutable representation/computation contract × one exact selected dependency state**. The existing PK is build ID; the DB does not provide a semantic unique key for that signature. Publication is a separate interval per edition. A catalogue singleton is a current discovery pointer, not the catalogue for every existing build or an immutable global-catalogue history.

| Existing destination | First-publisher use | Required rule |
|---|---|---|
| ingest.dataset_snapshots | Reuse sealed data and catalogue receipts, potentially with different generations | Never allocate a new snapshot merely because a global counter advanced; never reopen/add to sealed generations |
| analytics.aggregation_builds | building→validating→ready or failed; bind code/environment/contracts/digests and edition revision | Ready and its outputs immutable; exact selected edition/anchor agrees |
| analytics.match_summary | One row per selected eligible published match, including known upcoming/unknown date | Exact match revision, participants/retained labels/date/status, explicit score scope, separate shootout; NULL stays unknown |
| analytics.competition_summary | Exactly one edition row | matches/finished/engagement/player counters from the selected cohort; goals only under a documented complete score/coverage contract |
| analytics.metric_totals | Later registered metric products, scoped to build/subject | observed_count/eligible_count/minutes, numerator/denominator and coverage retained; no native H2H totals or generic source-subtree storage |
| analytics.player_competition_team_stats / player_competition_stats | Later per-team stint and cross-team player aggregates | Group by proper grain; appearances evidence, denominators/coverage, no duplicate periods, no averaging percentages |
| analytics.team_competition_stats | Later derived team results/metrics | Explicit score/sporting rules and points deductions; not a substitute for an observed standing table |
| analytics.publication_versions | Atomic affected-edition pointer close+insert | Ready build, matching edition/catalogue/representation; old pointers retained; identical tuple is no-op |
| analytics.catalog_publication | Current catalogue discovery activation, if required by the product | Change atomically with every affected edition; unchanged C keeps its own older catalogue snapshot |
| ingest.dirty_editions | Work scheduling/watermark only | Never treat its reason or absence as a complete dependency graph; clear only the processed generation/revision by comparison |

The first usable publication need only emit the two mandatory summary products supporting the existing four V1 routes. Other aggregate tables may remain unused and capabilities remain explicit. This does not establish full-site parity. Do not fill old summary-v1-shots-v1 blank stats/leader/media slots or change the frozen profile/frame policy. A later product that exposes aggregates gets a new representation adapter/contract and its own E2E; preserve old tokens and bodies.

Eligibility is an independent gate: retained matches must be deliberately admitted as published through the existing typed revision/generation process, with explicit edition engagements, aliases and accepted coverage/source policy. Do not flip draft rows in place, create guesses from folder/array position, fabricate engagements solely to satisfy a guard, or silently exclude useful draft matches and publish zero. Producer admission/reconciliation remains separate work; its lack must stop a ready/public build.

## Dataset versus catalogue cohort

For the existing V1 reader, dataset generation fixes the selected edition/matches/participants/scores, coverage and accepted shot source/variant, shot facts and period-definition references/order. Catalogue generation fixes competition labels, routing aliases and the exact allowed team/player profile selection. The selected match source and shot source participate in profile eligibility. Preserve the current V1 preference: same-source provider_global/provider:exact, same-source legacy_normalized_global, then global manual/NULL source; reject equal-priority ambiguity. A selected NULL name remains NULL. Pending107 occurrence-context profiles must not be substituted into this existing adapter.

Physical FK anchors and type/definition versions are checked as well as generation eligibility; a FK alone is not a full cohort proof. No latest-ID/timestamp, wall-clock current view, identity fallback or all-period sum chooses facts. Source aliases, optional/unknown coverage, absent profile candidates and collection order are dependencies as well as positive scalar values.

## Exact dependency closure and unchanged C

Existing aggregation_builds stores a **digest**, not dependency rows. dataset_snapshot_documents/document_lineage are provenance, not a generic reverse dependency registry. Do not store sporting input rows in error/quality JSON or invent a new history/registry table. The initial robust implementation can recompute the declared closure from retained typed history for every current published edition in bounded batches. Reverse-index optimization is later work only after equivalence is demonstrated.

The closure contract must be versioned and deterministic. For V1 it includes:

1. Edition selection/membership and all published match revisions, including relevant eligibility/exclusion states so a newly admitted/removed match cannot be missed.
2. Exact selected participants, score scope/value/shootout and engagement membership needed for summaries/counters; typed unknowns distinct from0.
3. Every selected shots-coverage state/count/source/variant and every retained accepted shot that **could** be lazily requested in that edition, not only shots already opened by a user. Include native fields, order and period definitions used by V1.
4. All selector-relevant alias/profile/dimension rows and absence markers for those matches/teams/players/competition at cg. A newly preferred provider profile or newly valid alias must be detected even though it was not in the prior positive result set.
5. Registered metric/period/position/rule/transform definitions actually used by the admitted product, plus the relevant code/environment/serialization policy. Exclude unrelated frontend files/commits and transport attempt counters/wall-clock recomputation timestamps from semantic equality.

Compute the closure **before and after** a correction. Changes to a shared identity through B can affect A as well; removed membership or a changed mapping can also remove dependencies. Inspect both sides, not just the new source's dirty edition. Hash typed values/types/states/order, physical accepted observation/version references and contract-relevant eligibility. New HTTP attempts or an unrelated publication generation alone are not relevant changes.

| Correction | Required publisher decision |
|---|---|
| A score/shot changes | New A build with selected new data state; old A remains readable |
| Shared team/player/profile/mapping used by A/B changes | Re-evaluate both closures; rebuild all affected A/B and publish their pointers together |
| Independent C changes | A/B closures equal→reuse **the same build IDs and dataset/catalogue snapshot IDs**, hence same tokens/ETags/cursors |
| A data unchanged, catalogue used by A changes | A new build can reuse old data snapshot and use new cg |
| Global max generation advances from unrelated data or pointer bookkeeping | Do not create a new C/A/B build merely to point at that number |
| Complete typed state and contracts identical on retry | Reuse current build/publication; allocate no accepted generation and no new token |
| Closure algorithm/version unavailable or impact incomplete | Stop affected publication or conservatively rebuild the bounded declared scope; do not claim fine isolation of C |

Do not put the ambient global generation or arbitrary snapshot ID into the **semantic change detector** and then conclude every edition changed. Snapshot IDs/generations are still bound in an actual immutable build/token; on no-op, reuse its earlier IDs rather than manufacture new equal snapshots. Code_commit can name the retained reviewed source; an unrelated new main commit alone is not a rebuild reason when the relevant code_content_sha256 and all contracts are unchanged.

## Build, validate, publish, retry

Proposed stages, with no new persistent relation:

1. Read/plan: choose sealed admitted input states and explicit representation/metric/source policies; resolve complete per-edition closures and affected union; compare retained builds. Produce inspectable hashes/counts/reasons without source bodies.
2. Build each changed edition under a deterministic transaction-scoped edition advisory lock. Recheck a matching ready/unfinished build, so two publishers cannot create semantically duplicate outputs. Compute from the same fixed snapshots, insert the typed outputs and run validation before ready. Commit ready outputs separately from public activation. No accepted generation is required merely to label an unfinished computation. The exact lock ordering and crash/retry behavior need pre-code E2E; this is application orchestration, not an existing013 semantic-uniqueness guarantee.
3. Final publish transaction: take the existing generation advisory lock first, then edition locks in sorted order; recheck plans/current pointer values/relevant dirty watermarks and input closure. If relevant input moved, stop/replan without publishing a stale partial group. An unrelated generation must not force a new C build. If all target pointer/catalogue tuples already match, return no-op **before** begin_generation.
4. For an actual activation, allocate one generation after the existing lock, close the affected publication intervals once, insert new exact build/catalogue/representation tuples and update catalogue discovery coherently. Clear only dirty rows still covered by the processed watermark/revision. Seal and commit all affected pointer changes together. Never rewrite old ready outputs, old facts or old source rows.
5. Crash before build commit: no ready output. Crash after ready but before publication: an immutable unpublished build may remain; a retry can verify/reuse it. Crash/failed validation during pointer transaction: old published group remains active; no remote rollback/delete is needed. A ready row cannot be marked failed/edited later to conceal a stale plan; leave it unpublished and record the reason in the bounded execution receipt.

A first implementation may scan more than the exact affected set, which costs read time. It must still avoid *publishing* unchanged builds. Edition lock hash collisions may serialize unrelated work but cannot select data. The global generation lock protects the activation boundary; do not hold it through an unbounded all-source computation. Lost invalidation, duplicate ready builds, lock ordering and restart are application requirements needing E2E, not claims of an already complete publisher. No memory/latency/large-volume capacity claim is made here.

## Aggregate correctness beyond FK guards

013 already checks sealed inputs, ready build immutability, exact selected match/date/status/participant/score agreement, mandatory summaries and engagements, populated counter agreement, output edition membership and same-build match scope for metric_totals. It protects typed interval/generation/no-op/revision rules and exact publication binding. Reuse it.

It does **not** recompute the dependency hash, complete reverse closure, correct numeric aggregation formulas/denominators, every optional product's completeness, historical native DTO parity, dirty-watermark ownership or atomic impact across all affected editions. A NULL summary counter can pass the optional counter guard; the publisher's chosen contract must require the counters it advertises, not use NULL to evade reconciliation. Ready status is necessary but not sufficient evidence of product correctness.

Define registered aggregations before adding products: sum disjoint compatible periods only; appearances from evidence rather than bench entries; ratio of summed numerator/denominator rather than mean of percentages; metric-specific eligible minutes; preserve NULL versus observed0/false/empty. Distinguish observed provider totals, canonical match-derived totals and analytic derived totals. Weighted provider rating requires its declared weighting/coverage; native order/labels cannot be reconstructed from an analytic average. Do not infer native H2H finished/totals or standard lineups from these products.

## Future pre-code publisher E2E gate

Write the workflow/protocol/harness before publisher code, retain a missing-publisher/old-behavior RED, then exercise real PG18.6 and real HTTP with:

- Admitted nonempty A/B/C, different dg/cg and source/profile/alias decoys; reject useful draft omissions, missing engagement or unavailable required input.
- Complete mandatory summaries, unknown dates/scores, separate shootouts; exact metric denominators/periods/0/NULL and independently calculated expected values.
- Same typed input/new HTTP receipt no-op; relevant code/definition/source policy change; source correction A; shared dependency corrected via B; independent C retains build/token/body/ETag/cursor.
- Change that removes membership; new higher-priority profile/alias; missing candidate becoming available; source-specific selection versus global decoy.
- Two concurrent builders/publishers; newer dirty watermark during computation; crash before build/after ready/during atomic pointer group; idempotent retry reuses ready output and clears no newer work.
- Old V1 body/ETag and frozen catalogue after multiple activations; mutable stale cursor409; cold HEAD/304 metadata-only; runtime is actually read-only.
- No source files/object/provider/legacy serving fallback; SQL/query/time/bytes/count evidence, tracked explicit source export, complete cleanup. No real-data or hosted performance conclusion from the fixture.

Existing reader/013 E2E receipts are regression evidence for their bounded contracts; they cannot substitute for this unimplemented production publisher workflow. Real source fidelity, source NULL/native states, bulk throughput, resource capacity and backend/data acceptance remain ROOT's separate gates before any activation or purge.
