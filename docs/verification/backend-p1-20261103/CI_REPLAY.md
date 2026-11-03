# Remote verification receipt

GitHub workflow `.github/workflows/verify-ingestion.yml` ran on `a4ade8c17b15157d88a4057cc42c9f9b064cbd08`: [run41733564574](https://github.com/OrionQuantPlatform/STATARENA/actions/runs/41733564574). Result: success. Ubuntu, Python3.13, disposable PostgreSQL16 service, dependencies from `dashboard/scripts/neon-requirements.txt`, eight existing daily-refresh tests and the actual daily/pulse SQL publication workflow. Expected/actual outcome: eight tests pass; MLS/Saudi goal0→1 publication retains season behavior. No production/provider writes. Full step/timing metadata is `ci.json`; exact executed commands and logs are `ci.log`.

Inspection commands:

```sh
gh run view 41733564574 --repo OrionQuantPlatform/STATARENA --json databaseId,status,conclusion,headSha,url,jobs
gh run view 41733564574 --repo OrionQuantPlatform/STATARENA --log
```

To replay the same workflow, dispatch `verify-ingestion.yml` with the branch/ref containing these changes; its workflow defines the setup, commands and expected service. The local actual-SQL equivalent is `STATARENA_SUMMARY_EVIDENCE=docs/verification/backend-p1-20261103/daily-replayed bun dashboard/scripts/verify_match_summary_materializer.mjs --daily` (PostgreSQL18 locally). The complete34 HTTP,8 materializer,18 SQL/S3 and11 browser checks are separate local evidence; the smaller existing GitHub workflow does not run those whole suites.

Vercel preview `dpl_2TdsMb4B5XQpuigEjay5G2MBHJZ4` is READY on the same source SHA. `preview.json` records build readiness, not a migrated production data model or live P1 performance. The subsequent delivery update modifies documentation/receipts only.

Suggested commit: `docs: record P1 branch publication and CI verification`.
