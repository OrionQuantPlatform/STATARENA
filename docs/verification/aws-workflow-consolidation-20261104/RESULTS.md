# Workflow consolidation results

Two duplicate football collection definitions become one AWS collector with daily, pulse and historical modes; current workflow files6→5(−16.7%). Shared setup now exists once instead of twice. All six daily trigger times and their default budgets are preserved. Manual runs can bound requests/minutes and omit image collection. Supplemental UEFA collection only runs on schedule/manual events; source pushes run verification. All writers use the existing AWS OIDC/bootstrap/concurrency and main-only entrypoints. No provider-time or website-latency gain is claimed from YAML consolidation.

Six obsolete one-off diagnostic workflow records absent from main were disabled. Active GitHub records 10→4 before registration of the new collector. The old daily/history workflows had already been disabled and the legacy Neon backfill was cancelled. No run history or source data deleted; the friend's source transfer was not changed. Optional availability monitor stays disabled.

Verification registered in PROTOCOL.md before implementation. Actual Bash planner: 19/19 pass (after.json); retained before.json fails because the consolidated entrypoint was absent. Disposable real PostgreSQL18 plus signed loopback SSM bootstrap/monitor: 13/13 pass (../aws-actions-20261104/consolidated/results.json and postgres.log). Exact commands/setup/expected/actual are in those receipts. No unit tests were added. Hosted CI and bounded AWS collection readback remain pending until this commit is pushed. Full serving-table population/production cutover remain separate gates.

Main integration d2a98c0d0991 already pushed. Hosted Verify ingestion41803444099 passed. Vercel production readback after main remains READY at0aaf316e with unchanged deploymentID; production-after-main.json. The temporary scoped main deployment guard remains until full AWS acceptance.

Suggested commit: `refactor: consolidate AWS collection workflows by function`.
