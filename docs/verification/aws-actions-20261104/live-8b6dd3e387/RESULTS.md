# Hosted Linux and RDS readiness on 8b6dd3e387

Both GitHub workflow runs completed successfully on codex/aws-backend-20261104 at 8b6dd3e387c670a384c8979d5fe6550527af694f. The Linux relational job took 42 seconds. Its sibling ingestion verification job took 69 seconds. The separate production readiness job took 51 seconds. [Linux CI run](https://github.com/OrionQuantPlatform/STATARENA/actions/runs/41761220307) · [RDS readiness run](https://github.com/OrionQuantPlatform/STATARENA/actions/runs/41761252181)

The downloaded CI receipts show 16/16 publisher workflows, 5/5 core SQL workflows, 10 core HTTP checks, 63 match detail requests, 65 catalog requests, and parity across 1,880 support keys. The bootstrap and security-group simulation passed 14/14 and 9/9. The role and runner worked with the checked-in workflow, so this verification yielded no CI code fixes.

The production job used batch=1, minutes=0.000001 and queue_all=false. It installed migrations 003–006, discovered 486 partition jobs and 36,228 catalog inputs, then observed its expired time budget. It published zero partitions, catalog inputs, support projections and assets. Pending work was 36,715 including the global pass. An independent reader using rds-runtime, verify-full TLS and an explicit read-only transaction confirmed 151 out of 151 application tables selectable, four migration receipts, zero published partitions and 486 queued partition jobs.

During the job, an independent read found one ManagedBy=statarena-actions rule owned by this run and attempt, with protocol TCP, port 5432 and an IPv4 /32. After completion the same security group had zero rules for this run. All preexisting unrelated rule IDs were unchanged.

The two run JSON files retain observed job/step statuses and timestamps. The three artifact descriptors retain the GitHub artifact ID, archive digest, file names, lengths, downloaded-file SHA-256 values and structured result counts. The production artifact's own counters, role observation and before/after group observations are separate JSON files in this directory.

To reinspect existing receipts without creating another run:

```sh
gh run view 41761220307 --json status,conclusion,headSha,jobs,url
gh run view 41761252181 --json status,conclusion,headSha,jobs,url
gh run download 41761220307 --dir /tmp/statarena-verify-41761220307
gh run download 41761252181 --dir /tmp/statarena-readiness-41761252181
```

Suggested commit: `docs: record hosted Linux CI and RDS publication readiness`
