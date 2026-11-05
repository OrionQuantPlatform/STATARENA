# First production publisher — existing four V1 readers

Suggested commit: `test: specify Pro V1 publisher gates and preserve missing CLI red`.

**Preparation only. Publisher implementation and PG/HTTP execution are not authorized in this phase.** The only executable run now is a bounded real CLI check against the absent dashboard/scripts/orion_pro_publish.py, without PostgreSQL/HTTP/source inputs. After that RED, send the proposed local budget to ROOT and stop. The fallback guard19/19, all old fixtures/proofs, normalizer, model,012/013, frontend, Git/CI/WORKLOG and remote state remain unchanged.

Baseline: model SHA256 `18da43f940870b7a3a3cb49323c847dd5e5174e5eea1f8ff0c8a159cf373cb08`,103 definitions/94 active/9 deferred.012 SHA `f255868599c72d69f40f575a919045325ea1093a00fe4f5a6b96eae9f2c49f65`;013 SHA `85525221cad51b32aff79a777098211b4112f9f00ea7161ac93945654eeb6968`. No014 exists in the inspected migration directory. The107-table proposal remains pending and is excluded.

The target is exactly the current `summary-v1-shots-v1` routes: manifest, bounded fixtures, light match summary and lazy shots. Only match_summary and competition_summary products are built. No new V1 field, capability, native-detail DTO, metric product, role/resource or schema is added. ProON501 is an interim boundary, not completion of full parity.

## Admission before computation

The inspected normalizer creates matches with publication_state=draft at line674 and source-scoped shot coverage at lines725–729. It does not insert competition_teams or ready builds/publications. The publisher must fail eligibility before writing a build/pointer/generation when those prerequisites are missing. Building an empty edition from omitted useful draft matches is not an admission policy.

| Input | Legitimate admission condition | Refuse instead of inventing |
|---|---|---|
| Source/reconciliation | Explicit retained typed contract/source-policy and accepted scope/reconciliation receipt pinned by hashes; complete intended match ID/revision set known | No raw body fetch, source RAM read, source path inference, unknown useful leaf discarded, or a fixture result substituted for real acceptance |
| Edition | Exact selected competition_season at dg, correct revision anchor and catalogue competition at cg | No folder-name/array-index identity |
| Matches | Deliberately published canonical/not-deleted revisions at dg; no unexplained selected draft/quarantined/useful omission | Publisher does not flip publication_state in place or silently skip drafts |
| Participants/engagements | Exact home/away facts and declared edition engagements already present, with accepted source/provenance/status | Do not fabricate confirmed engagement merely to pass013 |
| Scores | Explicit accepted final_without_shootout policy for this first publisher, separate shootout; selected compatible score facts or explicit unknown | Do not add half/regulation/extra-time totals, turn missing into0, or infer a final native score from a winner |
| Public routing/profiles | Existing valid aliases and V1 same-source profile policy at cg; no ambiguity; selected NULL remains NULL | No latest-ID/timestamp/global identity fallback or pending107 occurrence-profile substitution |
| Shots | One selected source/variant coverage per match when collected, accurate present/empty count and matching eligible shot facts, period/actor references | Unknown/unavailable may remain explicitly unavailable under V1; never call it an accepted empty collection. Ambiguous/stale/inconsistent coverage blocks the claimed capability |

Draft→published admission, if later authorized separately, must close the old typed interval and insert a reviewed successor in a new owned generation, preserving source values/provenance and every dependent revision binding. That producer/admission operation is **not part of this publisher**. The publisher consumes already admitted typed inputs. An acceptance receipt authorizes nothing by itself; it must reconcile to the actual retained cohort. If such a real receipt does not yet exist, real publication remains blocked while a synthetic owned fixture can test software.

Unknown shots coverage is permitted by the existing V1 response (summary coverage null, shots404/no-store); the first publisher must preserve that state, not require fictional collection for every match. An intended source scope must explicitly admit which capabilities are available. No claim of full native source fidelity follows from a ready minimal summary.

## Exact output scope

| Existing output | First-publisher contract |
|---|---|
| aggregation_builds | One edition + fixed dg/cg + relevant code/environment/representation/metrics/dependency contracts; status ready only after deferred validation |
| match_summary | Exactly one row for every admitted selected published match; exact match revision/date/status/participant IDs and retained labels; selected score scope/value and independent shootout |
| competition_summary | Exactly one row; non-NULL matches/finished/teams/players counters matching013's selected published-match, explicit engagement and canonical participant semantics. Bench/list membership is not relabelled as an appearance. goals remains NULL until a separate complete scoring-total contract is justified; V1 does not expose it |
| publication_versions | Exact ready build/edition/catalogue/representation tuple; close once and retain old tuples |
| catalog_publication | Current discovery pointer only, activated coherently if changed; old frozen reads use each build's own cg |

Do not fill V1 stats/leaders/media placeholders or compute unused aggregates as an implicit feature expansion. The ready trigger checks required summaries/cohorts but does not compute closure, certify source completeness or choose an admission policy.

## Closure and no-op contract

