# Post-adoption deployment availability

Rerun the existing complete public deployment E2E after RDS014. New control-plane reads bind both production aliases to the actual READY/production deployment74ea3f76de; do not replace that SHA with current Git main. Same13cases/12HTTP/2MiB/180s/10s per request: health+manifest GET200, manifest HEAD200/zero body/same ETag, conditional304/zero body on both Vercel aliases and AWS CloudFront. Save body hashes/headers/byte counts/timings only, no source bodies. No deployment/configuration/source/SQL mutation. This proves public availability and conditional responses only: Vercel's saved-Neon bridge and AWS's legacy manifest still differ; typedRDS cutover/full application parity remain unverified.

The copied E2E changes only its reported rerun command to its actual new path. All expectations and requests remain the previously qualified whole-workflow test. Suggested commit: `test: verify native RDS adoption and deployed availability`.
