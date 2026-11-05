# Real source construction: partial core, failed spatial phase

Actual attempt: source-runs/20261105T111626302849Z/result.json,203.982s,600s allocation not exhausted. The ordinary ingest worker reached PostgreSQL57014 under unchanged8s SQL timeout. Its core transaction was already sealed/committed; the subsequent spatial phase rolled back. No RDS business write occurred. Do not describe this workflow as a success or as an empty source.

Independent recovery readback observes839players,612matches,478547native metric values,1core import run,2snapshots including B0; core generation2/snapshot2 sealed. Heatmaps0. These counts do not independently prove field fidelity. Native31,94-table and phase/control verification are still required before transport; the separate core-checkpoint workflow will perform them without rerunning construction. All raw data remains in the existing RAM capture; this local database contains typed facts only.

The launcher cleanup had an independent coding error: it passed `None` to the qualified helper's callable `stop_reason` argument. The narrow fix supplies a no-op callable for the bounded15s cleanup reserve. No new unit test or expensive construction replay is needed for this reversible argument correction. ROOT_CLEANUP_RECOVERY.json records the actual helper-driven pg_ctl stop (exit0), and the original cleanup failure remains in result.json.

The first manual recovery also made an incorrect zero-core assumption and stopped at its readonly count assertion. It made no write or cleanup action. A second readback retained the actual nonzero counts and stopped only the owned server. The typed root remains stopped temporarily for diagnosis and the minimum backend import. It has not been reported as deleted. The one-shot original allocation stays consumed and its release/inputs unchanged; the corrected script cannot replay that release.

Before/after: RDS typed business rows remain0. Local core now contains612matches/478547native values, with semantic fidelity not yet accepted in this attempt. Spatial accepted rows remain0. There is no measured latency gain;203.982s is a failed workflow observation, not a successful throughput benchmark. Prior historical15/15 real-source acceptance remains historical and does not erase this failure.

Hugo's latest priority keeps backend completion and Neon runtime removal first while the data branch continues. Recover and verify the committed core as minimum backend input; diagnose spatial timeout separately. Keep every source and all existing cloud resources until their final reconciliation.

Suggested commit: `fix: clean up failed real SQL source construction`.