Use the full PUBLISHER_PLAN rationale from the previous coverage review, refined here for actual grants. Compute a versioned per-edition dependency closure before and after a correction. Include selected match/participant/score/engagement/coverage states, every potentially lazy-requested accepted shot and its ordering/period/actor source, selector-relevant aliases/profiles and absence markers at cg, plus only the relevant code/definition/environment policies. Do not hash the ambient maximum generation, transport attempt metadata or an unrelated frontend commit as semantic changes.

A/B share an observed identity dependency; C is independent. Correct A data, then correct the shared catalogue through B: new A/B builds must use coherent selected states, potentially distinct dg/cg, and pointer changes are atomic. C retains **the same** build ID, dataset/catalogue snapshot IDs, token, body/ETag/cursor. An unrelated C change must likewise leave A/B unchanged. A removed dependency and a newly preferred profile/alias must be detected from both old and new closures. The DB stores a digest, not a complete reverse dependency graph; initial bounded full scans are preferable to falsely precise invalidation.

Identical typed/cohort/contract input reuses the existing build and pointer **before begin_generation is called**. Verify function call traces and sequence state as well as table counts: a rejected identical publication after sequence allocation is not the required production no-op. A ready unpublished orphan can be verified/reused on retry, not relabelled as a newly changed input.

## Existing privileges and revised dirty handling

Use the existing statarena_ingest writer/build identity; web reads use statarena_runtime. No new role or grant is proposed. role_grants_sql grants the writer INSERT/UPDATE on mutable outputs/dirty_editions, INSERT plus interval-end UPDATE on publication_versions, and generation helpers. It does **not** grant DELETE on dirty_editions or direct EXECUTE on validate_aggregation_build. The latter is invoked by the deferred ready trigger as its owner. Direct snapshot insertion/update and generation-sequence use are not writer interfaces.

Therefore the first publisher must **retain dirty_editions rows**. Treat generation/revision as a durable hint/high-watermark, not a delete-to-ack queue or full dependency graph. Under the final generation lock, recheck the observed watermark and closure. A newer relevant dirty watermark invalidates a stale prepared activation; a later change must never be lost. Retained rows can cause later no-op rescans; accept that bounded read cost rather than adding a processed flag, resetting generation to a magic0, deleting without permission, adding a grant or allocating a no-op publication merely to acknowledge work. This refines the earlier general plan's “clear processed dirty” wording without changing that frozen document.

Per-edition build transactions are atomic: no committed partial-output repair requires DELETE. A crash before ready commit rolls back that build transaction; ready but unpublished outputs remain immutable and reusable. Force deferred ready validation or rely on commit; do not bypass it with an unauthorized direct helper call. The future workflow must run the actual publisher with writer privileges, not the fixture's superuser connection, and must prove web writes remain42501 even when its readonly startup setting is disabled.

## Transaction/retry shape to verify later

1. Read-only plan resolves admitted sealed inputs, closures, counts, current pointers and dirty watermarks. Equality returns no-op before any generation/write.
2. Under deterministic sorted edition advisory locks, recheck semantic duplicate/ready orphan and compute complete build outputs from fixed snapshots in one atomic build transaction. No accepted generation is allocated merely to label computation. No partial output is committed.
3. Final activation takes the existing global generation lock first, then sorted edition locks. Recheck closures, exact ready IDs, pointer compare-and-swap and watermarks. If relevant inputs moved, leave the old public set and replan; never publish a stale partial A/B group.
4. For a real change only, allocate one generation through begin_generation, close affected pointer intervals once, insert the exact new tuples, update discovery coherently if needed, seal and commit. C is untouched. Dirty rows remain; newer work is never overwritten.

The application lock-order/dedup/closure requirements are not already enforced by the semantic PK of aggregation_builds. Two workers, crash points and dirty races need actual E2E. No code, SQL query, lock acquisition or transaction is executed in this preparation phase.

## Future fixture and workflow

Reuse ReaderFixture and its actual HTTP server/readonly role without editing them. Its prepare currently hand-builds/publishes A/B/C and its correct explicitly chooses A/B; those shortcuts cannot serve as the publisher oracle. A **new local subclass in this namespace**, if later authorized, will reuse the typed input construction but suppress only its build/publish hooks and expose input mutations separately. No initial ready build/pointer may exist when the production publisher is first invoked. Expected summary/count/closure decisions must be calculated independently from the declared synthetic inputs, not by calling ReaderFixture.build or the production planner.

Initial intended inputs:3 editions,5 matches (A3/B1/C1), shared A/B team/player and independent C, tied/unknown dates, explicit engagements, same-source provider/legacy/manual profile decoys, accepted present/empty and unavailable/unknown shot states. Negative admission variants are separate fresh transactions. Add a draft negative and missing engagement, then restore only using new owned fixture facts; no source body or provider is read. Include an explicit native0/false/empty event and52.5/34-metre shot from the existing contract. No107 fields are used.

FAILURE_MATRIX.json is the complete intended local workflow. Only caseP00 (absent CLI) is executable now. P01–P29 remain unexecuted until ROOT reviews the budget and then authorizes the owned PG/HTTP harness. A missing CLI RED does **not** establish the future PostgreSQL/HTTP acceptance.
