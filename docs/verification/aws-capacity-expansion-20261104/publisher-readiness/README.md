# Readiness before the first bounded resume

The [read-only snapshot](before-resume.json) records the remote branch SHA, four writer definitions, all in-progress/queued/pending/waiting/requested jobs and the RDS publication state. It observed no AWS publisher advisory lease, 484 pending partition jobs, two published partitions and 189 published matches. The workflow’s wider remaining count was 36,709 at its previous checkpoint. The database occupied 11,250,128,575 bytes.

All four AWS writer jobs inherit the configurable SQL cap and share the non-cancelling `statarena-aws-ingestion` concurrency group. At observation the repository cap was 16,000,000,000 bytes. The old main Daily Sync had finished, and the one running Historical Backfill at main 01830e1f9b was in its provider collection step. Its workflow source uses the distinct `statarena-neon-ingestion` concurrency group and legacy storage settings. Secret targets were not inspected. [Historical run](main-backfill-job.json) · [Daily run](main-daily.json)

After the release owner confirms the actual allocated volume is 64 GiB, the proposed cap is **52,000,000,000 bytes**. With the materializer’s default reserve of 256,000,000 bytes, its effective database-size allowance is 51,744,000,000 bytes. The arithmetic difference from 64 GiB is 16,975,476,736 bytes. PostgreSQL WAL, temporary files, other databases and RDS overhead also consume capacity, so this difference is not a prediction of actual free filesystem bytes.

The first release-owner dispatch uses the already queued work, an eight-minute soft budget and ten partition jobs per selection. Each selected partition commits independently. A transaction can extend past the time budget. The batch size does not limit the run to ten completions. The workflow runs the relational publisher without provider collection.

```sh
gh workflow run rematerialize.yml -R OrionQuantPlatform/STATARENA --ref codex/aws-backend-20261104 -f queue_all=false -f minutes=8 -f batch=10
```

The readiness audit performed reads only. Its command is `PYTHONPATH=/tmp/statarena-archive-remat-pg/python python3 docs/verification/aws-capacity-expansion-20261104/publisher-readiness/readiness.py`; run to stdout or use a new timestamped filename for a later snapshot.
