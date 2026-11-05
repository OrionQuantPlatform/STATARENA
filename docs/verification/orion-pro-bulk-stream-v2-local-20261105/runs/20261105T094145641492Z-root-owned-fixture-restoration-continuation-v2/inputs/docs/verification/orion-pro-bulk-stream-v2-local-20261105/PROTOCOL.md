# Native streaming v2 — implementation preparation, no PG authorization yet

ROOT approved the frozen design, not a campaign. Only new streamer/test files and this new implementation namespace may change. No PG, source/RAM/cloud/RDS/SSM/API/git/CI/WORKLOG operation is authorized here. The first actual E2E run is the missing-implementation RED with zero PG. Further execution requires ROOT_CAMPAIGN_AUTHORIZATION.json binding the final source/test/bindings hashes and one campaign. Do not manufacture that authorization during preparation.

Current reference: guard-v2 P1 manifest6ecdf33f7084eba21eb31198621a50cd01a53309c303d8c221908c07503e2a92, oracle6305017e7294ba1f92361dc6d3115d4e46ba751918c20b8a39f477f4e4f9efd9, helper354d285787327900971cb2a4efe2ead688c06fe57fdc84fb64c4f210c0ccecce, runner3fe82b365b809efaab01c60cd16d64450ebeab0b1bf0e6148ef68bc88dca12b9. Static design's5250 reference is historical and unchanged.014e081 remains exact. All existing qualifiedImportPairs arrays stay empty; this writer needs a separate exact local source-overlay→target-journal pair acceptance.

The source-free fixture is the frozen native fixture function read-only, cloned in RAM, with native stage facts inserted before the first seal by the E2E supplement (compact1010stages: parent revision2000 before child2 and1008flat roots; dense2stages: parent10 before child2), with VERSION=source_free_stream_v2_fixture_v1 and actual E2E+fixture-code SHA as producer. Compact shape40×31=1240/four matches/40 players; dense15437×31=478547/612matches/800players. Every phase/import/fact receipt uses that actual fixture version/hash. No real-RAM result or real normalizer SHA is substituted as synthetic acceptance. ROOT's separate real15/15 is context, not this fixture's proof.

## E2E before product code

