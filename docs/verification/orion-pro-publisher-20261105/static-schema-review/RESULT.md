# Static review result — proposal awaiting ROOT review

Suggested commit: `docs: audit publisher harness against the sealed Pro schema`.

The complete static review is delivered. **No existing harness/product/receipt was changed; no fourth PostgreSQL run, HTTP request, source/provider read, cloud action, Git/CI/WORKLOG action or publisher implementation occurred.** The product path `dashboard/scripts/orion_pro_publish.py` remains absent.

Exact static rerun:

```sh
python3 docs/verification/orion-pro-publisher-20261105/static-schema-review/review.py
```

Actual output is retained in `static_inventory.stdout.log`. The command uses only Python standard-library text/AST/hash parsing and writes only this review directory. It imports no application, fixture, database driver or publisher. No source body or real-data row is input to this review.

| Expected check | Actual |
|---|---|
| Approved model/012 agree across94 active tables/1709 columns | Exact names,types,nullability,defaults,identity declarations matched |
| Actual key/constraint definitions agree |94 PKs,105 UQs,431 FKs including actions/deferral,846 CHECKs,153 indexes matched |
| Complete Python access/write/SQL inventory |1288 subscript/index sites,952 string-key sites,117 SQL execute/copy sites,145 typed calls |
| Raw row dictionaries tied to real table/column definitions |166 explicitly traced sites;165 valid keys,only `coverage['revision_id']` nonexistent |
| No unknown explicit typed write field or invalid literal enum | None found; dynamic spreads/PKs and intentional negative inputs separately reviewed |
| All actual/future-path SQL classified |45 sites:34 literal,11 dynamic; other72 are suppressed/unused Reader hooks or unrelated Pilot scenarios |
| Four frozen reader DTOs/selection/state contracts inspected | Paths,types,aliases/profiles,score scopes,coordinates and conditional/light/heavy branches mapped; no additional missing DTO key found |
| Explicit canonical API export includes every local import | All local imported module/JSON paths included |
| Earlier proof preservation | All148 SHA256 entries unchanged before and after; reviewed current code/model/SQL bytes also match the third-run source hashes |
| Database/HTTP/network execution |0/0/0; all runtime/deadline/privilege/concurrency checks remain unverified |

The principal concrete corrections are the real coverage five-column PK and typed revision/interval object, a coherent B playing/unused cohort that still distinguishes squad count2 from played-only1, explicit synthetic content revisions, a driver that preserves invalid empty admission input, and P01 recorded only after its complete setup criteria. `PROPOSED_DIFF.patch` contains an **unapplied partial proposal** for S01/S02/S03/S08/S09; proposed Python was AST-parsed only. It does not implement a publisher, apply the diff, or resolve the remaining oracle work by implication.

`AUDIT_MATRIX.md` records14 precise defects/contract/test gaps and the full SQL/access/result-index classifications. `COVERAGE_PROPOSAL.md` and `COVERAGE_CONTRACT.json` replace the nonexistent revision_id with the real composite key plus data_revision,match_revision_id and half-open interval. They preserve NULL/count/state/nullable document references and old pinned interval closure correctly, without inventing an id,is_deleted,unknown stored row or new table.

`READERS_AND_FAMILIES.md` traces all participating facts/profiles/aliases/outputs to the four frozen routes. `E2E_CHANGE_PLAN.md` supplies the outstanding pre-code oracles: exact coverage/alias/profile/shootout setup checks, selected generation flags, NULL score observation versus absence, selected NULL profiles and nullable shots, absent/null collection successors, real code/policy/closure metadata and precise dirty-race barrier placement. The actual snapshot policy, upstream row contracts/canonical policy/transform SHA and downstream publisher code remain separate declared levels; a digest does not authorize a business/source scope.

These are static conclusions, not SQL execution, trigger/transport validation, source fidelity or publisher acceptance. No real-source cohort,014/107,new reader/deployment,frontend behavior or future fourth run is approved by this dossier. ROOT reviews the proposal before any further amendment or execution. `STATIC_CHECKSUMS.json` pins the complete new dossier and source-review hashes; all earlier failures remain immutable and visibly failed.
