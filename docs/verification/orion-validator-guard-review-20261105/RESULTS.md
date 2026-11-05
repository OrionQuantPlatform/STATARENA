# P1 route and native catalogue guards — final local review

The [final actual E2E](runs/20261105T015159567796Z-pinned-route-expanded-native-catalogue-green/result.json) passes **14/14**,0failed/unverified. SHA256 `a37d657bf4871d3a24829ca599b2a07acab7fc4754ce59e02a4b9063a6ef0156`. These are the new route/catalogue review workflows. The earlier functional14/14 remains historical at commit `85033e90631b82d1257298ce54c72071fd091a61`; it does not prove these expanded guards.

Only the two reviewed product gaps changed. The runner now passes literal `hostaddr='127.0.0.1'` alongside host before libpq connects. Its owned marker, aware postmaster instant, database/user/read-only/ordinary-role checks remain unchanged. The helper now fingerprints46 native views with columns/types/collations/options/definition/owner/ACL, three schemas' owner/ACL, three fixture roles' safe native flags/configs, relevant schema/global default ACLs and memberships involving any fixture actor in either direction. References use role/schema/type names rather than nonportable OIDs; password fields are excluded. All previous table/column/FK/CHECK/index/trigger/function/sequence inspection stays intact and bounded.

The [actual pre-fix RED](runs/20261105T014626469650Z-exact-cast-functional-eight-guards-red/result.json) records6passes and8expected failures on the unchanged archived helper288…/runner1b1…. The same final E2E bytes `f2579dffc12243fd216e48ebc195dd87f0b1a3874dba60c65b07b1e5c2c9e368` produced RED and green. The eight failures were route pinning, missing categories, view drift, schema CREATE drift, schema/default ACL drift, global/default ACL drift, runtime BYPASSRLS and runtime→ingest membership. They were real missing-guard outcomes, not mocked football/database results.

## What the new proof establishes

| Check | Actual result |
|---|---|
| Poisoned PGHOSTADDR | Actual CLI subprocess with203.0.113.77; old connector attempt prevented by the E2E driver **before libpq**; no real nonlocal connection |
| Corrected CLI route | Explicit/effective hostaddr127.0.0.1, actual owned PG preflight succeeds; offline mode still makes0driver connection calls |
| Native categories |3schemas,46views,3roles; baseline default-ACL/membership counts0. Deliberate schema/global default grants and role edge/flag changes are detected |
| Drift handling | Each committed fixture drift refusesCATALOGUE; separate native view/schema/default/role/membership audit confirms exact restoration. Runner performs no repair |
| Positive014/no-op/LOCAL099 | One function+timestamped journal entry per apply; no-op changes no clocks; old journal rows exact; all views/security/roles/defaults and native bootstrap data unchanged |
| Core guarantees |014function SHA e0810f8670b2cb627ade2c76e3c8eb527ab31fd595d5cf939fd63bfc5cf649d6,139/46 equivalence, B0, native digests and routine properties/owner/ACL logic unchanged |
| Resource gate | Final local campaign18.08s; metadata maximum reported14908193bytes, not process RSS; bootstrap row-buffer peak2152bytes, not a COPY/dense memory benchmark |
| Cleanup |All clients closed, owned PG stopped and its directory removed |

The SQL predicate includes memberships in both directions and relevant creator defaults at schema/global scope. The executed mutations cover the exact reviewed cases; this is not an exhaustive test of every possible PostgreSQL privilege graph or a general RDS role mapping. The actors and targets remain the closed local fixture identities.

## Revisioned policy and preserved archive

New helper SHA `354d285787327900971cb2a4efe2ead688c06fe57fdc84fb64c4f210c0ccecce`; runner SHA `3fe82b365b809efaab01c60cd16d64450ebeab0b1bf0e6148ef68bc88dca12b9`.

The [new P1 manifest](../../../dashboard/backend/schema-policies/orion-pro/guard-review-v2/m18da43-p014-membership-nonnull-v1.json) SHA is `6ecdf33f7084eba21eb31198621a50cd01a53309c303d8c221908c07503e2a92`; [new native oracle](../../../dashboard/backend/schema-policies/orion-pro/guard-review-v2/m18da43-p014-local-oracle-v1.json) SHA `6305017e7294ba1f92361dc6d3115d4e46ba751918c20b8a39f477f4e4f9efd9`. They live under the new fixed `guard-review-v2` directory and declare manifest/oracle kind v2 plus an explicit inspection contract. The logical function policy ID retains v1 because the139/46 function itself is unchanged. Exact manifest hashes remain required; there is no latest/arbitrary path/SQL fallback.

The new revision binds its actual new source hashes, expanded native catalogue and historical checkpoint85033e9/old253 manifest/historical functional14clock receipt. It introduces no source-overlay or RDS compatibility pair. LOCAL099 has its own new [artifact and manifest](local-compensation/m18da43-p099-local-restore-v1.json), separate acceptance and append-only semantics. No production099/015, schema/table/index/grant or014function change is introduced.

The original253 manifest remains SHA `d4e98446837e3ee01c8b081e1883867e6b80241acda157dac69d1e72e95601a3`. All253 archived entries were read and hash-verified at85033e9; old proof/receipt/snapshot bytes and original policy JSON/oracle stay unchanged. **Current HEAD helper/runner hashes intentionally differ from that checkpoint**. Their historical bytes resolve through the archive commit and captured inputs; the old manifest is not edited to bless new HEAD. See [pre-green-static-review.json](pre-green-static-review.json), [product-review.diff](product-review.diff) and the archive checks in both actual runs.

## Preserved run history and bounds

1. [Original setup stop](runs/20261105T014130056047Z-archived-product-missing-guards-red/result.json),2pass/1fail/11unverified,3.209s: the new independent audit omitted `defaclobjtype::text`, causing42725. No targeted missing-guard case ran and product code was unchanged. This is a fixture failure, not the functional RED.
2. ROOT's cast-only continuation preserved that run/ledger, fixed only the test cast and allocated the functional RED+green with the same bounds.
3. [Actual eight-guard RED](runs/20261105T014626469650Z-exact-cast-functional-eight-guards-red/result.json),6pass/8expected failures/0unverified,16.533s, then the narrow product corrections.
4. [Final green](runs/20261105T015159567796Z-pinned-route-expanded-native-catalogue-green/result.json),14/14,18.08s, exact same tests as the actual RED. All three owned clusters were cleaned up. No fourth start is authorized.

The namespace has its own [campaign ledger](campaign.json), [archive authorization](archive-authorization.json), [cast continuation](root-cast-continuation.json), expected-failure traces, native metadata audits, safe route tripwire trace, prepared artifacts and source snapshots. Limits remained8s statements/1s locks,32MiB metadata/16MiB buffers,512MiB temp/backend,8GiB PG soft stop7GiB and64MiB evidence. No dense, source/API/cloud/RDS/SSM action occurred.

Exact final command:

```sh
python3 docs/verification/orion-validator-guard-review-20261105/e2e.py --label pinned-route-expanded-native-catalogue-green
```

The exhausted ledger refuses another PG start. Reproduction requires a fresh explicit ROOT allocation and retains the old ledger/receipts. [summary.json](summary.json), [environment.json](environment.json), [static-check.json](static-check.json) and [final-hashes.json](final-hashes.json) bind current local results. No old functional proof, dense9/9, RDS deployment, actual source SQL parity or streamer/cutover/purge is implied. `fullAcceptance=false`, `localOnly=true` remain.

Suggested commit: `fix: pin local policy routes and inspect complete security catalogue`.