| Case | Intended observable result |
|---|---|
| implementation_available | Actual missing streamer RED;0PG; later cases unverified |
| campaign_release | Without ROOT's exact final hash authorization refuse before PG; at most1ownedPG/2DB/20min, compact then one dense source+core transfer |
| owned_setup_and_compact_fixture | M0/94/1709/431, ordinary owner/reader/ingest, exact P1 overlay source with journal012/013 and P1 journal target012/013/014; known bootstrap; source/target hostaddr127 |
| offline_default | Actual CLI no DB/service connections and no source read |
| exact_policy_pair_and_ownership |6ec/630/helper/runner fixed; source overlay descriptor independently names journal/body/properties/producer; no abstract P0/P1 compatibility.74COPY/3controls/17empty,106 control components |
| endpoint_runtime_and_route_refusals | Wrong marker/port/epoch/role refuses before DML; poisonedPGHOSTADDR cannot route away; actual runtime native COPY denied42501 |
| source_and_binding_drift | Wrong code/policy/model/producer/acceptance or changed typed source refuses; no mutation. Real source hash is not a fixture hash |
| target_bootstrap_collision | Unrelated valid target fact refuses; no merge/ON CONFLICT/overwrite |
| policy_catalogue_drift | Actual target view property drift refuses TARGET_POLICY before COPY; expanded native guard catalogue retained |
| unowned_and_forward_source | A valid unowned run refuses SOURCE_RECEIPT; exact document-lineage future parent refuses PHASE_OWNERSHIP with source acceptance recomputed |
| reservation_bounds | Valid extra source identity above1M refuses before nextval/COPY; global5M bound maintained |
| bounded_self_graph_and_native_cycle | Valid source with>4096 self vertices refuses before graph fetch; native cycle attempt rejects23514 without disabling guards; compact positive native oracle plus observed actual self COPY windows prove parent2000 copied in an earlier command than child2, with strict rank/keyset progress; dense small graph orders upstream and m29/m30 before dependants |
| metadata_and_encoded_row_bounds | Valid typed oversized fact refuses before transport; SQL-native row size/encoded bounds, UTF8/escaping and arbitrary driver block splits kept≤1MiB/1000, total32/16MiB |
| compact_default_readonly | Actual preflight counts0COPY/nextval and all source/target tables/sequences unchanged |
| wrong_control_component | Deliberate closed local fault corrupts a mapped generation FK; intended native23503 or exact phase oracle refuses and rolls back. Correct inverse map covers H2H and standing business snapshot contrast |
| corruption_phase_oracle | Valid changed string passes SQL type but independent whole phase oracle rejects before seal; rollback; no weaker equality/dedup |
| compact_mid_copy_rollback_gaps | Actual failure after two COPY batches rolls back phase, monotone sequences retain gaps; retry maps source generation/snapshot separately |
| compact_deadline_rollback | Native57014 before seal causes full phase rollback, no deadline raise |
| compact_control_receipt_corruption | Wrong receipt checksum/noncontiguous prefix refuses; restored exact receipt allows no-op; old clocks unchanged |
| compact_lost_commit_ack | Worker commits core then reports unknown acknowledgement; fresh worker independently classifies exact prefix and transports families only |
| closed_history_refusal | Legal compact retained correction creates closed interval; source acceptance recomputed but closed history explicitly refused; no reset/bypass of native guards |
| compact_exact_native_oracle | Independent frozen SQL-native oracle over94 relations,91 native source-coordinate rows plus3 exact control contracts;29-digit/fraction numeric and JSONB null/array/text/false/empty/Unicode exact |
| dense_fixture_once | One source construction only, exact478547 canonical scalars/15437 participants/31 metrics/612matches/one variant; no routine original013 dense8s replay |
| dense_core_commit_interruption | Actual worker exits after committed core; next worker verifies prefix and does not COPY core again |
| dense_families_rollback_and_resume | One small families fault, committed core intact; new process rehydrates exact maps/checkpoints and finishes families only |
| dense_native94_and_controls | Independent all94 native/control parity; IDs/runs preserved, control generation/snapshot mapping transitive, one source→one successful target generation, sequences safe |
| dense_noop_next_identity | Subsequent worker0COPY/nextval/new generation/clock updates; next ordinary native identity exceeds copied maximum |
| no_publish_source_or_legacy_cleanup | Legacy sentinel/typed publication pointers unchanged; no raw bodies/collector/provider/network/file dump/TEMP/extra business object/grant/index |
| frozen_inputs_and_owned_cleanup | Exact setup/command/inputs/acceptance/pair/plans/counters/errors/timings/buffers/metadata/sequence gaps, all owned clients/PG/temp removed; old design/v1/scaffold/policy/SQL/model hashes untouched |

Impossible malformed source states are not forged by disabling guards: native cycle/FK admission is tested with real rejected SQL; source ownership refusal uses valid unowned run/scope or over-bound metadata. The compiler must still independently reject missing/forward ownership. Fixtures and assertions must identify which gate actually rejected a case; a setup/native error does not count as the intended semantic pass.

The compact workflow may reset only its two explicitly owned fixture schemas before the single dense construction; no production reset path exists in the writer. Dense core is built/copied once. Subsequent dense reopens only hash/verify committed prefix and retry the small family phase, never silently reload the core. Source RR is per phase; accepted global/source-prefix hashes are computed before target BEGIN; source RO closes before target inverse oracle/seal/commit. Closed history remains refused.

Limits remain64phases/2Mrows/500k per relation;32MiB total metadata,16MiB total buffers,1MiB encoded row/batch,1000rows/batch;4096 self vertices/8192edges/8MiB graph/rank input≤1MiB;1M nextval/sequence,5M global, blocks10000;8s statements/1s locks and actual idle deadlines,8GiB ownedPG soft7/temp512MiB/backend/proof64MiB. No PG campaign is authorized yet. First future unexpected failure/limit stops with receipt+cleanup and ROOT brief, no second dense start.

Suggested commit: `perf: stream typed native phases within bounded memory`.
